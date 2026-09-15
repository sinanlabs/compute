CREATE TABLE IF NOT EXISTS user_report (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  handle TEXT,
  kind TEXT NOT NULL,          -- quote | site | model | media | other
  key TEXT NOT NULL,           -- 站域名 / 模型 id / "站|模型"
  context TEXT,                -- 抽屉标题等上下文
  note TEXT NOT NULL,          -- 用户写的说明
  url TEXT,                    -- 用户给的佐证链接（可空）
  status TEXT NOT NULL DEFAULT 'open',   -- open | fixed | rejected
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  resolved_at TEXT, resolution TEXT
);
CREATE INDEX IF NOT EXISTS ix_report_status ON user_report(status, id);
