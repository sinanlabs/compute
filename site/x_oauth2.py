# -*- coding: utf-8 -*-
"""X（推特）OAuth 2.0 用户授权（PKCE）：用 Client ID / Client Secret 换取能发帖的用户令牌。凭据只在本机 data/secrets.env。
  python3 site/x_oauth2.py auth              → 打印授权链接（Eric 用 SinanLab 账号打开并同意，跳回 compute.sinanlab.com/?code=…）
  python3 site/x_oauth2.py exchange "<跳回的完整 URL>"   → 换取 access/refresh token 写进 secrets.env
  python3 site/x_oauth2.py refresh           → 用 refresh token 换新 access token（social_post 自动调用）"""
import os, io, sys, json, base64, hashlib, secrets, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ENVP = os.path.join(ROOT, "data", "secrets.env"); REDIRECT = "https://compute.sinanlab.com/"
SCOPES = "tweet.read tweet.write users.read offline.access"

def env():
    out = {}
    if os.path.exists(ENVP):
        for l in io.open(ENVP, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l: k, v = l.split("=", 1); out[k.strip()] = v.strip()
    return out
def save(upd):
    E = env(); E.update(upd)
    io.open(ENVP, "w", encoding="utf-8").write("\n".join("%s=%s" % kv for kv in E.items()) + "\n")
def basic(E): return "Basic " + base64.b64encode(("%s:%s" % (E["X_CLIENT_ID"], E["X_CLIENT_SECRET"])).encode()).decode()
def token_call(E, data):
    req = urllib.request.Request("https://api.x.com/2/oauth2/token", data=urllib.parse.urlencode(data).encode(), headers={"Authorization": basic(E), "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "sinan-social/0.1"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8", "ignore")[:400]

KV_NS = "01d14fee71b2465d906fdccbf4eac4bb"
def kv_load():
    """从线上 KV 读 x:oauth2（线上回调换取到的令牌），写进本机 secrets.env。"""
    import subprocess
    r = subprocess.run(["npx", "wrangler", "kv", "key", "get", "--namespace-id", KV_NS, "--remote", "x:oauth2"], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not r.stdout.strip().startswith("{"): print("KV 里还没有 X 令牌：", (r.stderr or r.stdout)[-200:]); return False
    js = json.loads(r.stdout); save({"X_OAUTH2_ACCESS": js["access_token"], "X_OAUTH2_REFRESH": js.get("refresh_token", "")}); print("已从线上取回 X 用户令牌（scope：%s）" % js.get("scope")); return True
def kv_save(E):
    import subprocess
    subprocess.run(["npx", "wrangler", "kv", "key", "put", "--namespace-id", KV_NS, "--remote", "x:oauth2", json.dumps({"access_token": E["X_OAUTH2_ACCESS"], "refresh_token": E.get("X_OAUTH2_REFRESH", ""), "obtained_at": __import__("datetime").datetime.utcnow().isoformat()})], cwd=ROOT, capture_output=True, text=True, timeout=120)

def main():
    E = env(); cmd = sys.argv[1] if len(sys.argv) > 1 else "auth"
    if cmd == "kv-load": kv_load(); return
    if cmd == "auth":
        verifier = secrets.token_urlsafe(64)[:100]; challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        state = secrets.token_urlsafe(16); save({"X_PKCE_VERIFIER": verifier, "X_PKCE_STATE": state})
        q = {"response_type": "code", "client_id": E["X_CLIENT_ID"], "redirect_uri": REDIRECT, "scope": SCOPES, "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
        print("https://x.com/i/oauth2/authorize?" + urllib.parse.urlencode(q))
    elif cmd == "exchange":
        u = urllib.parse.urlparse(sys.argv[2]); qs = urllib.parse.parse_qs(u.query)
        if qs.get("state", [""])[0] != E.get("X_PKCE_STATE"): print("state 不匹配，重新 auth"); return
        st, js = token_call(E, {"grant_type": "authorization_code", "code": qs["code"][0], "redirect_uri": REDIRECT, "code_verifier": E["X_PKCE_VERIFIER"], "client_id": E["X_CLIENT_ID"]})
        if st != 200: print("换取失败", st, js); return
        save({"X_OAUTH2_ACCESS": js["access_token"], "X_OAUTH2_REFRESH": js.get("refresh_token", "")}); print("已保存用户令牌（scope：%s）" % js.get("scope"))
    elif cmd == "refresh":
        st, js = token_call(E, {"grant_type": "refresh_token", "refresh_token": E["X_OAUTH2_REFRESH"], "client_id": E["X_CLIENT_ID"]})
        if st != 200: print("刷新失败", st, js); return
        save({"X_OAUTH2_ACCESS": js["access_token"], "X_OAUTH2_REFRESH": js.get("refresh_token", E["X_OAUTH2_REFRESH"])}); kv_save(env()); print("已刷新")
if __name__ == "__main__": main()
