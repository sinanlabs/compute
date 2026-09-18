// POST /api/robo/repro —— Robo 复现记录：用户报告"模型 × 本体：跑通 / 需微调 / 未跑通"（匿名可用），附证据链接。
// 每个来源每天 10 条；同一来源对同一 模型×本体 每天只记 1 条（后到覆盖）。入库即 pending，后台核验后适配矩阵才升格为"社区复现"。
// GET ?model=<id> —— 公开：该模型核验通过的复现记录（不含来源哈希）。
import { getSession, json, withCors, preflight, bump, sha256 } from "../_lib.js";
import { rateLimit } from "../auth/_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
async function _get({ request, env }) {
  const model = String(new URL(request.url).searchParams.get("model") || "").slice(0, 80);
  if (!/^[a-z0-9.\-]+$/.test(model)) return withCors(request, json({ error: "bad_request" }, 400));
  const r = await env.DB.prepare("SELECT id, embodiment_id, outcome, setting, evidence_url, note, created_at FROM robo_repro WHERE model_id=? AND review_status='verified' ORDER BY created_at DESC LIMIT 100").bind(model).all();
  return withCors(request, json({ model, items: r.results || [] }));
}
async function _post({ request, env }) {
  const s = await getSession(env, request);
  const b = await request.json().catch(() => ({}));
  const model = String(b.model_id || "").slice(0, 80), emb = String(b.embodiment_id || "").slice(0, 80);
  const outcome = ["works", "finetune", "failed"].includes(b.outcome) ? b.outcome : null;
  const setting = ["real", "sim"].includes(b.setting) ? b.setting : null;
  const url = String(b.evidence_url || "").trim().slice(0, 300); const note = String(b.note || "").trim().slice(0, 500);
  if (!/^[a-z0-9.\-]+$/.test(model) || !/^[a-z0-9.\-]+$/.test(emb) || !outcome) return withCors(request, json({ error: "bad_request", need: ["model_id", "embodiment_id", "outcome"] }, 400));
  if (url && !/^https?:\/\/[^\s]+$/.test(url)) return withCors(request, json({ error: "bad_url" }, 400));
  if (!url && !note) return withCors(request, json({ error: "need_evidence", message: "请给一个链接（日志 / 视频 / 仓库）或写几句说明。" }, 400));
  const ip = request.headers.get("CF-Connecting-IP") || "", ua = request.headers.get("User-Agent") || "";
  const src = (await sha256(ip + "|" + ua)).slice(0, 24);
  if (!(await rateLimit(env, `robo_repro:${src}`, 10, 86400))) return withCors(request, json({ error: "too_many_requests" }, 429));
  await env.DB.prepare("DELETE FROM robo_repro WHERE src_hash=? AND model_id=? AND embodiment_id=? AND date(created_at)=date('now') AND review_status='pending'").bind(src, model, emb).run();
  const r = await env.DB.prepare("INSERT INTO robo_repro(user_id, src_hash, model_id, embodiment_id, outcome, setting, evidence_url, note) VALUES (?,?,?,?,?,?,?,?)")
    .bind(s ? s.user.id : null, src, model, emb, outcome, setting, url || null, note || null).run();
  await bump(env, "robo_repro", outcome);
  return withCors(request, json({ ok: true, id: r.meta && r.meta.last_row_id, status: "pending", anonymous: !s }));
}

// 数据库不可用（如免费额度用尽）时返回 503 JSON，而不是抛 1101；调用方（bench.py / 页面表单）据此提示"稍后再试"。
const guard = (fn) => async (ctx) => { try { return await fn(ctx); } catch (e) { const msg = String(e && e.message || e); return withCors(ctx.request, json({ error: "db_unavailable", message: /row read limit|D1_ERROR/.test(msg) ? "数据库今日额度已满，请明天再试（数据不会丢，重跑一次即可）。" : "服务暂时不可用，请稍后再试。" }, 503)); } };
export const onRequestGet = guard(_get);
export const onRequestPost = guard(_post);
