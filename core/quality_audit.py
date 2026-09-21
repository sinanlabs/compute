# -*- coding: utf-8 -*-
"""数据核查（每晚在拉价之后、导出之前跑）。目的：错误不能靠用户发现。2026-09-06 的教训：apilio 把"按秒"写在附加字段里，
我们当成按次再按 5 秒折算，便宜 5 倍还排了榜首，是 Eric 看面板发现的。这里把这类错误变成机制：

  A 字段漂移   每站最新 /api/pricing 里出现解析器不认识的字段（含 other_info 子键）→ 报告"需要看一眼"
  B 单位提示（面板文字写了按秒）
  C 单位嫌疑（面板没写单位，但按次读异常低、按秒读正常）→ 该行待核 + 问站长   按次计价的图像/视频行，原始条目文字里却有"每秒 / /s / 按秒"→ 该行待核（不进比对、不进榜）
  C 价格孤点   同族里某站的每秒（图像：每张）实付 < 全族中位的 35%，且比第二便宜的站还低一半以上 → 待核，直到出现第二家相近价或人工放行
  D 榜首差距   （在 export_data 里执行）某族榜首比第二名低 40% 以上 → 榜首待核，不进榜

待核写进 quality_hold 表；export_media / export_data 读它。命令：
  python3 core/quality_audit.py            跑全部检查
  python3 core/quality_audit.py --list     看未放行的待核
  python3 core/quality_audit.py --clear ID [备注]   人工放行一条（复核过原始条目后）"""
import os, io, re, sys, json, statistics as st
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core.media import classify, compare, official_refs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 解析器（adapters/newapi_pricing.py）已处理或明知无关的字段；新字段出现即报告
KNOWN_FIELDS = {"model_name", "quota_type", "model_ratio", "model_price", "owner_by", "completion_ratio", "enable_groups", "supported_endpoint_types",
                "apis", "input_modalities", "output_modalities", "categories", "other_info", "release_at", "tags", "vendor_id", "description",
                "pricing_version", "show_name", "cache_ratio", "create_cache_ratio", "audio_ratio", "audio_completion_ratio", "image_ratio",
                "model_type", "group_ratio", "groups", "billing_type", "model", "name", "id", "price", "input", "output", "created", "object", "type",
                "icon", "sort", "status", "prompt", "completion", "context", "max_tokens", "note", "cache_creation_ratio", "cache_read_ratio", "web_search_price", "file_search_price", "search_ratio",
                "billing_mode", "billing_expr", "sort_order", "official_price", "available", "cover_image", "usage_count", "cache_creation_5m_ratio", "cache_creation_1h_ratio", "step_ratios", "billing_unit", "video_resolution_ratios", "billing_usage_schema", "billing_usage_examples", "translations", "context_length", "max_output_tokens", "release_date"}
KNOWN_OTHER_INFO = {"group_units", "default_discount"}
SEC_HINT = re.compile(r"(?<![a-z0-9-])(/\s*s(ec|econd|econds)?(?![a-z])|per[\s_-]?sec(ond)?(?![a-z])|每秒|/秒(?!内)|按秒|(?<![\d ])秒计[费价]|(?<![\d-])seconds?\b(?!\s*(of|video|clip|long)))", re.I)

def ensure(db):
    db.execute("""CREATE TABLE IF NOT EXISTS quality_hold (id INTEGER PRIMARY KEY, vendor TEXT, model TEXT, raw_name TEXT, unit TEXT, reason TEXT, detail TEXT,
                  created TEXT, cleared TEXT, cleared_note TEXT)""")
    db.execute("CREATE INDEX IF NOT EXISTS ix_qh_open ON quality_hold(vendor, raw_name, cleared)"); db.commit()

def open_holds(db):
    ensure(db)
    return db.execute("SELECT * FROM quality_hold WHERE cleared IS NULL").fetchall()

def hold(db, vendor, model, raw_name, unit, reason, detail):
    """幂等：同 站×原名×原因 未放行的只留一条。返回是否新增。"""
    r = db.execute("SELECT id FROM quality_hold WHERE vendor=? AND raw_name=? AND reason=? AND cleared IS NULL", (vendor, raw_name, reason)).fetchone()
    if r: return False
    db.execute("INSERT INTO quality_hold(vendor, model, raw_name, unit, reason, detail, created) VALUES (?,?,?,?,?,?,?)", (vendor, model, raw_name, unit, reason, detail[:300], D.now8()))
    return True

def latest_raw(db):
    """每个站最新一份 /api/pricing 原文 → {domain: [entries]}"""
    out = {}
    for r in db.execute("SELECT source, raw_key, MAX(fetched_at) f FROM source_snapshot WHERE source LIKE 'relay.pricing.%' GROUP BY source"):
        dom = r["source"][len("relay.pricing."):]; p = os.path.join(ROOT, "data", r["raw_key"])
        if not os.path.exists(p): continue
        try:
            d = json.loads(io.open(p, encoding="utf-8", errors="ignore").read())
        except Exception: continue
        data = d.get("data") if isinstance(d, dict) else d
        if isinstance(data, dict): data = [dict(v, model_name=k) for k, v in data.items() if isinstance(v, dict)]
        if isinstance(data, list): out[dom] = [m for m in data if isinstance(m, dict)]
    return out

