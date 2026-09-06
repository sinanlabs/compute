CREATE TABLE IF NOT EXISTS site_submission (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT NOT NULL,
  user_id TEXT,
  note TEXT,
  status TEXT NOT NULL DEFAULT 'pending',   -- pending | confirmed | already_listed | no_panel | unreachable
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  checked_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_submission_status ON site_submission(status, id);
