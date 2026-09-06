# -*- coding: utf-8 -*-
"""linux.do 发帖内容自动生成（Eric 只复制粘贴）。每晚在 export/build 之后跑，产出 data/posts/<日期>/*.md 与 data/posts/today.md，并邮件发给管理员。
帖子类型（按星期轮换，全部由当天数据生成，措辞过 core/wording 自检）：
  周一  rank     司南榜本期：12 张榜各前三 + 待核说明
  周三  model    模型专题：轮换一个最新代旗舰，谁在说得通区间卖、分布、参考价
  周五  probe    检测周报：可达分布、一致性探针、能力抽样、自测工具
  每天  daily    价格变动日报（主流模型变动 ≥5 条才生成）+ 新收录 + 7 天未连通
  任意  check    自测工具介绍（一次性，手动 python3 site/linuxdo_post.py check）
用法：python3 site/linuxdo_post.py [auto|rank|model|probe|daily|check]"""
import os, io, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.wording import lint
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BASE = "https://compute.sinanlab.com"; BJ = dt.timezone(dt.timedelta(hours=8))
FOOT = ("\n\n---\n**说明**：以上全部是测量结果，按数值排序，不构成推荐；每个数字在站内可点开看抓取快照。我们不收任何被测渠道的钱，出站链接不带推广参数，原始数据可下载。"
        "哪个价格和你在站上看到的不一样，回帖告诉我，核对后当天修正。\n数据与方法：%s/method" % BASE)
