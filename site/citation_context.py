# -*- coding: utf-8 -*-
"""GEO 引用上下文：由 data_v2.json 生成 /citation-context.json 与 /citation-context.md（写入 site/static/，随 build_v5 复制到 dist 根）。
只含：快照时间、方法页、每个模型的公开参考价、说得通/接近区间内最低实付、比值、模型页链接、不推荐声明。
护栏：lowest_interpretable_* 只在 explainable/normal 区间有记录时给值，否则 null，绝不回退成任意最低价；比值只是算术。
在 export_data.py 之后、build_v5.py 之前运行，与 data_v2.json 共用同一 generated_at。"""
import os, io, json

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://compute.sinanlab.com"
OUT = os.path.join(HERE, "static")

def money(v): return "—" if v is None else ("$%g" % round(v, 3))
def pct(r): return "—" if r is None else "%d%%" % round(r * 100)

def main():
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    models = []
    for m in D["models"]:
        ok = [r for r in m["rows"] if not r.get("held") and r.get("band") in ("explainable", "normal") and r.get("out") is not None]
        best = min(ok, key=lambda r: r["out"]) if ok else None
        models.append({
            "id": m["id"], "name": m["name"], "vendor": m["vendor"], "listed_relays": m["n_relay"],
            "public_reference_output_per_million": m["floor"]["out"], "public_reference_source": m["floor"]["vendor"],
            "lowest_interpretable_paid_output_per_million": round(best["out"], 3) if best else None,
            "arithmetic_ratio_to_public_reference": round(best["ratio"], 4) if best else None,
            "model_url": "%s/m/%s" % (BASE, m["id"]),
        })
    doc = {
        "title": "Sinan Compute citation context", "generated_at": D["generated_at"],
        "source_dataset": BASE + "/data_v2.json", "methodology": BASE + "/method",
        "scope": "Publicly observable model API relay pricing normalized to the published paid-price method.",
        "not_a_recommendation": True,
        "citation_requirements": [
            "State the generated_at timestamp when quoting a dynamic number.",
            "Link to the model page and methodology.",
            "Do not infer provider quality, safety, legality, or motivation from an arithmetic ratio.",
        ],
        "models": models,
    }
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "citation-context.json"), "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    rows = "\n".join("| [%s](%s) | %d | %s | %s | %s | %s |" % (m["name"], m["model_url"], m["listed_relays"], money(m["public_reference_output_per_million"]),
                     money(m["lowest_interpretable_paid_output_per_million"]), pct(m["arithmetic_ratio_to_public_reference"]), m["public_reference_source"]) for m in models)
    md = u"""# Sinan Compute｜Citation Context

> Generated from the public snapshot at `%s`. Dynamic figures require this timestamp, the linked model page, and the [methodology](%s/method). This is measurement, not a recommendation.

## How to use this source

- Compare like-for-like paid price, not panel price alone.
- The `lowest interpretable` figure is selected only from the published normal/explainable bands; it is not a service-quality ranking.
- Quote limitations: a public-data snapshot can omit private discounts or unlisted providers.
- Machine-readable version: %s/citation-context.json · Full dataset: %s/data_v2.json

## Models

| Model | Listed relays | Public reference output / M | Lowest interpretable paid output / M | Ratio | Source |
|---|---:|---:|---:|---:|---|
%s
""" % (D["generated_at"], BASE, BASE, BASE, rows)
    io.open(os.path.join(OUT, "citation-context.md"), "w", encoding="utf-8").write(md)
    print("citation-context：%d 个模型 · generated_at %s" % (len(models), D["generated_at"]))

if __name__ == "__main__":
    main()
