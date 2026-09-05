# -*- coding: utf-8 -*-
"""多模态（图像 / 视频）页面数据导出 → media.json。

结构：按族（veo / kling / hailuo / nano-banana / flux …）组织。每族：
  官方参考（有则给价与单位）、各站报价（实付、折算每秒、比率、分档、假设、版本提示、快照）、卖的站数。
无官方参考的族也导出（只列报价与区间，不给比率）—— 不硬比。
"""
import os, sys, json, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core.cost_floor import band
from core.media import compare, official_refs, media_site_gate, DEFAULT_CLIP, CLIP_SOURCE, parse_version, recent_versions, version_key, version_label
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILY_NAME = {"veo": "Veo（Google）", "kling": "Kling 可灵（快手）", "hailuo": "Hailuo / H3（MiniMax）", "seedance": "Seedance（字节）",
               "vidu": "Vidu（生数）", "wan": "Wan 万相（阿里）", "sora": "Sora（OpenAI）", "runway": "Runway", "pixverse": "PixVerse",
               "grok-vid": "Grok Imagine 视频（xAI）", "omni": "Gemini Omni Flash（Google）", "happyhorse": "HappyHorse", "luma": "Luma",
               "nano-banana": "Nano Banana / Gemini Image（Google）", "gpt-image": "GPT Image（OpenAI）", "seedream": "Seedream（字节）",
               "flux": "FLUX（BFL）", "qwen-image": "Qwen-Image（阿里）", "midjourney": "Midjourney", "grok-image": "Grok Imagine 图像（xAI）",
               "kling-image": "Kling Image（快手）", "ideogram": "Ideogram", "recraft": "Recraft", "sd": "Stable Diffusion", "hidream": "HiDream"}
REF_SOURCE = {"veo": "ai.google.dev 定价页（按秒）", "kling": "kling.ai/dev/pricing（按秒）", "hailuo": "platform.minimax.io 按量计费页（按秒）",
              "nano-banana": "ai.google.dev 定价页（按张等价价）", "flux": "bfl.ai/pricing（按百万像素，1 张按 1MP）", "kling-image": "kling.ai/dev/pricing（按张）"}
REF_MISSING = {"seedance": "火山方舟价格页为前端异步渲染，未能读取", "vidu": "Vidu 开放平台定价页为前端渲染，未能读取", "wan": "阿里百炼计费页为前端渲染，未能读取",
               "sora": "OpenAI 定价页拒绝抓取（403）", "gpt-image": "OpenAI 定价页拒绝抓取（403）", "midjourney": "Midjourney 官方无按次 API 定价（订阅制）",
               "seedream": "火山方舟价格页为前端异步渲染，未能读取", "qwen-image": "阿里百炼计费页为前端渲染，未能读取", "grok-image": "xAI 定价页未接入", "grok-vid": "xAI 定价页未接入"}


