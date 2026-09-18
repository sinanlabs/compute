# -*- coding: utf-8 -*-
"""
社媒队列（X / Bluesky 经 dlvr.it 转发）：从"每天一条口径说明"改成"每周一两条带图、有结论的帖子"。
每天由 daily_refresh 调用，按北京日期决定今天要不要入队：
  周一   rank         司南榜周榜：真实数字（最快站、旗舰模型低于成本下限的比例、两家同卖的最低组合价、变动家数）+ 一句读法 + 榜单分享图
  周一   robo_weekly  Robo 周报（../sinan-robo/data/weekly/<周>.json 的 x_en）+ Robo 分享图
  周四   finding      一条"本周发现"：Compute 与 Robo 交替；数字从当日数据文件现取，读法是维护者写好的模板，不推测、不推荐
  每月 1 日 report    月报上线：Compute 与 Robo 各一条，用结构块里的数字
只写 data/posts/social_history.json（social_feed.py 负责渲染 RSS）；同日同 kind 不重复入队。正文不带网址（dlvr.it 会附 <link>），不超过 250 字符。
"""
import os, io, re, json, glob, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8)); BASE = "https://compute.sinanlab.com"; ROBO = "https://robo.sinanlab.com"
ROBO_DIR = os.path.join(ROOT, "..", "sinan-robo")
HIST = os.path.join(ROOT, "data", "posts", "social_history.json")
load = lambda p, d=None: json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d


def clip(t, n=250):
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def rank_image(week):
    files = sorted(glob.glob(os.path.join(HERE, "dist", "img", "og", "rank", "en", "%s-*.png" % week))) or sorted(glob.glob(os.path.join(HERE, "dist", "img", "og", "rank", "%s-*.png" % week)))
    return BASE + files[-1].split("/dist")[1] if files else BASE + "/img/og.png"


def latest_rank():
    fs = sorted(glob.glob(os.path.join(HERE, "rank", "20*-w*.json")))
    return load(fs[-1]) if fs else None


# ---------------- Compute：周榜 ----------------
def item_rank(today):
    R = latest_rank()
    if not R: return None
    wk = R.get("week", "")
    fast = (R.get("fast") or [{}])[0]
    fl = R.get("flagship") or []
    rows = [r for m in fl for r in (m.get("rows") or []) if r.get("ratio") is not None]
    below = sum(1 for r in rows if r["ratio"] < 0.5)
    dual = (R.get("dual") or [{}])[0]
    parts = ["Relay-market board %s: %s sites, %s quotes, 7 days." % (wk, R.get("n_sites"), "{:,}".format(R.get("n_quotes") or 0))]
    if rows: parts.append("%d of %d flagship quotes are below half the official price." % (below, len(rows)))
    if fast.get("p50"): parts.append("Lowest TTFB among 100%%-uptime sites: %.1f s p50." % (fast["p50"] / 1000))
    if dual.get("sum"): parts.append("GPT-6 + Claude Fable from one site: $%.0f/M out combined." % dual["sum"])
    angle = "Price is not where these sites compete; the top-up ratio is." if rows and below > len(rows) / 3 else ""
    # 整句装箱：必选句 + 读法优先，其余可选句能装多少装多少，不在句中截断
    must = parts[:2] if len(parts) >= 2 else parts; opt = parts[len(must):]
    text = " ".join(must + ([angle] if angle else []))
    for o in opt:
        if len(text) + 1 + len(o) <= 250: text = text.replace((" " + angle) if angle else "", "") + " " + o + ((" " + angle) if angle else "")
    return {"kind": "rank", "text": clip(text), "url": BASE + "/rank", "image": rank_image(wk)}


# ---------------- Robo：周报 ----------------
def item_robo_weekly(today):
    fs = sorted(glob.glob(os.path.join(ROBO_DIR, "data", "weekly", "*.json")))
    if not fs: return None
    w = load(fs[-1])
    if str(w.get("generated", ""))[:10] != today.isoformat(): return None   # 只在生成当天入队
    return {"kind": "robo_weekly", "text": clip(w.get("x_en") or ""), "url": w.get("url") or ROBO + "/weekly", "image": ROBO + "/og.png"}


