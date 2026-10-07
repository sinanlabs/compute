-- 来信里的密钥（站长发来的核验用 Key）：Worker 存档前用本机公钥加密成密文存这里，正文里仍打码。
-- 只有维护者 Mac 上的私钥（compass/data/inbox_key.pem，不进任何仓库）能解开；云端数据库里永远没有明文。
-- 2026-10-07 起来信不再转发到所有者邮箱，这是 Key 唯一的取回途径。
ALTER TABLE inbox_mail ADD COLUMN secrets_enc TEXT;
