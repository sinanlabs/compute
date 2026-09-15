# -*- coding: utf-8 -*-
"""中国模型 API 中转市场月报（自动生成，每天重算当月，月底定稿）。数据全部来自站内已有产物：
weekly/*.json（逐日规模）、price_index.json（Token 价格指数）、data_v2.json（可达/检测/榜单）、media.json、gpu.json、relay_candidate（收录/退场/面板/注册）、quality_hold。
写 site/reports/<YYYY-MM>.json。第一期从 2026-09-02（数据起点）算。"""
import os, io, sys, json, glob, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
HERE = os.path.dirname(os.path.abspath(__file__)); BJ = dt.timezone(dt.timedelta(hours=8))
def J(p): return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None

def main(month=None):
    today = dt.datetime.now(BJ).date(); month = month or today.strftime("%Y-%m")
    y, m = map(int, month.split("-")); m0 = dt.date(y, m, 1); m1 = (dt.date(y + (m // 12), m % 12 + 1, 1) - dt.timedelta(days=1))
    end = min(m1, today); start = max(m0, dt.date(2026, 9, 2))
    db = D.connect()
    # 逐日规模
    days = {}
    for f in glob.glob(os.path.join(HERE, "weekly", "*.json")):
        for d_, v in (J(f) or {}).get("days", {}).items():
            if start.isoformat() <= d_ <= end.isoformat(): days[d_] = v
    ds = sorted(days); first, last = (days[ds[0]], days[ds[-1]]) if ds else ({}, {})
    # 收录 / 退场 / 面板 / 注册
    q = lambda sql, *a: db.execute(sql, a).fetchone()[0]
    new_sites = q("SELECT COUNT(*) FROM relay_candidate WHERE level>=1 AND first_seen_at>=? AND first_seen_at<?", start.isoformat(), (end + dt.timedelta(days=1)).isoformat())
    by_channel = {r[0] or "?": r[1] for r in db.execute("SELECT first_channel, COUNT(*) FROM relay_candidate WHERE level>=1 AND first_seen_at>=? AND first_seen_at<? GROUP BY 1 ORDER BY 2 DESC", (start.isoformat(), (end + dt.timedelta(days=1)).isoformat()))}
    panels = {r[0] or "?": r[1] for r in db.execute("SELECT panel_kind, COUNT(*) FROM relay_candidate WHERE level>=1 GROUP BY 1 ORDER BY 2 DESC")}
    reg = {r[0] or "unknown": r[1] for r in db.execute("SELECT register_state, COUNT(*) FROM relay_candidate WHERE level>=1 GROUP BY 1")}
    tools = q("SELECT COUNT(*) FROM relay_candidate WHERE status='tool'"); official = q("SELECT COUNT(*) FROM relay_candidate WHERE status='official'")
    # 变价（主流模型，来自周报）
    changes = []
    for f in glob.glob(os.path.join(HERE, "weekly", "*.json")):
        for c in (J(f) or {}).get("changes", []):
            if start.isoformat() <= c["t"][:10] <= end.isoformat(): changes.append(c)
    ups = sum(1 for c in changes if c["new"] > c["old"]); downs = len(changes) - ups
    # 全库变价行数（含非主流）
    all_changes = q("SELECT COUNT(*) FROM offer_norm WHERE vendor_kind='relay' AND unit='per_mtok_out' AND superseded_by IS NOT NULL AND valid_to>=? AND valid_to<?", start.isoformat(), (end + dt.timedelta(days=1)).isoformat())
    # 指数
    PI = J(os.path.join(HERE, "price_index.json")) or {}; ser = [x for x in PI.get("series", []) if start.isoformat() <= x["date"] <= end.isoformat()]
    idx = {"first": ser[0] if ser else None, "last": ser[-1] if ser else None, "series": ser}
    movers = []
    for mid, mm in (PI.get("models") or {}).items():
        s_ = [x for x in mm["series"] if start.isoformat() <= x["date"] <= end.isoformat()]
        if len(s_) >= 2 and s_[0]["median"]:
            movers.append({"id": mid, "name": mm["name"], "tier": mm["tier"], "from": s_[0]["median"], "to": s_[-1]["median"], "pct": (s_[-1]["median"] / s_[0]["median"] - 1) * 100, "n": s_[-1]["n"], "ratio": s_[-1]["ratio"]})
    movers.sort(key=lambda x: x["pct"])
    # 可达 / 检测 / 榜单
    Dv = J(os.path.join(HERE, "dist", "data_v2.json")) or J(os.path.join(HERE, "data_v2.json")) or {}
    stt = Dv.get("stats", {}); R = Dv.get("rank", {})
    holds = {r[0]: r[1] for r in db.execute("SELECT reason, COUNT(*) FROM quality_hold WHERE cleared IS NULL GROUP BY 1")}
    cleared = q("SELECT COUNT(*) FROM quality_hold WHERE cleared IS NOT NULL AND cleared>=?", start.isoformat())
    M = J(os.path.join(HERE, "media.json")) or {}
    media = {mod: [{"family": f["family"], "name": f.get("name"), "sites": f.get("n_sites"), "rows": len(f.get("rows", [])), "cmp": sum(1 for r in f["rows"] if r.get("ratio") is not None and not r.get("held")), "ref": (f.get("ref") or {}).get("price")} for f in M.get(mod, [])] for mod in ("video", "image")}
    G = J(os.path.join(HERE, "gpu.json")) or {}
    gpu = [{"gpu": g["gpu"], "vram": g["vram_gb"], "vast_median": next((x["usd"] for x in g["quotes"] if x["platform"] == "vast" and x["kind"] == "median"), None), "runpod_secure": next((x["usd"] for x in g["quotes"] if x["platform"] == "runpod" and x["kind"] == "secure"), None)} for g in G.get("gpus", [])]
    out = {"month": month, "period": [start.isoformat(), end.isoformat()], "generated_at": D.now8(), "final": end == m1 and today > m1,
           "scale": {"days": days, "first": first, "last": last, "confirmed_now": q("SELECT COUNT(*) FROM relay_candidate WHERE level>=1"), "new_sites": new_sites, "by_channel": by_channel, "panels": panels, "register": reg, "tools_excluded": tools, "official_excluded": official,
                     "dead": (R.get("dead") or 0)},
           "prices": {"mainstream_changes": len(changes), "ups": ups, "downs": downs, "all_changes": all_changes, "index": idx, "movers_down": movers[:8], "movers_up": movers[-8:][::-1], "clusters_first": first.get("clusters"), "clusters_last": last.get("clusters")},
           "reach": {"eligible": R.get("eligible_uptime"), "dist": R.get("dist_up"), "fast": (R.get("fast") or [])[:5], "low": (R.get("low") or [])[:5]},
           "probes": {"pairs": stt.get("probed_pairs"), "consistent": stt.get("probe_consistent"), "divergent": stt.get("probe_divergent"), "cap_pairs": stt.get("cap_pairs"), "cap_below": stt.get("cap_below"), "probed_sites": stt.get("probed_sites")},
           "audit": {"open_by_reason": holds, "cleared_this_month": cleared},
           "boards": {"price": (R.get("price") or [])[:5], "dual": (R.get("dual") or [])[:5], "coverage": (R.get("coverage") or [])[:5], "media_price": ((R.get("media") or {}).get("price") or [])[:5], "media_video": [{"family": f["family"], "name": f["name"], "top": f["rows"][:3]} for f in ((R.get("media") or {}).get("video") or [])]},
           "media": media, "gpu": gpu}
    os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
    io.open(os.path.join(HERE, "reports", month + ".json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    print("月报 %s：%s→%s · 站 %s→%s（新增 %d）· 主流变价 %d（涨 %d 降 %d）· 全库变价 %d · 指数 %s→%s" % (month, start, end, first.get("confirmed"), last.get("confirmed"), new_sites, len(changes), ups, downs, all_changes,
          ("%d%%" % round(idx["first"]["all"]["ratio"] * 100)) if idx["first"] else "—", ("%d%%" % round(idx["last"]["all"]["ratio"] * 100)) if idx["last"] else "—"))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
