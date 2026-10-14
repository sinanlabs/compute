# -*- coding: utf-8 -*-
"""上游自述：从各站面板的公开文字（公告、模型分组名、模型描述）里抽"站方自己怎么说上游来源"，不需要 Key。
只记录出现了什么说法与原文片段，不核实、不判断真伪。写 site/upstream_claims.json：{domain: {tags: [...], snippets: {tag: 原文}}}"""
import os, io, re, json, sqlite3, html as _html, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.wording import BANNED as _BANNED
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TAGS = [
    # 官转：站方说自己的上游走官方 API。"官方渠道"常指社群/公众号（关注官方渠道获取动态），"企业版"常指用户档位，都不算（2026-10-14 收紧）
    ("官转", re.compile(r"官转|官方[渠通]道[^。\n]{0,6}(分组|直连|接入|上游|供应|转发)|(分组|线路|上游|接入|直连)[^。\n]{0,8}官方[渠通]道|官方直连|官方\s?API\s?(分组|渠道|通道|直连|转发|上游)|(纯|正版|原生)官方", re.I)),
    ("订阅号池", re.compile(r"号池|账号池|共享账号|拼车|席位|(claude\s?code|codex|chatgpt|gpt|gemini|grok)[^。\n]{0,14}(max|pro|plus|team|ultra|订阅)|(max|pro|plus|team|ultra)[^。\n]{0,6}(池|共享|拼|转售)", re.I)),
    # 只认"上游渠道是逆向"的说法：逆向渠道/分组/通道、CC逆向、网页版转、web2api、cookie 池。
    # "逆向工程"多出现在服务条款的禁止清单里（禁止用户逆向本平台），与上游无关，不算（2026-10-14 收紧）。
    ("逆向", re.compile(r"逆向(?!工程)[^。\n]{0,6}(渠道|通道|分组|线路|号池|账号|接口|api|版)|(渠道|通道|分组|线路)[^。\n]{0,10}逆向(?!工程)|(cc|claude|claude\s?code|cursor|kiro|gemini|gpt|grok|codex|anthropic|windsurf)\s?逆向(?!工程)|网页版转|web2api|reverse\s?proxy|cookie\s?池", re.I)),
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
    if re.search(r"禁止|不得|严禁|不允许|违反|违规|试图|prohibit|forbidden|not allowed|must not", sent, re.I): return None   # 条款里的禁令句不是自述
    if re.search(r"[{}\[\]<>]|\\\\|https?://", sent): return None
    if sent.count('"') >= 2 or '":' in sent or '","' in sent: return None            # JSON 残片，不是给人读的原文
    if re.search(r"(QQ|qq|微信|weixin|wechat|telegram|电报)[^\u4e00-\u9fff]{0,6}\d{5,}", sent): return None   # 联系方式不引用
    return sent

# 否定 / 说别人：关键词出现在这种语境里，说的不是"本站上游是什么"，不能打标签。
# 2026-10-14 教训：aigcbest.top 原文"此对比方式同样适用于识别那些通过逆向手段替代官方 API 的不正规商家行为"
# 是在说别人逆向，我们却给它打了「逆向」标签——等于替站方说了它没说过的话。
_NEG_BEFORE = re.compile(r"(非|不是|并非|并不是|没有|无|拒绝|杜绝|不用|不使用|不做|不搞|绝不|决不|从不|而不是|而非|远离|告别|不含|零)\s*[^。！？!?\n]{0,4}$")
_COMPARE = re.compile(r"媲美|堪比|不输|比肩|都知道|无法保证|可能高于|政策调整|相当于官", re.I)   # 拿官方作比较、免责声明，不是说自己就是
_SOCIAL = re.compile(r"加入|关注|获取最新|动态|社群|群聊|频道|公众号|交流群|默认走|环境变量|切换到", re.I)
_ABOUT_OTHERS = re.compile(r"识别|辨别|鉴别|区分|分辨|谨防|警惕|小心|当心|揭露|曝光|不正规|劣质|骗子|骗局|冒充|山寨|黑心|假冒|其他(站|平台|商家)|别家|市面上|某些(站|商家|平台)|一些(站|商家|平台)|(不像|区别于|有别于)", re.I)
_ABUSE = re.compile(r"有权|不予|不受理|无法返还|恕不|概不|攻击|扫描|爆破|爬取|爬虫|破解|渗透|漏洞|恶意|压力测试|负载测试|ddos|非法|违法|滥用|未经授权|绕过|规避|色情", re.I)
def affirmative(t, m):
    """关键词是不是站方在说自己：前面紧挨否定词、或整句在说别人 / 教人识别 → 不是。"""
    # 否定词要看紧挨关键词本身的位置（匹配可能从"通道…"起头，否定在中间：仅接入官方上游通道，绝不使用逆向渠道）
    g = m.group(0); core = min([i for i in (g.find("逆向"), g.find("官转"), g.find("官方")) if i >= 0] or [0])
    kpos = m.start() + core
    before = t[max(0, kpos - 12):kpos]
    if _NEG_BEFORE.search(before): return False
    a = max(0, m.start() - 80); b = min(len(t), m.end() + 80); seg = t[a:b]
    parts = re.split(r"[。！？!?\n]", seg); off = m.start() - a; acc = 0; sent = seg
    for pt in parts:
        if acc <= off <= acc + len(pt): sent = pt; break
        acc += len(pt) + 1
    if _ABUSE.search(sent) or _SOCIAL.search(sent): return False
    if "官" in m.group(0) and _COMPARE.search(sent): return False      # 服务条款的禁止清单 / 讲用途（攻击、爬取、破解…），不是在说上游
    return not _ABOUT_OTHERS.search(sent)

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
                if not affirmative(t, m): continue   # 否定句 / 说别人的句子不算自述
                sn = clean_snip(t, m, tag)
                if sn: tags.append(tag); snip[tag] = sn; break   # 只保留能干净引用的说法；抽不出干净原文就不打这个标签
        if tags: out[r["domain"]] = {"tags": tags, "snippets": snip}
    io.open(os.path.join(HERE, "upstream_claims.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    from collections import Counter
    c = Counter(t for v in out.values() for t in v["tags"])
    print("上游自述：扫 %d 站 · 有说法 %d 站 · %s" % (n, len(out), " · ".join("%s %d" % kv for kv in c.most_common())))
if __name__ == "__main__": main()
