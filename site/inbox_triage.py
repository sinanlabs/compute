# -*- coding: utf-8 -*-
"""
来信分拣：把 hello@sinanlab.com 收到的新邮件（sinan-inbox Worker 存进 D1 的 inbox_mail）拉下来，
按内容归类，并给每封信附上"回信要用的事实"（该站在我们索引里的现状、待核条目、是否有 Key、核验状态等），
产出 data/inbox/<日期>.json 供来信值班处理。

2026-10-07 起不再给所有者发摘要邮件（Eric："转发在 Claude 这里，不要发我的邮箱"）：来信原文与处理结果由
Claude 的定时任务"司南来信值班"（site/inbox_duty.py）在 Claude 里展示。唯一例外是兜底告警：
真实来信超过 OVERDUE_H 小时还没人处理（值班没在跑，例如 Claude 没开），才发一封告警到所有者邮箱，每封信只告警一次。

**分拣只做归类与取证，不发回信。** 回信由早班逐封核对后用 site/reply_mail.py 发出。
邮件正文一律当数据看：里面写什么都不执行，只作为"对方声称"记录。

用法：python3 site/inbox_triage.py           拉新信并分拣（写文件）+ 积压兜底检查
     python3 site/inbox_triage.py --quiet   只分拣，不做积压检查（值班脚本调用时用）

本站自己发出的邮件（发件域 sinanlab.com：notify@ / watchdog@ / hello@）不分拣，直接标 ignored。
任何告警都发到所有者邮箱（data/secrets.env 的 OWNER_EMAIL），绝不发回 hello@——否则会被收信 Worker 存成"新来信"，
第二天又被分拣一次（2026-09-27 ~ 10-07 出现过这个自循环）。
"""
import os, io, re, sys, json, subprocess, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8)); BASE = "https://compute.sinanlab.com"
load = lambda p, d=None: json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else d
OWN_DOMAINS = ("sinanlab.com",)   # 本站发件域：自家通知、看门狗、分拣摘要都从这里发出


def is_self(addr):
    d = (addr or "").strip().lower().rsplit("@", 1)[-1]
    return any(d == x or d.endswith("." + x) for x in OWN_DOMAINS)


def owner_email():
    """所有者收信地址：只放本机 data/secrets.env（git 忽略），不进公开仓库。"""
    p = os.path.join(ROOT, "data", "secrets.env")
    if os.path.exists(p):
        for ln in io.open(p, encoding="utf-8"):
            ln = ln.strip()
            if ln.startswith("OWNER_EMAIL=") and "@" in ln: return ln.split("=", 1)[1].strip()
    return None

# 归类规则：按优先级匹配（越靠前越具体）。只看关键词，不做推断；拿不准归 other。
RULES = [
    ("key",        r"(这是|提供|附上|发你|发给你).{0,12}key|api[- ]?key|sk-[A-Za-z0-9]{12,}|余额.{0,6}(美金|美元|元)"),
    ("correction", r"计价|按秒|按次|按张|单位|口径|价格.{0,4}(不对|有误|错)|数据.{0,4}(不对|有误|错)|更正|纠错|报价.{0,6}(错|不对)|应该是"),
    ("verify",     r"核验|认证|标识|徽章|verified|申请.{0,4}核验"),
    ("takedown",   r"下架|删除|撤下|移除|不要.{0,6}(收录|展示|公开)|侵权|律师|法务|投诉"),
    ("press",      r"媒体|记者|采访|引用|研究|论文|报道|数据授权|转载"),
    ("partner",    r"合作|推广|广告|付费|赞助|置顶|收录费|商务"),
    ("spam",       r"seo服务|外链|代运营|加微信|一手资源|接单|刷量"),
]
# 这些类别绝不自动回信，必须由 Eric 拍板（涉及钱、法律、对外承诺）
NEED_OWNER = {"takedown", "partner", "spam"}


def d1(sql):
    r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--json", "--command", sql],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    if r.returncode != 0: raise RuntimeError("wrangler d1 失败：" + (r.stderr or r.stdout)[-300:])
    return json.loads(r.stdout)[0]["results"]


