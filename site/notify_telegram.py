# -*- coding: utf-8 -*-
"""把当天的价格变动推到 Telegram 频道。凭据只在本机 data/secrets.env（git 忽略）：
TELEGRAM_BOT_TOKEN=123:abc
TELEGRAM_CHAT=@sinancompute
每天只发一次（data/logs/.tg_last 记日期）；没有变动就不发。措辞只陈述测量，不含推荐。"""
import os, io, json, sys
import httpx
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BASE = "https://compute.sinanlab.com"

def env():
    p = os.path.join(ROOT, "data", "secrets.env"); out = {}
    if not os.path.exists(p): return out
    for l in io.open(p, encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, v = l.split("=", 1); out[k.strip()] = v.strip()
    return out

def fmt(x): return ("%.3f" % x) if x < 1 else ("%.2f" % x)

def send(tok, chat, text):
    r = httpx.post("https://api.telegram.org/bot%s/sendMessage" % tok, json={"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True}, timeout=30)
    print("Telegram：HTTP %d" % r.status_code); return r.status_code == 200

def extras(tok, chat, D):
    """周一发司南榜摘要，每月 1 日发上月月报链接；各自用标记文件保证只发一次。"""
    import datetime as dt, sys
    sys.path.insert(0, HERE)
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
    logs = os.path.join(ROOT, "data", "logs"); os.makedirs(logs, exist_ok=True)
    if today.weekday() == 0:
        mark = os.path.join(logs, ".tg_rank"); wk = D["rank"]["week"]
        if not (os.path.exists(mark) and io.open(mark).read().strip() == wk):
            from linuxdo_post import post_rank, load
            D2, M = load(); _, title, body = post_rank(D2, M)
            text = "🏆 " + title + "\n\n" + body.replace("**", "").replace("# ", "")
            if send(tok, chat, text[:3800] + ("\n\n全文：%s/rank/%s" % (BASE, wk))): io.open(mark, "w").write(wk)
    if today.day == 1:
        m = (today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m"); mark = os.path.join(logs, ".tg_report")
        rp = os.path.join(HERE, "reports", m + ".json")
        if os.path.exists(rp) and not (os.path.exists(mark) and io.open(mark).read().strip() == m):
            R = json.load(io.open(rp, encoding="utf-8")); sc = R["scale"]; pr = R["prices"]
            text = "📰 中国模型 API 中转市场月报 · %s\n\n已确认中转站 %d · 本期新收录 %d · 主流模型变价 %d 次（涨 %d 降 %d）。价格指数、市场结构、可达与检测、图像视频、算力成本五部分，附原始数据与引用格式。\n\n%s/report/%s" % (m, sc["confirmed_now"], sc["new_sites"], pr["mainstream_changes"], pr["ups"], pr["downs"], BASE, m)
            if send(tok, chat, text): io.open(mark, "w").write(m)

def main():
    E = env(); tok, chat = E.get("TELEGRAM_BOT_TOKEN"), E.get("TELEGRAM_CHAT")
    if not tok or not chat: print("Telegram：未配置 data/secrets.env，跳过"); return
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    try: extras(tok, chat, D)
    except Exception as e: print("Telegram 周/月推送失败", e)
    day = D["generated_at"][:10]; mark = os.path.join(ROOT, "data", "logs", ".tg_last")
    if os.path.exists(mark) and io.open(mark).read().strip() == day: print("Telegram：今天已发过"); return
    ch = [c for c in D.get("changes", []) if c["t"][:10] == day]
    if not ch and not D.get("new_sites"): print("Telegram：今天无变动"); return
    lines = ["📊 Sinan Compute · %s 价格变动" % day]
    for c in ch[:12]:
        arrow = "↑" if c["new"] > c["old"] else "↓"
        lines.append("• %s · %s：%s → %s %s（%s，$/百万输出）" % (c["vendor"], c["model"], fmt(c["old"]), fmt(c["new"]), arrow, "中转站名义价" if c["kind"] == "relay" else "公开参考价"))
    if len(ch) > 12: lines.append("… 另有 %d 条，见站内" % (len(ch) - 12))
    if D.get("new_sites"): lines.append("🆕 新收录 %d 个中转站" % len(D["new_sites"]))
    lines.append(""); lines.append("此为算术比值，不构成对任何渠道的指控。全部数据：%s" % BASE)
    r = httpx.post("https://api.telegram.org/bot%s/sendMessage" % tok, json={"chat_id": chat, "text": "\n".join(lines), "disable_web_page_preview": False}, timeout=30)
    print("Telegram：HTTP %d" % r.status_code)
    if r.status_code == 200:
        os.makedirs(os.path.dirname(mark), exist_ok=True); io.open(mark, "w").write(day)

if __name__ == "__main__":
    main()
