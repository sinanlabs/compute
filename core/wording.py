# -*- coding: utf-8 -*-
"""措辞宪法 —— 代码级强制，不是写在网站上的承诺。

用法：任何要对外发布的文本，先过 lint()。返回 ERROR 就发不出去。
理由：靠人的自觉守不住，写稿的时候情绪一上来就会写「实锤」。让机器守。

三种文本类型的规矩不同：
  fact         事实清单（域名年龄、备案、报价）—— 只禁指控词
  measurement  实测结论（分布、延迟、取回）—— 还必须带 样本量 / 时间窗 / 置信度
  discovery    发现榜 —— 还禁一切推荐性表述（推荐即担责）
"""
from __future__ import unicode_literals
import re

ERROR, WARN = "ERROR", "WARN"

# 指控性结论：任何文本都不许出现
BANNED = {
    "实锤": "改成陈述观测到的事实＋置信度",
    "假模型": "改成「输出分布与参考端点统计不一致」",
    "套壳": "改成「tokenizer 指纹与其声明模型不匹配」",
    "掺假": "改成「与声明模型的指纹不一致」",
    "造假": "改成具体的观测项，如「计费值与独立计数偏差 X%」",
    "伪造": "同上",
    "诈骗": "这是刑事定性，绝不能用",
    "欺诈": "同上",
    "骗子": "同上",
    "行骗": "同上",
    "黑榜": "改成「观测异常清单」",
    "曝光": "改成「发布测量结果」",
    "打假": "改成「一致性检测」",
    "割韭菜": "情绪词，删除",
    "智商税": "情绪词，删除",
    "无良": "情绪词，删除",
    "垃圾": "情绪词，删除",
    "坑人": "情绪词，删除",
    "涉嫌": "这是法律定性用语，改成陈述观测",
    "降智": "口语词但已被当成指控，改成「输出质量指标下降」并附指标",
    "scam": "banned", "fraud": "banned", "fake model": "banned", "busted": "banned",
}

# 绝对化 / 因果断言：一律降级为观察
SOFT = {
    "疑似": "改成给出概率或置信度",
    "必然": "去掉，给区间",
    "一定是": "去掉，给区间",
    "证明了": "改成「与…一致 / 不一致」",
    "毫无疑问": "去掉",
    "肯定是": "去掉",
}

# 推荐性表述：discovery 类禁用（推荐即担责）
RECOMMEND = ["推荐", "首选", "必买", "闭眼入", "无脑冲", "最佳选择", "值得入手", "建议购买", "强烈建议"]

# 最高级：任何类型都不许（除非带明确限定的口径）
SUPERLATIVE = ["最好的", "最强", "最靠谱", "最稳", "天花板", "遥遥领先"]

_N = re.compile(r"(?:\bn\s*[=＝]\s*[\d,]+|样本量\s*[:：]?\s*[\d,]+|共\s*[\d,]+\s*次)")
_WINDOW = re.compile(r"(?:\d{4}-\d{2}(?:-\d{2})?\s*(?:至|到|–|-|~)\s*\d{4}-\d{2}(?:-\d{2})?"
                     r"|\d{4}-\d{2}\s*窗口|近\s*\d+\s*(?:天|周|小时)|\d{1,2}:\d{2}\s*[-–~至]\s*\d{1,2}:\d{2})")
_CONF = re.compile(r"(?:置信度|置信区间|\bCI\b|p\s*[<＜]\s*0?\.\d+)")


def _hits(text, table):
    out = []
    for term in table:
        idx = text.lower().find(term.lower())
        if idx >= 0:
            out.append((term, idx))
    return out


def lint(text, kind="fact"):
    """返回 [(level, code, message, hint), ...]。含 ERROR 即不许发布。"""
    v = []
    for term, idx in _hits(text, BANNED):
        v.append((ERROR, "banned_term", "禁用词「%s」（位置 %d）" % (term, idx), BANNED[term]))
    for term, idx in _hits(text, SOFT):
        v.append((WARN, "soft_claim", "断言性措辞「%s」" % term, SOFT[term]))
    for term in SUPERLATIVE:
        if term in text:
            v.append((ERROR, "superlative", "最高级表述「%s」" % term, "改成带口径的比较，如「在本站 30 天窗口内 p95 最低」"))

    if kind == "measurement":
        if not _N.search(text):
            v.append((ERROR, "missing_n", "质量结论缺样本量", "补 n=1240 或「样本量 1,240」"))
        if not _WINDOW.search(text):
            v.append((ERROR, "missing_window", "质量结论缺时间窗", "补「2026-08-01 至 2026-08-31」或「20:00–24:00」"))
        if not _CONF.search(text):
            v.append((ERROR, "missing_conf", "质量结论缺置信度/置信区间", "补「置信度 94%」或给区间"))

    if kind == "discovery":
        for term in RECOMMEND:
            if term in text:
                v.append((ERROR, "recommendation", "推荐性表述「%s」" % term,
                          "发现引擎只给事实清单。推荐即担责，中转站跑路率高，这条线不能越"))
    return v


def require_evidence(evidence_ids):
    """铁律：对外的每个数字都要能 join 回 source_snapshot。"""
    if not evidence_ids:
        return [(ERROR, "no_evidence", "该结论没有关联任何快照 ID", "join 不到证据的数字不许显示")]
    return []


def guard(text, kind="fact", evidence_ids=None):
    """发布闸。返回 (allowed: bool, violations: list)。"""
    v = lint(text, kind) + require_evidence(evidence_ids or [])
    return (not any(lv == ERROR for lv, _, _, _ in v)), v


def explain(violations):
    lines = []
    for lv, code, msg, hint in violations:
        lines.append("  [%s] %-16s %s\n        → %s" % (lv, code, msg, hint))
    return "\n".join(lines) if lines else "  （无）"


if __name__ == "__main__":
    cases = [
        ("实锤！渠道 C31 就是套壳的假模型，纯纯智商税", "measurement", [1]),
        ("渠道 C31 在 20:00–24:00 的输出分布与参考端点统计不一致（置信度 94%，n=1,240）。本站不对成因作判断。",
         "measurement", [8812]),
        ("渠道 C31 对 Claude Opus 4.5 的报价为本站已收录最低官方渠道价的 7.5%。此为算术比值，不构成任何指控。",
         "fact", [8812]),
        ("本周新发现 7 个站，其中 #C31 最靠谱，推荐入手", "discovery", [1]),
        ("渠道 A7 可用率 99.2%，首字延迟 p50 0.71 秒。", "measurement", []),
    ]
    for text, kind, ev in cases:
        ok, v = guard(text, kind, ev)
        print("\n%s [%s] %s" % ("放行" if ok else "拦下", kind, text[:46] + ("…" if len(text) > 46 else "")))
        print(explain(v))
