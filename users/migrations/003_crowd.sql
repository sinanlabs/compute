-- 自测结果回流：只存计数与判定，绝不存 Key 或响应正文
CREATE TABLE IF NOT EXISTS crowd_probe (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL REFERENCES users(id),
  base TEXT NOT NULL,                  -- 被测站域名
  model TEXT NOT NULL,                 -- 归一模型 id
  raw_model TEXT,                      -- 用户实际填的模型名
  counts_json TEXT NOT NULL,           -- 8 条公开探针的 prompt_tokens
  echo_model TEXT,
  ttfb_json TEXT,
  ok_n INTEGER NOT NULL DEFAULT 0,
  verdict TEXT NOT NULL,               -- consistent | prefix | divergent | no_ref | failed
  review_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS crowd_probe_base ON crowd_probe(base, model);
