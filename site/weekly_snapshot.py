# -*- coding: utf-8 -*-
"""每周价格周报的数据积累：每天把当天的变动、新收录、四类分布快照合并进 site/weekly/<ISO周>.json（随仓库提交）。
build_v5 读取全部周文件生成 /weekly 与 /weekly/<周> 页面。"""
import os, io, json, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "weekly")

def main():
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    today = dt.date.fromisoformat(D["generated_at"][:10])
    iso = today.isocalendar(); wk = "%d-w%02d" % (iso[0], iso[1])
    p = os.path.join(OUT, wk + ".json")
    W = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {"week": wk, "days": {}, "changes": [], "new_sites": {}}
    seen = {(c["t"], c["vendor"], c["model"]) for c in W["changes"]}
    for c in D.get("changes", []):
        if c["t"][:10] < (today - dt.timedelta(days=today.weekday())).isoformat(): continue   # 只收本周
        k = (c["t"], c["vendor"], c["model"])
        if k not in seen: W["changes"].append(c); seen.add(k)
    W["days"][today.isoformat()] = {"confirmed": D["stats"]["confirmed"], "with_quotes": D["stats"]["with_quotes"], "quotes": D["stats"]["quotes"], "clusters": D["stats"]["clusters"], "fx": D["fx"]["rate"]}
    W["new_sites"][today.isoformat()] = D.get("new_sites", [])
    W["changes"].sort(key=lambda c: c["t"], reverse=True)
    # 每个模型的说得通最低实付（本周每日），用于周报里的“本周最低价”
    W.setdefault("best", {})
    for m in D["models"]:
        ok = [r for r in m["rows"] if not r["held"] and r["band"] in ("explainable", "normal")]
        if ok:
            b = min(ok, key=lambda r: r["out"])
            W["best"].setdefault(m["id"], {})[today.isoformat()] = {"vendor": b["vendor"], "out": b["out"], "ratio": b["ratio"], "floor": m["floor"]["out"], "name": m["name"]}
    io.open(p, "w", encoding="utf-8").write(json.dumps(W, ensure_ascii=False))
    print("周报数据 %s：%d 天 · %d 条变动" % (wk, len(W["days"]), len(W["changes"])))

if __name__ == "__main__":
    main()
