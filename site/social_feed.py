# -*- coding: utf-8 -*-
"""社媒转发源：把每天的英文短帖（linuxdo_post.variants 的 x_en）累积成 RSS（site/dist/social.xml），
供 dlvr.it / IFTTT 一类免费"RSS → 社交账号"服务自动转发到 X，不需要 X 付费接口。历史存 data/posts/social_history.json（保留 60 条）。"""
import os, io, re, json, datetime as dt, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8)); BASE = "https://compute.sinanlab.com"
def main():
    hist_p = os.path.join(ROOT, "data", "posts", "social_history.json")
    hist = json.load(io.open(hist_p, encoding="utf-8")) if os.path.exists(hist_p) else []
    tp = os.path.join(ROOT, "data", "posts", "today.json")
    if os.path.exists(tp):
        today = dt.datetime.now(BJ).date().isoformat()
        for p in json.load(io.open(tp, encoding="utf-8")):
            if p.get("x_en") and not any(h["date"] == today and h["kind"] == p["kind"] for h in hist):
                url = {"rank": "%s/rank" % BASE, "daily": BASE, "model": BASE, "probe": "%s/check" % BASE, "check": "%s/check" % BASE}.get(p["kind"], BASE)
                hist.append({"date": today, "kind": p["kind"], "text": p["x_en"], "url": url, "ts": dt.datetime.now(BJ).isoformat()[:19]})
    hist = hist[-60:]
    os.makedirs(os.path.dirname(hist_p), exist_ok=True); json.dump(hist, io.open(hist_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    def strip_url(t):   # 正文里不带网址：dlvr.it 会自己把 <link> 附在后面，重复就会被截断
        import re as _r; return _r.sub(r"\s*https?://\S+\s*$", "", t).strip()
    for h in hist:
        m = re.search(r"https?://\S+", h["text"])
        if m and h.get("url", BASE) in (BASE, ""): h["url"] = m.group(0)
    items = "".join('<item><title>%s</title><link>%s</link><guid isPermaLink="false">%s</guid><pubDate>%s</pubDate><description>%s</description></item>' % (
        html.escape(strip_url(h["text"])[:230]), html.escape(h["url"]), "sinan-social-%s-%s" % (h["date"], h["kind"]), dt.datetime.fromisoformat(h["ts"]).replace(tzinfo=BJ).strftime("%a, %d %b %Y %H:%M:%S %z"), html.escape(strip_url(h["text"]))) for h in reversed(hist))
    xml = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Sinan Lab · daily post</title><link>%s</link><description>One measured line a day from Sinan Lab: relay-market prices, rankings, probes.</description>%s</channel></rss>' % (BASE, items)
    for d in (os.path.join(HERE, "dist"),):
        if os.path.exists(d): io.open(os.path.join(d, "social.xml"), "w", encoding="utf-8").write(xml)
    print("社媒源：%d 条 → /social.xml" % len(hist))
if __name__ == "__main__": main()
