#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sinan-probe —— 用你自己的 Key，在终端里测一个中转站：
  1) 一致性探针：向指定模型发 8 条公开探针串，比对返回的 token 计数与司南多渠道参考计数（/assets/tokref.json）
  2) 首字节延迟：每条请求的 TTFB p50
  3) 回显模型名：返回的 model 字段是否与请求一致
只依赖 Python 3.8+ 标准库。Key 只在本机使用，不上传；--report 才会把结果（不含 Key）提交给司南帮助扩大检测覆盖。

用法：
  python3 sinan_probe.py https://toapis.cn sk-xxxx --models gpt-5.6-luna,claude-sonnet-5
  python3 sinan_probe.py toapis.cn sk-xxxx --all          # 测参考表里全部有参考的模型
"""
import sys, json, time, argparse, urllib.request, urllib.error, statistics

TOKREF = "https://compute.sinanlab.com/assets/tokref.json"
REPORT = "https://compute.sinanlab.com/api/check/report"

def get_json(url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=(json.dumps(data).encode() if data is not None else None), headers=headers or {}, method="POST" if data is not None else "GET")
    if data is not None: req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))

def probe_model(base, key, model, probes):
    counts, ttfb, echo, ok, err = [], [], None, 0, None
    for p in probes:
        t0 = time.time()
        try:
            js = get_json(base + "/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": p}], "max_tokens": 4}, {"Authorization": "Bearer " + key})
            ttfb.append((time.time() - t0) * 1000); counts.append((js.get("usage") or {}).get("prompt_tokens")); echo = echo or js.get("model"); ok += 1
        except urllib.error.HTTPError as e:
            err = "HTTP %d %s" % (e.code, e.read()[:120].decode("utf-8", "ignore")); counts.append(None)
        except Exception as e:
            err = type(e).__name__; counts.append(None)
    return counts, ttfb, echo, ok, err

def verdict(counts, ref):
    if not ref: return "无参考", ""
    ds = [c - r for c, r in zip(counts, ref) if c is not None and r is not None]
    if not ds: return "请求失败", ""
    u = sorted(set(ds))
    if u == [0]: return "一致", ""
    if len(u) == 1: return "含固定前缀约 %d token" % u[0], ""
    return "不一致", "计数差值 %s" % u[:6]

def main():
    ap = argparse.ArgumentParser(description="用自己的 Key 测一个中转站（司南实验室公开探针）")
    ap.add_argument("base"); ap.add_argument("key"); ap.add_argument("--models", default=""); ap.add_argument("--all", action="store_true"); ap.add_argument("--report", action="store_true", help="把结果（不含 Key）提交给司南")
    a = ap.parse_args()
    base = a.base if a.base.startswith("http") else "https://" + a.base; base = base.rstrip("/")
    TR = get_json(TOKREF)
    probes = TR["probes"]; refs = TR.get("models") or {}
    models = [m.strip() for m in a.models.split(",") if m.strip()] or ([m for m, v in refs.items() if v.get("ref")] if a.all else [])
    if not models: print("请用 --models 指定模型，或 --all 测全部有参考的模型（当前有参考：%s）" % ", ".join(m for m, v in refs.items() if v.get("ref"))); sys.exit(1)
    print("司南探针 · %s · 参考计数版本 %s（%s）· %d 条探针" % (base, TR.get("version"), TR.get("generated_at", "")[:10], len(probes)))
    print("%-24s %-10s %-9s %-26s %s" % ("模型", "成功", "TTFB p50", "判定", "回显模型名"))
    results = []
    for m in models:
        counts, ttfb, echo, ok, err = probe_model(base, a.key, m, probes)
        rf = (refs.get(m) or {}).get("ref"); weak = (refs.get(m) or {}).get("weak")
        v, detail = verdict(counts, rf)
        if weak and v not in ("无参考", "请求失败"): v += "（弱参考）"
        p50 = ("%dms" % statistics.median(ttfb)) if ttfb else "—"
        print("%-24s %-10s %-9s %-26s %s" % (m, "%d/%d" % (ok, len(probes)), p50, v, (echo or "—") + ((" · " + err) if err and ok == 0 else "")))
        if detail: print("   " + detail + " · 本机计数 " + str(counts) + " · 参考 " + str(rf))
        results.append({"model": m, "counts": counts, "ttfb": ttfb, "echo": echo, "ok": ok, "verdict": {"一致": "consistent", "不一致": "divergent", "无参考": "no_ref", "请求失败": "failed"}.get(v.split("（")[0], "prefix")})
    print("\n判定只有四种：一致 / 含固定前缀 / 不一致 / 无参考。不一致 = 该渠道对同一输入返回的 token 计数与多渠道共识不同，成因很多，本工具不推测。这是一致性测量，不是真伪判定。")
    if a.report:
        print("--report 需要登录态，网页版 %s/check 可直接回流；命令行回流将在下一版支持。" % "https://compute.sinanlab.com")

if __name__ == "__main__":
    main()
