import { json, withCors, preflight } from "./_lib.js";
// 公开的功能开关（只暴露前台需要的）
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env }) {
  if (!env.DB) return withCors(request, json({ MAINTENANCE_BANNER: "", SIGNUP_OPEN: "1" }));
  const r = await env.DB.prepare("SELECT key, value FROM flags WHERE key IN ('MAINTENANCE_BANNER','SIGNUP_OPEN')").all();
  const out = {}; (r.results || []).forEach((x) => (out[x.key] = x.value));
  return withCors(request, json(out, 200, { "Cache-Control": "public, max-age=60" }));
}
