# -*- coding: utf-8 -*-
"""「最新一代」自动推导。不再手排热门清单 —— 手排必然过时（教训：fable-5.1 早在库里，清单里没有）。

按厂商族分组，在库里真实出现过的模型里按版本号排序，取每族最新的若干个。
同时标出「哪些最新模型尚无中转站上架」—— 这本身是有价值的事实。
"""
from __future__ import unicode_literals
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D

FAMILY = [
    ("anthropic", re.compile(r"^claude-(fable|opus|sonnet|haiku)-?(\d+(?:\.\d+)?)")),
    ("openai",    re.compile(r"^gpt-(\d+(?:\.\d+)?)")),
    ("google",    re.compile(r"^gemini-(\d+(?:\.\d+)?)")),
    ("deepseek",  re.compile(r"^deepseek-v(\d+(?:\.\d+)?)")),
    ("moonshot",  re.compile(r"^kimi-k(\d+(?:\.\d+)?)")),
    ("zhipu",     re.compile(r"^glm-(\d+(?:\.\d+)?)")),
    ("xai",       re.compile(r"^grok-(\d+(?:\.\d+)?)")),
    ("alibaba",   re.compile(r"^qwen(\d+(?:\.\d+)?)")),
    ("minimax",   re.compile(r"^minimax-m(\d+(?:\.\d+)?)")),
]
# 排除非主线变体：-pro/-mini/-lite/-image/-preview 等留给详情页
# 注意不排 -pro：deepseek-v4-pro 是旗舰主线。-pro-preview / -multi-agent 这类才是变体。
SKIP = re.compile(r"(-mini|-nano|-lite|-image|-preview|-thinking|-vision|-exp|-turbo|-flash-lite|-code|-omni|-customtools|-batch|-multi-agent|-pro-preview|\.\d+b\b|-a\d+b\b)")
# -pro 因厂商而异：deepseek-v4-pro 是旗舰，gpt-5.5-pro / gemini-*-pro 是高价变体
PRO_IS_VARIANT = {"openai", "google", "moonshot"}


def _ver(s):
    try:
        return tuple(int(x) for x in s.split("."))
    except ValueError:
        return (0,)


def latest_by_family(db, per_family=2, kinds=("official", "marketplace", "relay")):
    rows = db.execute("SELECT model, vendor_kind FROM offer_norm WHERE superseded_by IS NULL AND unit='per_mtok_out' "
                      "AND vendor_kind IN (%s) AND vendor NOT LIKE '参考官方%%'" % ",".join("?" * len(kinds)), kinds).fetchall()
    seen = {}
    for r in rows:
        seen.setdefault(r["model"], set()).add(r["vendor_kind"])
    fam = {}
    for model, kinds_ in seen.items():
        if SKIP.search(model.replace("claude-", "", 1) if model.startswith("claude-") else model) and not model.startswith("claude-"):
            continue
        for name, rx in FAMILY:
            m = rx.match(model)
            if m:
                if name in PRO_IS_VARIANT and re.search(r"-pro(\b|-)", model):
                    break
                ver = _ver(m.group(m.lastindex))
                if any(x > 50 for x in ver): break   # gpt-5.2025.08.07 这类把日期写进名字的站方原名，不算版本
                fam.setdefault(name, []).append((ver, model, kinds_))
                break
    out = []
    for name, _ in FAMILY:
        items = sorted(fam.get(name, []), key=lambda x: x[0], reverse=True)
        # 「最新两代」= 该厂商最新的 per_family 个版本号；同一版本号下的全部主线模型都算最新
        # （Claude 5 代：fable-5.1 / fable-5 / opus-5 / sonnet-5 同时在列；GPT-6 与 5.6 两代并列，不再被一个模型占掉整代）
        top_vers = []
        for ver, _m, _k in items:
            if ver not in top_vers: top_vers.append(ver)
            if len(top_vers) >= per_family: break
        for ver, model, kinds_ in items:
            if ver not in top_vers: continue
            out.append({"family": name, "model": model, "version": ".".join(map(str, ver)),
                        "has_relay": "relay" in kinds_, "has_reference": bool(kinds_ & {"official", "marketplace"})})
    return out


if __name__ == "__main__":
    db = D.connect()
    rows = latest_by_family(db, per_family=2)
    print("%-10s %-26s %-8s %-8s %s" % ("厂商", "库里最新", "版本", "有中转", "有参考价"))
    for r in rows:
        print("%-10s %-26s %-8s %-8s %s" % (r["family"], r["model"], r["version"],
                                            "是" if r["has_relay"] else "—  ← 尚无中转上架", "是" if r["has_reference"] else "—"))
