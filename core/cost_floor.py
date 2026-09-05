# -*- coding: utf-8 -*-
"""成本下限检验 —— 不注册、不测试、不指控，就能给出最有用的那个信号。

原理：每个上游模型有已知的最低官方渠道价。若某渠道对同一模型的报价只有
官方最低价的 7%，那么在「无补贴」假设下它数学上不可能长期提供真实模型。
这是算术比值，不是指控 —— 所以措辞宪法容得下，可以直接具名公开。
"""
from __future__ import unicode_literals
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core import wording as W

# 比率分档。边界是设计选择，写死在这里并公开，别让它变成可调的黑箱。
BANDS = [
    (0.00, 0.15, "unsustainable", "在无补贴假设下数学上不可持续"),
    (0.15, 0.40, "below_bulk",    "显著低于常见批量折扣区间"),
    (0.40, 0.75, "explainable",   "可由批量折扣解释"),
    (0.75, 1.25, "normal",        "与公开渠道价接近"),
    (1.25, 3.00, "premium",       "高于公开渠道价，可能含服务溢价"),
    (3.00, 1e9,  "far_above",     "显著高于公开渠道价"),
]

# 极端值闸门：比率落在这个区间之外，先别发布，先核对计价单位。
# 实测教训：aidianwo 的 deepseek-v4-flash 算出 73 倍，措辞闸照样放行（句子结构合规），
# 但 73 倍大概率是我把倍率基数读错了，不是事实。语法闸拦不住语义上的荒谬，要另设一道。
SANE_LOW, SANE_HIGH = 0.05, 5.0


def sanity(ratio, evidenced=False):
    """返回 (可发布?, 原因)。

    evidenced=True 表示换算链每一环都有证据：面板 price 字段已存、汇率有独立快照、
    倍率基数与 price 语义已从 new-api 源码核对（topup.go getPayMoney）。
    这道闸是防【我算错】的，不是防【事实极端】的 —— 链条全了，极端值就是事实，放行。
    """
    if SANE_LOW <= ratio <= SANE_HIGH:
        return True, None
    if evidenced:
        return True, None
    if ratio < SANE_LOW:
        return False, "比率 %.3f 低于 %.2f 且换算链不全，先核对计价单位与分组倍率" % (ratio, SANE_LOW)
    return False, "比率 %.2f 高于 %.1f 且换算链不全，先核对倍率基数/币种" % (ratio, SANE_HIGH)


def band(ratio):
    for lo, hi, code, label in BANDS:
        if lo <= ratio < hi:
            return code, label
    return "far_above", "显著高于公开渠道价"


def official_floor(db, model, unit, currency="CNY"):
    """从 L3 归一层取该模型的最低官方渠道价。带 snapshot_id，否则不许用。"""
    row = db.execute(
        "SELECT price, currency, vendor, snapshot_id FROM offer_norm "
        "WHERE model=? AND unit=? AND vendor_kind='official' AND currency=? AND superseded_by IS NULL "
        "ORDER BY price ASC LIMIT 1", (model, unit, currency)).fetchone()
    return dict(row) if row else None


def check(db, relay_vendor, model, unit, quoted_price, currency="CNY"):
    floor = official_floor(db, model, unit, currency)
    if not floor:
        return {"ok": False, "reason": "no_official_reference",
                "note": "本站尚未收录该模型的官方渠道价，不出结论"}
    ratio = quoted_price / floor["price"]
    code, label = band(ratio)
    return {
        "ok": True, "relay": relay_vendor, "model": model, "unit": unit,
        "quoted": quoted_price, "floor": floor["price"], "floor_vendor": floor["vendor"],
        "currency": currency, "ratio": round(ratio, 4), "band": code, "band_label": label,
        "evidence_ids": [floor["snapshot_id"]],
    }


def render(result, relay_snapshot_id):
    """生成对外句子，并强制过发布闸。过不了就不返回文本。"""
    if not result.get("ok"):
        return None, [(W.ERROR, "no_reference", result["note"], "先收录官方参考价")]
    ev = list(result["evidence_ids"]) + [relay_snapshot_id]
    text = ("%s 对 %s 的报价为 %.2f %s，为本站已收录最低官方渠道价（%s，%.2f %s）的 %.1f%%，"
            "%s。此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低官方来源。") % (
        result["relay"], result["model"], result["quoted"], result["currency"],
        result["floor_vendor"], result["floor"], result["currency"],
        result["ratio"] * 100, result["band_label"])
    allowed, v = W.guard(text, kind="fact", evidence_ids=ev)
    return (text if allowed else None), v


if __name__ == "__main__":
    db = D.connect()
    # 种子数据：占位，标明待校准。真实值由 W0 的适配器抓取填入。
    sid = D.put_snapshot(db, "seed.placeholder", "about:seed",
                         b"PLACEHOLDER reference prices - to be replaced by real adapters",
                         note="占位参考价，非真实报价，W0 适配器上线后覆盖")
    seed = [("参考官方A", "Claude Opus 4.5", 107.0), ("参考官方B", "GPT-5", 72.0),
            ("参考官方C", "Claude Sonnet 4.5", 21.4), ("参考官方D", "DeepSeek-V3.2", 6.4)]
    if not db.execute("SELECT 1 FROM offer_norm LIMIT 1").fetchone():
        for v, m, p in seed:
            D.put_offer(db, v, "official", m, "per_mtok_out", p, "CNY", sid,
                        conditions={"note": "占位参考价，待真实适配器覆盖"})
        db.commit()

    rsid = D.put_snapshot(db, "relay.pricing.demo", "about:demo", b"relay quoted prices demo")
    db.commit()
    for relay, model, quoted in [("渠道 #C31", "Claude Opus 4.5", 8.0),
                                 ("渠道 #A7", "GPT-5", 45.0),
                                 ("渠道 #B14", "Claude Sonnet 4.5", 6.2),
                                 ("渠道 #D08", "DeepSeek-V3.2", 5.8)]:
        r = check(db, relay, model, "per_mtok_out", quoted)
        text, v = render(r, rsid)
        print("\n%-10s ratio=%.3f  [%s]" % (relay, r["ratio"], r["band"]))
        print("  " + (text if text else "!! 发布闸拦下"))
        if v:
            print(W.explain(v))
