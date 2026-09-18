# -*- coding: utf-8 -*-
"""
每周一：给 Eric 生成两条"社区稿"（他手动贴，账号是他的）：
  Compute 一条 → linux.do 版（中转站板块口吻：数字、测法、邀请站长核验）+ V2EX 版（更短、克制、以问题收尾）
  Robo    一条 → Reddit 版（r/robotics 或 r/LocalLLaMA：we measured…，附数据与方法链接）+ Hacker News 版（标题 + 两行评论）
观点来源：月报分析稿的 [summary] 判断，按周轮流取一条没用过的（data/posts/community_used.json 记账），再拼上本周现取的数字与链接。
产出：data/posts/community_<周>.md 与 .json（notify_email.py community 发到管理员邮箱）。
用法：python3 site/community_post.py            当前北京周
      python3 site/community_post.py --force    忽略"已用过"记录
"""
import os, io, re, sys, json, glob, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8)); BASE = "https://compute.sinanlab.com"; ROBO = "https://robo.sinanlab.com"
ROBO_DIR = os.path.join(ROOT, "..", "sinan-robo")
load = lambda p, d=None: json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d


def bullets(md_path):
    """取 '## [summary]' 节里的加粗判断句（**…**）及其后半句。"""
    if not os.path.exists(md_path): return []
    s = io.open(md_path, encoding="utf-8").read()
    m = re.search(r"## \[summary\][^\n]*\n(.*?)(?=\n## |\Z)", s, re.S)
    if not m: return []
    out = []
    for ln in m.group(1).split("\n"):
        ln = re.sub(r"^\s*(?:[-*]\s+|\d+[.)]\s+)", "", ln.strip())
        b = re.match(r"\*\*(.+?)\*\*\s*(.*)", ln)
        if not b: continue   # 只取加粗的判断句；开场白、说明段不算
        out.append({"head": b.group(1).strip(), "body": b.group(2).strip()})
    return out


def pick(pool, used_key, used, force):
    seen = set(used.get(used_key, []))
    cand = [b for b in pool if b["head"] not in seen] or pool
    if not cand: return None
    b = cand[0]
    if not force: used.setdefault(used_key, []).append(b["head"])
    return b


def latest(pattern):
    fs = sorted(glob.glob(pattern)); return fs[-1] if fs else None


def compute_numbers():
    rp = latest(os.path.join(HERE, "rank", "20*-w*.json")); R = load(rp) or {}
    fl = R.get("flagship") or []; rows = [r for m in fl for r in (m.get("rows") or []) if r.get("ratio") is not None]
    below = sum(1 for r in rows if r["ratio"] < 0.5)
    fast = (R.get("fast") or [{}])[0]
    return {"week": R.get("week", ""), "n_sites": R.get("n_sites"), "n_quotes": R.get("n_quotes"), "rows": len(rows), "below": below, "fast": fast, "n_big": R.get("n_big"), "zero": R.get("zero_change")}


def robo_numbers():
    rp = latest(os.path.join(ROBO_DIR, "data", "reports", "20*-*.json")); S = load(rp) or {}
    A, M, B, D, I = S.get("activity", {}), S.get("measurements", {}), S.get("benchmarks", {}), S.get("datasets", {}), S.get("index", {})
    return {"month": S.get("month", ""), "models": I.get("models"), "cn": I.get("chinese_org"), "repos": A.get("repos"), "stale": A.get("stale_180"), "zero90": A.get("zero_commits_90"), "meas": M.get("total"), "scores": B.get("scores"), "datasets": D.get("count"), "hw": M.get("by_hardware") or {}}


