// 报错：POST {kind, key, context, note, url} —— 需登录（防刷）。GET —— 我的报错。核实后进修正日志并署名（handle）。
import { getSession, json, withCors, preflight, bump } from "./_lib.js";
import { rateLimit } from "./auth/_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const r = await env.DB.prepare("SELECT id, kind, key, note, status, created_at, resolution FROM user_report WHERE user_id=? ORDER BY id DESC LIMIT 30").bind(s.user.id).all();
  return withCors(request, json({ items: r.results || [] }));
}
export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const b = await request.json().catch(() => ({}));
  const kind = ["quote", "site", "model", "media", "other"].includes(b.kind) ? b.kind : "other";
  const key = String(b.key || "").slice(0, 200), note = String(b.note || "").trim().slice(0, 1000), url = String(b.url || "").trim().slice(0, 500);
  if (note.length < 4) return withCors(request, json({ error: "note_too_short" }, 400));
  if (url && !/^https?:\/\//.test(url)) return withCors(request, json({ error: "bad_url" }, 400));
  if (!(await rateLimit(env, `report:${s.user.id}`, 10, 86400))) return withCors(request, json({ error: "too_many_requests" }, 429));
  await env.DB.prepare("INSERT INTO user_report(user_id, handle, kind, key, context, note, url) VALUES (?,?,?,?,?,?,?)").bind(s.user.id, s.user.handle || null, kind, key, String(b.context || "").slice(0, 300), note, url || null).run();
  await bump(env, "report", kind);
  return withCors(request, json({ ok: true }));
}
