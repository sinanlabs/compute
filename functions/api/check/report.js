// POST /api/check/report —— 众测回流（匿名可用；登录用户带 user_id）。只收计数与判定，不收 Key、不收响应正文。
// body = { base, model, raw_model, counts:[8], echo, ttfb_ms:[8], ok, verdict, source: web|cli }
// 防刷：每个来源（IP+UA 哈希）每天 60 条；同一来源对同一 站×模型 每天只记 1 条（后到的覆盖前面的）。
import { getSession, json, withCors, preflight, bump, sha256 } from "../_lib.js";
import { rateLimit } from "../auth/_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  // 公开：某站的众测汇总（30 天）
  const base = (new URL(request.url).searchParams.get("base") || "").toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "").slice(0, 120);
  if (!/^[a-z0-9.\-]+$/.test(base)) return withCors(request, json({ error: "bad_request" }, 400));
  const r = await env.DB.prepare("SELECT model, verdict, COUNT(*) n, COUNT(DISTINCT COALESCE(src_hash, user_id)) srcs FROM crowd_probe WHERE base=? AND created_at >= datetime('now','-30 days') GROUP BY model, verdict").bind(base).all();
  return withCors(request, json({ base, items: r.results || [] }));
}
export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request);
  const b = await request.json().catch(() => ({}));
  const base = String(b.base || "").toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "").slice(0, 120);
  const model = String(b.model || "").slice(0, 80), raw = String(b.raw_model || "").slice(0, 120);
  if (!/^[a-z0-9.\-]+$/.test(base) || !model) return withCors(request, json({ error: "bad_request" }, 400));
  const ip = request.headers.get("CF-Connecting-IP") || "", ua = request.headers.get("User-Agent") || "";
  const src = (await sha256(ip + "|" + ua)).slice(0, 24);
  if (!(await rateLimit(env, `crowd:${src}`, 60, 86400))) return withCors(request, json({ error: "too_many_requests" }, 429));
  const counts = Array.isArray(b.counts) ? b.counts.slice(0, 16).map((x) => (Number.isFinite(+x) ? +x : null)) : [];
  const ttfb = Array.isArray(b.ttfb_ms) ? b.ttfb_ms.slice(0, 16).map((x) => (Number.isFinite(+x) ? Math.round(+x) : null)) : [];
  const verdict = ["consistent", "prefix", "divergent", "no_ref", "failed"].includes(b.verdict) ? b.verdict : "unknown";
  const source = b.source === "cli" ? "cli" : "web";
  // 同一来源、同一 站×模型、同一天：只保留最后一条
  await env.DB.prepare("DELETE FROM crowd_probe WHERE src_hash=? AND base=? AND model=? AND date(created_at)=date('now')").bind(src, base, model).run();
  await env.DB.prepare("INSERT INTO crowd_probe(user_id, src_hash, source, base, model, raw_model, counts_json, echo_model, ttfb_json, ok_n, verdict) VALUES (?,?,?,?,?,?,?,?,?,?,?)")
    .bind(s ? s.user.id : null, src, source, base, model, raw, JSON.stringify(counts), String(b.echo || "").slice(0, 120), JSON.stringify(ttfb), Math.min(16, +b.ok || 0), verdict).run();
  await bump(env, "crowd_probe", verdict);
  return withCors(request, json({ ok: true, anonymous: !s }));
}