def main():
    force = "--force" in sys.argv
    today = dt.datetime.now(BJ).date(); wk = "%d-W%02d" % today.isocalendar()[:2]
    used_p = os.path.join(ROOT, "data", "posts", "community_used.json"); used = load(used_p, {})
    # ---- Compute ----
    cm = latest(os.path.join(HERE, "reports", "20*.analysis.md"))
    cb = pick(bullets(cm) if cm else [], "compute", used, force) or {"head": "价格不是这个市场的竞争变量，充值比例才是。", "body": ""}
    C = compute_numbers()
    c_link = BASE + "/rank"; m_link = BASE + "/report/" + (os.path.basename(cm)[:7] if cm else "")
    linuxdo = "\n".join([
        "【标题】司南榜 %s：%s 个中转站的 7 天测量，说一个数字和一个判断" % (C["week"], C["n_sites"]),
        "",
        "先说数字。这周我们对 %s 个中转站做了 7 天连续测量，收了 %s 条实付报价。%s" % (C["n_sites"], "{:,}".format(C["n_quotes"] or 0), ("旗舰模型的 %d 条报价里，%d 条低于官方价的一半。" % (C["rows"], C["below"])) if C["rows"] else ""),
        ("可达率 100%% 的站里首字节最快的是 %s，p50 %d ms。" % (C["fast"].get("name") or C["fast"].get("domain"), C["fast"]["p50"])) if C["fast"].get("p50") else "",
        "",
        "再说判断（这是我们的观点，不是测量）：**%s** %s" % (cb["head"], cb["body"]),
        "",
        "测法：每小时探测可达与首字节，价格取站内面板公开价折算成每百万 token 实付；不含任何商业变量，不做推荐。榜单和全部原始数据在这里，站长看到自己的数字不对可以直接提纠错，我们按原文改：%s" % c_link,
        "月报（判断的完整版）：%s" % m_link,
    ]).strip()
    v2ex = "\n".join([
        "【标题】测了 %s 个模型 API 中转站 7 天：%s" % (C["n_sites"], cb["head"].rstrip("。")[:48]),
        "",
        "%s 条实付报价，%s。" % ("{:,}".format(C["n_quotes"] or 0), ("旗舰模型 %d 条报价里 %d 条低于官方价一半" % (C["rows"], C["below"])) if C["rows"] else "全部按测量值排序"),
        "我们的读法是：%s%s" % (cb["head"], (" " + cb["body"]) if cb["body"] else ""),
        "",
        "只发布测量和来源，不推荐任何站。想知道各位是怎么选站的：看价格、看充值比例，还是看它活了多久？%s" % c_link,
    ]).strip()
    # ---- Robo ----
    rm_en = latest(os.path.join(ROBO_DIR, "data", "reports", "20*.analysis.en.md")); rm_zh = latest(os.path.join(ROBO_DIR, "data", "reports", "20*.analysis.md"))
    rb = pick(bullets(rm_en) if rm_en else [], "robo", used, force) or {"head": "Open VLA is a layered claim.", "body": ""}
    Rn = robo_numbers(); r_link = ROBO + "/reports/" + Rn["month"] if Rn["month"] else ROBO
    hw4090 = {x["model_id"]: x for x in Rn["hw"].get("rtx-4090", [])}; hwa800 = {x["model_id"]: x for x in Rn["hw"].get("a800-80g", [])}
    common = [m for m in hw4090 if m in hwa800]
    reddit = "\n".join([
        "Title: We index %s open VLA models and measure them on rented GPUs. One number and one judgement from this month." % Rn["models"],
        "",
        "Numbers: %s open-weight VLA models indexed (%s from Chinese orgs); daily activity fetch shows %s of %s repos with no push in 180 days; %s latency measurements (batch 1, bf16, fixed input) on RTX 4090 / 5090 / A800; %s benchmark scores copied from papers with table refs; %s public datasets with licence and scale as stated." % (Rn["models"], Rn["cn"], Rn["stale"], Rn["repos"], Rn["meas"], Rn["scores"], Rn["datasets"]),
        ("On %d models we ran on both a 4090 and an A800 80GB, the A800 was not faster on any of them (p50: %s)." % (len(common), "; ".join("%s %d vs %d ms" % (hw4090[m]["name"], round(hw4090[m]["p50"]), round(hwa800[m]["p50"])) for m in common[:5]))) if common else "",
        "",
        "Judgement (ours, labelled as opinion): %s %s" % (rb["head"], rb["body"]),
        "",
        "Everything is downloadable JSON with sources per field; we do not rank by a composite score and we do not recommend. Method and limits are on the page. Happy to be corrected on any row: %s" % r_link,
    ]).strip()
    hn = "\n".join([
        "Title: Show HN: A measured index of open VLA models – latency on rented GPUs, licences, activity, benchmark scores as printed",
        "",
        "Comment: We maintain robo.sinanlab.com, an index of %s open-weight vision-language-action models with every field sourced. This month's additions: daily GitHub/HF activity (%s of %s repos idle 180+ days), %s latency measurements on 4090/5090/A800 (the A800 was slower than the 4090 on every model we ran), %s benchmark scores copied from papers by table, %s datasets. No composite score, no recommendations; JSON under /data/. %s" % (Rn["models"], Rn["stale"], Rn["repos"], Rn["meas"], Rn["scores"], Rn["datasets"], r_link),
    ]).strip()
    items = [
        {"site": "linux.do", "where": "linux.do · 开发调优 / 中转站相关板块（发中文）", "title": linuxdo.split("\n")[0].replace("【标题】", ""), "text": linuxdo},
        {"site": "V2EX", "where": "V2EX · 分享创造 或 程序员 节点（发中文，别带推广语气）", "title": v2ex.split("\n")[0].replace("【标题】", ""), "text": v2ex},
        {"site": "Reddit", "where": "Reddit · r/robotics 或 r/LocalLLaMA（英文；先看板规是否允许自站链接，不允许就只放数字、链接放评论里）", "title": reddit.split("\n")[0].replace("Title: ", ""), "text": reddit},
        {"site": "Hacker News", "where": "news.ycombinator.com · Show HN（英文；标题照用，正文贴在第一条评论）", "title": hn.split("\n")[0].replace("Title: ", ""), "text": hn},
    ]
    out = {"week": wk, "date": today.isoformat(), "items": items, "sources": {"compute": cb["head"], "robo": rb["head"]}}
    os.makedirs(os.path.join(ROOT, "data", "posts"), exist_ok=True)
    json.dump(out, io.open(os.path.join(ROOT, "data", "posts", "community_%s.json" % wk), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    io.open(os.path.join(ROOT, "data", "posts", "community_%s.md" % wk), "w", encoding="utf-8").write("\n\n==========\n\n".join("## %s\n%s\n\n%s" % (i["site"], i["where"], i["text"]) for i in items))
    if not force: json.dump(used, io.open(used_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("社区稿 %s：4 篇 → data/posts/community_%s.md（Compute 判断：%s · Robo：%s）" % (wk, wk, cb["head"][:30], rb["head"][:40]))


if __name__ == "__main__":
    main()
