-- 众测：允许匿名回流（不再强制登录），记来源哈希与来源类型（web / cli）。旧表数据迁入。
CREATE TABLE IF NOT EXISTS crowd_probe_v2 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  src_hash TEXT,                        -- sha256(IP + UA) 前 24 位，只用来数"来自几个不同来源"
  source TEXT NOT NULL DEFAULT 'web',   -- web | cli
  base TEXT NOT NULL,
  model TEXT NOT NULL,
  raw_model TEXT,
  counts_json TEXT NOT NULL,
  echo_model TEXT,
  ttfb_json TEXT,
  ok_n INTEGER NOT NULL DEFAULT 0,
  verdict TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO crowd_probe_v2(user_id, base, model, raw_model, counts_json, echo_model, ttfb_json, ok_n, verdict, review_status, created_at)
  SELECT user_id, base, model, raw_model, counts_json, echo_model, ttfb_json, ok_n, verdict, review_status, created_at FROM crowd_probe;
DROP TABLE crowd_probe;
ALTER TABLE crowd_probe_v2 RENAME TO crowd_probe;
CREATE INDEX IF NOT EXISTS crowd_probe_base ON crowd_probe(base, model);
CREATE INDEX IF NOT EXISTS crowd_probe_time ON crowd_probe(created_at);
