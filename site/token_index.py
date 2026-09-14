# -*- coding: utf-8 -*-
"""司南 Token 价格指数（Sinan Token Price Index）。
问题：Token 正成为 AI 服务的计量与结算单位，但没有任何机构每天发布"中国市场每百万 Token 多少钱"。我们每天有几万条中转站实付报价，压成一条可引用的序列。

口径（全部可复现）：
  · 样本：已确认中转站里，非"计价方式待核"站，对每个最新两代主流模型的每百万输出 token 实付价（面板名义价 × 充值比例 ÷ 汇率，与站内账本同一算法）
  · 每模型每日：跨站中位数、25/75 分位、样本站数（≥15 站才计入）
  · 分档按官方参考价：旗舰 ≥$20/M、中档 $2–20、快速 <$2
  · 档指数 = 档内各模型"中位实付 ÷ 官方参考价"的中位数（折价率），以及档内各模型中位实付的中位数（价格水平，$/M 与 ¥/M）
  · 全市场 = 所有计入模型的同样两个数
  · 历史：按 offer_norm 的 valid_from / valid_to 区间重建每天收盘状态，从 2026-09-02 起；汇率用当日最近一条
写出 site/price_index.json → dist/price-index.json。"""
import os, io, sys, json, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core.modelname import canonical
HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DATE = "2026-09-02"; MIN_SITES = 15
TIERS = [("flagship", "旗舰", 20, 1e9), ("mid", "中档", 2, 20), ("flash", "快速", 0, 2)]

def tier_of(floor):
    for k, n, lo, hi in TIERS:
        if lo <= floor < hi: return k
    return "mid"

