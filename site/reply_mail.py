# -*- coding: utf-8 -*-
"""
用 notify@sinanlab.com 给某个地址发一封人工回信（回复地址 hello@sinanlab.com）。
正文按空行分段；发之前过一遍措辞自检（禁用词命中就不发）。

用法：python3 site/reply_mail.py <收件人> "<主题>" <正文文件.txt>
     python3 site/reply_mail.py --dry ...   只预览不发送
"""
import os, io, sys, json, secrets, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import httpx
from core.wording import lint
BASE = "https://compute.sinanlab.com"


def d1(sql):
    r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--command", sql], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if r.returncode != 0: raise RuntimeError("wrangler d1 失败：" + (r.stderr or r.stdout)[-300:])


def main():
    args = [a for a in sys.argv[1:] if a != "--dry"]; dry = "--dry" in sys.argv
    if len(args) != 3: return print(__doc__)
    to, subject, body_p = args
    body = io.open(body_p, encoding="utf-8").read().strip()
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    hits = [x for x in lint(subject + "\n" + body) if x[1] == "banned_term"]
    if hits: return print("措辞自检未通过，未发送：", hits[:3])
    print("收件人 %s\n主题 %s\n段落 %d\n---\n%s\n---" % (to, subject, len(paras), body[:1200]))
    if dry: return print("（dry-run，未发送）")
    tok = secrets.token_hex(32); th = hashlib.sha256(tok.encode()).hexdigest()
    d1("INSERT INTO notify_jobs(token_hash, kind) VALUES('%s','reply')" % th)
    r = httpx.post(BASE + "/api/notify/run", json={"token": tok, "kind": "reply", "payload": {"to": to, "subject": subject, "paragraphs": paras}}, timeout=120)
    print("HTTP %d %s" % (r.status_code, r.text[:300]))


if __name__ == "__main__":
    main()
