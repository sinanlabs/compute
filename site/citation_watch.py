# -*- coding: utf-8 -*-
"""被引用监测（每周一）：GitHub 代码搜索 + Hacker News + 站内外部来源计数（D1 events name='ref'），新旧对比后发管理员一封周报。
状态文件 data/cite_seen.json 记已见过的条目。用法：python3 site/citation_watch.py [--force]"""
import os, io, sys, json, subprocess, datetime as dt
import httpx
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from notify_email import run as mail_run
BJ = dt.timezone(dt.timedelta(hours=8))
SEEN = os.path.join(ROOT, "data", "cite_seen.json")
OWN = ("sinanlabs/", "ericbing727")

def gh_search(q):
    try:
        out = subprocess.run(["gh", "api", "-X", "GET", "search/code", "-f", "q=%s" % q, "-f", "per_page=50", "--jq", ".items[] | [.repository.full_name, .path, .html_url] | @tsv"], capture_output=True, text=True, timeout=60).stdout
        return [dict(repo=a, path=b, url=c) for a, b, c in (l.split("\t") for l in out.strip().splitlines() if l.count("\t") == 2) if not a.startswith(OWN)]
    except Exception as e:
        print("gh 搜索失败", e); return []

def hn():
    try:
        d = httpx.get("https://hn.algolia.com/api/v1/search?query=sinanlab.com&tags=(story,comment)", timeout=30).json()
        # Algolia 会模糊匹配（还会命中叫 sinanlab 的用户名），只留正文/链接里真写了 sinanlab.com 的
        hits = [h for h in d.get("hits", []) if "sinanlab.com" in " ".join(str(h.get(k) or "") for k in ("url", "story_url", "title", "story_text", "comment_text")).lower()]
        return [dict(title=h.get("title") or (h.get("comment_text") or "")[:80], url="https://news.ycombinator.com/item?id=%s" % h["objectID"], date=(h.get("created_at") or "")[:10]) for h in hits]
    except Exception as e:
        print("HN 失败", e); return []

def referrers(days=7):
    since = (dt.datetime.now(BJ).date() - dt.timedelta(days=days)).isoformat()
    try:
        r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--json", "--command", "SELECT key host, SUM(n) n FROM events WHERE name='ref' AND day>='%s' GROUP BY key ORDER BY n DESC LIMIT 40" % since], cwd=ROOT, capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout)[0]["results"]
    except Exception as e:
        print("D1 读取失败", e); return []

def ref_pages(days=7):
    since = (dt.datetime.now(BJ).date() - dt.timedelta(days=days)).isoformat()
    try:
        r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--json", "--command", "SELECT key k, SUM(n) n FROM events WHERE name='refpath' AND day>='%s' GROUP BY key ORDER BY n DESC LIMIT 40" % since], cwd=ROOT, capture_output=True, text=True, timeout=120)
        return [{"host": x["k"].split("|")[0], "path": x["k"].split("|", 1)[1] if "|" in x["k"] else "", "n": x["n"]} for x in json.loads(r.stdout)[0]["results"]]
    except Exception as e:
        print("refpath 读取失败", e); return []

def main():
    today = dt.datetime.now(BJ).date()
    if today.weekday() != 0 and "--force" not in sys.argv: print("引用监测：非周一，跳过"); return
    seen = json.load(io.open(SEEN, encoding="utf-8")) if os.path.exists(SEEN) else {"github": [], "hn": []}
    gh = {}
    for q in ("sinanlab.com", "compute.sinanlab.com", "robo.sinanlab.com"):
        for x in gh_search(q): gh[x["url"]] = x
    gh = list(gh.values()); hs = hn()
    for x in gh: x["new"] = x["url"] not in seen["github"]
    for x in hs: x["new"] = x["url"] not in seen["hn"]
    rf = referrers()
    poll = {}
    try:
        r = subprocess.run(["npx", "wrangler", "d1", "execute", "sinan-users", "--remote", "--json", "--command", "SELECT key a, SUM(n) n FROM events WHERE name='poll:byok' GROUP BY key"], cwd=ROOT, capture_output=True, text=True, timeout=120)
        poll = {x["a"]: x["n"] for x in json.loads(r.stdout)[0]["results"]}
    except Exception as e: print("poll 读取失败", e)
    wk = "%d-w%02d" % today.isocalendar()[:2]
    summary = "%s：GitHub 提到我们的文件 %d 个（新 %d）· Hacker News %d 条（新 %d）· 本周外部来源访问 %d 次，来自 %d 个站点。" % (wk, len(gh), sum(x["new"] for x in gh), len(hs), sum(x["new"] for x in hs), sum(int(x["n"]) for x in rf), len(rf))
    print(summary)
    mail_run("cite", {"week": wk, "summary": summary, "github": sorted(gh, key=lambda x: not x["new"]), "hn": sorted(hs, key=lambda x: not x["new"]), "referrers": rf, "ref_pages": ref_pages(), "poll": poll})
    seen = {"github": sorted(set(seen["github"]) | set(x["url"] for x in gh)), "hn": sorted(set(seen["hn"]) | set(x["url"] for x in hs)), "last": today.isoformat()}
    json.dump(seen, io.open(SEEN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__": main()
