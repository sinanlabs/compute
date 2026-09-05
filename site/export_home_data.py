# -*- coding: utf-8 -*-
"""从库里导出主页数据。全部真数据，每个数字带快照 ID。不编、不补、不猜。

主页第一板块是「按模型比价」：官方 / 公开市场 / 中转站放同一张表，实付口径，带判读标签。
"""
from __future__ import unicode_literals
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core.cost_floor import band
from core.latest import latest_by_family
from core.modelname import canonical

HERE = os.path.dirname(os.path.abspath(__file__))

# 用户最常问的模型，按热度手排。只展示库里真有报价的。
HOT = ["claude-opus-4.6", "claude-sonnet-4.6", "claude-opus-5", "claude-sonnet-5",
       "gpt-5.5", "gpt-5.4", "gpt-5.6-terra", "deepseek-v4-pro", "deepseek-v4-flash",
       "gemini-3.5-flash", "kimi-k3", "kimi-k2.6", "glm-5.1", "grok-4.6", "minimax-m2.5"]

PRETTY = {"claude-opus-4.6": "Claude Opus 4.6", "claude-sonnet-4.6": "Claude Sonnet 4.6",
          "claude-opus-5": "Claude Opus 5", "claude-sonnet-5": "Claude Sonnet 5",
          "gpt-5.5": "GPT-5.5", "gpt-5.4": "GPT-5.4", "gpt-5.6-terra": "GPT-5.6 Terra",
          "deepseek-v4-pro": "DeepSeek V4 Pro", "deepseek-v4-flash": "DeepSeek V4 Flash",
          "gemini-3.5-flash": "Gemini 3.5 Flash", "kimi-k3": "Kimi K3", "kimi-k2.6": "Kimi K2.6",
          "glm-5.1": "GLM-5.1", "grok-4.6": "Grok 4.6", "minimax-m2.5": "MiniMax M2.5",
          "claude-fable-5.1": "Claude Fable 5.1", "gpt-5.6-luna": "GPT-5.6 Luna", "gpt-5.6-sol": "GPT-5.6 Sol",
          "gemini-3.7-flash": "Gemini 3.7 Flash", "gemini-3.6-flash": "Gemini 3.6 Flash", "glm-5.3-flash": "GLM-5.3 Flash",
          "glm-5.2": "GLM-5.2", "grok-4.20": "Grok 4.20", "deepseek-v3.2": "DeepSeek V3.2", "kimi-k2.6": "Kimi K2.6",
          "minimax-m2.7": "MiniMax M2.7", "qwen3.8-flash": "Qwen 3.8 Flash", "qwen3.7-flash": "Qwen 3.7 Flash"}


def fx(db):
    r = db.execute("SELECT rate, as_of, snapshot_id FROM fx_rate ORDER BY id DESC LIMIT 1").fetchone()
    return r["rate"], r["as_of"], r["snapshot_id"]


def snapshot_meta(db, sid):
    r = db.execute("SELECT source, url, fetched_at, sha256 FROM source_snapshot WHERE id=?", (sid,)).fetchone()
    return dict(r) if r else None


def live_offers(db):
    return db.execute("SELECT vendor, vendor_kind, model, unit, price, currency, conditions, snapshot_id, valid_from "
                      "FROM offer_norm WHERE superseded_by IS NULL AND unit IN ('per_mtok_in','per_mtok_out') "
                      "AND vendor NOT LIKE '参考官方%'").fetchall()


