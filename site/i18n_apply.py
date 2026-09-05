# -*- coding: utf-8 -*-
"""英文版生成：读 dist/ 里的中文页面，按文本节点用词典翻译，输出到 dist/en/（Compute）或 public/en/（母站）。
- 词典 site/i18n_en.json：{"html": {中文模式: 英文模式}, "js": {JS字面量: 英文字面量}}，模式里的 {n} 匹配数字。
- 只翻文本节点与 title/alt/placeholder/aria-label/content/data-label 属性；标签、数据 JSON、模型名、域名不碰。
- 站内链接改到 /en/ 前缀；<html lang="en">；canonical/og:url 指向英文页；两种语言互加 hreflang；顶栏加语言切换。
- 生成 assets/app.en.js（按 JS 字面量词典替换），英文页引用它。
- 结尾报告残留中文的文本节点数，便于补词典。
用法：python3 i18n_apply.py <dist目录> <站点根 URL>   （例：python3 i18n_apply.py dist https://compute.sinanlab.com）
"""
import os, io, re, sys, json, html as H
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
DICT = json.load(io.open(os.path.join(HERE, "i18n_en.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "i18n_en.json")) else {"html": {}, "js": {}}
CJK = re.compile(r"[一-鿿]")
NUM = r"(\d[\d,\.]*)"
STR = r"(.+?)"   # {s}：任意文字（模型名、站名、域名），非贪婪

# 预编译：模式 → 正则（{n} → 数字捕获），按长度降序
RULES = []
for zh, en in DICT.get("html", {}).items():
    if not zh.strip(): continue
    rx = re.compile("^" + re.escape(zh).replace(re.escape("{n}"), NUM).replace(re.escape("{s}"), STR) + "$", re.S)
    RULES.append((zh, rx, en))
EXACT = {zh: en for zh, _, en in RULES if "{n}" not in zh and "{s}" not in zh}
RULES = [r for r in RULES if "{n}" in r[0] or "{s}" in r[0]]
# 长的、含 {s} 少的优先（更具体）
RULES.sort(key=lambda r: (-len(r[0]), r[0].count("{s}")))

def fill(en, groups):
    """按英文模板里 {n}/{s} 出现顺序依次填入捕获组；捕获到的中文（模型族名、画像标签等）再翻一次。"""
    it = iter(groups)
    def one(m):
        g = next(it, None)
        if g is None: return m.group(0)
        return tr_text(g) if CJK.search(g) else g
    out = re.sub(r"\{[ns]\}", one, en)
    return re.sub(r"\b1 (sites|rows|models|quotes|changes|probes|days|images)\b", lambda m: "1 " + m.group(1)[:-1], out)

def tr_text(t):
    """翻一个文本节点（保留首尾空白）。"""
    m = re.match(r"^(\s*)(.*?)(\s*)$", t, re.S)
    lead, core, tail = m.group(1), m.group(2), m.group(3)
    if not core or not CJK.search(core): return t
    core_n = re.sub(r"\s+", " ", core)
    if core_n in EXACT: return lead + EXACT[core_n] + tail
    for zh, rx, en in RULES:
        mm = rx.match(core_n)
        if mm:
            return lead + fill(en, mm.groups()) + tail
    if "、" in core_n and len(core_n) < 60:
        parts = [tr_text(x) for x in core_n.split("、")]
        if not any(CJK.search(x) for x in parts): return lead + ", ".join(parts) + tail
    return t   # 没翻到：保留中文（残留计数）

class Tr(HTMLParser):
    """逐 token 重建 HTML，只改文本与选定属性。"""
    ATTRS = {"title", "alt", "placeholder", "aria-label", "content", "data-label"}
    def __init__(self): super().__init__(convert_charrefs=False); self.out = []; self.skip = 0; self.left = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1
        parts = []
        for k, v in attrs:
            if v is None: parts.append(k); continue
            if k in self.ATTRS and CJK.search(v):
                nv = tr_text(v)
                if CJK.search(nv): self.left += 1
                v = nv
            parts.append('%s="%s"' % (k, v.replace('"', "&quot;")))
        self.out.append("<%s%s>" % (tag, (" " + " ".join(parts)) if parts else ""))
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs)
    def handle_endtag(self, tag):
        if tag in ("script", "style"): self.skip = max(0, self.skip - 1)
        self.out.append("</%s>" % tag)
    def handle_data(self, d):
        if self.skip: self.out.append(d); return
        if CJK.search(d):
            nd = tr_text(d)
            if CJK.search(nd): self.left += 1
            self.out.append(nd)
        else: self.out.append(d)
    def handle_entityref(self, n): self.out.append("&%s;" % n)
    def handle_charref(self, n): self.out.append("&#%s;" % n)
    def handle_comment(self, d): self.out.append("<!--%s-->" % d)
    def handle_decl(self, d): self.out.append("<!%s>" % d)

JS_RULES = sorted(DICT.get("js", {}).items(), key=lambda x: -len(x[0]))
def js_tr(js):
    for zh, en in JS_RULES: js = js.replace(zh, en)
    return js

def inline_js(html):
    """页内 <script>（非 JSON-LD）里的中文字面量，按 JS 词典替换。"""
    def fix(m):
        if "ld+json" in m.group(1): return m.group(0)
        return "<script%s>%s</script>" % (m.group(1), js_tr(m.group(2)))
    return re.sub(r"<script([^>]*)>(.*?)</script>", fix, html, flags=re.S)

def relink(html, base):
    """站内绝对路径改 /en/ 前缀（资源与接口除外）。"""
    keep = ("/assets/", "/fonts/", "/img/", "/api/", "/go/", "/badge/", "/history/", "/data_v2.json", "/media.json", "/go_links.json", "/feed.xml", "/llms.txt", "/sitemap", "/favicon", "/robots")
    def fix(m):
        attr, q, url = m.group(1), m.group(2), m.group(3)
        if url.startswith(keep) or url.startswith("/en/") or url == "/en": return m.group(0)
        if url == "/": return '%s=%s/en/%s' % (attr, q, q)
        return '%s=%s/en%s%s' % (attr, q, url, q)
    html = re.sub(r'\b(href|action)=(["\'])(/[^"\']*)\2', fix, html)
    # 三站之间的绝对 URL 都指向对方的英文页（Robo 本身就有 /en/）
    for host in ("https://compute.sinanlab.com", "https://robo.sinanlab.com", "https://sinanlab.com"):
        html = re.sub(r'(href=["\'])' + re.escape(host) + r'(/(?!en/|en"|assets/|api/|img/|fonts/|badge/|history/|feed|llms|data_v2|media\.json|go/|sitemap|robots|favicon)[^"\']*)?(["\'])',
                      lambda m: m.group(1) + host + "/en" + (m.group(2) or "/") + m.group(3), html)
    return html

def head_fix(html, base, path_zh):
    en_path = "/en/" if path_zh == "/" else "/en" + path_zh
    html = html.replace('<html lang="zh-CN"', '<html lang="en"', 1)
    html = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s%s">' % (base, en_path), html, 1)
    html = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s%s">' % (base, en_path), html, 1)
    html = html.replace('"inLanguage": "zh-CN"', '"inLanguage": "en"')
    alt = '<link rel="alternate" hreflang="zh-CN" href="%s%s"><link rel="alternate" hreflang="en" href="%s%s"><link rel="alternate" hreflang="x-default" href="%s%s">' % (base, path_zh, base, en_path, base, path_zh)
    html = html.replace("</head>", alt + "</head>", 1)
    html = html.replace("/assets/app.js?", "/assets/app.en.js?").replace('src="/assets/app.js"', 'src="/assets/app.en.js"')
    return html

def switch_link(html, to_href, label):
    """顶栏语言切换：Compute 放在 #auth 前；母站放在 .right 里。"""
    a = '<a class="lang" href="%s" hreflang="%s" style="font-family:var(--mono);font-size:11.5px;border:1px solid var(--hair-2);border-radius:999px;padding:4px 10px;color:var(--ink-2);background:var(--card);margin-right:6px;white-space:nowrap;line-height:1.4">%s</a>' % (to_href, "en" if label == "EN" else "zh-CN", label)
    if '<div class="auth" id="auth"></div>' in html:
        return html.replace('<div class="auth" id="auth"></div>', a + '<div class="auth" id="auth"></div>', 1)
    if '<span class="auth" id="auth"></span>' in html:
        return html.replace('<span class="auth" id="auth"></span>', a + '<span class="auth" id="auth"></span>', 1)
    return html

def zh_path_of(rel):
    p = "/" + rel[:-5] if rel.endswith(".html") else "/" + rel
    if p.endswith("/index"): p = p[:-5] or "/"
    return p

def main(dist, base):
    left_total = 0; n = 0
    for root, _, files in os.walk(dist):
        if os.path.relpath(root, dist).startswith("en"): continue
        for fn in files:
            if not fn.endswith(".html"): continue
            src = os.path.join(root, fn); rel = os.path.relpath(src, dist).replace(os.sep, "/")
            html = io.open(src, encoding="utf-8").read()
            html = re.sub(r'<a class="lang" [^>]*>EN</a>', "", html)
            html = re.sub(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*">', "", html)
            path_zh = zh_path_of(rel)
            # 中文页加 EN 切换（幂等）
            if 'hreflang="en"' not in html:
                en_p = "/en/" if path_zh == "/" else "/en" + path_zh
                zh_html = switch_link(html, en_p, "EN")
                zh_html = zh_html.replace("</head>", '<link rel="alternate" hreflang="en" href="%s%s"><link rel="alternate" hreflang="zh-CN" href="%s%s"></head>' % (base, en_p, base, path_zh), 1)
                io.open(src, "w", encoding="utf-8").write(zh_html)
            t = Tr(); t.feed(html); en_html = "".join(t.out)
            en_html = inline_js(en_html)
            en_html = head_fix(relink(en_html, base), base, path_zh)
            en_html = switch_link(en_html, path_zh, "中文")
            dst = os.path.join(dist, "en", rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            io.open(dst, "w", encoding="utf-8").write(en_html)
            left_total += t.left; n += 1
    # app.en.js
    js_src = os.path.join(dist, "assets", "app.js")
    if os.path.exists(js_src):
        js = io.open(js_src, encoding="utf-8").read()
        js = js_tr(js)
        js = js.replace('location.href="/s/"+s.d', 'location.href="/en/s/"+s.d').replace('location.href="/#m="+m.id', 'location.href="/en/#m="+m.id')
        js = js.replace('href="/s/', 'href="/en/s/').replace("href='/s/", "href='/en/s/").replace('href="/m/', 'href="/en/m/').replace('href="/media/', 'href="/en/media/').replace('href="/me"', 'href="/en/me"').replace('href="/sites', 'href="/en/sites')
        # 数据 JSON 里的中文：esc() 出口处按 DATA 表翻（精确表 + 正则表，捕获组里的中文递归再翻）
        exact = {k: v for k, v in DICT.get("data", {}).items() if "{n}" not in k and "{s}" not in k}
        def to_js_tpl(v):
            i = [0]
            def rep(m): i[0] += 1; return "$%d" % i[0]
            return re.sub(r"\{[ns]\}", rep, v)
        rules = []
        for k, v in sorted(DICT.get("data", {}).items(), key=lambda x: (x[0].count("{s}"), -len(x[0]))):
            if "{n}" in k or "{s}" in k:
                rx = "^" + re.escape(k).replace(re.escape("{n}"), r"(\d[\d,\.]*)").replace(re.escape("{s}"), "(.+?)") + "$"
                rules.append([rx, to_js_tpl(v)])
        shim = ("var __TX=%s,__TR=%s;function __T(s){if(!/[\\u4e00-\\u9fff]/.test(s))return s;if(__TX[s])return __TX[s];"
                "for(var i=0;i<__TR.length;i++){var m=new RegExp(__TR[i][0]).exec(s);if(m){var out=__TR[i][1];for(var k=1;k<m.length;k++){var g=m[k];if(/[\\u4e00-\\u9fff]/.test(g))g=__T(g);out=out.split(\"$\"+k).join(g)}return out}}return s}\n"
                % (json.dumps(exact, ensure_ascii=False), json.dumps(rules, ensure_ascii=False)))
        js = shim + js.replace('function esc(s){return String(s==null?"":s)', 'function esc(s){return __T(String(s==null?"":s))', 1)
        io.open(os.path.join(dist, "assets", "app.en.js"), "w", encoding="utf-8").write(js)
        print("app.en.js 残留中文字面量：%d" % len(re.findall(r'"[^"\n]*[一-鿿][^"\n]*"', js)))
    # sitemap：加英文页
    sm = os.path.join(dist, "sitemap.xml")
    if os.path.exists(sm):
        s = io.open(sm, encoding="utf-8").read()
        if "/en/" not in s:
            locs = re.findall(r"<loc>(%s[^<]*)</loc>" % re.escape(base), s)
            add = "".join("  <url><loc>%s</loc></url>\n" % (base + "/en" + u[len(base):]) for u in locs)
            io.open(sm, "w", encoding="utf-8").write(s.replace("</urlset>", add + "</urlset>"))
    print("英文页 %d 个 · 残留未翻文本节点 %d" % (n, left_total))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "dist"), sys.argv[2] if len(sys.argv) > 2 else "https://compute.sinanlab.com")
