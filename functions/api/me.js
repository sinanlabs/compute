import { getSession, json, withCors, preflight } from "./_lib.js";
import { mailReady } from "./_mail.js";
import { smsReady } from "./_sms.js";
const methods = (env) => ({ github: !!(env.GITHUB_CLIENT_ID && env.SESSION_SECRET), email: !!(mailReady(env) && env.SESSION_SECRET), phone: !!(smsReady(env) && env.SESSION_SECRET) });

export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  const s = await getSession(env, request);
  if (!s) { const m = methods(env); return withCors(request, json({ user: null, login: m.github || m.email || m.phone, methods: m })); }
  const w = await env.DB.prepare("SELECT kind, key, created_at FROM watches WHERE user_id=? ORDER BY created_at DESC LIMIT 300").bind(s.user.id).all();
  await env.DB.prepare("UPDATE users SET last_seen_at=datetime('now') WHERE id=?").bind(s.user.id).run();
  return withCors(request, json({ user: s.user, watches: w.results || [], login: true, methods: methods(env) }));
}
