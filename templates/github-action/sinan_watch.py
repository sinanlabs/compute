#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每天检查你关注的模型在中国中转市场的价格（司南实验室公开数据），有变动就输出 Markdown 给工作流开 Issue。
环境变量：SINAN_MODELS  逗号分隔的模型 id（见 https://compute.sinanlab.com/api-docs），如 gpt-5.6-luna,claude-sonnet-5
          SINAN_THRESHOLD 触发阈值（市场中位价变动百分比，默认 5）
状态文件 .sinan_state.json 由工作流提交回仓库。只依赖标准库。"""
import os, json, urllib.request, sys
H = {"User-Agent": "sinan-watch/0.1 (+https://compute.sinanlab.com/api-docs)"}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read())
models = [m.strip() for m in os.environ.get("SINAN_MODELS", "").split(",") if m.strip()]
thr = float(os.environ.get("SINAN_THRESHOLD", "5"))
PI = get("https://compute.sinanlab.com/price-index.json")
st = json.load(open(".sinan_state.json")) if os.path.exists(".sinan_state.json") else {}
lines, new_state = [], {}
for mid in models or list(PI["models"])[:10]:
    mm = PI["models"].get(mid)
    if not mm or not mm.get("series"): continue
    last = mm["series"][-1]; med = last.get("median"); new_state[mid] = med
    prev = st.get(mid)
    if med is None or prev is None: continue
    pct = (med / prev - 1) * 100
    if abs(pct) >= thr:
        lines.append("| %s | $%.3f | $%.3f | %+.1f%% | %s 站 | https://compute.sinanlab.com/m/%s |" % (mm["name"], prev, med, pct, last.get("n", "—"), mid))
json.dump(new_state, open(".sinan_state.json", "w"), indent=1)
if lines:
    print("## 中转市场价格变动 · %s\n\n市场中位实付（$/百万输出 token），数据：司南实验室 compute.sinanlab.com/price-index\n\n| 模型 | 上次 | 现在 | 变动 | 样本 | 页面 |\n|---|---|---|---|---|---|" % PI["generated_at"][:10])
    print("\n".join(lines)); print("\n只陈述测量，不含推荐。口径：https://compute.sinanlab.com/method")
    sys.exit(0)
print("无超过阈值的变动")
