# -*- coding: utf-8 -*-
"""站点数据导出 v2：给首页 + 每站详情页。全部真数据，每个数字带快照 ID。

新增：站点画像（中位比率 → 簇）、可用性（T0 心跳 24h）、面板事实（登录方式/人机验证/通道价）、
真实价格变动（同 sku 前后价不同）、模型芯片按厂商分组。
"""
from __future__ import unicode_literals
import os, sys, json, re, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as D
from core.cost_floor import band
from core.latest import latest_by_family
from core.modelname import canonical

HERE = os.path.dirname(os.path.abspath(__file__))
REF_KINDS = ("official", "marketplace")
PRETTY = json.load(open(os.path.join(HERE, "pretty.json"))) if os.path.exists(os.path.join(HERE, "pretty.json")) else {}
VENDOR_OF = [("anthropic", r"^claude"), ("openai", r"^(gpt|o\d|codex)"), ("google", r"^gemini"), ("deepseek", r"^deepseek"),
             ("moonshot", r"^kimi"), ("zhipu", r"^glm"), ("xai", r"^grok"), ("alibaba", r"^qwen"), ("minimax", r"^minimax")]
VENDOR_NAME = {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google", "deepseek": "DeepSeek", "moonshot": "Moonshot",
               "zhipu": "智谱", "xai": "xAI", "alibaba": "阿里", "minimax": "MiniMax"}
# 站点画像与单条分档用同一把尺：<15% 不可持续 · 15–40% 低于批量折扣 · 40–125% 说得通/接近 · ≥125% 高于公开价
CLUSTER = [(0.15, "ultra", "超低价", "该站可比模型的实付中位数不到公开价的 15%，在无补贴假设下数学上不可持续"),
           (0.40, "cheap", "低于批量折扣", "实付中位数约为公开价的 15%–40%，低于常见批量采购折扣区间"),
           (1.25, "near", "与公开价接近", "实付中位数约为公开价的 40%–125%，价格本身说得通"),
           (1e9, "high", "高于公开价", "实付中位数高于公开价 1.25 倍，通常含服务溢价或倍率基数差异")]
LABEL_HELP = {
    "unsustainable": "实付低于该模型在无补贴假设下的成本下限。本站不推测成因，只给算术；是否下单由你判断。",
    "below_bulk": "低于常见的批量采购折扣区间（通常为公开价的 40%–75%）。存在真实批量渠道的可能，本站不下结论。",
    "explainable": "落在常见批量折扣区间内，价格本身说得通。这只说明价格不反常，不说明其他。",
    "normal": "与公开渠道价接近，相当于按官方价转售，差价是支付与稳定性的服务费。",
    "premium": "高于公开价，常见于含稳定性、并发或发票等服务的渠道。",
    "far_above": "显著高于公开价。常见原因是站方倍率基数与上游不同，也可能是本站读取的基数有误。",
}

def vendor_of(model):
    for v, rx in VENDOR_OF:
        if re.match(rx, model): return v
    return "other"

def pretty(m):
    if m in PRETTY: return PRETTY[m]
    s = m.replace("-", " ").replace("claude ", "Claude ").replace("gpt ", "GPT-").replace("gemini ", "Gemini ").replace("deepseek ", "DeepSeek ")
    s = s.replace("kimi ", "Kimi ").replace("glm ", "GLM-").replace("grok ", "Grok ").replace("qwen", "Qwen ").replace("minimax ", "MiniMax ")
    return re.sub(r"\b(v\d)", lambda x: x.group(1).upper(), s).replace("  ", " ").strip()

def fx(db):
    r = db.execute("SELECT rate, as_of, snapshot_id FROM fx_rate ORDER BY id DESC LIMIT 1").fetchone()
    return r["rate"], r["as_of"], r["snapshot_id"]

def snap(db, sid):
    r = db.execute("SELECT id, source, url, fetched_at, sha256 FROM source_snapshot WHERE id=?", (sid,)).fetchone()
    return dict(r) if r else None

def floors(db):
    out = {}
    for r in db.execute("SELECT model, unit, price, currency, vendor, snapshot_id, conditions FROM offer_norm WHERE vendor_kind IN (?,?) "
                        "AND superseded_by IS NULL AND unit IN ('per_mtok_in','per_mtok_out') AND vendor NOT LIKE '参考官方%'", REF_KINDS):
        rate = FX[0]
        usd = r["price"] / rate if r["currency"] == "CNY" else r["price"]
        k = (canonical(r["model"]), r["unit"])
        if k not in out or usd < out[k]["usd"]:
            out[k] = {"usd": usd, "vendor": r["vendor"], "sid": r["snapshot_id"], "cny": r["price"] if r["currency"] == "CNY" else None}
    return out

