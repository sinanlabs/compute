# -*- coding: utf-8 -*-
"""中国模型 API 中转市场月报（自动生成，每天重算当月，月底定稿）。数据全部来自站内已有产物：
weekly/*.json（逐日规模）、price_index.json（Token 价格指数）、data_v2.json（可达/检测/榜单）、media.json、gpu.json、relay_candidate（收录/退场/面板/注册）、quality_hold。
写 site/reports/<YYYY-MM>.json。第一期从 2026-09-02（数据起点）算。"""
import os, io, sys, json, glob, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
HERE = os.path.dirname(os.path.abspath(__file__)); BJ = dt.timezone(dt.timedelta(hours=8))
def J(p): return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None

DOMESTIC = {"deepseek", "alibaba", "qwen", "zhipu", "moonshot", "minimax", "bytedance", "baidu", "tencent", "stepfun", "xiaomi", "01ai", "sensetime", "iflytek"}
def is_domestic(vendor): return (vendor or "").lower() in DOMESTIC

def structure_block(Dv, PI, M, G, changes):
    """结构性发现（每期自动重算，给分析当脚手架）：国产/海外折价、分档区间分布、充值比例分布、15% 惯例、面板家族、登录生态、TLD、变价方向、多模态族比率、开源模型算力下限。"""
    from collections import Counter, defaultdict
    out = {}
    # 1. 国产 / 海外
    rows = []
    for mid, m in (PI.get("models") or {}).items():
        t = m["series"][-1]
        rows.append({"id": mid, "name": m["name"], "vendor": m["vendor"], "tier": m["tier"], "official": m["floor"], "median": t["median"], "ratio": t["ratio"], "n": t["n"], "domestic": is_domestic(m["vendor"])})
    rows.sort(key=lambda r: r["ratio"])
    dom = [r["ratio"] for r in rows if r["domestic"]]; frn = [r["ratio"] for r in rows if not r["domestic"]]
    out["origin"] = {"rows": rows, "domestic_median": st.median(dom) if dom else None, "foreign_median": st.median(frn) if frn else None, "n_domestic": len(dom), "n_foreign": len(frn)}
    # 2. 分档区间分布
    tier_of = {mid: m["tier"] for mid, m in (PI.get("models") or {}).items()}
    bands = defaultdict(Counter)
    for m in Dv.get("models", []):
        t = tier_of.get(m["id"])
        if not t: continue
        for r in m.get("rows", []):
            if r.get("band"): bands[t][r["band"]] += 1
    out["bands_by_tier"] = {t: {"n": sum(c.values()), "share": {k: round(v / sum(c.values()), 3) for k, v in c.items()}} for t, c in bands.items()}
    # 3. 充值比例（每站众数）与 15% 惯例
    pf = Counter()
    for m in Dv.get("models", []):
        for r in m.get("rows", []):
            if r.get("price_field") is not None: pf[(r["vendor"], round(r["price_field"], 2))] += 1
    site_pf = {}
    for (v, p_), n in pf.items():
        if v not in site_pf or n > site_pf[v][1]: site_pf[v] = (p_, n)
    dist = Counter(p_ for p_, _ in site_pf.values())
    flag = [m for m in Dv.get("models", []) if tier_of.get(m["id"]) in ("flagship", "mid") and not is_domestic(m.get("vendor"))]
    sellers, at15 = set(), set()
    for m in flag:
        for r in m.get("rows", []):
            sellers.add(r["vendor"])
            if r.get("ratio") and 0.14 <= r["ratio"] <= 0.155: at15.add(r["vendor"])
    out["topup"] = {"sites": len(site_pf), "dist": sorted(dist.items(), key=lambda kv: -kv[1])[:10], "at_par_1cny": dist.get(1.0, 0), "near_usd_par": sum(v for k, v in dist.items() if 6.5 <= k <= 7.5), "deep_discount": sum(v for k, v in dist.items() if k < 0.6), "foreign_sellers": len(sellers), "foreign_sellers_at_15": len(at15)}
    # 4. 面板家族
    fam = defaultdict(list)
    for s_ in Dv.get("sites", []): fam[s_.get("panel") or "unknown"].append(s_)
    def reg(s_):
        r = s_.get("register"); return (r.get("state") if isinstance(r, dict) else r) or "unknown"
    out["panels"] = [{"panel": k, "n": len(v), "open": sum(1 for x in v if reg(x) == "open"), "closed": sum(1 for x in v if reg(x) == "closed"), "unknown": sum(1 for x in v if reg(x) == "unknown"), "with_quotes": sum(1 for x in v if x.get("median")), "median_ratio": (st.median([x["median"] for x in v if x.get("median")]) if any(x.get("median") for x in v) else None)} for k, v in sorted(fam.items(), key=lambda kv: -len(kv[1]))]
    # 5. 登录生态
    login = defaultdict(Counter)
    for s_ in Dv.get("sites", []):
        grp = "sub2api" if s_.get("panel") == "sub2api" else "one-api"
        for l in ((s_.get("facts") or {}).get("login") or []): login[grp][l] += 1
    out["logins"] = {k: dict(v) for k, v in login.items()}
    # 6. TLD
    tld = Counter(s_["domain"].rsplit(".", 1)[-1] for s_ in Dv.get("sites", []))
    out["tld"] = tld.most_common(10)
    # 7. 变价方向 × 国产/海外
    dirs = Counter()
    for c in changes:
        m = (PI.get("models") or {}).get(c["model"])
        if not m: continue
        dirs[("domestic" if is_domestic(m["vendor"]) else "foreign") + ":" + ("up" if c["new"] > c["old"] else "down")] += 1
    out["change_dirs"] = dict(dirs)
    # 8. 多模态：族中位 ÷ 参考
    med = {}
    for mod in ("video", "image"):
        med[mod] = [{"family": f["family"], "name": f.get("name"), "sites": f.get("n_sites"), "cmp": f.get("n_cmp"), "ref": (f.get("ref") or {}).get("price"), "eff_med": f.get("eff_med"), "ratio": (f["eff_med"] / f["ref"]["price"]) if f.get("eff_med") and (f.get("ref") or {}).get("price") else None, "bands": f.get("bands"), "domestic": any(k in (f.get("name") or "") for k in ("阿里", "字节", "快手", "生数", "MiniMax", "智谱"))} for f in M.get(mod, []) if f.get("ref")]
    out["media"] = med
    # 9. 开源模型算力下限（METHOD §13 假设：H100 3000 tok/s，4090 800 tok/s）
    gp = {g["gpu"]: next((x["usd"] for x in g["quotes"] if x["platform"] == "vast" and x["kind"] == "median"), None) for g in G.get("gpus", [])}
    h100, r4090 = gp.get("H100 SXM"), gp.get("RTX 4090")
    floors = {"h100_per_m": (h100 / (3000 * 3600 / 1e6)) if h100 else None, "rtx4090_per_m": (r4090 / (800 * 3600 / 1e6)) if r4090 else None, "h100_hour": h100, "rtx4090_hour": r4090}
    floors["open_models"] = [{"id": r["id"], "name": r["name"], "official": r["official"], "median": r["median"], "ratio": r["ratio"], "below_h100_floor": (r["official"] < floors["h100_per_m"]) if floors["h100_per_m"] else None} for r in rows if r["domestic"]]
    out["cost_floor"] = floors
    return out

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
    Dv = J(os.path.join(HERE, "data_v2.json")) or J(os.path.join(HERE, "dist", "data_v2.json")) or {}   # 先读刚导出的，dist 里是上次构建的旧副本
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
           "media": media, "gpu": gpu, "structure": structure_block(Dv, PI, M, G, changes)}
    os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
    io.open(os.path.join(HERE, "reports", month + ".json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    print("月报 %s：%s→%s · 站 %s→%s（新增 %d）· 主流变价 %d（涨 %d 降 %d）· 全库变价 %d · 指数 %s→%s" % (month, start, end, first.get("confirmed"), last.get("confirmed"), new_sites, len(changes), ups, downs, all_changes,
          ("%d%%" % round(idx["first"]["all"]["ratio"] * 100)) if idx["first"] else "—", ("%d%%" % round(idx["last"]["all"]["ratio"] * 100)) if idx["last"] else "—"))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
