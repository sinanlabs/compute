# -*- coding: utf-8 -*-
"""SEO / GEO 技术体检：部署前扫一遍 dist/，写 dist/seo_status.json，给后台「SEO / GEO」页看。
只数事实：sitemap 收了多少 URL、多少页带 FAQ 结构化数据、llms.txt 是不是今天的、首页多大、各类页面多少。
用法：python3 site/seo_status.py   （在 i18n_apply 之后、部署之前跑；daily_refresh.sh 与 redeploy.sh 已接）"""
import os, io, re, json, glob, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__)); DIST = os.path.join(HERE, "dist")
BJ = dt.timezone(dt.timedelta(hours=8))


def main():
    sm = io.open(os.path.join(DIST, "sitemap.xml"), encoding="utf-8").read() if os.path.exists(os.path.join(DIST, "sitemap.xml")) else ""
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    pages = [p for p in glob.glob(os.path.join(DIST, "**", "*.html"), recursive=True) if "/snap/" not in p and "/_en_src/" not in p]
    types, faq_zh, faq_en, faq_by = {}, 0, 0, {}
    for p in pages:
        rel = os.path.relpath(p, DIST)
        try: t = io.open(p, encoding="utf-8").read()
        except Exception: continue
        lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
        has_faq = False
        for b in lds:
            for ty in re.findall(r'"@type":\s*"([A-Za-z]+)"', b): types[ty] = types.get(ty, 0) + 1
            if '"FAQPage"' in b: has_faq = True
        if has_faq:
            if rel.startswith("en/"): faq_en += 1
            else: faq_zh += 1
            kind = (rel[3:] if rel.startswith("en/") else rel).split("/")[0]
            kind = kind if kind in ("s", "m", "media", "rank", "report") else "other"
            faq_by[kind] = faq_by.get(kind, 0) + 1
    llms = io.open(os.path.join(DIST, "llms.txt"), encoding="utf-8").read() if os.path.exists(os.path.join(DIST, "llms.txt")) else ""
    m = re.search(r"今日关键数字（(\d{4}-\d{2}-\d{2})", llms)
    cnt = lambda pre: len([p for p in pages if os.path.relpath(p, DIST).startswith(pre)])
    out = {"generated_at": dt.datetime.now(BJ).isoformat(timespec="seconds"),
           "sitemap_urls": len(locs), "sitemap_en": sum(1 for u in locs if "/en/" in u),
           "html_pages": len(pages), "pages": {"站点页": cnt("s/"), "模型页": cnt("m/"), "图像视频族页": cnt("media/"), "榜单期": cnt("rank/"), "月报": cnt("report/"), "对比页": cnt("vs/"), "英文页": cnt("en/")},
           "faq_pages": faq_zh + faq_en, "faq_zh": faq_zh, "faq_en": faq_en, "faq_by_kind": faq_by, "jsonld_types": dict(sorted(types.items(), key=lambda x: -x[1])),
           "llms_date": m.group(1) if m else None, "llms_bytes": len(llms.encode("utf-8")),
           "index_kb": round(os.path.getsize(os.path.join(DIST, "index.html")) / 1024) if os.path.exists(os.path.join(DIST, "index.html")) else None,
           "robots_ok": os.path.exists(os.path.join(DIST, "robots.txt")) and "Disallow: /\n" not in io.open(os.path.join(DIST, "robots.txt"), encoding="utf-8").read()}
    io.open(os.path.join(DIST, "seo_status.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    print("SEO 体检：sitemap %d 条 · 带问答结构化数据 %d 页（中 %d / 英 %d）· llms.txt %s · 首页 %s KB" % (
        out["sitemap_urls"], out["faq_pages"], faq_zh, faq_en, out["llms_date"], out["index_kb"]))


if __name__ == "__main__":
    main()
