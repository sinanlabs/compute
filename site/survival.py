# -*- coding: utf-8 -*-
"""站点存续测量：记录哪些站消失了、消失前有什么可测特征，按特征桶给出"同类站在 N 天内消失的比例"（历史基率）。
不预测、不指控；样本不足（<30）的桶不出数。写 site/survival.json；消失/恢复事件写 site_event 表并同步 relay_candidate.status。
定义：消失 = 连续 7 天、≥80 轮有效探测一次都没连上（与 export_data 的 DEAD 一致，且剔除我方故障轮次）。"""
import os, io, sys, json, sqlite3, datetime as dt, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8))
PREMIUM = {"com", "net", "org", "cn", "ai", "io", "dev", "app", "tech", "cloud", "co", "me"}
BUDGET = {"top", "cc", "xyz", "vip", "site", "online", "fun", "icu", "sbs", "cfd", "shop", "store", "live", "work", "club", "link", "pro", "run", "space", "website", "life", "world", "one", "lol", "asia", "buzz", "cyou", "us", "uk", "in", "de", "eu"}
def tld_group(d):
    t = d.rsplit(".", 1)[-1]
    return "premium" if t in PREMIUM else "budget" if t in BUDGET else "other"
def age_bucket(days):
    if days is None: return "unknown"
    return "<180d" if days < 180 else "180–730d" if days < 730 else ">730d"

