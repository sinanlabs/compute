// POST /api/verify {domain, contact, note} —— 站长申请"经司南核验"。GET —— 我的申请。Key 不经网页，走邮件。
import { getSession, json, withCors, preflight, bump } from "./_lib.js";
import { rateLimit } from "./auth/_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const r = await env.DB.prepare("SELECT domain, status, created_at, updated_at FROM verify_request WHERE user_id=? ORDER BY id DESC LIMIT 20").bind(s.user.id).all();
  return withCors(request, json({ items: r.results || [] }));
}
export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const b = await request.json().catch(() => ({}));
  const d = String(b.domain || "").trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "").replace(/^www\./, "");
  if (!/^(?=.{4,120}$)([a-z0-9-]+\.)+[a-z]{2,}$/.test(d)) return withCors(request, json({ error: "bad_domain" }, 400));
  if (!(await rateLimit(env, `verify:${s.user.id}`, 5, 86400))) return withCors(request, json({ error: "too_many_requests" }, 429));
  // 必须已在总表里（go_links.json 由每日流水线生成，含全部已确认站）
  try {
    const gl = await env.ASSETS.fetch(new URL("/go_links.json", request.url)).then((r) => r.json());
    if (!gl[d]) return withCors(request, json({ error: "not_listed" }, 400));
  } catch (e) { /* 读不到清单时不拦 */ }
  const dup = await env.DB.prepare("SELECT status FROM verify_request WHERE domain=? AND status IN ('pending','keyed','verified') ORDER BY id DESC LIMIT 1").bind(d).first();
  if (dup) return withCors(request, json({ ok: true, domain: d, status: dup.status, duplicate: true }));
  await env.DB.prepare("INSERT INTO verify_request(domain, user_id, contact, note) VALUES (?,?,?,?)").bind(d, s.user.id, String(b.contact || "").slice(0, 160), String(b.note || "").slice(0, 300)).run();
  await bump(env, "verify_request");
  return withCors(request, json({ ok: true, domain: d, status: "pending" }));
}