def relay_rows(db):
    rows = {}
    for r in db.execute("SELECT vendor, model, unit, price, conditions, snapshot_id, valid_from FROM offer_norm WHERE vendor_kind='relay' "
                        "AND superseded_by IS NULL AND unit IN ('per_mtok_in','per_mtok_out','per_call','per_second')"):
        c = json.loads(r["conditions"] or "{}")
        p = c.get("panel_price")
        if c.get("usd_direct"): eff = r["price"]; p = FX[0]        # 直接美元标价（kie.ai）：等价 price=汇率
        elif p is None: continue
        else: eff = r["price"] * float(p) / FX[0]
        key = (r["vendor"], canonical(r["model"]))
        m = rows.setdefault(key, {"vendor": r["vendor"], "model": canonical(r["model"]), "raw": c.get("raw_name") or r["model"],
                                  "in": None, "out": None, "call": None, "sec": None, "nominal_out": None, "price_field": float(p),
                                  "stripe": c.get("panel_stripe_unit_price"), "sids": set(), "as_of": r["valid_from"], "mtype": c.get("model_type")})
        side = {"per_mtok_in": "in", "per_mtok_out": "out", "per_call": "call", "per_second": "sec"}[r["unit"]]
        m[side] = eff
        if side == "out": m["nominal_out"] = r["price"]
        m["sids"].add(r["snapshot_id"])
    return rows

def site_gate(per_site_ratios):
    held = set()
    for v, rs in per_site_ratios.items():
        if len(rs) >= 3:
            med = st.median(rs); wild = sum(1 for x in rs if x > 20) / float(len(rs))
            if med > 3 or wild > 0.10 or med < 0.01: held.add(v)
    return held

def availability(db, hours=24):
    out = {}
    for r in db.execute("SELECT entity, metric, p50, window_from FROM metric_ts WHERE metric IN ('availability','ttfb_ms') "
                        "AND window_from >= datetime('now','-%d hours') ORDER BY window_from" % hours):
        d = out.setdefault(r["entity"], {"up": [], "ms": [], "last": r["window_from"]})
        (d["up"] if r["metric"] == "availability" else d["ms"]).append(r["p50"]); d["last"] = r["window_from"]
    res = {}
    for k, d in out.items():
        res[k] = {"uptime": round(100.0 * sum(d["up"]) / len(d["up"]), 1) if d["up"] else None, "n": len(d["up"]),
                  "ttfb_p50": round(st.median(d["ms"])) if d["ms"] else None, "last": d["last"]}
    return res

def status_facts(db):
    facts = {}
    for r in db.execute("SELECT c.domain, s.raw_key FROM relay_candidate c LEFT JOIN source_snapshot s ON s.id=c.snapshot_id WHERE c.level>=1"):
        if not r["raw_key"]: continue
        try:
            js = json.loads(open(os.path.join(os.path.dirname(D.DB_PATH), r["raw_key"]), "rb").read().decode("utf-8", "ignore"))
            d = js.get("data", js)
            login = [n for k, n in (("email_verification", "邮箱"), ("github_oauth", "GitHub"), ("wechat_login", "微信"), ("telegram_oauth", "Telegram"),
                                    ("linuxdo_oauth", "LINUX DO"), ("oidc_enabled", "OIDC"), ("discord_oauth", "Discord")) if d.get(k)]
            facts[r["domain"]] = {"system_name": d.get("system_name"), "version": d.get("version"), "login": login,
                                  "turnstile": bool(d.get("turnstile_check")), "price": d.get("price"), "stripe": d.get("stripe_unit_price"),
                                  "display": d.get("quota_display_type"), "announce": bool(d.get("announcements")), "checkin": bool(d.get("checkin_enabled")),
                                  "start_time": d.get("start_time")}
        except Exception: pass
    return facts