def main():
    db = sqlite3.connect(os.path.join(ROOT, "data", "compass.sqlite")); db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS site_event(domain TEXT, event TEXT, at TEXT, PRIMARY KEY(domain, event, at))")
    for col in ("died_at TEXT",):
        try: db.execute("ALTER TABLE relay_candidate ADD COLUMN " + col)
        except sqlite3.OperationalError: pass
    now = dt.datetime.now(BJ); today = now.date()
    # 可达：剔除我方故障轮次
    bad = set(r["h"] for r in db.execute("SELECT substr(window_from,1,13) h, AVG(p50) up FROM metric_ts WHERE metric='availability' AND window_from >= datetime('now','-168 hours') GROUP BY h HAVING COUNT(*) >= 50 AND up < 0.5"))
    up = {}
    for r in db.execute("SELECT entity, p50, window_from FROM metric_ts WHERE metric='availability' AND window_from >= datetime('now','-168 hours') ORDER BY window_from"):
        if r["window_from"][:13] in bad: continue
        up.setdefault(r["entity"], []).append((r["window_from"][:10], r["p50"]))
    def uptime(v): return round(100.0 * sum(x[1] for x in v) / len(v), 1) if v else None
    def trend(v):
        if len(v) < 48: return None
        d3 = (today - dt.timedelta(days=3)).isoformat(); a = [x for x in v if x[0] >= d3]; b = [x for x in v if x[0] < d3]
        return round(uptime(a) - uptime(b), 1) if a and b else None
    dead_now = {e for e, v in up.items() if len(v) >= 80 and uptime(v) == 0}
    # 事件：消失 / 恢复
    prev_dead = {r["domain"] for r in db.execute("SELECT domain FROM relay_candidate WHERE level>=1 AND status='dead'")}
    for d in dead_now - prev_dead:
        db.execute("INSERT OR IGNORE INTO site_event VALUES(?,?,?)", (d, "dead", today.isoformat())); db.execute("UPDATE relay_candidate SET status='dead', died_at=COALESCE(died_at, ?) WHERE domain=? AND status IN ('alive','dead')", (today.isoformat(), d))
    for d in prev_dead - dead_now:
        if d in up: db.execute("INSERT OR IGNORE INTO site_event VALUES(?,?,?)", (d, "revived", today.isoformat())); db.execute("UPDATE relay_candidate SET status='alive' WHERE domain=?", (d,))
    db.commit()
    # 价格变动 7 天
    pc = {r[0]: r[1] for r in db.execute("SELECT vendor, COUNT(*) FROM offer_norm WHERE vendor_kind='relay' AND superseded_by IS NOT NULL AND valid_to >= date('now','-7 days') GROUP BY vendor")}
    # 每站特征
    sites = {}
    for r in db.execute("SELECT domain, first_seen_at, panel_kind, icp, register_state, status, domain_created, first_cert, died_at FROM relay_candidate WHERE level>=1"):
        created = r["domain_created"] or r["first_cert"]
        age = (today - dt.date.fromisoformat(created)).days if created else None
        v = up.get(r["domain"], [])
        fam = "sub2api" if r["panel_kind"] == "sub2api" else "one-api" if (r["panel_kind"] or "").find("api") >= 0 else "other"
        sites[r["domain"]] = {"first_seen": r["first_seen_at"][:10], "observed_days": (today - dt.date.fromisoformat(r["first_seen_at"][:10])).days, "created": created, "age_src": "rdap" if r["domain_created"] else ("crt" if r["first_cert"] else None), "age_days": age, "age_bucket": age_bucket(age),
                              "tld": tld_group(r["domain"]), "icp": (bool(r["icp"]) if r["icp"] is not None else None), "register": r["register_state"] or "unknown", "family": fam, "uptime7": uptime(v), "trend3d": trend(v), "price_changes7": pc.get(r["domain"], 0), "dead": r["domain"] in dead_now or r["status"] == "dead", "died_at": r["died_at"]}
    # 基率：观察满 N 天的站里，消失的比例；按特征桶
    dims = {"tld": lambda s_: s_["tld"], "register": lambda s_: s_["register"], "family": lambda s_: s_["family"], "age": lambda s_: s_["age_bucket"], "uptime": lambda s_: ("≥99%" if s_["uptime7"] >= 99 else "<99%") if s_["uptime7"] is not None else "unknown"}
    if any(s_["icp"] is not None for s_ in sites.values()): dims["icp"] = lambda s_: "有备案" if s_["icp"] else "无备案"
    windows = {}
    for N in (7, 14, 30, 90):
        cohort = [s_ for s_ in sites.values() if s_["observed_days"] >= N]
        if len(cohort) < 30: windows[str(N)] = None; continue
        def rate(xs): return {"n": len(xs), "dead": sum(1 for x in xs if x["dead"]), "rate": round(sum(1 for x in xs if x["dead"]) / len(xs), 4)} if len(xs) >= 30 else None
        buckets = {}
        for dim, f in dims.items():
            groups = {}
            for s_ in cohort: groups.setdefault(f(s_), []).append(s_)
            buckets[dim] = {k: rate(v) for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))}
        windows[str(N)] = {"overall": rate(cohort), "buckets": buckets}
    events = [dict(r) for r in db.execute("SELECT domain, event, at FROM site_event ORDER BY at DESC, domain LIMIT 200")]
    month0 = today.replace(day=1).isoformat()
    churn = {"month": today.strftime("%Y-%m"), "dead_this_month": sum(1 for e in events if e["event"] == "dead" and e["at"] >= month0), "revived_this_month": sum(1 for e in events if e["event"] == "revived" and e["at"] >= month0), "sites": len(sites)}
    out = {"generated_at": now.isoformat()[:19], "definition": "消失 = 连续 7 天、≥80 轮有效探测一次都没连上（剔除我方故障轮次）。比例 = 观察满 N 天的站里已消失的份额，只是历史基率，不是对任何站的预测。", "age_coverage": sum(1 for s_ in sites.values() if s_["created"]), "windows": windows, "events": events, "churn": churn, "sites": sites}
    io.open(os.path.join(HERE, "survival.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    w14 = windows.get("14") or {}
    print("存续：站 %d · 有站龄 %d · 当前消失 %d · 本月新消失 %d · 14 天基率 %s" % (len(sites), out["age_coverage"], len(dead_now), churn["dead_this_month"], (w14.get("overall") or {}).get("rate") if w14 else "样本不足"))
if __name__ == "__main__": main()
