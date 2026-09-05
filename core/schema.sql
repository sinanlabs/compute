-- 四层数据模型。铁律：任何对外展示的数字都必须能 join 回 source_snapshot。
-- join 不到 -> publish_guard 拒绝发布（见 core/wording.py 的 require_evidence）。

PRAGMA journal_mode=WAL;

-- L1 原始层：抓什么存什么，永不覆盖
CREATE TABLE IF NOT EXISTS source_snapshot (
  id            INTEGER PRIMARY KEY,
  source        TEXT    NOT NULL,          -- 逻辑源名，如 'siliconflow.pricing'
  url           TEXT    NOT NULL,
  fetched_at    TEXT    NOT NULL,          -- ISO8601 +08:00
  http_status   INTEGER,
  sha256        TEXT    NOT NULL,          -- 正文哈希，对象存储的 key
  raw_key       TEXT    NOT NULL,          -- 对象存储路径
  fetch_note    TEXT
);
CREATE INDEX IF NOT EXISTS ix_snap_src  ON source_snapshot(source, fetched_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_snap_hash ON source_snapshot(source, sha256);

-- L2 解析层：解析器版本化，改口径可回溯重跑
CREATE TABLE IF NOT EXISTS offer_raw (
  id             INTEGER PRIMARY KEY,
  snapshot_id    INTEGER NOT NULL REFERENCES source_snapshot(id),
  parser_version TEXT    NOT NULL,
  parsed_json    TEXT    NOT NULL,
  parse_ok       INTEGER NOT NULL DEFAULT 1,
  parse_error    TEXT
);
CREATE INDEX IF NOT EXISTS ix_raw_snap ON offer_raw(snapshot_id);

-- L3 归一层：比价 / 计算器 / 成本下限 只读这一层
CREATE TABLE IF NOT EXISTS offer_norm (
  id           INTEGER PRIMARY KEY,
  sku_key      TEXT    NOT NULL,           -- vendor::model::unit::region
  vendor       TEXT    NOT NULL,
  vendor_kind  TEXT    NOT NULL,           -- official | relay | gpu
  model        TEXT    NOT NULL,
  region       TEXT,
  currency     TEXT    NOT NULL,
  unit         TEXT    NOT NULL,           -- per_mtok_in | per_mtok_out | per_hour | per_clip
  price        REAL    NOT NULL,
  conditions   TEXT,                       -- JSON：阶梯、缓存、独占/切分、关机计费…
  valid_from   TEXT    NOT NULL,
  valid_to     TEXT,
  snapshot_id  INTEGER NOT NULL REFERENCES source_snapshot(id),   -- ★ 证据一等公民
  superseded_by INTEGER REFERENCES offer_norm(id)
);
CREATE INDEX IF NOT EXISTS ix_norm_sku ON offer_norm(sku_key, valid_from);
CREATE INDEX IF NOT EXISTS ix_norm_mdl ON offer_norm(model, unit, vendor_kind);

-- L4 指标层：探针产出，天生带样本量与置信区间
CREATE TABLE IF NOT EXISTS metric_ts (
  id          INTEGER PRIMARY KEY,
  entity      TEXT    NOT NULL,            -- 端点标识
  model       TEXT,
  metric      TEXT    NOT NULL,            -- availability | ttft_ms | tok_fp_match | bill_drift | ctx_recall | js_distance
  window_from TEXT    NOT NULL,
  window_to   TEXT    NOT NULL,
  probe_node  TEXT    NOT NULL,            -- cn-node-1 | ov-node-1
  n           INTEGER NOT NULL,
  p50         REAL, p95 REAL, mean REAL,
  ci_low      REAL, ci_high REAL,
  extra       TEXT
);
CREATE INDEX IF NOT EXISTS ix_metric ON metric_ts(entity, metric, window_from);

-- 发现引擎：候选池与分级
CREATE TABLE IF NOT EXISTS relay_candidate (
  id             INTEGER PRIMARY KEY,
  domain         TEXT UNIQUE NOT NULL,
  first_seen_at  TEXT NOT NULL,
  first_channel  TEXT NOT NULL,            -- ct_log | panel_fp | community | adjacency
  level          INTEGER NOT NULL DEFAULT 0,   -- 0..4
  cert_issued_at TEXT,
  panel_kind     TEXT,
  panel_version  TEXT,
  icp            TEXT,
  entity_name    TEXT,
  pay_methods    TEXT,
  model_count    INTEGER,
  min_cost_ratio REAL,                     -- 成本下限检验的最低比率
  last_checked   TEXT,
  status         TEXT DEFAULT 'alive',
  snapshot_id    INTEGER REFERENCES source_snapshot(id)
);
CREATE INDEX IF NOT EXISTS ix_cand_lv ON relay_candidate(level, first_seen_at);

-- 发布闸：每一条对外文本都要过闸并留痕
CREATE TABLE IF NOT EXISTS publish_log (
  id          INTEGER PRIMARY KEY,
  kind        TEXT NOT NULL,               -- fact | measurement | discovery
  target      TEXT NOT NULL,
  text        TEXT NOT NULL,
  verdict     TEXT NOT NULL,               -- pass | blocked
  violations  TEXT,
  evidence_ids TEXT NOT NULL,
  notified_at TEXT,                        -- 预通知发出时间
  window_ends TEXT,                        -- 72h 申诉窗口截止
  published_at TEXT,
  created_at  TEXT NOT NULL
);

-- 更正日志：不删不改
CREATE TABLE IF NOT EXISTS correction_log (
  id           INTEGER PRIMARY KEY,
  publish_id   INTEGER REFERENCES publish_log(id),
  original     TEXT NOT NULL,
  corrected    TEXT NOT NULL,
  reason       TEXT NOT NULL,
  corrected_at TEXT NOT NULL
);
