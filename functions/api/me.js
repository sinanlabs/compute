import { getSession, json, withCors, preflight } from "./_lib.js";

export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  const s = await getSession(env, request);
  if (!s) return withCors(request, json({ user: null, login: !!(env.GITHUB_CLIENT_ID && env.SESSION_SECRET) }));
  const w = await env.DB.prepare("SELECT kind, key, created_at FROM watches WHERE user_id=? ORDER BY created_at DESC LIMIT 300").bind(s.user.id).all();
  await env.DB.prepare("UPDATE users SET last_seen_at=datetime('now') WHERE id=?").bind(s.user.id).run();
  return withCors(request, json({ user: s.user, watches: w.results || [], login: true }));
}
