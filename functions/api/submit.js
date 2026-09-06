// POST /api/submit {domain, note?} —— 用户提交一个中转站。登录用户每天最多 10 条；只收域名，夜间流水线做面板确认后回写状态。
// GET /api/submit —— 我提交过的
import { getSession, json, withCors, preflight, bump } from "./_lib.js";
import { rateLimit } from "./auth/_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const r = await env.DB.prepare("SELECT domain, status, note, created_at, checked_at FROM site_submission WHERE user_id=? ORDER BY id DESC LIMIT 50").bind(s.user.id).all();
  return withCors(request, json({ items: r.results || [] }));
}
export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const b = await request.json().catch(() => ({}));
  let d = String(b.domain || "").trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "").replace(/^www\./, "");
  if (!/^(?=.{4,120}$)([a-z0-9-]+\.)+[a-z]{2,}$/.test(d)) return withCors(request, json({ error: "bad_domain" }, 400));
  if (!(await rateLimit(env, `submit:${s.user.id}`, 10, 86400))) return withCors(request, json({ error: "too_many_requests" }, 429));
  const dup = await env.DB.prepare("SELECT status FROM site_submission WHERE domain=? AND status IN ('pending','confirmed','already_listed') ORDER BY id DESC LIMIT 1").bind(d).first();
  if (dup) return withCors(request, json({ ok: true, domain: d, status: dup.status, duplicate: true }));
  await env.DB.prepare("INSERT INTO site_submission(domain, user_id, note) VALUES (?,?,?)").bind(d, s.user.id, String(b.note || "").slice(0, 200)).run();
  await bump(env, "submit");
  return withCors(request, json({ ok: true, domain: d, status: "pending" }));
}