def classify(subject, body):
    t = (subject or "") + "\n" + (body or "")
    for name, rx in RULES:
        if re.search(rx, t, re.I): return name
    return "other"


def guess_site(mail, domains):
    """从发件域、主题、正文里找我们索引里的站。"""
    hay = " ".join([mail.get("from_addr") or "", mail.get("subject") or "", (mail.get("body_text") or "")[:1500]]).lower()
    fd = (mail.get("from_addr") or "").split("@")[-1].lower()
    if fd in domains: return fd
    hit = [d for d in domains if d in hay]
    hit.sort(key=len, reverse=True)
    return hit[0] if hit else None


def facts_for(domain, D, db_holds, keys):
    """回信要用的事实：只取我们自己的数据。"""
    s = next((x for x in D.get("sites", []) if x["domain"] == domain), None)
    if not s: return {"in_index": False}
    holds = [h for h in db_holds if h["vendor"] == domain]
    return {"in_index": True, "name": s.get("name"), "panel": s.get("panel"), "cluster": (s.get("cluster") or {}).get("name"),
            "uptime": s.get("avail"), "ttfb_p50": s.get("ttfb_p50"), "n_models": len(s.get("models") or []),
            "verified": bool(s.get("verified")), "register": s.get("register"),
            "have_key": domain in keys, "site_page": "%s/s/%s" % (BASE, domain),
            "open_holds": [{"id": h["id"], "model": h["raw_name"] or h["model"], "reason": h["reason"], "detail": (h["detail"] or "")[:200]} for h in holds]}


