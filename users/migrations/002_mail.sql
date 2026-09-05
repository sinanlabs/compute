-- 邮件：订阅者（不登录也能订周报）+ 通知任务令牌（每日流水线触发发送用）
CREATE TABLE IF NOT EXISTS subscribers (
  email_hash TEXT PRIMARY KEY,         -- sha256(lower(email))
  email TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', -- pending | active | unsubscribed
  token_hash TEXT,                     -- 确认 / 退订链接令牌的 sha256
  lang TEXT NOT NULL DEFAULT 'zh',     -- zh | en
  digest TEXT NOT NULL DEFAULT 'weekly', -- weekly | daily
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  confirmed_at TEXT,
  unsubscribed_at TEXT,
  last_sent_at TEXT
);

CREATE TABLE IF NOT EXISTS notify_jobs (
  token_hash TEXT PRIMARY KEY,         -- 流水线本地生成随机令牌，写入哈希；接口校验后即作废
  kind TEXT NOT NULL,                  -- test | daily | weekly
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  used_at TEXT,
  result_json TEXT
);
