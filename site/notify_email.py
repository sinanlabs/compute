# -*- coding: utf-8 -*-
"""邮件通知触发器（本机每日流水线调用，部署之后跑）。
流程：本机生成随机令牌 → 用 wrangler 把令牌哈希写进线上 D1 的 notify_jobs → POST 到 /api/notify/run，由线上函数读取收件人并经 Resend 发送。
本机不持有 Resend 密钥，只持有 wrangler 登录态。
用法：python3 site/notify_email.py            按日期自动：每天 daily，北京时间周一再加一次 weekly
      python3 site/notify_email.py test       给管理员发一封测试信
      python3 site/notify_email.py weekly     手动补发周报
"""
import os, io, sys, json, secrets, hashlib, subprocess, datetime as dt
import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = "https://compute.sinanlab.com"
BJ = dt.timezone(dt.timedelta(hours=8))

def d1(sql):
    r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--command", sql], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if r.returncode != 0: raise RuntimeError("wrangler d1 失败：" + (r.stderr or r.stdout)[-400:])

def run(kind, payload):
    tok = secrets.token_hex(32); th = hashlib.sha256(tok.encode()).hexdigest()
    d1("INSERT INTO notify_jobs(token_hash, kind) VALUES('%s','%s')" % (th, kind))
    r = httpx.post(BASE + "/api/notify/run", json={"token": tok, "kind": kind, "payload": payload}, timeout=120)
    print("邮件任务 %s → HTTP %d %s" % (kind, r.status_code, r.text[:300]))

def daily_payload():
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    names = {s["domain"]: s.get("name") for s in D["sites"]}
    mnames = {m["id"]: m["name"] for m in D["models"]}
    ch = [{"vendor": c["vendor"], "site_name": names.get(c["vendor"]), "model": c["model"], "model_name": mnames.get(c["model"], c["model"]), "old": c["old"], "new": c["new"]} for c in D.get("changes", []) if c.get("kind") == "relay"]
    return {"date": D["generated_at"][:10], "changes": ch, "new_sites": [{"domain": d, "name": names.get(d)} for d in D.get("new_sites", [])]}

def weekly_payload(today):
    wd = os.path.join(HERE, "weekly")
    weeks = sorted(f[:-5] for f in os.listdir(wd) if f.endswith(".json")) if os.path.exists(wd) else []
    cur = "%d-w%02d" % today.isocalendar()[:2]
    done = [w for w in weeks if w != cur]          # 周一凌晨：上一周已完整
    if not done: return None
    wk = done[-1]; W = json.load(io.open(os.path.join(wd, wk + ".json"), encoding="utf-8"))
    days = sorted(W["days"]); ch = W.get("changes", [])
    ups = sum(1 for c in ch if c["new"] > c["old"]); downs = len(ch) - ups
    n_new = sum(len(v) for v in W.get("new_sites", {}).values())
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    order = [m["id"] for m in D["models"]]
    best = []
    for mid in order:
        b = W.get("best", {}).get(mid)
        if not b: continue
        last = b[sorted(b)[-1]]
        best.append({"name": last.get("name", mid), "site": last["vendor"], "out": last["out"], "ratio": last.get("ratio")})
        if len(best) >= 10: break
    return {"week": wk, "from": days[0], "to": days[-1], "n_changes": len(ch), "up": ups, "down": downs, "n_new": n_new, "best": best, "url": "%s/weekly/%s" % (BASE, wk)}

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "auto"
    today = dt.datetime.now(BJ).date()
    if arg == "test": return run("test", {})
    if arg in ("auto", "daily"):
        p = daily_payload()
        if p["changes"] or p["new_sites"]: run("daily", p)
        else: print("今日无变动，不发 daily")
    if arg == "weekly" or (arg == "auto" and today.weekday() == 0):
        p = weekly_payload(today)
        if p: run("weekly", p)
        else: print("没有可发的完整周报")

if __name__ == "__main__":
    main()