def probe_summary(db, days=7, n_probes=12, min_peers=3):
    """T1 指纹探针汇总：每个 站×模型 取最近一轮（同一 probe_idx 取最新一条），
    与同模型其他渠道的 token 计数签名比对：≥min_peers 站签名相同 → 形成共识簇。
    产出 {(site, model): {status, ok, n, echo, peers, ts}}，status ∈ consistent / divergent / no_consensus / failed。"""
    try:
        rows = db.execute("SELECT site, model, probe_idx, prompt_tokens, echo_model, status, ts FROM probe_t1 WHERE ts >= datetime('now','-%d days') ORDER BY id" % days).fetchall()
    except Exception:
        return {}
    latest = {}
    for r in rows:
        latest[(r["site"], r["model"], r["probe_idx"])] = r
    pairs = {}
    for (site, m, idx), r in latest.items():
        d = pairs.setdefault((site, m), {"sig": {}, "ok": 0, "n": 0, "echo_ok": 0, "ts": r["ts"][:10]})
        d["n"] += 1; d["ts"] = max(d["ts"], r["ts"][:10])
        if r["status"] == 200 and r["prompt_tokens"] is not None:
            d["ok"] += 1; d["sig"][idx] = r["prompt_tokens"]
            echo = (r["echo_model"] or "").lower().replace("_", "-")
            if m.lower() in echo or echo == "": d["echo_ok"] += 1
    out = {}
    by_model = {}
    for (site, m), d in pairs.items(): by_model.setdefault(m, []).append(site)
    def match(sa, sb):
        """两站签名在重叠位上差值恒定 → 同一分词器（差值 = 固定前缀 token 数）。返回 (是否匹配, 差值 b-a)。"""
        ks = [i for i in range(n_probes) if sa.get(i) is not None and sb.get(i) is not None]
        if len(ks) < 8: return False, 0
        ds = {sb[i] - sa[i] for i in ks}
        return (len(ds) == 1, ds.pop() if len(ds) == 1 else 0)
    for m, sites in by_model.items():
        full = [s_ for s_ in sites if pairs[(s_, m)]["ok"] >= n_probes - 2]
        clusters = []   # [{"sites": [...], "ref": sig, "offsets": {site: 相对 ref 的差}}]
        for s_ in full:
            sig = pairs[(s_, m)]["sig"]
            for cl in clusters:
                ok, off = match(cl["ref"], sig)
                if ok: cl["sites"].append(s_); cl["offsets"][s_] = off; break
            else:
                clusters.append({"sites": [s_], "ref": sig, "offsets": {s_: 0}})
        major = max(clusters, key=lambda c: len(c["sites"])) if clusters else None
        npeer = len(major["sites"]) if major else 0
        base_off = min(major["offsets"].values()) if major else 0
        for s_ in sites:
            d = pairs[(s_, m)]; offset = 0
            if d["ok"] == 0: status = "failed"
            elif s_ not in full: status = "partial"
            elif npeer < min_peers: status = "no_consensus"
            elif s_ in major["sites"]:
                status = "consistent"; offset = major["offsets"][s_] - base_off   # 相对簇内最小者多出的固定前缀
            else: status = "divergent"
            out[(s_, m)] = {"status": status, "ok": d["ok"], "n": max(d["n"], n_probes if d["ok"] else d["n"]), "echo": (d["echo_ok"] >= max(1, d["ok"])) if d["ok"] else None,
                            "peers": npeer, "offset": offset, "ts": d["ts"]}
    return out

def t2_summary(db, PB, days=7, min_peers=3):
    """T2 能力抽样：每个 站×模型 取最近一轮（同一 task_idx 取最新一条）的答对数；同模型 ≥min_peers 个渠道时给中位数。
    并入 PB[(site, model)]["cap"] = {score, n, median, peers, status}，status ∈ in_line（≥中位-2）/ below / no_ref。"""
    try:
        rows = db.execute("SELECT site, model, task_idx, ok, status, ts FROM probe_t2 WHERE ts >= datetime('now','-%d days') ORDER BY id" % days).fetchall()
    except Exception:
        return
    latest = {}
    for r in rows: latest[(r["site"], r["model"], r["task_idx"])] = r
    agg = {}
    for (site, m, i), r in latest.items():
        d = agg.setdefault((site, m), {"score": 0, "n": 0, "ok_req": 0, "ts": r["ts"][:10]})
        d["n"] += 1; d["score"] += r["ok"] or 0; d["ok_req"] += 1 if r["status"] == 200 else 0; d["ts"] = max(d["ts"], r["ts"][:10])
    by_model = {}
    for (site, m), d in agg.items():
        if d["ok_req"] >= 24: by_model.setdefault(m, []).append(d["score"])
    import statistics
    for (site, m), d in agg.items():
        if d["ok_req"] < 24: continue   # 请求成功太少，不出分
        peers = len(by_model.get(m, []))
        med = int(statistics.median(by_model[m])) if peers >= min_peers else None
        status = "no_ref" if med is None else ("in_line" if d["score"] >= med - 2 else "below")
        cap = {"score": d["score"], "n": d["n"], "median": med, "peers": peers, "status": status, "ts": d["ts"]}
        if (site, m) in PB: PB[(site, m)]["cap"] = cap
        else: PB[(site, m)] = {"status": "cap_only", "ok": 0, "n": 0, "echo": None, "peers": 0, "offset": 0, "ts": d["ts"], "cap": cap}

