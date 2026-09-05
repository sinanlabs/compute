# -*- coding: utf-8 -*-
"""把全量价格走势（site/history_full/*.json）推到 Cloudflare KV（SINAN_KV），键 history:<model>。
登录用户经 /api/history/<model> 读取；匿名只拿公开的 7 天文件。每日流水线在 export_history 之后调用。"""
import os, io, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FULL = os.path.join(HERE, "history_full"); KV_ID = "01d14fee71b2465d906fdccbf4eac4bb"
def main():
    items = []
    for fn in sorted(os.listdir(FULL)):
        if fn.endswith(".json") and fn != "index.json":
            items.append({"key": "history:" + fn[:-5], "value": io.open(os.path.join(FULL, fn), encoding="utf-8").read()})
    if not items: print("history_full 为空"); return
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8"); json.dump(items, tmp); tmp.close()
    r = subprocess.run(["npx", "wrangler", "kv", "bulk", "put", tmp.name, "--namespace-id", KV_ID, "--remote"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    os.unlink(tmp.name)
    print("KV 推送 %d 个模型的全量走势：%s" % (len(items), "成功" if r.returncode == 0 else ("失败 " + (r.stderr or r.stdout)[-200:])))
if __name__ == "__main__":
    main()
