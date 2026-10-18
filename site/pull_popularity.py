# -*- coding: utf-8 -*-
"""站点页近 30 天真人浏览量（D1 events 的 pv_detail /s/<域名>）→ site/site_popularity.json。
给「A vs B」对比页挑站用：大家实际在看的站，才值得做对比页。读一次约 1.2 万行，远低于 D1 每日额度。
用法：python3 site/pull_popularity.py（每日刷新在构建前跑；失败就沿用上一份文件）"""
import os, io, json, subprocess, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "site_popularity.json")


def main():
    sql = "SELECT key, SUM(n) n FROM events WHERE name='pv_detail' AND day >= date('now','-30 days') AND key LIKE '/s/%' GROUP BY key ORDER BY n DESC LIMIT 600"
    try:
        r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--json", "--command", sql],
                           cwd=ROOT, capture_output=True, text=True, timeout=180)
        t = r.stdout; rows = json.loads(t[t.find("["):])[0]["results"]
    except Exception as e:
        return print("站点浏览量：拉取失败（%s），沿用上一份" % str(e)[:120])
    pop = {x["key"][3:]: int(x["n"]) for x in rows if str(x.get("key", "")).startswith("/s/")}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps({"generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
                                                          "window_days": 30, "pv": pop}, ensure_ascii=False))
    print("站点浏览量：%d 个站有浏览记录 → site/site_popularity.json" % len(pop))


if __name__ == "__main__":
    main()