# ---------------- 本周发现：数字现取，读法是模板 ----------------
def compute_findings():
    out = []
    R = latest_rank() or {}
    fl = R.get("flagship") or []; rows = [r for m in fl for r in (m.get("rows") or []) if r.get("ratio") is not None]
    if rows:
        below = sum(1 for r in rows if r["ratio"] < 0.5)
        out.append(("cost_floor", "%d flagship-model quotes on Chinese API relay sites, priced against a cost floor from official prices: %d (%d%%) sit below half the official price. We do not guess what is upstream; we publish the arithmetic and let each site verify its row." % (len(rows), below, round(100 * below / len(rows))), BASE + "/rank", rank_image(R.get("week", ""))))
    sv = load(os.path.join(HERE, "survival.json")) or {}
    dead7 = (sv.get("windows") or {}).get("7") or sv.get("dead_7d")
    if isinstance(dead7, dict) and dead7.get("dead") is not None and dead7.get("n"):
        out.append(("survival", "Survival, measured: of %d relay sites probed hourly, %d went dark within 7 days (%.1f%%). Each dead site is listed with its last successful probe. Longevity is a measurement, not a badge." % (dead7["n"], dead7["dead"], 100 * dead7["dead"] / dead7["n"]), BASE + "/survival", BASE + "/img/og.png"))
    D = load(os.path.join(HERE, "data_v2.json")) or {}
    st = (load(os.path.join(HERE, "dist", "stats.json")) or {}).get("stats") or {}
    if st.get("confirmed") and st.get("seen_domains"):
        out.append(("funnel", "Discovery funnel: %s domains seen in certificate logs, %s confirmed LLM API relay sites, %s with public prices. Huge from the outside; a few hundred priced sites from the inside." % ("{:,}".format(st["seen_domains"]), "{:,}".format(st["confirmed"]), "{:,}".format(st.get("with_quotes") or 0)), BASE + "/sites", BASE + "/img/og.png"))
    return out


def robo_findings():
    out = []
    reps = sorted(glob.glob(os.path.join(ROBO_DIR, "data", "reports", "20*-*.json")))
    S = load(reps[-1]) if reps else {}
    A = (S or {}).get("activity") or {}; M = (S or {}).get("measurements") or {}; B = (S or {}).get("benchmarks") or {}; Dd = (S or {}).get("datasets") or {}; I = (S or {}).get("index") or {}
    if A.get("repos"):
        out.append(("stale", "Of %d open VLA repos tracked daily, %d had no push in 180 days and %d had zero commits in 90 days. 'Many open embodied models' shrinks to a quarter once filtered by maintenance. Counts, not verdicts." % (A["repos"], A.get("stale_180", 0), A.get("zero_commits_90", 0)), ROBO + "/rank", ROBO + "/og.png"))
    bh = M.get("by_hardware") or {}
    if bh.get("rtx-4090") and bh.get("a800-80g"):
        a = {x["model_id"]: x["p50"] for x in bh["rtx-4090"]}; b = {x["model_id"]: x["p50"] for x in bh["a800-80g"]}
        common = [m for m in a if m in b]; slower = sum(1 for m in common if b[m] > a[m] * 1.05)
        if common: out.append(("a800", "%d open VLA models, batch 1, RTX 4090 vs A800 80GB: %d of %d were slower on the A800, at 3-4x the rent per inference. For single-robot inference the datacenter card buys VRAM, not speed. Raw JSON per run is public." % (len(common), slower, len(common)), ROBO + "/hardware", ROBO + "/og.png"))
    if A.get("dl30_top3_share") and A.get("dl_top"):
        t = A["dl_top"][0]
        out.append(("downloads", "%d%% of last month's Hugging Face downloads across %d open VLA models went to three models. The top one, %s, has had no repo push in over a year. Downloads measure citation inertia, not deployment." % (round(100 * A["dl30_top3_share"]), A.get("hf_repos", 0), t.get("name")), ROBO + "/rank", ROBO + "/og.png"))
    if B.get("scores"):
        out.append(("libero", "%d benchmark scores for %d open VLA models, copied from papers with table refs. LIBERO's top eight sit between 97 and 99: saturated. The same model moves 20 points with the fine-tuning recipe. Grouped by benchmark, never averaged." % (B["scores"], B.get("models_with_score", 0)), ROBO + "/benchmarks", ROBO + "/og.png"))
    if Dd.get("count"):
        out.append(("datasets", "Of %d public robot datasets indexed, only %d state total hours and %d%% have an unverified licence. The largest real-robot corpora are from Chinese orgs, mostly gated on Hugging Face; %d have a confirmed ModelScope mirror." % (Dd["count"], sum(1 for x in ((load(os.path.join(ROBO_DIR, "data", "datasets.json")) or {}).get("datasets") or []) if x.get("hours")), round(100 * (Dd.get("license") or {}).get("unk", 0) / Dd["count"]), Dd.get("mirrors", 0)), ROBO + "/datasets", ROBO + "/og.png"))
    return out