def price_changes(db, days=7):
    out = []
    for r in db.execute("""SELECT n.vendor, n.model, n.unit, o.price AS old_p, n.price AS new_p, n.valid_from, n.vendor_kind
                           FROM offer_norm n JOIN offer_norm o ON o.superseded_by=n.id
                           WHERE n.unit='per_mtok_out' AND abs(n.price-o.price)>1e-9 AND n.valid_from >= datetime('now','-%d days')
                           ORDER BY n.valid_from DESC LIMIT 200""" % days):
        out.append({"t": r["valid_from"], "vendor": r["vendor"], "model": canonical(r["model"]), "old": r["old_p"], "new": r["new_p"], "kind": r["vendor_kind"]})
    return out

def main():
    global FX
    db = D.connect(); FX = fx(db)
    F = floors(db); R = relay_rows(db); AV = availability(db); SF = status_facts(db); PB = probe_summary(db); t2_summary(db, PB)
    try: REG = {r["domain"]: (r["register_state"], r["register_msg"], r["register_checked"]) for r in db.execute("SELECT domain, register_state, register_msg, register_checked FROM relay_candidate WHERE level>=1")}
    except Exception: REG = {}
    CLOSED = {d_ for d_, v in REG.items() if v[0] == "closed"}

    # 站级比率 + 闸
    per_site = {}
    for (v, m), row in R.items():
        f = F.get((m, "per_mtok_out"))
        if f and row["out"] is not None and f["usd"] > 0:
            row["ratio"] = row["out"] / f["usd"]; row["floor"] = f
            per_site.setdefault(v, []).append(row["ratio"])
    HELD = site_gate(per_site)

    # ---- 模型表 ----
    latest = [x["model"] for x in latest_by_family(db, per_family=2) if x["has_reference"]]
    sold = {}
    for (v, m), row in R.items():
        if row.get("ratio") is not None: sold[m] = sold.get(m, 0) + 1
    hot = sorted([m for m, n in sold.items() if n >= 8 and (m, "per_mtok_out") in F], key=lambda m: -sold[m])
    # 新模型哨：中转站在卖（≥5 站）但没有官方/公开参考价 → 上不了账本，要么等 OpenRouter 收录，要么加官方定价适配器。每天打印，别再让新旗舰漏掉。
    sellers = {}
    for (v, m), row in R.items():
        if row.get("out") is not None: sellers[m] = sellers.get(m, 0) + 1
    no_ref = sorted([(m, n) for m, n in sellers.items() if n >= 5 and (m, "per_mtok_out") not in F and not re.search(r"(thinking|-cc$|-r$|-vip|-aws|-kiro|-je$|-qe$|-er$|-mi$|-wf$|-dt$|-da$|premium|\[|熊猫|特价)", m)], key=lambda x: -x[1])[:25]
    if no_ref: print("新模型哨（有中转报价、无参考价，上不了账本）：", ", ".join("%s(%d站)" % x for x in no_ref))
    order = latest + [m for m in hot if m not in latest]
    models, groups = [], {}
    for m in order[:40]:
        f = F.get((m, "per_mtok_out")); fi = F.get((m, "per_mtok_in"))
        if not f: continue
        rows = []
        for (v, mm), row in R.items():
            if mm != m or row.get("ratio") is None: continue
            code, label = band(row["ratio"])
            rows.append({"vendor": v, "out": round(row["out"], 3), "in": round(row["in"], 3) if row["in"] is not None else None,
                         "ratio": round(row["ratio"], 4), "band": code, "held": v in HELD, "as_of": row["as_of"][:16],
                         "nominal_out": row["nominal_out"], "price_field": row["price_field"], "stripe": row["stripe"], "sids": sorted(row["sids"]),
                         "uptime": (AV.get(v) or {}).get("uptime"), "name": (SF.get(v) or {}).get("system_name"), "probe": PB.get((v, m)), "reg": (REG.get(v) or ("unknown",))[0]})
        if not rows: continue
        rank = {"explainable": 0, "normal": 1, "premium": 2, "below_bulk": 3, "unsustainable": 4, "far_above": 5}
        rows.sort(key=lambda x: (1 if x["held"] else 0, rank.get(x["band"], 9), x["out"]))
        ven = vendor_of(m)
        entry = {"id": m, "name": pretty(m), "vendor": ven, "floor": {"vendor": f["vendor"], "out": round(f["usd"], 3), "in": round(fi["usd"], 3) if fi else None,
                 "sid": f["sid"], "cny": f["cny"]}, "n_relay": len(rows), "rows": rows, "is_latest": m in latest}
        models.append(entry); groups.setdefault(ven, []).append(m)

    # ---- 站点 ----
    sites = []
    for r in db.execute("SELECT domain, first_seen_at, first_channel, level, panel_kind, panel_version, entity_name, site_url FROM relay_candidate WHERE level>=1"):
        v = r["domain"]; rs = per_site.get(v, [])
        med = st.median(rs) if rs else None
        cl = None
        if v in HELD: cl = {"code": "held", "name": "计价方式待核", "help": "该站全线报价与公开价差距异常，常见原因是面板倍率基数与上游不同。核实前本站只列名义报价，不出比率。"}
        elif med is not None:
            for th, code, name, help_ in CLUSTER:
                if med < th: cl = {"code": code, "name": name, "help": help_}; break
        mrows = []
        for (vv, m), row in R.items():
            if vv != v: continue
            code, label = band(row["ratio"]) if row.get("ratio") is not None else (None, None)
            mrows.append({"model": m, "name": pretty(m), "raw": row["raw"], "in": row["in"], "out": row["out"], "call": row["call"], "sec": row["sec"],
                          "ratio": row.get("ratio"), "band": code, "floor_vendor": (row.get("floor") or {}).get("vendor"),
                          "floor_out": (row.get("floor") or {}).get("usd"), "mtype": row["mtype"], "sids": sorted(row["sids"]), "as_of": row["as_of"][:16], "probe": PB.get((v, m))})
        mrows.sort(key=lambda x: (0 if x["ratio"] is not None else 1, x["ratio"] or 0))
        sf = SF.get(v) or {}
        sites.append({"domain": v, "name": sf.get("system_name") or r["entity_name"], "site_url": r["site_url"], "first_seen": r["first_seen_at"][:10],
                      "channel": r["first_channel"], "panel": r["panel_kind"], "version": sf.get("version") or r["panel_version"],
                      "cluster": cl, "median": round(med, 3) if med is not None else None, "n_models": len(mrows), "n_ratio": len(rs),
                      "avail": AV.get(v), "facts": sf, "models": mrows, "register": {"state": (REG.get(v) or ("unknown", None, None))[0], "msg": (REG.get(v) or (None, None, None))[1], "checked": ((REG.get(v) or (None, None, None))[2] or "")[:10]}, "ok_count": sum(1 for x in mrows if x["band"] in ("explainable", "normal")),
                      "un_count": sum(1 for x in mrows if x["band"] == "unsustainable"),
                      "probe": {"pairs": sum(1 for x in mrows if x["probe"]), "consistent": sum(1 for x in mrows if x["probe"] and x["probe"]["status"] == "consistent"),
                                "divergent": sum(1 for x in mrows if x["probe"] and x["probe"]["status"] == "divergent"), "ts": max([x["probe"]["ts"] for x in mrows if x["probe"]] or [""])} if any(x["probe"] for x in mrows) else None})
    sites.sort(key=lambda s: (-(s["n_ratio"]), s["domain"]))

    snaps = {}
    for mdl in models:
        for row in mdl["rows"]:
            for sid in row["sids"]: snaps[sid] = snaps.get(sid) or snap(db, sid)
        snaps[mdl["floor"]["sid"]] = snaps.get(mdl["floor"]["sid"]) or snap(db, mdl["floor"]["sid"])
    snaps[FX[2]] = snap(db, FX[2])
    for s_ in sites:
        for row in s_["models"]:
            for sid in row["sids"]: snaps[sid] = snaps.get(sid) or snap(db, sid)

    changes_raw = price_changes(db)
    from collections import Counter
    cnt = Counter((c["vendor"], c["model"]) for c in changes_raw)
    changes = [c for c in changes_raw if cnt[(c["vendor"], c["model"])] == 1]
    # 只展示账本里的主流模型（最新两代 + 在卖最多的 40 个）的变动；老模型、站方自造名字的变价不进变动流 / RSS / 邮件 / 周报
    ledger_ids = {m["id"] for m in models}
    changes = [c for c in changes if c["model"] in ledger_ids]
    new_sites = [r["domain"] for r in db.execute("SELECT domain FROM relay_candidate WHERE level>=1 AND first_seen_at >= datetime('now','-1 day')")]

    # ---- 司南榜（测量榜，不是推荐榜）：六张榜 + 检测覆盖，全部带门槛与样本量 ----
    import datetime as _dt
    _t = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8)))
    week_id = "%d-w%02d" % _t.isocalendar()[:2]
    AV7 = availability(db, hours=168)
    site_by = {s_["domain"]: s_ for s_ in sites}
    def _nm(d_): return (site_by.get(d_) or {}).get("name")
    elig = [(d_, v) for d_, v in AV7.items() if v["n"] >= 24 and d_ in site_by and site_by[d_]["n_models"] >= 10 and d_ not in CLOSED]   # 关闭注册的站不上榜
    up_board = [{"domain": d_, "name": _nm(d_), "uptime": v["uptime"], "n": v["n"], "p50": v["ttfb_p50"]} for d_, v in sorted(elig, key=lambda kv: (-kv[1]["uptime"], kv[1]["ttfb_p50"] or 9e9))[:8]]
    fast_board = [{"domain": d_, "name": _nm(d_), "uptime": v["uptime"], "n": v["n"], "p50": v["ttfb_p50"]} for d_, v in sorted([kv for kv in elig if kv[1]["uptime"] >= 99 and kv[1]["ttfb_p50"]], key=lambda kv: kv[1]["ttfb_p50"])[:8]]
    vol = Counter(c["vendor"] for c in changes)
    big = [s_ for s_ in sites if s_["n_models"] >= 20 and s_["domain"] not in CLOSED]
    vol_board = [{"domain": d_, "name": _nm(d_), "n": n_} for d_, n_ in sorted([(s_["domain"], vol.get(s_["domain"], 0)) for s_ in big if vol.get(s_["domain"], 0) > 0], key=lambda x: -x[1])[:8]]
    zero_change = sum(1 for s_ in big if vol.get(s_["domain"], 0) == 0)
    cov_board = [{"domain": s_["domain"], "name": s_.get("name"), "n": s_["n_models"]} for s_ in sorted([s_ for s_ in sites if s_["n_models"] and s_["domain"] not in CLOSED], key=lambda s_: -s_["n_models"])[:8]]
    def _inrange(m): return sorted([r for r in m["rows"] if not r["held"] and r["band"] in ("explainable", "normal") and r["vendor"] not in CLOSED], key=lambda r: r["out"])
    flagship = []
    for m in [x for x in models if x["is_latest"]]:
        rs = _inrange(m)[:3]
        if rs: flagship.append({"id": m["id"], "name": m["name"], "vendor": m["vendor"], "floor": m["floor"]["out"], "n_inrange": len(_inrange(m)),
                                "rows": [{"vendor": r["vendor"], "name": r.get("name"), "out": r["out"], "ratio": r["ratio"]} for r in rs]})
    def _rows_of(mid):
        m = next((x for x in models if x["id"] == mid), None); return {r["vendor"]: r for r in _inrange(m)} if m else {}
    g6, f51 = _rows_of("gpt-6-astra"), _rows_of("claude-fable-5.1")
    dual = sorted([{"domain": v, "name": _nm(v), "gpt6": g6[v]["out"], "fable": f51[v]["out"], "sum": round(g6[v]["out"] + f51[v]["out"], 3)} for v in set(g6) & set(f51)], key=lambda x: x["sum"])[:8]
    probe_cov = sorted([dict(domain=s_["domain"], name=s_.get("name"), **s_["probe"]) for s_ in sites if s_.get("probe")], key=lambda x: (-x["consistent"], -x["pairs"]))
    # 可达分布 + 最低 8 家（满屏 100% 没有区分度，改成看分布和尾部）
    dist_up = {"full": sum(1 for _, v in elig if v["uptime"] >= 99.95), "hi": sum(1 for _, v in elig if 99 <= v["uptime"] < 99.95), "low": sum(1 for _, v in elig if v["uptime"] < 99)}
    low_board = [{"domain": d_, "name": _nm(d_), "uptime": v["uptime"], "n": v["n"], "p50": v["ttfb_p50"]} for d_, v in sorted(elig, key=lambda kv: (kv[1]["uptime"], -(kv[1]["ttfb_p50"] or 0)))[:8]]
    # 价格优势榜：最新代模型在说得通区间内的实付中位数（参考价的几成）最低；≥8 个可比模型
    latest_ids = {m["id"] for m in models if m["is_latest"]}
    psr = {}
    for m in models:
        if m["id"] not in latest_ids: continue
        for r in m["rows"]:
            if not r["held"] and r["band"] in ("explainable", "normal"): psr.setdefault(r["vendor"], []).append(r["ratio"])
    price_board = sorted([{"domain": v, "name": _nm(v), "median": round(st.median(rs), 4), "n": len(rs)} for v, rs in psr.items() if len(rs) >= 8 and v not in CLOSED], key=lambda x: x["median"])[:8]
    # 期号徽章：只对四张“正向语义”榜发（响应 / 价格优势 / 双旗舰 / 覆盖），每站取最好名次
    BOARD_NAME = {"fast": "响应榜", "price": "价格优势榜", "dual": "双旗舰榜", "coverage": "覆盖榜"}
    placements = {}
    for key, items, vt in (("fast", fast_board, lambda x: "%dms" % x["p50"]), ("price", price_board, lambda x: "参考价的 %d%%" % round(x["median"] * 100)),
                           ("dual", dual, lambda x: "$%s" % round(x["sum"], 2)), ("coverage", cov_board, lambda x: "%d 个模型" % x["n"])):
        for i, x in enumerate(items):
            cur = placements.get(x["domain"])
            if cur is None or i + 1 < cur["pos"]:
                placements[x["domain"]] = {"week": week_id, "board": key, "board_name": BOARD_NAME[key], "pos": i + 1, "value": vt(x)}
    for s_ in sites: s_["rank_badge"] = placements.get(s_["domain"])
    # ---- 多模态榜（图像 / 视频）：读 media.json（export_media 先跑）----
    media_rank = {"video": [], "image": [], "coverage": [], "price": []}
    mp = os.path.join(HERE, "media.json")
    if os.path.exists(mp):
        MJ = json.load(open(mp, encoding="utf-8")); held_media = set(MJ.get("held_sites") or [])
        fam_count, site_ratios = {}, {}
        for mod in ("video", "image"):
            for f in MJ.get(mod, []):
                rows = [r for r in f.get("rows", []) if not r.get("held") and r.get("site") not in held_media and r.get("site") not in CLOSED]
                for r in rows: fam_count.setdefault(r["site"], set()).add(f["family"])
                inr = [r for r in rows if r.get("band") in ("explainable", "normal") and r.get("ratio") is not None]
                for r in inr: site_ratios.setdefault(r["site"], []).append(r["ratio"])
                if not inr: continue
                keyf = (lambda r: r.get("per_s") or r.get("eff")) if mod == "video" else (lambda r: r.get("eff"))
                seen_site, best = set(), []
                for r in sorted([r for r in inr if keyf(r)], key=keyf):   # 同一站多个版本只取最低的一条
                    if r["site"] in seen_site: continue
                    seen_site.add(r["site"]); best.append(r)
                    if len(best) >= 3: break
                if best:
                    media_rank[mod].append({"family": f["family"], "name": f.get("name") or f["family"], "ref": (f.get("ref") or {}).get("usd") or best[0].get("ref_price"), "n_inrange": len(inr), "n_sites": f.get("n_sites"),
                                            "rows": [{"site": r["site"], "name": _nm(r["site"]), "value": round(keyf(r), 4), "ratio": r["ratio"], "label": r.get("version_label") or r.get("name")} for r in best]})
        media_rank["coverage"] = [{"domain": d_, "name": _nm(d_), "n": len(fs)} for d_, fs in sorted(fam_count.items(), key=lambda kv: -len(kv[1]))[:8]]
        media_rank["price"] = sorted([{"domain": d_, "name": _nm(d_), "median": round(st.median(rs), 4), "n": len(rs)} for d_, rs in site_ratios.items() if len(rs) >= 5], key=lambda x: x["median"])[:8]
        for i, x in enumerate(media_rank["price"]):
            cur = placements.get(x["domain"])
            if cur is None or i + 1 < cur["pos"]:
                placements[x["domain"]] = {"week": week_id, "board": "media_price", "board_name": "多模态价格优势榜", "pos": i + 1, "value": "参考价的 %d%%" % round(x["median"] * 100)}
        for s_ in sites: s_["rank_badge"] = placements.get(s_["domain"])
    rank = {"week": week_id, "media": media_rank, "date": D.now8()[:10], "window_days": 7, "n_sites": len(sites), "n_quotes": stats_quotes if False else None,
            "uptime": up_board, "fast": fast_board, "flagship": flagship, "dual": dual, "volatility": vol_board, "zero_change": zero_change, "n_big": len(big),
            "coverage": cov_board, "probe": probe_cov, "eligible_uptime": len(elig), "dist_up": dist_up, "low": low_board, "price": price_board,
            "register": {"closed": len(CLOSED), "open": sum(1 for v in REG.values() if v[0] == "open"), "unknown": sum(1 for v in REG.values() if v[0] not in ("open", "closed"))}}
    stats = {"confirmed": len(sites), "with_quotes": sum(1 for s_ in sites if s_["n_models"]), "quotes": db.execute("SELECT COUNT(*) c FROM offer_norm WHERE vendor_kind='relay' AND superseded_by IS NULL").fetchone()["c"],
             "seen_domains": db.execute("SELECT COUNT(*) c FROM seen_domain").fetchone()["c"], "held": len(HELD),
             "clusters": {k: sum(1 for s_ in sites if s_["cluster"] and s_["cluster"]["code"] == k) for k in ("ultra", "cheap", "near", "high", "held")},
             "reachable": sum(1 for s_ in sites if (s_["avail"] or {}).get("uptime", 0) and s_["avail"]["uptime"] >= 50),
             "reg_closed": len(CLOSED), "reg_open": sum(1 for v in REG.values() if v[0] == "open"),
             "probed_sites": sum(1 for s_ in sites if s_["probe"]), "probed_pairs": len(PB), "probe_consistent": sum(1 for v in PB.values() if v["status"] == "consistent"), "cap_pairs": sum(1 for v in PB.values() if v.get("cap")), "cap_below": sum(1 for v in PB.values() if (v.get("cap") or {}).get("status") == "below"), "probe_divergent": sum(1 for v in PB.values() if v["status"] == "divergent")}
    data = {"generated_at": D.now8(), "fx": {"rate": FX[0], "as_of": FX[1], "sid": FX[2]}, "models": models, "groups": groups,
            "vendor_name": VENDOR_NAME, "sites": sites, "stats": stats, "changes": changes[:40], "new_sites": new_sites,
            "snaps": {str(k): v for k, v in snaps.items() if v}, "label_help": LABEL_HELP, "probe_node": "美国西部探测节点", "rank": rank,
            "probe_help": "用本站在该中转站注册的 Key，向声明的模型发 12 条固定探针串（中英/emoji/代码/生僻字混排），各只要 1 个输出 token；记录返回的 prompt_tokens 计数与回显的模型名。同一模型不同分词器切出的 token 数不同：若 ≥3 个渠道对同一模型报出完全相同的 12 个计数，视为该模型的共识簇；某渠道的计数与共识簇不同，只记为“计数不一致”，不推测成因。这是一致性测量，不是真伪判定。"}
    rank["n_quotes"] = stats["quotes"]
    os.makedirs(os.path.join(HERE, "rank"), exist_ok=True)
    json.dump(rank, open(os.path.join(HERE, "rank", week_id + ".json"), "w"), ensure_ascii=False, default=str)   # 每周一期，永久链接用
    json.dump(data, open(os.path.join(HERE, "data_v2.json"), "w"), ensure_ascii=False, default=str)
    print("模型 %d · 站点 %d（有报价 %d，待核 %d）· 价格变动 %d · 新收录 %d · 快照 %d" % (
        len(models), len(sites), stats["with_quotes"], stats["held"], len(changes), len(new_sites), len(snaps)))
    print("簇：", stats["clusters"])

if __name__ == "__main__":
    main()
