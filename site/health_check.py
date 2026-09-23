# -*- coding: utf-8 -*-
"""部署健康自检：今天的每日刷新有没有真的上线。不健康就退出码 1，并打印原因与报错尾巴，供早班直接动手修。

判定（任一成立即不健康）：
  1. 线上 data_v2.json 的 generated_at 距今超过 26 小时（北京时间）——页面停更；
  2. 最近一轮 daily_refresh 日志里出现「构建失败」「措辞自检未通过」，或没有 sinan-compute 的 Deployment complete。
用法：python3 site/health_check.py     （早班第 0 步；也可随时手动跑）
"""
import os, io, re, sys, json, datetime as dt, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LOG = os.path.join(ROOT, "data", "logs", "daily_refresh.log")
BJ = dt.timezone(dt.timedelta(hours=8))
MAX_AGE_H = 26


def live_age():
    try:
        req = urllib.request.Request("https://compute.sinanlab.com/data_v2.json", headers={"User-Agent": "SinanLabHealth/1.0", "Cache-Control": "no-cache"})
        g = json.loads(urllib.request.urlopen(req, timeout=30).read())["generated_at"]
        t = dt.datetime.fromisoformat(g)
        return g, (dt.datetime.now(BJ) - t).total_seconds() / 3600
    except Exception as e:
        return "取不到（%s）" % type(e).__name__, None


def last_run():
    if not os.path.exists(LOG): return None, ""
    t = io.open(LOG, encoding="utf-8", errors="replace").read()
    i = t.rfind("===== ")
    j = t.rfind(" 开始 =====")
    seg = t[t.rfind("\n=====", 0, j) + 1:] if j >= 0 else t[-20000:]
    head = seg.splitlines()[0] if seg else ""
    return head, seg


def main():
    problems = []
    g, age = live_age()
    if age is None: problems.append("线上 data_v2.json %s" % g)
    elif age > MAX_AGE_H: problems.append("线上数据停在 %s，已 %.0f 小时没更新" % (g, age))
    head, seg = last_run()
    if not seg: problems.append("找不到每日刷新日志")
    else:
        if "构建失败" in seg: problems.append("最近一轮构建失败（%s）" % head.strip("= "))
        if "措辞自检未通过" in seg: problems.append("最近一轮措辞自检未通过，没有部署（%s）" % head.strip("= "))
        if " 结束 =====" in seg and not re.search(r"Deployment complete!.*sinan-compute", seg): problems.append("最近一轮没有 sinan-compute 的部署记录（%s）" % head.strip("= "))
    tb = ""
    if seg and "Traceback" in seg:
        k = seg.rfind("Traceback"); tb = "\n".join(seg[k:].splitlines()[:40])
    hits = re.findall(r"措辞违规 .+", seg or "")
    print("线上数据：%s%s" % (g, (" · %.1f 小时前" % age) if age is not None else ""))
    print("最近一轮：%s" % (head.strip("= ") or "—"))
    if not problems:
        print("健康：今天的数据已上线"); return 0
    print("不健康：\n  - " + "\n  - ".join(problems))
    if tb: print("\n报错尾巴：\n" + tb)
    if hits: print("\n措辞违规：\n" + "\n".join(hits[:10]))
    return 1


if __name__ == "__main__": sys.exit(main())
