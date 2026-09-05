-- Sinan Lab 用户系统 · D1 schema v1
-- 原则：不注册也能看全部公开数据；注册只解锁“个人化、历史、写入、工具”。邮箱只在需要发信时存，查询用哈希。

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,                 -- ulid
  handle TEXT,                         -- 展示名（GitHub login 或自定）
  email TEXT,                          -- 可空；用于魔法链接/提醒
  email_hash TEXT,                     -- sha256(lower(email))，唯一查找用
  avatar_url TEXT,
  role TEXT NOT NULL DEFAULT 'user',   -- user | contributor | admin
  status TEXT NOT NULL DEFAULT 'active', -- active | banned
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_hash ON users(email_hash) WHERE email_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS identities (        -- 第三方登录身份
  provider TEXT NOT NULL,              -- github | email
  provider_uid TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(id),
  raw_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (provider, provider_uid)
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,                 -- 随机 32 字节 hex；cookie 里只放 id，签名在服务端校验
  user_id TEXT NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL,
  ua_hash TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS magic_tokens (      -- 邮箱魔法链接（Resend 接入后启用）
  token_hash TEXT PRIMARY KEY,
  email_hash TEXT NOT NULL,
  email TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL,
  used_at TEXT
);

CREATE TABLE IF NOT EXISTS watches (           -- 关注列表：站或模型
  user_id TEXT NOT NULL REFERENCES users(id),
  kind TEXT NOT NULL,                  -- site | model
  key TEXT NOT NULL,                   -- 域名 或 模型 id
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (user_id, kind, key)
);

CREATE TABLE IF NOT EXISTS alert_prefs (
  user_id TEXT PRIMARY KEY REFERENCES users(id),
  email_on INTEGER NOT NULL DEFAULT 0,
  webhook_url TEXT,                    -- 飞书/钉钉
  digest TEXT NOT NULL DEFAULT 'daily' -- instant | daily | weekly
);

CREATE TABLE IF NOT EXISTS api_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  key_hash TEXT NOT NULL UNIQUE,
  label TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_used_at TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS corrections (       -- 用户纠错/补充（进审核队列）
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  site TEXT,                           -- compute | robo
  entity TEXT NOT NULL,                -- 域名 / 模型 id
  field TEXT,
  proposed TEXT NOT NULL,
  evidence_url TEXT,
  status TEXT NOT NULL DEFAULT 'pending', -- pending | accepted | rejected
  reviewer TEXT,
  reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ===== 后台（仅管理员写） =====
CREATE TABLE IF NOT EXISTS site_overrides (    -- 对某个中转站的人工干预，构建时读取
  domain TEXT PRIMARY KEY,
  hidden INTEGER NOT NULL DEFAULT 0,   -- 1 = 不在前台出现
  referral_url TEXT,                   -- 推广链接（默认空；一旦填写前台自动标“广告”）
  referral_label TEXT,
  note TEXT,                           -- 前台可见的说明（走措辞检查）
  updated_by TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS flags (             -- 功能开关
  key TEXT PRIMARY KEY,                -- REFERRAL_ENABLED | MAINTENANCE_BANNER | SIGNUP_OPEN ...
  value TEXT NOT NULL,
  updated_by TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO flags(key, value) VALUES ('REFERRAL_ENABLED', '0'), ('SIGNUP_OPEN', '1'), ('MAINTENANCE_BANNER', '');

CREATE TABLE IF NOT EXISTS audit_log (         -- 后台每一次写操作
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,                 -- 管理员邮箱
  action TEXT NOT NULL,
  target TEXT,
  before_json TEXT,
  after_json TEXT,
  at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (            -- 无 PII 的轻量计数：登录数、关注数、出站点击
  day TEXT NOT NULL,
  name TEXT NOT NULL,
  key TEXT NOT NULL DEFAULT '',
  n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, name, key)
);
