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

def main():
    E = env(); tok, chat = E.get("TELEGRAM_BOT_TOKEN"), E.get("TELEGRAM_CHAT")
    if not tok or not chat: print("Telegram：未配置 data/secrets.env，跳过"); return
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
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
