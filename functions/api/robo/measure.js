// POST /api/robo/measure —— Robo 众测：bench.py --upload 回流一条推理实测（匿名可用；登录用户带 user_id）。
// 只收指标与硬件指纹，不收图像、不收数据、不收密钥。每个来源每天 20 条；同一来源对同一 模型×显卡×精度 每天只记 1 条（后到覆盖）。
// 指标做范围校验（p50 1–60000 ms、p95 ≥ p50、显存 0–200 GB）；不通过直接拒。入库即 pending，后台核验后才进 Robo 站。
// GET ?model=<id> —— 公开：该模型的众测汇总（核验通过的，90 天）。
import { getSession, json, withCors, preflight, bump, sha256 } from "../_lib.js";
import { rateLimit } from "../auth/_otp.js";
const GPU_MAP = [[/4090/i, "rtx-4090"], [/5090/i, "rtx-5090"], [/A800/i, "a800-80g"], [/H800/i, "h800-80g"], [/A100/i, "a100-80g"], [/H100/i, "h100-80g"], [/Thor/i, "jetson-thor"], [/Orin/i, "jetson-orin"]];
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  const model = String(new URL(request.url).searchParams.get("model") || "").slice(0, 80);
  if (!/^[a-z0-9.\-]+$/.test(model)) return withCors(request, json({ error: "bad_request" }, 400));
  const r = await env.DB.prepare("SELECT hardware_id, gpu_name, precision, COUNT(*) n, COUNT(DISTINCT COALESCE(src_hash,user_id)) srcs, MIN(json_extract(metrics_json,'$.latency_ms_p50')) p50_min, MAX(json_extract(metrics_json,'$.latency_ms_p50')) p50_max FROM robo_measurement WHERE model_id=? AND review_status='verified' AND created_at >= datetime('now','-90 days') GROUP BY hardware_id, gpu_name, precision").bind(model).all();
  return withCors(request, json({ model, items: r.results || [] }));
}
export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request);
  const b = await request.json().catch(() => ({}));
  const model = String(b.model_id || "").slice(0, 80);
  const gpu = String((b.env && b.env.gpu) || b.gpu_name || "").slice(0, 80);
  const precision = ["bf16", "fp16", "fp32", "int8", "fp8", "int4"].includes(b.precision) ? b.precision : null;
  const m = b.metrics || {}; const p50 = +m.latency_ms_p50, p95 = m.latency_ms_p95 == null ? null : +m.latency_ms_p95, thr = m.throughput_chunks_s == null ? null : +m.throughput_chunks_s, vram = m.vram_peak_gb == null ? null : +m.vram_peak_gb;
  if (!/^[a-z0-9.\-]+$/.test(model) || !gpu || !precision) return withCors(request, json({ error: "bad_request", need: ["model_id", "env.gpu", "precision"] }), 400);
  if (!(p50 >= 1 && p50 <= 60000) || (p95 != null && !(p95 >= p50 && p95 <= 120000)) || (vram != null && !(vram >= 0 && vram <= 200))) return withCors(request, json({ error: "out_of_range" }, 400));
  const c = b.config || {}; const cfg = { batch: Math.max(1, Math.min(64, +c.batch || 1)), image_res: String(c.image_res || "").slice(0, 20), action_chunk: Math.max(0, Math.min(1000, +c.action_chunk || 0)), warmup_steps: Math.max(0, Math.min(10000, +c.warmup_steps || 0)), steps: Math.max(1, Math.min(100000, +c.steps || 0)) };
  if (cfg.steps < 100) return withCors(request, json({ error: "too_few_steps", min: 100 }, 400));
  const e = b.env || {}; const envj = { gpu, vram_gb: e.vram_gb == null ? null : +e.vram_gb, driver: String(e.driver || "").slice(0, 40), cuda: String(e.cuda || "").slice(0, 20), torch: String(e.torch || "").slice(0, 40), os: String(e.os || "").slice(0, 80), revision: String(e.revision || "").slice(0, 80) };
  const hw = (GPU_MAP.find(([re]) => re.test(gpu)) || [])[1] || null;
  const ip = request.headers.get("CF-Connecting-IP") || "", ua = request.headers.get("User-Agent") || "";
  const src = (await sha256(ip + "|" + ua)).slice(0, 24);
  if (!(await rateLimit(env, `robo_meas:${src}`, 20, 86400))) return withCors(request, json({ error: "too_many_requests" }, 429));
  await env.DB.prepare("DELETE FROM robo_measurement WHERE src_hash=? AND model_id=? AND gpu_name=? AND precision=? AND date(created_at)=date('now') AND review_status='pending'").bind(src, model, gpu, precision).run();
  const r = await env.DB.prepare("INSERT INTO robo_measurement(user_id, src_hash, model_id, hardware_id, gpu_name, precision, config_json, metrics_json, env_json, client_version) VALUES (?,?,?,?,?,?,?,?,?,?)")
    .bind(s ? s.user.id : null, src, model, hw, gpu, precision, JSON.stringify(cfg), JSON.stringify({ latency_ms_p50: p50, latency_ms_p95: p95, throughput_chunks_s: thr, vram_peak_gb: vram }), JSON.stringify(envj), String(b.client_version || "").slice(0, 20)).run();
  await bump(env, "robo_meas", hw || "unmapped");
  return withCors(request, json({ ok: true, id: r.meta && r.meta.last_row_id, hardware_id: hw, status: "pending", anonymous: !s }));
}
