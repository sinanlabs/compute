# -*- coding: utf-8 -*-
"""自测参考计数：把公开探针集（core/public_probes.py）在我们有 Key 的多个渠道上得到的 prompt_tokens 计数做共识，
写出 site/tokref.json → dist/assets/tokref.json，供浏览器端“用我的 Key 测”比对。
共识规则与站内一致：同一模型下，两渠道在重叠位置差值恒定视为同一分词器（差值 = 固定前缀）；最大簇 ≥3 渠道为正式参考，=2 渠道为弱参考（页面标出）；
参考计数取簇内前缀最小的那组。没有共识的模型不给参考（前端只显示原始计数与回显）。"""
import os, io, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core.public_probes import PUBLIC_PROBES, PUBLIC_BASE

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    db = D.connect()
    rows = db.execute("SELECT site, model, probe_idx, prompt_tokens, ts FROM probe_t1 WHERE status=200 AND prompt_tokens IS NOT NULL AND probe_idx>=? AND ts>=datetime('now','-14 days') ORDER BY id", (PUBLIC_BASE,)).fetchall()
    latest = {}
    for r in rows: latest[(r["site"], r["model"], r["probe_idx"] - PUBLIC_BASE)] = r["prompt_tokens"]
    sig = {}
    for (site, m, i), n in latest.items(): sig.setdefault(m, {}).setdefault(site, {})[i] = n
    K = len(PUBLIC_PROBES)
    def match(a, b):
        ks = [i for i in range(K) if i in a and i in b]
        if len(ks) < K - 1: return False, 0
        ds = {b[i] - a[i] for i in ks}
        return (len(ds) == 1, ds.pop() if len(ds) == 1 else 0)
    out = {}
    for m, by in sig.items():
        full = {s: v for s, v in by.items() if len(v) >= K - 1}
        clusters = []
        for s, v in full.items():
            for c in clusters:
                ok, off = match(c["ref"], v)
                if ok: c["sites"].append(s); c["offs"][s] = off; break
            else: clusters.append({"ref": v, "sites": [s], "offs": {s: 0}})
        if not clusters: continue
        c = max(clusters, key=lambda c: len(c["sites"]))
        if len(c["sites"]) < 2: out[m] = {"ref": None, "peers": len(c["sites"]), "weak": False, "note": "共识样本不足"}; continue
        base = min(c["offs"].values())
        ref = [(c["ref"][i] - (c["offs"][c["sites"][0]] - base)) if i in c["ref"] else None for i in range(K)]
        # 2 渠道一致 = 弱参考（页面会标出）；≥3 渠道 = 正式参考
        out[m] = {"ref": ref, "peers": len(c["sites"]), "weak": len(c["sites"]) < 3, "note": "弱参考：仅 2 个渠道一致" if len(c["sites"]) < 3 else None}
    doc = {"version": "public-v1", "generated_at": D.now8(), "probes": PUBLIC_PROBES, "models": out,
           "how": "对每条探针发 max_tokens=4 的 chat 请求，读 usage.prompt_tokens；与 ref 逐位比：全等=一致；恒定差值=含固定前缀；否则=不一致。"}
    io.open(os.path.join(HERE, "tokref.json"), "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print("tokref：%d 个模型有数据，%d 个形成共识" % (len(out), sum(1 for v in out.values() if v["ref"])))

if __name__ == "__main__":
    main()
