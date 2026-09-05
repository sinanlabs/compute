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
              region=None, conditions=None, valid_from=None):
    sku = "%s::%s::%s::%s" % (vendor, model, unit, region or "-")
    cur = db.execute(
        "INSERT INTO offer_norm(sku_key,vendor,vendor_kind,model,region,currency,unit,price,"
        "conditions,valid_from,snapshot_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (sku, vendor, vendor_kind, model, region, currency, unit, price,
         json.dumps(conditions or {}, ensure_ascii=False), valid_from or now8(), snapshot_id))
    return cur.lastrowid