def check_fields(raw):
    unknown = defaultdict(set); unknown_oi = defaultdict(set)
    for dom, entries in raw.items():
        for m in entries:
            for k in m.keys():
                if k not in KNOWN_FIELDS: unknown[k].add(dom)
            oi = m.get("other_info")
            if isinstance(oi, dict):
                for k in oi.keys():
                    if k not in KNOWN_OTHER_INFO: unknown_oi["other_info." + k].add(dom)
    rep = [{"field": k, "sites": len(v), "example": sorted(v)[:3]} for k, v in list(unknown.items()) + list(unknown_oi.items())]
    return sorted(rep, key=lambda x: -x["sites"])

def check_unit_hints(db, raw):
    """按次计价的图像/视频行，原始条目文字里有按秒提示 → 待核。"""
    new = 0; items = []
    idx = {dom: {str(m.get("model_name")): m for m in entries} for dom, entries in raw.items()}
    rows = db.execute("SELECT vendor, model, unit, price, conditions FROM offer_norm WHERE vendor_kind='relay' AND unit='per_call' AND superseded_by IS NULL").fetchall()
    for r in rows:
        c = json.loads(r["conditions"] or "{}"); name = c.get("raw_name") or r["model"]
        mod, fam = classify(name)
        if mod not in ("image", "video"): continue
        m = (idx.get(r["vendor"]) or {}).get(name)
        if not m: continue
        text = " ".join(str(m.get(k) or "") for k in ("tags", "description", "show_name", "note")) + " " + json.dumps(m.get("other_info") or {}, ensure_ascii=False)
        hit = SEC_HINT.search(text)
        if hit:
            if hold(db, r["vendor"], r["model"], name, r["unit"], "unit_hint", "原始条目含按秒提示「%s」但解析为按次：%s" % (hit.group(0), text[:120])): new += 1
            items.append({"site": r["vendor"], "name": name, "hint": hit.group(0)})
    return new, items


def check_unit_suspect(db):
    """C 单位嫌疑：面板没写单位、我们默认当按次的图像/视频行，若"按次读"远低于同型号参考价（<25%），
    而"按秒读"正好落回正常区间（40%–150%），就有很大可能是按秒计费被我们读成了按次（2026-09-20 relaydance 站长指出的那类错误）。
    这只是嫌疑，不改数字：该行标"待核"，不进比对与榜单，并由站长通知去问对方实际口径。"""
    from core.media import DEFAULT_CLIP
    refs = official_refs(db); new = 0; items = []
    rows = db.execute("SELECT vendor, model, unit, price, conditions FROM offer_norm WHERE vendor_kind='relay' AND unit='per_call' AND superseded_by IS NULL").fetchall()
    for r in rows:
        c = json.loads(r["conditions"] or "{}")
        if c.get("unit_source") or c.get("billing_mode"): continue   # 面板明确写了单位的不猜
        name = c.get("raw_name") or r["model"]
        mod, fam = classify(name)
        if mod not in ("image", "video") or not fam: continue
        a = compare({"name": name, "unit": "per_call", "eff_usd": r["price"]}, refs).get("ratio")
        if a is None or a >= 0.25: continue
        b = compare({"name": name, "unit": "per_second", "eff_usd": r["price"]}, refs).get("ratio")
        if b is None or not (0.4 <= b <= 1.5): continue
        clip = DEFAULT_CLIP.get(fam) or 5
        detail = "面板未写单位，按次读 = 参考价的 %d%%（异常低）；按每秒读 = %d%%（正常）。若确为按秒计费，我们按 %s 秒折算就会低估 %s 倍。" % (round(a * 100), round(b * 100), clip, clip)
        if hold(db, r["vendor"], r["model"], name, r["unit"], "unit_suspect", detail): new += 1
        items.append({"site": r["vendor"], "name": name, "per_call_ratio": round(a, 4), "per_second_ratio": round(b, 4)})
    return new, items

