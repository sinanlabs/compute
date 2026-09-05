// POST /api/check/report —— 自测结果回流（可选、登录用户）。只收计数与判定，不收 Key、不收响应正文。
// body = { base, model, raw_model, counts:[8], echo, ttfb_ms:[8], ok, verdict }
import { getSession, json, withCors, preflight, bump } from "../_lib.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const b = await request.json().catch(() => ({}));
  const base = String(b.base || "").toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "").slice(0, 120);
  const model = String(b.model || "").slice(0, 80), raw = String(b.raw_model || "").slice(0, 120);
  if (!/^[a-z0-9.\-]+$/.test(base) || !model) return withCors(request, json({ error: "bad_request" }, 400));
  const counts = Array.isArray(b.counts) ? b.counts.slice(0, 16).map((x) => (Number.isFinite(+x) ? +x : null)) : [];
  const ttfb = Array.isArray(b.ttfb_ms) ? b.ttfb_ms.slice(0, 16).map((x) => (Number.isFinite(+x) ? Math.round(+x) : null)) : [];
  const verdict = ["consistent", "prefix", "divergent", "no_ref", "failed"].includes(b.verdict) ? b.verdict : "unknown";
  await env.DB.prepare("INSERT INTO crowd_probe(user_id, base, model, raw_model, counts_json, echo_model, ttfb_json, ok_n, verdict) VALUES (?,?,?,?,?,?,?,?,?)")
    .bind(s.user.id, base, model, raw, JSON.stringify(counts), String(b.echo || "").slice(0, 120), JSON.stringify(ttfb), Math.min(16, +b.ok || 0), verdict).run();
  await bump(env, "crowd_probe", verdict);
  return withCors(request, json({ ok: true }));
}
