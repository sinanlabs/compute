# -*- coding: utf-8 -*-
"""社媒转发源：把 data/posts/social_history.json（由 social_weekly.py 每周入队：周榜 / Robo 周报 / 本周发现 / 月报）渲染成 RSS
（site/dist/social.xml），供 dlvr.it 一类免费"RSS → 社交账号"服务转发到 X / Bluesky。
每条带 <enclosure> 与 <media:content> 图片（榜单分享图 / 站点 og 图），带图的帖子比纯文字加链接曝光高得多。
正文里不放网址（dlvr.it 会自己把 <link> 附在后面，重复就会被截断）。"""
import os, io, re, json, datetime as dt, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8)); BASE = "https://compute.sinanlab.com"
def main():
    hist_p = os.path.join(ROOT, "data", "posts", "social_history.json")
    hist = json.load(io.open(hist_p, encoding="utf-8")) if os.path.exists(hist_p) else []
    def strip_url(t): return re.sub(r"\s*https?://\S+\s*$", "", t or "").strip()
    def img(h):
        if h.get("image"): return h["image"]
        return "https://robo.sinanlab.com/og.png" if str(h.get("kind", "")).startswith("robo") else BASE + "/img/og.png"
    items = []
    for h in reversed(hist[-60:]):
        text = strip_url(h["text"]); link = h.get("url") or BASE; im = img(h)
        try: pub = dt.datetime.fromisoformat(h["ts"]).replace(tzinfo=BJ).strftime("%a, %d %b %Y %H:%M:%S %z")
        except Exception: pub = dt.datetime.now(BJ).strftime("%a, %d %b %Y %H:%M:%S %z")
        items.append('<item><title>%s</title><link>%s</link><guid isPermaLink="false">%s</guid><pubDate>%s</pubDate><description>%s</description>'
                     '<enclosure url="%s" type="image/png" length="0"/><media:content url="%s" medium="image" type="image/png"/></item>' % (
                         html.escape(text[:250]), html.escape(link), "sinan-social-%s-%s" % (h["date"], h["kind"]), pub, html.escape(text), html.escape(im), html.escape(im)))
    xml = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel><title>Sinan Lab · measured</title><link>%s</link>'
           '<description>One or two measured findings a week from Sinan Lab: China\'s LLM API relay market and open embodied models. Numbers with sources; no recommendations.</description>%s</channel></rss>' % (BASE, "".join(items)))
    for d in (os.path.join(HERE, "dist"),):
        if os.path.exists(d): io.open(os.path.join(d, "social.xml"), "w", encoding="utf-8").write(xml)
    print("社媒源：%d 条（带图）→ /social.xml" % len(items))
if __name__ == "__main__": main()
