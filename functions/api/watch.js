import { getSession, json, withCors, preflight, bump } from "./_lib.js";

const OK_KIND = new Set(["site", "model"]);
export async function onRequestOptions({ request }) { return preflight(request); }

export async function onRequestGet({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const w = await env.DB.prepare("SELECT kind, key, created_at FROM watches WHERE user_id=? ORDER BY created_at DESC").bind(s.user.id).all();
  return withCors(request, json({ watches: w.results || [] }));
}
export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const b = await request.json().catch(() => ({}));
  const kind = String(b.kind || ""), key = String(b.key || "").trim().toLowerCase().slice(0, 120);
  if (!OK_KIND.has(kind) || !/^[a-z0-9.\-]+$/.test(key)) return withCors(request, json({ error: "bad_request" }, 400));
  const n = await env.DB.prepare("SELECT COUNT(*) c FROM watches WHERE user_id=?").bind(s.user.id).first();
  if (n && n.c >= 200) return withCors(request, json({ error: "limit", message: "最多关注 200 个" }, 429));
  await env.DB.prepare("INSERT OR IGNORE INTO watches(user_id, kind, key) VALUES (?,?,?)").bind(s.user.id, kind, key).run();
  await bump(env, "watch", kind);
  return withCors(request, json({ ok: true, kind, key }));
}
export async function onRequestDelete({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const b = await request.json().catch(() => ({}));
  await env.DB.prepare("DELETE FROM watches WHERE user_id=? AND kind=? AND key=?").bind(s.user.id, String(b.kind || ""), String(b.key || "").toLowerCase()).run();
  return withCors(request, json({ ok: true }));
}
