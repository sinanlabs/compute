# -*- coding: utf-8 -*-
"""价格走势导出：每个模型一个 JSON（site/history/<model>.json），由 build_v5 复制进 dist/history/。

来源：offer_norm 全部版本（含已被 superseded 的旧行），按 (vendor, model) 组成时间序列：
  - 中转站：实付 = 名义价 × 面板充值比例 ÷ 当时汇率（汇率取该行 valid_from 之前最近的一条 fx_rate）
  - 参考价：官方/公开市场 per_mtok_out 的最低价随时间变化
每个点 [ISO 时间, 美元/百万输出]。系列以"每次抓取有变化才记一行"的方式存在，所以点数 = 变价次数 + 1。
公开文件（site/history/）只含最近 7 天（含窗口前最后一个点，保证线连续）；全量写到 site/history_full/（不进 dist），由 push_history_kv.py 推到 KV，登录用户经 /api/history/<model> 读取。
"""
from __future__ import unicode_literals
import os, sys, json, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core.modelname import canonical

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "history")
FULL = os.path.join(HERE, "history_full")

def main():
    db = D.connect()
    data = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    models = {m["id"] for m in data["models"]}
    fx = [(r["as_of"], r["rate"]) for r in db.execute("SELECT as_of, rate FROM fx_rate ORDER BY id")]
    rate_now = fx[-1][1] if fx else 7.0
    os.makedirs(OUT, exist_ok=True); os.makedirs(FULL, exist_ok=True)
    import datetime as _dt
    cutoff = (_dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8))) - _dt.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    series = {}   # model -> vendor -> [(t, usd)]
    for r in db.execute("SELECT vendor, vendor_kind, model, price, currency, conditions, valid_from FROM offer_norm WHERE unit='per_mtok_out' ORDER BY valid_from"):
        m = canonical(r["model"])
        if m not in models: continue
        c = json.loads(r["conditions"] or "{}")
        if r["vendor_kind"] == "relay":
            if c.get("usd_direct"): usd = r["price"]
            elif c.get("panel_price") is None: continue
            else: usd = r["price"] * float(c["panel_price"]) / rate_now
            key = r["vendor"]
        else:
            usd = r["price"] / rate_now if r["currency"] == "CNY" else r["price"]
            key = "__ref__:" + r["vendor"]
        series.setdefault(m, {}).setdefault(key, []).append([r["valid_from"][:16], round(usd, 4)])
    n = 0
    for m, vend in series.items():
        refs = {k[8:]: v for k, v in vend.items() if k.startswith("__ref__:")}
        relays = {k: v for k, v in vend.items() if not k.startswith("__ref__:")}
        # 参考价：各来源逐时刻最低
        floor = []
        pts = sorted({t for v in refs.values() for t, _ in v})
        for t in pts:
            vals = [min(p for tt, p in v if tt <= t) for v in refs.values() if any(tt <= t for tt, _ in v)]
            if vals: floor.append([t, round(min(vals), 4)])
        full = {"model": m, "generated_at": D.now8(), "unit": "usd_per_mtok_out", "floor": floor, "vendors": relays, "scope": "full"}
        io.open(os.path.join(FULL, m + ".json"), "w", encoding="utf-8").write(json.dumps(full, ensure_ascii=False, separators=(",", ":")))
        def trim(pts):
            keep = [p for p in pts if p[0] >= cutoff]
            before = [p for p in pts if p[0] < cutoff]
            return ([before[-1]] if before else []) + keep
        pub = {"model": m, "generated_at": D.now8(), "unit": "usd_per_mtok_out", "floor": trim(floor), "vendors": {k: trim(v) for k, v in relays.items()}, "scope": "7d", "full_via": "/api/history/%s" % m}
        io.open(os.path.join(OUT, m + ".json"), "w", encoding="utf-8").write(json.dumps(pub, ensure_ascii=False, separators=(",", ":")))
        n += 1
    io.open(os.path.join(OUT, "index.json"), "w", encoding="utf-8").write(json.dumps({"models": sorted(series.keys()), "generated_at": D.now8()}, ensure_ascii=False))
    print("价格走势：%d 个模型 · 目录 %s" % (n, OUT))

if __name__ == "__main__":
    main()
