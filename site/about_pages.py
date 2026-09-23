# -*- coding: utf-8 -*-
"""站方说明页：面板公开的「关于 / 说明」正文（one-api 系的 /api/about，匿名可读，不需要 Key）。

我们不转载站方写的内容，只做三件可核实的事：
  1. 记录它确实公开可读（HTTP 状态 + 抓取时间 + 正文哈希）；
  2. 存一份快照，读者能自己回溯；
  3. 用固定词表列出这份说明覆盖了哪些话题（支付方式 / 最低充值 / 退款 / 发票 / 计价口径 / 地区限制）。
活动、赠金、优惠、联系方式一律不进话题表：那是站方的促销内容，不是测量。

写 site/about_pages.json：{domain: {url, fetched, sha256, chars, topics, self_updated}}
快照正文写 data/raw/about.<domain>/<sha256>，并记一行 source_snapshot。
用法：python3 site/about_pages.py [并发数]
"""
import os, io, re, sys, json, time, hashlib, sqlite3, html as _html
import urllib.request, urllib.error
import concurrent.futures as cf

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
UA = "SinanLabBot/1.0 (+https://compute.sinanlab.com/method)"
TIMEOUT = 10
MIN_CHARS = 200          # 正文太短的是面板默认空页，不算「有说明页」
MAX_BYTES = 800000

# 只认这几个中性话题；顺序即展示顺序
TOPICS = [
    ("支付方式", re.compile(r"支付方式|微信支付|支付宝|USDT|TRC ?20|PayPal|信用卡|对公转账", re.I)),
    ("最低充值", re.compile(r"最低充值|最低起充|起充|最低订单|最低购买")),
    ("退款", re.compile(r"退款|退费|退还")),
    ("发票", re.compile(r"发票|开票")),
    ("计价口径", re.compile(r"计价|计费|额度单位|站内额度|倍率|billing_expr", re.I)),
    ("地区限制", re.compile(r"地区限制|不提供访问|大陆地区|仅限.{0,6}地区|禁止.{0,6}地区")),
]
_UPD = re.compile(r"(?:更新(?:时间|于)|最后更新|Last updated)[：: ]*([0-9]{4})\s*[-年/]\s*([0-9]{1,2})\s*[-月/]\s*([0-9]{1,2})", re.I)


def strip_html(s):
    t = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", s, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "\n", t); t = _html.unescape(t)
    t = t.replace("\\n", "\n").replace('\\"', '"')
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n{2,}", "\n", t).strip()


def fetch(domain):
    url = "https://%s/api/about" % domain
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES); status = r.status
    except urllib.error.HTTPError as e:
        return domain, {"err": "http_%d" % e.code}
    except Exception as e:
        return domain, {"err": type(e).__name__}
    if status != 200: return domain, {"err": "http_%d" % status}
    try:
        j = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return domain, {"err": "not_json"}
    data = j.get("data")
    if not isinstance(data, str): return domain, {"err": "no_data"}
    text = strip_html(data)
    if len(text) < MIN_CHARS: return domain, {"err": "empty"}
    m = _UPD.search(text)
    return domain, {
        "url": url, "public_url": "https://%s/about" % domain,
        "fetched": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(time.time() + 15 * 3600)),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "chars": len(text),
        "topics": [name for name, rx in TOPICS if rx.search(text)],
        "self_updated": ("%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3))) if m else None),
        "_text": text,
    }


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    db = sqlite3.connect(os.path.join(ROOT, "data", "compass.sqlite"))
    # 域名取自站库本身，不依赖 data_v2.json，避免与导出步骤的先后顺序耦合
    doms = [r[0] for r in db.execute("SELECT DISTINCT domain FROM relay_candidate WHERE level>=1 ORDER BY domain")]
    out = {}; errs = {}
    with cf.ThreadPoolExecutor(workers) as ex:
        for dom, r in ex.map(fetch, doms):
            if r.get("err"): errs[r["err"]] = errs.get(r["err"], 0) + 1; continue
            text = r.pop("_text")
            key = "raw/about.%s/%s" % (dom, r["sha256"])
            p = os.path.join(ROOT, "data", key)
            if not os.path.exists(p):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                io.open(p, "w", encoding="utf-8").write(text)
            r["raw_key"] = key
            row = db.execute("SELECT id FROM source_snapshot WHERE source=? AND sha256=?", ("about.%s" % dom, r["sha256"])).fetchone()
            if not row:
                db.execute("INSERT INTO source_snapshot(source,url,fetched_at,http_status,sha256,raw_key,fetch_note) VALUES(?,?,?,?,?,?,?)",
                           ("about.%s" % dom, r["url"], r["fetched"], 200, r["sha256"], key, "站方说明页正文（站方自述，未核实）"))
            out[dom] = r
    db.commit(); db.close()
    io.open(os.path.join(HERE, "about_pages.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    from collections import Counter
    c = Counter(t for v in out.values() for t in v["topics"])
    print("站方说明页：扫 %d 站 · 公开可读 %d 站 · %s · 未取到 %s" % (
        len(doms), len(out), " · ".join("%s %d" % kv for kv in c.most_common()),
        " ".join("%s=%d" % kv for kv in sorted(errs.items(), key=lambda x: -x[1])[:4])))


if __name__ == "__main__": main()