def fmt(x): return "—" if x is None else ("%.3f" % x if x < 1 else "%.2f" % x if x < 100 else "%.0f" % x)
def pct(r): return "—" if r is None else "%d%%" % round(r * 100)
def load():
    D = json.load(io.open(os.path.join(HERE, "dist", "data_v2.json"), encoding="utf-8"))
    M = json.load(io.open(os.path.join(HERE, "dist", "media.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "dist", "media.json")) else {}
    return D, M
def nm(D, dom):
    s = next((x for x in D["sites"] if x["domain"] == dom), None); return ("%s（%s）" % (dom, s["name"])) if s and s.get("name") and s["name"] != dom else dom

def post_rank(D, M):
    R = D["rank"]; st = D["stats"]; wk = R["week"]
    L = ["# 司南榜 %s：%d 个中转站的 7 天测量结果（响应 / 价格 / 可达 / 多模态）" % (wk, R["n_sites"]),
         "每周一出一期。每张榜只回答一个能测量的问题，按测量值排序，不含任何商业变量。数据窗口 7 天，%s 条实付报价。\n" % format(R["n_quotes"] or st["quotes"], ",")]
    def top(title, rows, val, sub=None, n=3):
        L.append("**%s**" % title)
        for i, x in enumerate(rows[:n]): L.append("%d. %s — %s%s" % (i + 1, nm(D, x["domain"]), val(x), ("（%s）" % sub(x)) if sub else ""))
        L.append("")
    top("响应榜（可达率 ≥99% 的站里首字节延迟 p50 最低）", R["fast"], lambda x: "%dms" % x["p50"], lambda x: "可达 %.1f%%" % x["uptime"])
    top("价格优势榜（最新代模型在说得通区间内的实付中位数最低）", R.get("price", []), lambda x: "参考价的 %s" % pct(x["median"]), lambda x: "%d 个可比模型" % x["n"])
    top("双旗舰榜（同时在说得通区间卖 GPT-6 Astra 与 Claude Fable 5.1）", R["dual"], lambda x: "两者实付合计 $%s/百万输出" % fmt(x["sum"]))
    dd = R.get("dist_up", {}); L.append("**可达榜**：%d 家过门槛，100%% 有 %d 家 · 99%%–99.9%% 有 %d 家 · 低于 99%% 有 %d 家。可达率最低的三家：%s\n" % (
        R["eligible_uptime"], dd.get("full", 0), dd.get("hi", 0), dd.get("low", 0), "、".join("%s %.1f%%" % (x["domain"], x["uptime"]) for x in R.get("low", [])[:3])))
    top("覆盖榜（在卖模型最多）", R["coverage"], lambda x: "%d 个模型" % x["n"])
    MR = R.get("media") or {}
    if MR.get("price"): top("多模态价格优势榜（图像 / 视频报价说得通区间内实付中位数最低）", MR["price"], lambda x: "官方参考价的 %s" % pct(x["median"]), lambda x: "%d 条可比报价" % x["n"])
    for fam in MR.get("video", [])[:6]:
        L.append("**%s 每秒实付最低三家**：%s" % (fam["name"], "、".join("%s $%s/秒（参考价的 %s）" % (r["site"], fmt(r["value"]), pct(r["ratio"])) for r in fam["rows"])))
    L.append("")
    au = R.get("audit") or []
    L.append("**本期待核**：%d 条榜首因比第二名低 40%% 以上且只此一家暂不进榜；另有 %d 条报价待核（单位提示不一致 / 价格孤点 / 按规格计价）不参与比对。" % (len(au), R.get("audit_open") or 0))
    L.append("\n完整 12 张榜与永久链接：%s/rank/%s" % (BASE, wk))
    return "rank", L[0].lstrip("# "), "\n".join(L[1:]) + FOOT

def post_model(D, M, pick=None):
    latest = [m for m in D["models"] if m["is_latest"] and m["n_relay"] >= 15]
    if not latest: return None
    day = dt.datetime.now(BJ).timetuple().tm_yday
    m = pick and next((x for x in D["models"] if x["id"] == pick), None) or latest[day % len(latest)]
    rows = [r for r in m["rows"] if not r["held"] and r["ratio"] is not None and r.get("reg") != "closed"]
    ok = sorted([r for r in rows if r["band"] in ("explainable", "normal")], key=lambda r: r["out"])
    bands = {b: sum(1 for r in rows if r["band"] == b) for b in ("unsustainable", "below_bulk", "explainable", "normal", "premium", "far_above")}
    L = ["# %s 在 %d 家中转站的实付价：谁在说得通的区间里卖" % (m["name"], len(rows)),
         "参考价取官方与公开市场最低：**$%s / 百万输出**（%s）。下面的「几成」= 该站实付 ÷ 参考价，实付已按人民币充值通道折成美元。\n" % (fmt(m["floor"]["out"]), m["floor"]["vendor"]),
         "**分布**：低于成本下限（<15%%）%d 家 · 低于批量折扣（15–40%%）%d 家 · 说得通（40–125%%）%d 家 · 高于公开价 %d 家。\n" % (bands["unsustainable"], bands["below_bulk"], bands["explainable"] + bands["normal"], bands["premium"] + bands["far_above"]),
         "**说得通区间内实付最低的 8 家**（新用户注册已关闭的不列）：\n", "| 站 | 输出 $/百万 | 输入 $/百万 | 几成 | 24h 可达 |", "|---|---:|---:|---:|---:|"]
    for r in ok[:8]: L.append("| %s | %s | %s | %s | %s |" % (nm(D, r["vendor"]), fmt(r["out"]), fmt(r["in"]), pct(r["ratio"]), ("%.0f%%" % r["uptime"]) if r.get("uptime") is not None else "—"))
    L.append("\n低于成本下限的 %d 家我们不做推测，只标出来：价格低于任何公开渠道的成本，怎么做到的我们不知道。有 Key 的可以用站上的自测工具比一下 token 计数。" % bands["unsustainable"])
    L.append("\n全部 %d 家与抓取快照：%s/m/%s" % (len(rows), BASE, m["id"]))
    return "model", L[0].lstrip("# "), "\n".join(L[1:]) + FOOT

def post_probe(D, M):
    st = D["stats"]; R = D["rank"]; dd = R.get("dist_up", {})
    L = ["# 中转站检测周报：%d 站可达分布、一致性探针 %d 组、能力抽样 %d 组" % (R["eligible_uptime"], st.get("probed_pairs", 0), st.get("cap_pairs", 0)),
         "我们对已确认的 %d 个中转站做三层检测，全部用自己的 Key，结果只分「一致 / 不一致 / 样本不足」，不做真伪判定。\n" % st["confirmed"],
         "**T0 可达**：过去 7 天 %d 家过门槛（≥24 次探测、在卖 ≥10 模型）：100%% 有 %d 家、99%%–99.9%% 有 %d 家、低于 99%% 有 %d 家。首字节最快：%s。\n" % (
             R["eligible_uptime"], dd.get("full", 0), dd.get("hi", 0), dd.get("low", 0), "、".join("%s %dms" % (x["domain"], x["p50"]) for x in R["fast"][:3])),
         "**T1 一致性探针**：对同一模型发固定探针串，比对返回的 token 计数与回显模型名。%d 组站×模型：%d 组与其他渠道一致，%d 组不一致，其余样本不足。不一致只说明该渠道对同一输入返回的计数与多渠道共识不同，成因很多，我们不推测。\n" % (st.get("probed_pairs", 0), st.get("probe_consistent", 0), st.get("probe_divergent", 0)),
         "**T2 能力抽样**：30 道机器判分小题，本站答对数与同模型多渠道中位数比。%d 组已抽样，%d 组低于中位。\n" % (st.get("cap_pairs", 0), st.get("cap_below", 0)),
         "**自己测**：登录后在 %s/check 填站点和你的 Key，浏览器直接向该站发 8 条探针（Key 不上传），几秒出结果，一次不到一分钱。\n" % BASE,
         "**本周待核**：%d 条报价因单位提示不一致 / 价格孤点 / 榜首差距过大暂不进榜，核对原始条目后放行。" % (R.get("audit_open") or 0)]
    return "probe", L[0].lstrip("# "), "\n".join(L[1:]) + FOOT

def post_daily(D, M, min_changes=5):
    day = D["generated_at"][:10]
    ch = [c for c in D.get("changes", []) if c.get("kind") == "relay" and c["t"][:10] == day]
    news = D.get("new_sites", []); dead = [s for s in D["sites"] if s.get("dead")]
    if len(ch) < min_changes and not news: return None
    mn = {m["id"]: m["name"] for m in D["models"]}
    L = ["# %s 中转站价格变动：%d 条主流模型变价、新收录 %d 站" % (day, len(ch), len(news)),
         "只记主流模型（每厂商最新两代）的名义价变动，连续两次抓取一致才发布。单位 $/百万输出 token（面板名义价，实付还要乘充值比例）。\n",
         "| 站 | 模型 | 旧 | 新 | |", "|---|---|---:|---:|:-:|"]
    for c in ch[:40]: L.append("| %s | %s | %s | %s | %s |" % (c["vendor"], mn.get(c["model"], c["model"]), fmt(c["old"]), fmt(c["new"]), "↑" if c["new"] > c["old"] else "↓"))
    if news: L.append("\n**新收录 %d 站**（经面板指纹确认）：%s%s" % (len(news), "、".join(news[:20]), "…" if len(news) > 20 else ""))
    if dead: L.append("\n**7 天未连通**（页面保留，不进榜）：%s" % "、".join(s["domain"] for s in dead[:20]))
    L.append("\n站点总表与每站的实付比率：%s/sites" % BASE)
    return "daily", L[0].lstrip("# "), "\n".join(L[1:]) + FOOT

def post_check(D, M):
    L = ["# 用自己的 Key 几秒测一个中转站：8 条固定探针，比 token 计数、回显模型名和延迟",
         "很多佬友买了中转站的额度，最关心的是「我调的到底是不是那个模型」。我们做了一个不用装任何东西的自测：\n",
         "1. 登录 %s/check（GitHub / Google / 邮箱验证码，不设密码）\n2. 填站点地址和你在该站的 Key（Key 只在你浏览器里，不上传）\n3. 浏览器直接向该站发 8 条固定探针，每条只要 4 个输出 token，一次自测不到一分钱\n4. 逐位比对返回的 token 计数与我们从多个渠道得到的参考计数，判定只有四种：一致 / 含固定前缀 / 不一致 / 无参考\n" % BASE,
         "为什么比 token 计数：同一模型不同分词器切出的 token 数不同，改不了、装不了。含固定前缀说明该渠道给你加了系统提示；不一致说明计数与多渠道共识不同，成因很多（上游分流、注入、量化、缓存），我们不推测。\n",
         "参考计数来自 ≥3 个有 Key 渠道的一致结果；只有 2 个渠道一致的标「弱参考」。结果可以选择回流给我们（不含 Key），帮助扩大检测覆盖。"]
    return "check", L[0].lstrip("# "), "\n".join(L[1:]) + FOOT

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "auto"
    D, M = load(); today = dt.datetime.now(BJ); wd = today.weekday()
    kinds = {"auto": ["daily"] + (["rank"] if wd == 0 else []) + (["model"] if wd == 2 else []) + (["probe"] if wd == 4 else []),
             "all": ["rank", "model", "probe", "daily", "check"]}.get(arg, [arg])
    gens = {"rank": post_rank, "model": post_model, "probe": post_probe, "daily": post_daily, "check": post_check}
    outdir = os.path.join(ROOT, "data", "posts", today.strftime("%Y-%m-%d")); os.makedirs(outdir, exist_ok=True)
    made = []
    for k in kinds:
        res = gens[k](D, M)
        if not res: print("  %s：今天数据不够，不生成" % k); continue
        kind, title, body = res
        bad = [x for x in lint(title + "\n" + body) if x[1] == "banned_term"]
        if bad: print("  %s：措辞自检命中 %s，不发" % (kind, bad[:3])); continue
        txt = "【标题】\n%s\n\n【正文】\n%s\n" % (title, body)
        io.open(os.path.join(outdir, kind + ".md"), "w", encoding="utf-8").write(txt); made.append((kind, title, txt))
    if made:
        io.open(os.path.join(ROOT, "data", "posts", "today.md"), "w", encoding="utf-8").write("\n\n==========\n\n".join(t for _, _, t in made))
        json.dump([{"kind": k, "title": t, "text": x} for k, t, x in made], io.open(os.path.join(ROOT, "data", "posts", "today.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("发帖稿：%s → data/posts/today.md" % ", ".join(k for k, _, _ in made) if made else "发帖稿：今天没有可发的")

if __name__ == "__main__":
    main()
