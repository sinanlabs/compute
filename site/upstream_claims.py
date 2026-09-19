# -*- coding: utf-8 -*-
"""上游自述：从各站面板的公开文字（公告、模型分组名、模型描述）里抽"站方自己怎么说上游来源"，不需要 Key。
只记录出现了什么说法与原文片段，不核实、不判断真伪。写 site/upstream_claims.json：{domain: {tags: [...], snippets: {tag: 原文}}}"""
import os, io, re, json, sqlite3, html as _html, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.wording import BANNED as _BANNED
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TAGS = [
    ("官转", re.compile(r"官转|官方[渠通]道|官方直连|官方\s?API|官方接口|企业(账号|号|版)", re.I)),
    ("订阅号池", re.compile(r"号池|账号池|共享账号|拼车|席位|(claude\s?code|codex|chatgpt|gpt|gemini|grok)[^。\n]{0,14}(max|pro|plus|team|ultra|订阅)|(max|pro|plus|team|ultra)[^。\n]{0,6}(池|共享|拼|转售)", re.I)),
    ("逆向", re.compile(r"逆向|网页版转|web2api|reverse\s?(engineer|proxy)|cookie\s?池", re.I)),
    ("云厂商额度", re.compile(r"\bazure\b|(?<![A-Za-z0-9+/=])AZ(?![A-Za-z0-9+/=])|bedrock|vertex\s?ai|(?<![A-Za-z0-9+/=])aws(?![A-Za-z0-9+/=])|(?<![A-Za-z0-9+/=])gcp(?![A-Za-z0-9+/=])", re.I)),
    ("公益免费", re.compile(r"公益站|公益|免费额度|白嫖|签到送", re.I)),
]

_B64 = re.compile(r"[A-Za-z0-9+/=]{24,}")
_CJK = re.compile(r"[\u4e00-\u9fff]")
def clean_text(t):
    """先把面板原文从 HTML / JSON 里洗成正文：去标签、还原实体、去转义引号。"""
    t = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t); t = _html.unescape(t); t = t.replace('\\"', '"').replace("\\n", "\n")
    return re.sub(r"[ \t\r\f\v]+", " ", t)
def clean_snip(t, m, tag):
    """取匹配所在的句子；含禁用词、像 base64、没有中文、太短的都不要（宁缺毋滥：自述是给读者看的原文，不是证据）。"""
    a = max(0, m.start() - 60); b = min(len(t), m.end() + 60); seg = t[a:b]
    parts = re.split(r"[。！？!?\n]", seg)
    off = m.start() - a; acc = 0; sent = seg
    for pt in parts:
        if acc <= off <= acc + len(pt): sent = pt; break
        acc += len(pt) + 1
    sent = re.sub(r"\s+", " ", sent).strip(" ,，;；:：\"'「」【】[]{}")
    if len(sent) > 60: sent = sent[:60].rstrip() + "…"
    if len(sent) < 6 or _B64.search(sent) or len(_CJK.findall(sent)) < 4 and tag != "云厂商额度": return None
    low = sent.lower()
    if any(w.lower() in low for w in _BANNED): return None
    if re.search(r"[{}\[\]<>]|\\\\|https?://", sent): return None
    return sent

def main():
    db = sqlite3.connect(os.path.join(ROOT, "data", "compass.sqlite")); db.row_factory = sqlite3.Row
    out = {}; n = 0
    for r in db.execute("SELECT c.domain, c.panel_kind, s.raw_key FROM relay_candidate c JOIN source_snapshot s ON s.id=c.snapshot_id WHERE c.level>=1"):
        p = os.path.join(ROOT, "data", r["raw_key"])
        if not os.path.exists(p): continue
        try: t = open(p, "rb").read(300000).decode("utf-8", "ignore")
        except Exception: continue
        n += 1; tags, snip = [], {}; t = clean_text(t)
        if r["panel_kind"] == "sub2api": tags.append("订阅制面板"); snip["订阅制面板"] = "Sub2API 面板：按套餐转售订阅席位（面板类型判定，非文字）"
        for tag, rx in TAGS:
            if tag == "订阅号池" and r["panel_kind"] == "sub2api": continue
            for m in rx.finditer(t):
                sn = clean_snip(t, m, tag)
                if sn: tags.append(tag); snip[tag] = sn; break   # 只保留能干净引用的说法；抽不出干净原文就不打这个标签
        if tags: out[r["domain"]] = {"tags": tags, "snippets": snip}
    io.open(os.path.join(HERE, "upstream_claims.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    from collections import Counter
    c = Counter(t for v in out.values() for t in v["tags"])
    print("上游自述：扫 %d 站 · 有说法 %d 站 · %s" % (n, len(out), " · ".join("%s %d" % kv for kv in c.most_common())))
if __name__ == "__main__": main()
