# -*- coding: utf-8 -*-
"""每晚：把线上 D1 的众测回流（30 天）拉到本地 compass.sqlite 的 crowd_probe 表（整表替换），供 export_data 汇总。"""
import os, io, sys, json, sqlite3, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
def main():
    r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--json", "--command",
                        "SELECT id, user_id, src_hash, source, base, model, raw_model, counts_json, echo_model, ttfb_json, ok_n, verdict, created_at FROM crowd_probe WHERE created_at >= datetime('now','-30 days') ORDER BY id"], cwd=ROOT, capture_output=True, text=True, timeout=180)
    if r.returncode != 0: print("众测拉取失败", (r.stderr or r.stdout)[-200:]); return
    rows = json.loads(r.stdout)[0]["results"]
    db = sqlite3.connect(os.path.join(ROOT, "data", "compass.sqlite"))
    db.execute("CREATE TABLE IF NOT EXISTS crowd_probe(id INTEGER PRIMARY KEY, user_id TEXT, src_hash TEXT, source TEXT, base TEXT, model TEXT, raw_model TEXT, counts_json TEXT, echo_model TEXT, ttfb_json TEXT, ok_n INTEGER, verdict TEXT, created_at TEXT)")
    db.execute("DELETE FROM crowd_probe")
    db.executemany("INSERT INTO crowd_probe VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", [(x["id"], x["user_id"], x["src_hash"], x["source"], x["base"], x["model"], x["raw_model"], x["counts_json"], x["echo_model"], x["ttfb_json"], x["ok_n"], x["verdict"], x["created_at"]) for x in rows])
    db.commit(); print("众测：30 天 %d 条 · %d 站 · %d 个来源" % (len(rows), len(set(x["base"] for x in rows)), len(set(x["src_hash"] or x["user_id"] for x in rows))))
if __name__ == "__main__": main()
