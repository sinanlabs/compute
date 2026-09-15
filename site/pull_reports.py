# -*- coding: utf-8 -*-
"""每晚：从线上 D1 拉用户报错（open），与本地 correction_log（已确认修正，含署名）一起写成 site/reports_open.json，供 /corrections 页与证据链使用。
处理报错的流程（人工）：python3 site/pull_reports.py fix <report_id> "<原值>" "<改后>" "<原因>"   → 本地记 correction_log(credit=提交者) 并把线上状态改 fixed
                      python3 site/pull_reports.py reject <report_id> "<说明>"                     → 线上状态改 rejected"""
import os, io, sys, json, sqlite3, subprocess, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BJ = dt.timezone(dt.timedelta(hours=8))

def d1(sql):
    r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--json", "--command", sql], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if r.returncode != 0: raise RuntimeError((r.stderr or r.stdout)[-300:])
    return json.loads(r.stdout)[0]["results"]

def main():
    db = sqlite3.connect(os.path.join(ROOT, "data", "compass.sqlite")); db.row_factory = sqlite3.Row
    arg = sys.argv[1] if len(sys.argv) > 1 else "pull"
    if arg == "fix":
        rid, orig, corr, reason = int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
        r = d1("SELECT handle, kind, key FROM user_report WHERE id=%d" % rid)[0]
        db.execute("INSERT INTO correction_log(publish_id, original, corrected, reason, corrected_at, credit, report_id, target) VALUES(NULL,?,?,?,?,?,?,?)", (orig, corr, reason, dt.datetime.now(BJ).isoformat()[:19], r["handle"], rid, "%s · %s" % (r["kind"], r["key"]))); db.commit()
        d1("UPDATE user_report SET status='fixed', resolved_at=datetime('now'), resolution='%s' WHERE id=%d" % (reason.replace("'", "''"), rid)); print("已记修正并署名", r["handle"])
    elif arg == "reject":
        rid, note = int(sys.argv[2]), sys.argv[3]
        d1("UPDATE user_report SET status='rejected', resolved_at=datetime('now'), resolution='%s' WHERE id=%d" % (note.replace("'", "''"), rid)); print("已标维持原判")
    try: items = d1("SELECT id, handle, kind, key, note, url, created_at FROM user_report WHERE status='open' ORDER BY id DESC LIMIT 50")
    except Exception as e: print("D1 读取失败", e); items = []
    fixed = [dict(r) for r in db.execute("SELECT corrected_at date, target, original, corrected, reason, credit FROM correction_log ORDER BY id DESC LIMIT 200")]
    json.dump({"open": len(items), "items": items, "fixed": fixed, "generated_at": dt.datetime.now(BJ).isoformat()[:19]}, io.open(os.path.join(HERE, "reports_open.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("报错：待处理 %d · 已修正 %d" % (len(items), len(fixed)))

if __name__ == "__main__": main()