def main():
    db = D.connect()
    Dv = json.load(io.open(os.path.join(HERE, "dist", "data_v2.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "dist", "data_v2.json")) else json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    models = {m["id"]: {"name": m["name"], "floor": m["floor"]["out"], "vendor": m["vendor"], "tier": tier_of(m["floor"]["out"])} for m in Dv["models"] if m["is_latest"] and m["floor"] and m["floor"].get("out")}
    held = {s["domain"] for s in Dv["sites"] if (s.get("cluster") or {}).get("code") == "held"}
    fx_rows = db.execute("SELECT rate, as_of FROM fx_rate ORDER BY id").fetchall(); fx_latest = fx_rows[-1]["rate"]
    rows = db.execute("SELECT vendor, model, price, conditions, valid_from, valid_to FROM offer_norm WHERE vendor_kind='relay' AND unit='per_mtok_out'").fetchall()
    # 预处理：每行 → (vendor, model_id, eff_usd, from, to)
    R = []
    for r in rows:
        mid = canonical(r["model"])
        if mid not in models or r["vendor"] in held: continue
        c = json.loads(r["conditions"] or "{}"); p = c.get("panel_price")
        if c.get("usd_direct"): eff = r["price"]
        elif p is None: continue
        else: eff = r["price"] * float(p) / fx_latest
        if eff <= 0: continue
        R.append((r["vendor"], mid, eff, r["valid_from"][:19], (r["valid_to"] or "9999")[:19]))
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
    d0 = dt.date.fromisoformat(BASE_DATE); series = []; per_model = {m: [] for m in models}
    while d0 <= today:
        cut = d0.isoformat() + "T23:59:59"
        # 当天有效的最新一条（同 站×模型 取 valid_from 最大）
        cur = {}
        for v, m, eff, f, t in R:
            if f <= cut and t > cut:
                k = (v, m)
                if k not in cur or f > cur[k][1]: cur[k] = (eff, f)
        by_m = {}
        for (v, m), (eff, _) in cur.items(): by_m.setdefault(m, []).append(eff)
        day = {"date": d0.isoformat()}; tier_ratio = {k: [] for k, *_ in TIERS}; tier_price = {k: [] for k, *_ in TIERS}; n_q = 0
        for m, effs in by_m.items():
            if len(effs) < MIN_SITES: continue
            effs.sort(); med = st.median(effs); q1 = effs[len(effs) // 4]; q3 = effs[(3 * len(effs)) // 4]
            ratio = med / models[m]["floor"]; n_q += len(effs)
            per_model[m].append({"date": d0.isoformat(), "median": round(med, 4), "p25": round(q1, 4), "p75": round(q3, 4), "n": len(effs), "ratio": round(ratio, 4)})
            tier_ratio[models[m]["tier"]].append(ratio); tier_price[models[m]["tier"]].append(med)
        allr = [x for k in tier_ratio for x in tier_ratio[k]]; allp = [x for k in tier_price for x in tier_price[k]]
        def pack(rs, ps): return {"ratio": round(st.median(rs), 4), "price_usd": round(st.median(ps), 3), "price_cny": round(st.median(ps) * fx_latest, 2), "n_models": len(rs)} if rs else None
        day["all"] = pack(allr, allp); day["all"] and day["all"].update({"n_quotes": n_q})
        for k, *_ in TIERS: day[k] = pack(tier_ratio[k], tier_price[k])
        if day["all"]: series.append(day)
        d0 += dt.timedelta(days=1)
    # 链式点位（基日 = 100）：只比较相邻两天都有数据的模型，取"各模型中位价日环比"的几何平均，消掉模型进出带来的成分变化
    import math
    def chain(key_filter):
        level = 100.0; prev = None; out_ = []
        for day in series:
            cur = {m: next((x for x in per_model[m] if x["date"] == day["date"]), None) for m in per_model if key_filter(m)}
            cur = {m: x["median"] for m, x in cur.items() if x}
            if prev:
                common = [m for m in cur if m in prev and prev[m] > 0]
                if common: level *= math.exp(sum(math.log(cur[m] / prev[m]) for m in common) / len(common))
            out_.append(round(level, 2)); prev = cur
        return out_
    levels = {"all": chain(lambda m: True)}
    for k, *_ in TIERS: levels[k] = chain(lambda m, k=k: models[m]["tier"] == k)
    for i, day in enumerate(series):
        for k, lv in levels.items():
            if day.get(k): day[k]["level"] = lv[i]
    out = {"name": "司南 Token 价格指数", "name_en": "Sinan Token Price Index", "version": "v1", "generated_at": D.now8(), "base_date": BASE_DATE, "fx": fx_latest, "min_sites": MIN_SITES,
           "tiers": [{"id": k, "name": n, "floor_lo": lo, "floor_hi": (None if hi > 1e8 else hi)} for k, n, lo, hi in TIERS],
           "series": series, "latest": series[-1] if series else None,
           "models": {m: dict(models[m], series=per_model[m]) for m in models if per_model[m]},
           "method": "每模型每日取跨站每百万输出 token 实付价中位数（≥%d 站），折价率 = 中位实付 ÷ 官方参考价；档与全市场的折价率、中位价取各模型的中位数（当日快照，受模型进出影响）；点位以 %s = 100 起算，按相邻两日共有模型中位价环比的几何平均链式相乘（不受模型进出影响，用于看涨跌）；历史按报价有效区间逐日重建。" % (MIN_SITES, BASE_DATE)}
    io.open(os.path.join(HERE, "price_index.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    L = out["latest"]
    print("Token 价格指数：%d 天 · 今日全市场折价率 %s · 点位 %.1f（基日 100）· 中位 $%.2f/M ≈ ¥%.1f/M · %d 模型 %d 条 · 旗舰 %s · 中档 %s · 快速 %s" % (
        len(series), "%d%%" % round(L["all"]["ratio"] * 100), L["all"]["level"], L["all"]["price_usd"], L["all"]["price_cny"], L["all"]["n_models"], L["all"]["n_quotes"],
        *["%d%%" % round(L[k]["ratio"] * 100) if L.get(k) else "—" for k in ("flagship", "mid", "flash")]) if L else "Token 价格指数：无数据")

if __name__ == "__main__":
    main()