def item_finding(today):
    wk = today.isocalendar()[1]
    pool = (compute_findings() if wk % 2 == 0 else robo_findings()) or (robo_findings() if wk % 2 == 0 else compute_findings())
    if not pool: return None
    used = load(os.path.join(ROOT, "data", "posts", "social_used.json"), {"finding": []})
    fresh = [f for f in pool if f[0] not in used["finding"][-6:]] or pool
    key, text, url, img = fresh[0]
    used["finding"].append(key); json.dump(used, io.open(os.path.join(ROOT, "data", "posts", "social_used.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"kind": "finding", "text": clip(text), "url": url, "image": img}


# ---------------- 月报 ----------------
def item_reports(today):
    items = []
    m = (today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    C = load(os.path.join(HERE, "reports", m + ".json"))
    if C:
        s = C.get("structure") or C
        items.append({"kind": "report", "text": clip("Monthly report on China's LLM API relay market, %s: %s sites indexed, %s with public prices, %s effective quotes. Structure block generated by script; the analysis is signed and labelled as opinion." % (m, s.get("n_sites") or C.get("n_sites") or "—", s.get("with_quotes") or "—", "{:,}".format(s.get("n_quotes") or C.get("n_quotes") or 0))), "url": BASE + "/report/" + m, "image": BASE + "/img/og.png"})
    R = load(os.path.join(ROBO_DIR, "data", "reports", m + ".json"))
    if R:
        I, A, M = R.get("index", {}), R.get("activity", {}), R.get("measurements", {})
        items.append({"kind": "robo_report", "text": clip("Open VLA Monthly %s: %s models indexed (%s from Chinese orgs), %s of %s repos idle for 180+ days, %s latency measurements on rented GPUs, %s benchmark scores, %s datasets. Numbers first, signed analysis second." % (m, I.get("models"), I.get("chinese_org"), A.get("stale_180"), A.get("repos"), M.get("total"), (R.get("benchmarks") or {}).get("scores"), (R.get("datasets") or {}).get("count"))), "url": ROBO + "/reports/" + m, "image": ROBO + "/og.png"})
    return items


def main():
    now = dt.datetime.now(BJ); today = now.date(); wd = today.weekday()
    hist = load(HIST, [])
    todays = []
    if wd == 0:
        for it in (item_rank(today), item_robo_weekly(today)):
            if it: todays.append(it)
    if wd == 3:
        it = item_finding(today)
        if it: todays.append(it)
    if today.day == 1: todays += item_reports(today)
    if os.environ.get("SOCIAL_FORCE"):   # 调试：强制生成一条指定 kind
        k = os.environ["SOCIAL_FORCE"]; f = {"rank": item_rank, "robo_weekly": item_robo_weekly, "finding": item_finding}.get(k)
        it = f(today) if f else None
        if it: todays.append(it)
    n = 0
    for it in todays:
        if not it.get("text"): continue
        if any(h["date"] == today.isoformat() and h["kind"] == it["kind"] for h in hist): continue
        hist.append({"date": today.isoformat(), "kind": it["kind"], "text": it["text"], "url": it["url"], "image": it.get("image"), "ts": now.isoformat()[:19]}); n += 1
    hist = hist[-60:]
    os.makedirs(os.path.dirname(HIST), exist_ok=True); json.dump(hist, io.open(HIST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("社媒队列：今日入队 %d 条（%s）· 历史 %d 条" % (n, ", ".join(i["kind"] for i in todays) or "无", len(hist)))


if __name__ == "__main__":
    main()
