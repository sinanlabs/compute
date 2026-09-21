-- 收信存档：hello@sinanlab.com 的来信由 sinan-inbox Worker 写入，供每天早上的来信处理使用。
-- 只存正文与信头字段，不存附件内容；原件仍转发到所有者邮箱。
CREATE TABLE IF NOT EXISTS inbox_mail (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  msg_id TEXT,                          -- Message-ID
  from_addr TEXT NOT NULL,
  from_name TEXT,
  to_addr TEXT,
  subject TEXT,
  sent_at TEXT,                         -- 发件人信头里的时间
  in_reply_to TEXT,                     -- 若是对我们某封通知的回复
  body_text TEXT,                       -- 纯文本正文（上限 24 KB）
  body_len INTEGER,
  attachments TEXT,                     -- 附件文件名列表，仅记录名字
  spf TEXT, dkim TEXT,                  -- 发件校验信头，判定来信是否可信时参考
  received_at TEXT NOT NULL DEFAULT (datetime('now')),
  status TEXT NOT NULL DEFAULT 'new',   -- new | triaged | replied | ignored | error
  category TEXT,                        -- correction | key | verify | press | partnership | spam | other
  site TEXT,                            -- 若能对上我们索引里的站，记域名
  handled_at TEXT, handled_by TEXT, action TEXT, note TEXT
);
CREATE INDEX IF NOT EXISTS inbox_status ON inbox_mail(status, received_at);
CREATE INDEX IF NOT EXISTS inbox_from ON inbox_mail(from_addr);
