-- 手机号登录：只存哈希
ALTER TABLE users ADD COLUMN phone_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS users_phone_hash ON users(phone_hash) WHERE phone_hash IS NOT NULL;
