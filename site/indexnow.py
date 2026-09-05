# -*- coding: utf-8 -*-
"""IndexNow：部署后把更新过的 URL 推给 Bing（IndexNow 参与方之间互相同步；Google 不支持，靠 sitemap）。通用端点 api.indexnow.org 在本机代理下返回 403，直接用 bing.com 端点。
密钥文件 site/indexnow.key（随机 32 位，随仓库），构建时复制成 dist/<key>.txt 供验证。"""
import os, io, json, sys, secrets
import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://compute.sinanlab.com"
KEYF = os.path.join(HERE, "indexnow.key")

def key():
    if not os.path.exists(KEYF):
        io.open(KEYF, "w").write(secrets.token_hex(16))
    return io.open(KEYF).read().strip()

def urls():
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    u = [BASE + "/", BASE + "/sites", BASE + "/media", BASE + "/method", BASE + "/feed.xml"]
    u += [BASE + "/m/" + m["id"] for m in D["models"]]
    # 站点页：今天有变价或新收录的
    changed = {c["vendor"] for c in D.get("changes", [])} | set(D.get("new_sites", [])[:200])
    u += [BASE + "/s/" + d for d in sorted(changed) if any(s["domain"] == d for s in D["sites"])]
    u += [BASE + "/en" + x[len(BASE):] for x in list(u)]   # 英文镜像页一起推
    return u[:10000]

def main():
    k = key(); us = urls()
    body = {"host": "compute.sinanlab.com", "key": k, "keyLocation": "%s/%s.txt" % (BASE, k), "urlList": us}
    try:
        r = httpx.post("https://www.bing.com/indexnow", json=body, timeout=30, headers={"Content-Type": "application/json; charset=utf-8"})
        print("IndexNow：提交 %d 个 URL → HTTP %d" % (len(us), r.status_code))
    except Exception as e:
        print("IndexNow 提交失败：", e)

if __name__ == "__main__":
    main()
