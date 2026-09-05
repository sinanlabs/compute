# -*- coding: utf-8 -*-
"""导出 go_links.json：domain -> {url, referral_url, label}。referral 默认空。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
db=D.connect(); out={}
import re as _re
def _ok(u, dom):
    # 目标地址守卫：https + 公网主机名 + 与收录域同注册域，否则回退 https://<域名>/
    try:
        m=_re.match(r"^https://([a-z0-9.\-]+)(/|$)", (u or "").strip().lower()); h=m.group(1) if m else ""
        return bool(h) and (h==dom or h.endswith("."+dom) or dom.endswith("."+h))
    except Exception: return False
for r in db.execute("SELECT domain, site_url, referral_url, referral_label FROM relay_candidate WHERE level>=1"):
    url = r["site_url"] if _ok(r["site_url"], r["domain"]) else "https://%s/" % r["domain"]
    out[r["domain"]]={"url": url, "referral_url": r["referral_url"], "label": r["referral_label"] or ("广告" if r["referral_url"] else None)}
p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"go_links.json")
json.dump(out, open(p,"w"), ensure_ascii=False, indent=1)
print("go_links.json：%d 站，其中带推广参数 %d" % (len(out), sum(1 for v in out.values() if v["referral_url"])))
