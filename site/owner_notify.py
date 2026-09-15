# -*- coding: utf-8 -*-
"""站长自动通知：站点发生"可测量的事"时给站长发一封信，只陈述事实、附徽章代码，不推销。
事件（每站每事只发一封，每站每周最多一封，每天全局最多 25 封）：
  rank     本周进入某张司南榜（rank_badge）        → 榜名、名次、测量值、徽章嵌入代码
  verified 首次拿到"经司南核验"标识                → 条件、徽章代码
  hold     本站有报价进入"待核"（quality_hold 新开）→ 我们抓到的原文与疑点，请站长核对回复
联系方式：从该站面板的公开快照里抽邮箱（site_contact 表，每晚重扫）。
开闸：data/secrets.env 里 OWNER_MAIL_ENABLED=1；否则只打印将要发送的清单（dry-run）。退订由线上 KV optout 记录，run.js 发送前检查。
用法：python3 site/owner_notify.py [--dry]"""
import os, io, re, sys, json, sqlite3, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from notify_email import run as mail_run
BASE = "https://compute.sinanlab.com"
BJ = dt.timezone(dt.timedelta(hours=8))
EM = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
BAD = ('example.', 'sentry', 'wixpress', 'schema.org', 'w3.org', 'noreply', 'no-reply', '@2x', '.png', '.jpg', '.svg', '.webp', '.css', '.js', 'yourdomain', 'test@', 'admin@admin', 'user@')
DAILY_CAP = 25

def env():
    p = os.path.join(ROOT, "data", "secrets.env"); out = {}
    if os.path.exists(p):
        for l in io.open(p, encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l: k, v = l.split("=", 1); out[k.strip()] = v.strip()
    return out

def rescan_contacts(db):
    db.execute("CREATE TABLE IF NOT EXISTS site_contact(domain TEXT PRIMARY KEY, email TEXT, source TEXT, seen TEXT)")
    n = 0
    for r in db.execute("SELECT c.domain, s.raw_key, s.url FROM relay_candidate c JOIN source_snapshot s ON s.id=c.snapshot_id WHERE c.level>=1").fetchall():
        p = os.path.join(ROOT, "data", r[1])
        if not os.path.exists(p): continue
        try: t = open(p, "rb").read(400000).decode("utf-8", "ignore")
        except Exception: continue
        ems = sorted(set(e.lower() for e in EM.findall(t) if not any(b in e.lower() for b in BAD)))
        if not ems: continue
        # 优先本域邮箱，其次 support/contact/admin 前缀
        dom = r[0].split(".")[-2] if "." in r[0] else r[0]
        ems.sort(key=lambda e: (0 if dom in e.split("@")[1] else 1, 0 if e.split("@")[0] in ("support", "contact", "admin", "hello", "service") else 1))
        db.execute("INSERT INTO site_contact(domain,email,source,seen) VALUES(?,?,?,?) ON CONFLICT(domain) DO UPDATE SET email=excluded.email, source=excluded.source, seen=excluded.seen", (r[0], ems[0], r[2], dt.datetime.now(BJ).isoformat()[:19])); n += 1
    db.commit(); return n

def main():
    dry = "--dry" in sys.argv or env().get("OWNER_MAIL_ENABLED") != "1"
    db = sqlite3.connect(os.path.join(ROOT, "data", "compass.sqlite")); db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS owner_mail(domain TEXT, event TEXT, email TEXT, sent_at TEXT, PRIMARY KEY(domain, event))")
    n_contacts = rescan_contacts(db)
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    contacts = {r["domain"]: r["email"] for r in db.execute("SELECT domain, email FROM site_contact")}
    today = dt.datetime.now(BJ).date(); week_ago = (today - dt.timedelta(days=7)).isoformat()
    recent = set(r[0] for r in db.execute("SELECT domain FROM owner_mail WHERE sent_at >= ?", (week_ago,)))
    sent_today = db.execute("SELECT COUNT(*) FROM owner_mail WHERE substr(sent_at,1,10)=?", (today.isoformat(),)).fetchone()[0]
    items = []
    def push(dom, event, kind, extra):
        if dom not in contacts or dom in recent: return
        if db.execute("SELECT 1 FROM owner_mail WHERE domain=? AND event=?", (dom, event)).fetchone(): return
        if any(x["domain"] == dom for x in items): return
        s = next((s_ for s_ in D["sites"] if s_["domain"] == dom), None)
        items.append(dict(to=contacts[dom], domain=dom, name=(s or {}).get("name") or dom, event=event, kind=kind, **extra))
    R = D["rank"]; wk = R["week"]
    for s in D["sites"]:
        rb = s.get("rank_badge")
        if rb and rb["week"] == wk: push(s["domain"], "rank:%s:%s" % (wk, rb["board"]), "rank", {"board": rb["board"], "board_name": rb["board_name"], "pos": rb["pos"], "value": rb.get("value"), "week": wk, "badge": "%s/badge/%s.svg" % (BASE, s["domain"]), "rank_url": "%s/rank/%s" % (BASE, wk)})
        if s.get("verified"): push(s["domain"], "verified:%s" % today.strftime("%Y-%m"), "verified", {"badge": "%s/badge/verified/%s.svg" % (BASE, s["domain"])})
    for h in db.execute("SELECT id, vendor, model, raw_name, unit, reason, detail, created FROM quality_hold WHERE cleared IS NULL AND created >= ?", (week_ago,)):
        push(h["vendor"], "hold:%d" % h["id"], "hold", {"model": h["raw_name"] or h["model"], "unit": h["unit"], "reason": h["reason"], "detail": (h["detail"] or "")[:300], "created": (h["created"] or "")[:10]})
    items = items[:max(0, DAILY_CAP - sent_today)]
    print("站长通知：联系方式 %d 站 · 候选 %d 封（%s）" % (n_contacts, len(items), "dry-run，未发送" if dry else "发送"))
    for it in items: print("  %-28s %-9s → %s" % (it["domain"], it["kind"], it["to"]))
    if dry or not items: return
    mail_run("owner", {"items": items, "date": today.isoformat()})
    now = dt.datetime.now(BJ).isoformat()[:19]
    for it in items: db.execute("INSERT OR REPLACE INTO owner_mail(domain,event,email,sent_at) VALUES(?,?,?,?)", (it["domain"], it["event"], it["to"], now))
    db.commit()

if __name__ == "__main__": main()
