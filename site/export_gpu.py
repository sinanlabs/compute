# -*- coding: utf-8 -*-
"""导出 site/gpu.json：每 平台×GPU×口径 的最新报价 + 最近 30 天按日序列。"""
import os, io, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
HERE = os.path.dirname(os.path.abspath(__file__))
def main():
    db = D.connect()
    try: rows = db.execute("SELECT ts, platform, gpu, vram_gb, kind, usd_per_hour, cny_per_hour, n, snapshot_id FROM gpu_price WHERE ts >= datetime('now','-30 days') ORDER BY id").fetchall()
    except Exception: rows = []
    latest, series = {}, {}
    for r in rows:
        k = (r["platform"], r["gpu"], r["kind"]); latest[k] = dict(r)
        series.setdefault(k, {})[r["ts"][:10]] = r["usd_per_hour"]
    fx = db.execute("SELECT rate FROM fx_rate ORDER BY id DESC LIMIT 1").fetchone()["rate"]
    gpus = {}
    for (pf, gpu, kind), r in latest.items():
        g = gpus.setdefault(gpu, {"gpu": gpu, "vram_gb": r["vram_gb"], "quotes": []})
        g["quotes"].append({"platform": pf, "kind": kind, "usd": r["usd_per_hour"], "cny": r["cny_per_hour"], "n": r["n"], "ts": r["ts"][:16], "sid": r["snapshot_id"], "series": sorted(series[(pf, gpu, kind)].items())})
    order = ["RTX 4090", "RTX 4090 D", "RTX 5090", "RTX 5090 D", "RTX A6000", "RTX PRO 6000", "L40S", "V100 32GB", "A100 PCIe 40GB", "A100 SXM4", "A800 80GB", "H800 80GB", "H100 SXM", "H100 NVL", "H200", "B200"]
    out = {"generated_at": D.now8(), "fx": fx, "platforms": {"runpod": {"name": "RunPod", "url": "https://www.runpod.io/pricing", "kinds": {"secure": "安全云", "community": "社区云"}},
                                                          "vast": {"name": "Vast.ai", "url": "https://vast.ai/pricing", "kinds": {"min": "按需最低", "median": "按需中位"}},
                                                          "suanli": {"name": "共绩算力", "url": "https://suanli.cn/", "kinds": {"starting": "官网起步价"}},
                                                          "autodl": {"name": "AutoDL（国内）", "url": "https://www.autodl.com/market/list", "kinds": {"min": "按量最低", "median": "按量中位"}}},
           "gpus": [gpus[g] for g in order if g in gpus]}
    io.open(os.path.join(HERE, "gpu.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    print("gpu.json：%d 款 GPU · %d 条报价" % (len(out["gpus"]), sum(len(g["quotes"]) for g in out["gpus"])))
if __name__ == "__main__":
    main()