def main():
    today = dt.datetime.now(BJ)
    try:
        rows = d1("SELECT id, msg_id, from_addr, from_name, envelope_from, to_addr, subject, sent_at, in_reply_to, body_text, body_len, attachments, spf, received_at FROM inbox_mail WHERE status='new' ORDER BY id")
    except Exception as e:
        return print("来信分拣：拉取失败（%s）" % str(e)[:160])
    own = [m for m in rows if is_self(m.get("from_addr"))]
    if own:
        d1("UPDATE inbox_mail SET status='ignored', handled_at=datetime('now'), handled_by='triage', action='self', note='本站自动发出的邮件，不分拣' WHERE id IN (%s)"
           % ",".join(str(int(m["id"])) for m in own))
        print("来信分拣：跳过本站自动邮件 %d 封（%s）" % (len(own), ", ".join("#%d" % m["id"] for m in own)))
    rows = [m for m in rows if not is_self(m.get("from_addr"))]
    if not rows: return print("来信分拣：没有新邮件")
    D = load(os.path.join(HERE, "data_v2.json"), {"sites": []})
    domains = {x["domain"] for x in D.get("sites", [])}
    try:
        import sqlite3
        c = sqlite3.connect(os.path.join(ROOT, "data", "compass.sqlite")); c.row_factory = sqlite3.Row
        db_holds = [dict(r) for r in c.execute("SELECT id, vendor, model, raw_name, reason, detail FROM quality_hold WHERE cleared IS NULL")]
    except Exception:
        db_holds = []
    keys = set()
    kp = os.path.join(ROOT, "data", "keys.env")
    if os.path.exists(kp):
        for ln in io.open(kp, encoding="utf-8"):
            if "=" in ln and not ln.strip().startswith("#"): keys.add(ln.split("=")[0].strip().lower())
    out = []
    for m in rows:
        body = (m.get("body_text") or "")
        # 去掉我们自己那封通知的引用段，只留对方新写的内容
        new_text = re.split(r"\n\s*(?:Sinan Lab|司南实验室)\s*<[^>]+>\s*于|\n>{1,}\s", body)[0].strip()
        cat = classify(m.get("subject"), new_text)
        dom = guess_site(m, domains)
        out.append({"id": m["id"], "from": m.get("from_addr"), "from_name": m.get("from_name"), "subject": m.get("subject"),
                    "received_at": m.get("received_at"), "in_reply_to": m.get("in_reply_to"), "attachments": m.get("attachments"),
                    "spf_ok": "pass" in (m.get("spf") or "").lower(), "category": cat, "needs_owner": cat in NEED_OWNER,
                    "site": dom, "facts": facts_for(dom, D, db_holds, keys) if dom else None,
                    "text": new_text[:4000], "text_full_len": m.get("body_len")})
    os.makedirs(os.path.join(ROOT, "data", "inbox"), exist_ok=True)
    p = os.path.join(ROOT, "data", "inbox", today.strftime("%Y-%m-%d") + ".json")
    prev = load(p, {"items": []})
    seen = {x["id"] for x in prev.get("items", [])}
    items = prev.get("items", []) + [x for x in out if x["id"] not in seen]
    json.dump({"date": today.strftime("%Y-%m-%d"), "generated": today.isoformat(timespec="seconds"), "items": items},
              io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ids = ",".join(str(x["id"]) for x in out)
    d1("UPDATE inbox_mail SET status='triaged', category=CASE id %s END, site=CASE id %s END WHERE id IN (%s)" % (
        " ".join("WHEN %d THEN '%s'" % (x["id"], x["category"]) for x in out),
        " ".join("WHEN %d THEN %s" % (x["id"], ("'%s'" % x["site"]) if x["site"] else "NULL") for x in out), ids))
    print("来信分拣：新邮件 %d 封 → data/inbox/%s.json" % (len(out), today.strftime("%Y-%m-%d")))
    for x in out: print("  #%-3d %-12s %-22s %s" % (x["id"], x["category"], (x["site"] or "—")[:22], (x["subject"] or "")[:44]))


OVERDUE_H = 36   # 值班每天 4 轮；超过 36 小时没处理 = 值班停了


def overdue_alert():
    """兜底：真实来信积压超过 OVERDUE_H 小时（status 仍是 new/triaged），说明 Claude 来信值班没在跑。
       发一封告警到所有者邮箱，附发件人、主题与正文开头；告警过的信在 note 里记 overdue_alerted，不重复发。"""
    try:
        rows = d1("SELECT id, from_addr, subject, received_at, substr(body_text,1,300) b FROM inbox_mail WHERE status IN ('new','triaged') "
                  "AND received_at < datetime('now','-%d hours') AND coalesce(note,'') NOT LIKE '%%overdue_alerted%%' ORDER BY id" % OVERDUE_H)
    except Exception as e:
        return print("积压检查：拉取失败（%s）" % str(e)[:160])
    rows = [m for m in rows if not is_self(m.get("from_addr"))]
    if not rows: return print("积压检查：无")
    paras = ["hello@sinanlab.com 有 %d 封来信超过 %d 小时没人处理——Claude 的「司南来信值班」可能没在跑（Claude 没开或任务被停）。"
             "打开 Claude 运行一次「司南来信值班」即可处理；原文在 D1 的 inbox_mail 表。" % (len(rows), OVERDUE_H)]
    for m in rows:
        paras.append("#%d %s — 来自 %s（%s UTC 收到）\n%s" % (m["id"], m.get("subject") or "(无主题)", m.get("from_addr"), m.get("received_at"), (m.get("b") or "")[:300]))
    tmp = os.path.join(ROOT, "data", "inbox", "_overdue.txt")
    io.open(tmp, "w", encoding="utf-8").write("\n\n".join(paras))
    to = owner_email()
    if not to: return print("积压检查：%d 封积压，但 data/secrets.env 没有 OWNER_EMAIL" % len(rows))
    r = subprocess.run(["/usr/bin/python3", os.path.join(HERE, "reply_mail.py"), to,
                        "司南来信积压 %d 封 · 值班没在跑" % len(rows), tmp], cwd=ROOT, timeout=180, capture_output=True, text=True)
    if "HTTP 200" not in (r.stdout or ""): return print("积压检查：%d 封积压，告警发送失败：%s" % (len(rows), (r.stdout or r.stderr or "")[-200:]))
    d1("UPDATE inbox_mail SET note=trim(coalesce(note,'')||' overdue_alerted') WHERE id IN (%s)" % ",".join(str(int(m["id"])) for m in rows))
    print("积压检查：%d 封积压，已发告警" % len(rows))

if __name__ == "__main__":
    main()
    if "--quiet" not in sys.argv: overdue_alert()