def main():
    db = D.connect()
    fxr = db.execute("SELECT rate, as_of, snapshot_id FROM fx_rate ORDER BY id DESC LIMIT 1").fetchone()
    refs = official_refs(db)
    rows = db.execute("SELECT vendor, model, unit, price, conditions, snapshot_id, valid_from FROM offer_norm WHERE vendor_kind='relay' "
                      "AND unit IN ('per_call','per_second') AND superseded_by IS NULL").fetchall()
    fam_rows = defaultdict(list); per_site = defaultdict(list)
    for r in rows:
        c = json.loads(r["conditions"] or "{}"); p = c.get("panel_price")
        if c.get("usd_direct"): eff = r["price"]; p = fxr["rate"]
        elif p is None: continue
        else: eff = r["price"] * float(p) / fxr["rate"]
        name = c.get("raw_name") or r["model"]
        res = compare({"name": name, "unit": r["unit"], "eff_usd": eff, "duration_s": c.get("duration_s")}, refs)
        if res["modality"] not in ("image", "video") or not res.get("family") or res.get("placeholder"): continue
        row = {"site": r["vendor"], "name": name, "unit": r["unit"], "eff": round(eff, 4), "nominal": r["price"], "price_field": round(float(p), 4), "usd_direct": bool(c.get("usd_direct")), "spec": c.get("spec"),
               "sids": [r["snapshot_id"]], "as_of": r["valid_from"][:16], "tier": res.get("tier"), "version_note": res.get("version_note")}
        if res.get("ratio") is not None:
            code, label = band(res["ratio"])
            row.update({"ratio": round(res["ratio"], 4), "band": code, "assumption": res.get("assumption"), "ref_model": res["ref_model"],
                        "ref_price": res["ref_price"], "ref_region": res["ref_region"], "ref_sid": res["ref_sid"],
                        "per_s": round(res["relay_per_s"], 4) if res["modality"] == "video" else None})
            per_site[r["vendor"]].append(res["ratio"])
        fam_rows[(res["modality"], res["family"])].append(row)
    HELD = media_site_gate(per_site)
    out = {"image": [], "video": []}
    for (mod, fam), lst in fam_rows.items():
        for x in lst: x["held"] = x["site"] in HELD
        cmp_rows = [x for x in lst if x.get("ratio") is not None and not x["held"]]
        ref = None
        for (m, u), (price, region, sid, vendor) in refs.items():
            pass
        # 官方参考：取该族第一条比对里的 ref
        if cmp_rows:
            r0 = cmp_rows[0]
            ref = {"model": r0["ref_model"], "price": r0["ref_price"], "region": r0["ref_region"], "sid": r0["ref_sid"],
                   "unit": "per_second" if mod == "video" else "per_call", "source": REF_SOURCE.get(fam)}
        rank = {"explainable": 0, "normal": 1, "premium": 2, "below_bulk": 3, "unsustainable": 4, "far_above": 5}
        # 版本：每族只主推最新两代，其余标 old 折叠
        recent = recent_versions(fam, [x["name"] for x in lst], k=2)
        for x in lst:
            v = parse_version(fam, x["name"]); x["version"] = v; x["version_label"] = version_label(fam, v)
            x["recent"] = (v in recent) if v is not None else (len(recent) == 0)
        lst.sort(key=lambda x: (1 if x["held"] else 0, 0 if x["recent"] else 1, -version_key(x["version"]), rank.get(x.get("band"), 9), x.get("ratio") or 0, x["eff"]))
        effs = [x["eff"] for x in lst if not x["held"]]
        out[mod].append({"family": fam, "name": FAMILY_NAME.get(fam, fam), "ref": ref, "ref_missing": None if ref else REF_MISSING.get(fam, "官方定价未接入"),
                         "default_clip": DEFAULT_CLIP.get(fam) if mod == "video" else None, "clip_source": CLIP_SOURCE.get(fam) if mod == "video" else None,
                         "n_sites": len({x["site"] for x in lst}), "n_rows": len(lst), "n_cmp": len(cmp_rows),
                         "eff_min": min(effs) if effs else None, "eff_med": st.median(effs) if effs else None, "eff_max": max(effs) if effs else None,
                         "bands": {k: sum(1 for x in cmp_rows if x["band"] == k) for k in rank}, "rows": lst,
                         "recent_versions": recent, "recent_labels": [version_label(fam, v) for v in recent], "n_old": sum(1 for x in lst if not x["recent"])})
    for mod in out:
        out[mod].sort(key=lambda f: (0 if f["ref"] else 1, -f["n_sites"]))
    snaps = {}
    for mod in out:
        for f in out[mod]:
            if f["ref"]: snaps[f["ref"]["sid"]] = 1
            for x in f["rows"]:
                for s in x["sids"]: snaps[s] = 1
    snapmeta = {}
    for sid in snaps:
        r = db.execute("SELECT id, source, url, fetched_at, sha256 FROM source_snapshot WHERE id=?", (sid,)).fetchone()
        if r: snapmeta[str(sid)] = dict(r)
    r = db.execute("SELECT id, source, url, fetched_at, sha256 FROM source_snapshot WHERE id=?", (fxr["snapshot_id"],)).fetchone()
    if r: snapmeta[str(r["id"])] = dict(r)
    data = {"generated_at": D.now8(), "fx": {"rate": fxr["rate"], "as_of": fxr["as_of"], "sid": fxr["snapshot_id"]}, "held_sites": sorted(HELD),
            "image": out["image"], "video": out["video"], "snaps": snapmeta,
            "stats": {"image_rows": sum(f["n_rows"] for f in out["image"]), "video_rows": sum(f["n_rows"] for f in out["video"]),
                      "image_sites": len({x["site"] for f in out["image"] for x in f["rows"]}), "video_sites": len({x["site"] for f in out["video"] for x in f["rows"]}),
                      "image_cmp": sum(f["n_cmp"] for f in out["image"]), "video_cmp": sum(f["n_cmp"] for f in out["video"])}}
    json.dump(data, open(os.path.join(HERE, "media.json"), "w"), ensure_ascii=False, default=str)
    s = data["stats"]
    print("图像：%d 族 / %d 条 / %d 站 / 可比 %d   视频：%d 族 / %d 条 / %d 站 / 可比 %d   媒体站级闸 %d 站" % (
        len(out["image"]), s["image_rows"], s["image_sites"], s["image_cmp"], len(out["video"]), s["video_rows"], s["video_sites"], s["video_cmp"], len(HELD)))
    for mod in ("video", "image"):
        for f in out[mod]:
            print("  %-6s %-34s 站 %3d 条 %3d 可比 %3d  官方 %s" % (mod, f["name"], f["n_sites"], f["n_rows"], f["n_cmp"], ("%.3f %s" % (f["ref"]["price"], f["ref"]["unit"])) if f["ref"] else "—"))


if __name__ == "__main__":
    main()
