-- Robo 众测：推理延迟实测回流（bench.py --upload）与复现记录（模型 × 本体：跑通 / 需微调 / 未跑通）。
-- 匿名可用；只收指标与硬件指纹，不收图像、不收数据。待审 → 核验 / 拒绝 由后台完成；核验后进 Robo 站。
CREATE TABLE IF NOT EXISTS robo_measurement (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  src_hash TEXT,                        -- sha256(IP + UA) 前 24 位
  model_id TEXT NOT NULL,               -- Robo 索引里的模型 id
  hardware_id TEXT,                     -- 映射到 Robo 硬件 id（映射不了为空，保留 gpu_name）
  gpu_name TEXT NOT NULL,
  precision TEXT NOT NULL,
  config_json TEXT NOT NULL,            -- batch / image_res / action_chunk / warmup / steps
  metrics_json TEXT NOT NULL,           -- latency_ms_p50 / p95 / throughput_chunks_s / vram_peak_gb
  env_json TEXT,                        -- driver / cuda / torch / os / weights revision（无 PII）
  client_version TEXT,
  review_status TEXT NOT NULL DEFAULT 'pending',   -- pending | verified | rejected
  reviewer TEXT, reviewed_at TEXT, note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS robo_meas_key ON robo_measurement(model_id, hardware_id, precision);
CREATE INDEX IF NOT EXISTS robo_meas_status ON robo_measurement(review_status, created_at);

CREATE TABLE IF NOT EXISTS robo_repro (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  src_hash TEXT,
  model_id TEXT NOT NULL,
  embodiment_id TEXT NOT NULL,
  outcome TEXT NOT NULL,                -- works | finetune | failed
  setting TEXT,                         -- real | sim
  evidence_url TEXT,                    -- 日志 / 视频 / 仓库链接
  note TEXT,
  review_status TEXT NOT NULL DEFAULT 'pending',
  reviewer TEXT, reviewed_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS robo_repro_key ON robo_repro(model_id, embodiment_id);
CREATE INDEX IF NOT EXISTS robo_repro_status ON robo_repro(review_status, created_at);
