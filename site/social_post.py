# -*- coding: utf-8 -*-
"""把当天发帖稿的英文短帖自动发到 X 与 Bluesky（有正式接口的平台）。凭据只在本机 data/secrets.env：
  X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET   （developer.x.com 免费档，应用权限必须是 Read and Write）
  BSKY_HANDLE / BSKY_APP_PASSWORD                                 （bsky.app 设置 → App Passwords）
每个平台每天最多一条（data/logs/.social_<平台> 记日期）；没配凭据就跳过。只依赖标准库。措辞来自 linuxdo_post.variants 的 x_en，已过措辞自检。"""
import os, io, sys, json, time, hmac, hashlib, base64, secrets, urllib.parse, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8))

def env():
    p = os.path.join(ROOT, "data", "secrets.env"); out = {}
    if os.path.exists(p):
        for l in io.open(p, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l: k, v = l.split("=", 1); out[k.strip()] = v.strip()
    return out

def once(platform, day):
    mark = os.path.join(ROOT, "data", "logs", ".social_" + platform); os.makedirs(os.path.dirname(mark), exist_ok=True)
    if os.path.exists(mark) and io.open(mark).read().strip() == day: return None
    return mark

def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=(json.dumps(data).encode() if data is not None else None), headers=dict({"User-Agent": "sinan-social/0.1", "Content-Type": "application/json"}, **(headers or {})), method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8", "ignore")[:300]

# ---------- X（OAuth 1.0a 用户上下文，标准库手写签名）
def _pct(s): return urllib.parse.quote(str(s), safe="~")
def x_post(E, text):
    url = "https://api.x.com/2/tweets"
    o = {"oauth_consumer_key": E["X_API_KEY"], "oauth_nonce": secrets.token_hex(16), "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())), "oauth_token": E["X_ACCESS_TOKEN"], "oauth_version": "1.0"}
    base = "&".join(["POST", _pct(url), _pct("&".join("%s=%s" % (_pct(k), _pct(v)) for k, v in sorted(o.items())))])
    key = _pct(E["X_API_SECRET"]) + "&" + _pct(E["X_ACCESS_SECRET"])
    o["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    auth = "OAuth " + ", ".join('%s="%s"' % (_pct(k), _pct(v)) for k, v in sorted(o.items()))
    return http(url, {"text": text}, {"Authorization": auth})

# ---------- Bluesky（AT 协议：建会话 → 写记录，链接做成可点的 facet）
def bsky_post(E, text):
    st, body = http("https://bsky.social/xrpc/com.atproto.server.createSession", {"identifier": E["BSKY_HANDLE"], "password": E["BSKY_APP_PASSWORD"]})
    if st != 200: return st, body
    s = json.loads(body); tb = text.encode("utf-8"); facets = []
    for tok in text.split():
        if tok.startswith("http"):
            i = tb.find(tok.encode("utf-8")); facets.append({"index": {"byteStart": i, "byteEnd": i + len(tok.encode("utf-8"))}, "features": [{"$type": "app.bsky.richtext.facet#link", "uri": tok}]})
    rec = {"$type": "app.bsky.feed.post", "text": text, "createdAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"), "langs": ["en"]}
    if facets: rec["facets"] = facets
    return http("https://bsky.social/xrpc/com.atproto.repo.createRecord", {"repo": s["did"], "collection": "app.bsky.feed.post", "record": rec}, {"Authorization": "Bearer " + s["accessJwt"]})

def main():
    E = env(); day = dt.datetime.now(BJ).date().isoformat()
    pj = os.path.join(ROOT, "data", "posts", "today.json")
    if not os.path.exists(pj): print("社媒：今天没有发帖稿"); return
    posts = json.load(io.open(pj, encoding="utf-8")); text = next((p.get("x_en") for p in posts if p.get("x_en")), None)
    if not text: print("社媒：没有英文短帖"); return
    jobs = [("x", all(E.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")), lambda: x_post(E, text[:280])),
            ("bluesky", bool(E.get("BSKY_HANDLE") and E.get("BSKY_APP_PASSWORD")), lambda: bsky_post(E, text[:300]))]
    for name, ready, fn in jobs:
        if not ready: print("社媒 %s：未配置凭据，跳过" % name); continue
        mark = once(name, day)
        if not mark: print("社媒 %s：今天已发" % name); continue
        st, body = fn(); ok = st in (200, 201)
        print("社媒 %s：HTTP %d %s" % (name, st, "" if ok else body[:160]))
        if ok: io.open(mark, "w").write(day)

if __name__ == "__main__": main()