def check_lone_outliers(db):
    """同族里价格孤点：< 全族中位 35% 且比第二便宜的站低一半以上。"""
    fxr = db.execute("SELECT rate FROM fx_rate ORDER BY id DESC LIMIT 1").fetchone(); refs = official_refs(db)
    fam_best = defaultdict(dict)   # (mod, fam) -> site -> (value, name, unit)
    for r in db.execute("SELECT vendor, model, unit, price, conditions FROM offer_norm WHERE vendor_kind='relay' AND unit IN ('per_call','per_second') AND superseded_by IS NULL"):
        c = json.loads(r["conditions"] or "{}"); p = c.get("panel_price")
        if c.get("usd_direct"): eff = r["price"]
        elif p is None: continue
        else: eff = r["price"] * float(p) / fxr["rate"]
        name = c.get("raw_name") or r["model"]
        res = compare({"name": name, "unit": r["unit"], "eff_usd": eff, "duration_s": c.get("duration_s")}, refs)
        if res.get("modality") not in ("image", "video") or not res.get("family") or res.get("ratio") is None: continue
        v = res["relay_per_s"] if res["modality"] == "video" else eff
        if v is None or v <= 0: continue
        cur = fam_best[(res["modality"], res["family"])].get(r["vendor"])
        if cur is None or v < cur[0]: fam_best[(res["modality"], res["family"])][r["vendor"]] = (v, name, r["unit"], r["model"])
    new = 0; items = []
    for (mod, fam), sites in fam_best.items():
        if len(sites) < 4: continue
        vals = sorted((v[0], s) for s, v in sites.items()); med = st.median([x[0] for x in vals])
        v1, s1 = vals[0]; v2 = vals[1][0]
        if v1 < 0.35 * med and v1 < 0.5 * v2:
            _, name, unit, model = sites[s1]
            if hold(db, s1, model, name, unit, "lone_outlier", "%s/%s：%s%.4f，第二便宜 %.4f，族中位 %.4f（%d 站）" % (mod, fam, "每秒 $" if mod == "video" else "每张 $", v1, v2, med, len(sites))): new += 1
            items.append({"family": fam, "site": s1, "name": name, "value": round(v1, 4), "second": round(v2, 4), "median": round(med, 4)})
    return new, items

def retire_unit_switch(db):
    """同一 站×型号 同时有按次与按秒（或按分）两条现行行 = 解析升级后单位改判；旧单位那条作废（链到新行，但不算变价：单位不同）。"""
    n = 0
    for r in db.execute("""SELECT a.id AS old_id, b.id AS new_id FROM offer_norm a JOIN offer_norm b
                           ON a.vendor=b.vendor AND a.model=b.model AND a.superseded_by IS NULL AND b.superseded_by IS NULL AND a.unit<>b.unit
                           AND a.unit IN ('per_call','per_second','per_minute') AND b.unit IN ('per_call','per_second','per_minute') AND a.valid_from < b.valid_from""").fetchall():
        db.execute("UPDATE offer_norm SET superseded_by=?, valid_to=? WHERE id=?", (r["new_id"], D.now8(), r["old_id"])); n += 1
    db.commit(); return n

def main():
    db = D.connect(); ensure(db)
    if "--list" in sys.argv:
        for r in open_holds(db): print("#%-4d %-22s %-40s %-13s %s" % (r["id"], r["vendor"], (r["raw_name"] or "")[:40], r["reason"], (r["detail"] or "")[:90]))
        return
    if "--clear" in sys.argv:
        i = sys.argv.index("--clear"); hid = int(sys.argv[i + 1]); note = " ".join(sys.argv[i + 2:]) or "人工复核放行"
        db.execute("UPDATE quality_hold SET cleared=?, cleared_note=? WHERE id=?", (D.now8(), note, hid)); db.commit(); print("已放行 #%d" % hid); return
    n_ret = retire_unit_switch(db)
    raw = latest_raw(db)
    fields = check_fields(raw)
    n_hint, hints = check_unit_hints(db, raw)
    n_sus, suspects = check_unit_suspect(db)
    n_out, outs = check_lone_outliers(db)
    db.commit()
    opened = open_holds(db)
    rep = {"date": D.now8(), "sites_scanned": len(raw), "unit_switch_retired": n_ret, "unknown_fields": fields, "unit_hint_new": n_hint, "unit_hint": hints[:50], "unit_suspect_new": n_sus, "unit_suspect": suspects[:80],
           "lone_outlier_new": n_out, "lone_outliers": outs[:50], "open_holds": len(opened)}
    os.makedirs(os.path.join(ROOT, "data", "audit"), exist_ok=True)
    io.open(os.path.join(ROOT, "data", "audit", D.now8()[:10] + ".json"), "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False, indent=1))
    io.open(os.path.join(ROOT, "data", "audit", "latest.json"), "w", encoding="utf-8").write(json.dumps(rep, ensure_ascii=False))
    print("数据核查：扫 %d 站 · 单位改判作废旧行 %d · 未知字段 %d 个 · 单位提示新增待核 %d · 单位嫌疑新增待核 %d · 价格孤点新增待核 %d · 未放行待核共 %d" % (len(raw), n_ret, len(fields), n_hint, n_sus, n_out, len(opened)))
    for f in fields[:8]: print("   未知字段 %-34s %3d 站  例：%s" % (f["field"], f["sites"], ", ".join(f["example"])))
    for x in outs[:8]: print("   孤点 %-14s %-22s %-36s $%.4f（第二 %.4f · 中位 %.4f）" % (x["family"], x["site"], x["name"][:36], x["value"], x["second"], x["median"]))

if __name__ == "__main__":
    main()
