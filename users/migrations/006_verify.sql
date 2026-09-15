CREATE TABLE IF NOT EXISTS verify_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  user_id TEXT,
  contact TEXT,
  note TEXT,
  status TEXT NOT NULL DEFAULT 'pending',   -- pending | keyed | verified | failed
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_verify_status ON verify_request(status, id);
