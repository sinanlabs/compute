# -*- coding: utf-8 -*-
import hashlib, json, os, sqlite3, datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "compass.sqlite")
TZ8 = datetime.timezone(datetime.timedelta(hours=8))


def now8():
    """一律北京时间。本机是美西，差 15 小时，用错会把昨天当今天。"""
    return datetime.datetime.now(TZ8).isoformat(timespec="seconds")


def connect(path=None):
    db = sqlite3.connect(path or DB_PATH, timeout=60)   # 多线程拉价时等锁，别直接报 database is locked
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def put_snapshot(db, source, url, body, http_status=200, note=None):
    """存快照，哈希寻址，同源同哈希只存一次。正文实际应落对象存储，这里先落本地。"""
    if isinstance(body, str):
        body = body.encode("utf-8")
    h = hashlib.sha256(body).hexdigest()
    row = db.execute("SELECT id FROM source_snapshot WHERE source=? AND sha256=?", (source, h)).fetchone()
    if row:
        return row["id"]
    raw_key = "raw/%s/%s" % (source, h)
    cur = db.execute(
        "INSERT INTO source_snapshot(source,url,fetched_at,http_status,sha256,raw_key,fetch_note)"
        " VALUES(?,?,?,?,?,?,?)", (source, url, now8(), http_status, h, raw_key, note))
    p = os.path.join(os.path.dirname(DB_PATH), raw_key)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(body)
    return cur.lastrowid


def put_offer(db, vendor, vendor_kind, model, unit, price, currency, snapshot_id,
              region=None, conditions=None, valid_from=None, sku=None):
    sku = sku or "%s::%s::%s::%s" % (vendor, model, unit, region or "-")
    cur = db.execute(
        "INSERT INTO offer_norm(sku_key,vendor,vendor_kind,model,region,currency,unit,price,"
        "conditions,valid_from,snapshot_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (sku, vendor, vendor_kind, model, region, currency, unit, price,
         json.dumps(conditions or {}, ensure_ascii=False), valid_from or now8(), snapshot_id))
    return cur.lastrowid


def ensure_panel_currency(db):
    db.execute("CREATE TABLE IF NOT EXISTS panel_currency (vendor TEXT PRIMARY KEY, currency_type TEXT, payment_symbol TEXT, price REAL, stripe_unit_price REAL, checked TEXT)")


def save_panel_currency(db, vendor, st):
    """面板 /api/status 里和充值币种有关的字段（adapters/newapi_pricing 每次抓价时顺带记）。"""
    ensure_panel_currency(db)
    db.execute("INSERT INTO panel_currency(vendor, currency_type, payment_symbol, price, stripe_unit_price, checked) VALUES (?,?,?,?,?,?) "
               "ON CONFLICT(vendor) DO UPDATE SET currency_type=excluded.currency_type, payment_symbol=excluded.payment_symbol, price=excluded.price, "
               "stripe_unit_price=excluded.stripe_unit_price, checked=excluded.checked",
               (vendor, st.get("currency_type"), st.get("payment_currency_symbol"), st.get("price"), st.get("stripe_unit_price"), now8()))


def usd_topup(db):
    """美元充值的站 → (每 $1 额度实付多少美元, 依据, 来源 auto|owner)。这些站实付 = 站方标价 × 每 $1 实付美元，不除汇率。
       ①面板公开设置写明美元充值：currency_type=USD 且支付符号 $，此时 price 就是每 $1 额度的美元售价（apiniuma.com 站长 2026-11-16 确认）；
       ②站长来信确认、写在 data/topup_overrides.json 的（如 catrouter.io：标准面板 price=1，实际走 Stripe 美元充值）。
       2026-11-25 起；此前一律按人民币充值折算（÷ 汇率），这类站实付被低估约 6.7 倍。"""
    out = {}
    try:
        ensure_panel_currency(db)
        for r in db.execute("SELECT vendor, price FROM panel_currency WHERE upper(coalesce(currency_type,''))='USD' AND payment_symbol='$' AND price > 0"):
            out[r["vendor"]] = (float(r["price"]), "面板公开设置：充值币种美元，$1 额度售价 $%g" % float(r["price"]), "auto")
    except Exception:
        pass
    p = os.path.join(os.path.dirname(DB_PATH), "topup_overrides.json")
    if os.path.exists(p):
        for v, x in json.load(open(p, encoding="utf-8")).items():
            if v.startswith("_") or not isinstance(x, dict) or not x.get("usd_per_credit"): continue
            out[v] = (float(x["usd_per_credit"]), x.get("source") or "站长确认", "owner")
    return out


def pricing_last_ok(db):
    """站 → 最近一次完整读到定价接口的时间（adapters/base.mark_pricing_ok 记的；接口返回空或不完整不算）。
       2026-10-24 前用快照表里 HTTP 200 的时间：接口改成要登录、返回空列表也是 200，旧价一直被写成「今天核对过」。"""
    try:
        return {r["vendor"]: r["last_ok"] for r in db.execute("SELECT vendor, last_ok FROM pricing_ok WHERE last_ok IS NOT NULL")}
    except Exception:
        return {r["source"][len("relay.pricing."):]: r["t"] for r in db.execute("SELECT source, max(fetched_at) t FROM source_snapshot WHERE source LIKE 'relay.pricing.%' AND http_status=200 GROUP BY source")}