def build_models(db):
    rate, fx_asof, fx_sid = fx(db)
    rows = live_offers(db)
    by = {}
    for r in rows:
        cond = json.loads(r["conditions"] or "{}")
        if r["vendor_kind"] == "relay":
            p = cond.get("panel_price")
            if p is None:
                continue
            usd = r["price"] * float(p) / rate
            note = {"nominal_usd": r["price"], "panel_price": float(p),
                    "stripe_unit_price": cond.get("panel_stripe_unit_price"), "channel": "人民币充值通道"}
        elif r["currency"] == "CNY":
            usd = r["price"] / rate
            note = {"cny": r["price"], "tier": cond.get("tier")}
        else:
            usd = r["price"]
            note = {}
        key = (canonical(r["model"]), r["vendor"])
        m = by.setdefault(key, {"model": canonical(r["model"]), "vendor": r["vendor"], "kind": r["vendor_kind"],
                                "in": None, "out": None, "sids": set(), "note": note, "as_of": r["valid_from"]})
        side = "in" if r["unit"] == "per_mtok_in" else "out"
        # 官方多档（空闲/高峰）取最低 —— 保守方向
        if m[side] is None or usd < m[side]:
            m[side] = usd
        m["sids"].add(r["snapshot_id"])

    models = {}
    for (model, vendor), m in by.items():
        if m["out"] is None:
            continue
        models.setdefault(model, []).append(m)

    latest = [x["model"] for x in latest_by_family(db, per_family=2) if x["has_reference"]]
    order = latest + [m for m in HOT if m not in latest]
    out = []
    for model in order:
        chans = models.get(model)
        if not chans:
            continue
        refs = [c for c in chans if c["kind"] in ("official", "marketplace")]
        if not refs:
            continue
        floor = min(refs, key=lambda c: c["out"])
        table = []
        for c in chans:
            ratio = c["out"] / floor["out"] if floor["out"] else None
            code, label = band(ratio) if (ratio is not None and c["kind"] == "relay") else (None, None)
            table.append({
                "vendor": c["vendor"], "kind": c["kind"],
                "out": round(c["out"], 3), "in": (round(c["in"], 3) if c["in"] is not None else None),
                "ratio": (round(ratio, 3) if ratio is not None else None),
                "band": code, "band_label": label, "is_floor": c is floor,
                "note": c["note"], "as_of": c["as_of"],
                "evidence": [dict(snapshot_meta(db, s), id=s) for s in sorted(c["sids"])] +
                            ([dict(snapshot_meta(db, fx_sid), id=fx_sid)] if c["kind"] == "relay" or c["note"].get("cny") else []),
            })
        table.sort(key=lambda x: (0 if x["is_floor"] else 1, x["out"]))
        out.append({"id": model, "name": PRETTY.get(model, model), "floor_vendor": floor["vendor"],
                    "floor_out": round(floor["out"], 3), "n_relay": sum(1 for c in chans if c["kind"] == "relay"),
                    "rows": table})
    return out, {"rate": rate, "as_of": fx_asof, "snapshot_id": fx_sid}


def build_sites(db):
    sites = []
    for r in db.execute("SELECT domain, first_channel, first_seen_at, level, panel_kind, panel_version, "
                        "entity_name, model_count, site_url FROM relay_candidate WHERE level>=1 ORDER BY level DESC, first_seen_at"):
        d = dict(r)
        # 该站的价格画像：相对参考价比率的分布
        d["n_quotes"] = db.execute("SELECT COUNT(*) c FROM offer_norm WHERE vendor=? AND superseded_by IS NULL "
                                   "AND unit='per_mtok_out'", (r["domain"],)).fetchone()["c"]
        sites.append(d)
    stats = {
        "seen_domains": db.execute("SELECT COUNT(*) c FROM seen_domain").fetchone()["c"],
        "candidates": db.execute("SELECT COUNT(*) c FROM relay_candidate").fetchone()["c"],
        "confirmed": db.execute("SELECT COUNT(*) c FROM relay_candidate WHERE level>=1").fetchone()["c"],
        "snapshots": db.execute("SELECT COUNT(*) c FROM source_snapshot").fetchone()["c"],
        "quotes": db.execute("SELECT COUNT(*) c FROM offer_norm WHERE superseded_by IS NULL AND vendor NOT LIKE '参考官方%'").fetchone()["c"],
    }
    return sites, stats


def build_feed(db):
    feed = []
    for r in db.execute("SELECT domain, first_channel, first_seen_at, panel_kind, panel_version, entity_name "
                        "FROM relay_candidate WHERE level>=1 AND first_channel LIKE '%ct_log%' ORDER BY first_seen_at DESC LIMIT 5"):
        feed.append({"t": r["first_seen_at"], "kind": "new_site",
                     "text": "发现引擎自主确认新站 %s（%s %s）" % (r["domain"], r["panel_kind"], r["panel_version"] or ""),
                     "sub": "通道：%s · 系统名「%s」" % (r["first_channel"], r["entity_name"] or "—")})
    for r in db.execute("SELECT source, url, fetched_at, id FROM source_snapshot WHERE source LIKE 'relay.pricing.%' "
                        "OR source IN ('openrouter.models','deepseek.pricing') ORDER BY fetched_at DESC LIMIT 6"):
        n = db.execute("SELECT COUNT(*) c FROM offer_norm WHERE snapshot_id=?", (r["id"],)).fetchone()["c"]
        if n:
            feed.append({"t": r["fetched_at"], "kind": "collect",
                         "text": "采集 %s：%d 条报价入库" % (r["source"], n), "sub": r["url"], "sid": r["id"]})
    feed.sort(key=lambda x: x["t"], reverse=True)
    return feed[:8]


def main():
    db = D.connect()
    models, fxinfo = build_models(db)
    sites, stats = build_sites(db)
    data = {"generated_at": D.now8(), "fx": fxinfo, "models": models, "sites": sites,
            "stats": stats, "feed": build_feed(db)}
    p = os.path.join(HERE, "home_data.json")
    with open(p, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)
    print("模型 %d 个 · 站点 %d · 动态 %d · %s" % (len(models), len(sites), len(data["feed"]), p))
    for m in models:
        print("  %-18s 参考 %-11s $%-7.2f  中转 %d 家" % (m["name"], m["floor_vendor"], m["floor_out"], m["n_relay"]))


if __name__ == "__main__":
    main()
