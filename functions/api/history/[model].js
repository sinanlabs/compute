// GET /api/history/<model> —— 全量价格走势，登录用户可用；匿名请用公开的 /history/<model>.json（最近 7 天）。
import { getSession, json, withCors, preflight, bump } from "../_lib.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestGet({ request, env, params }) {
  const m = String(params.model || "").toLowerCase();
  if (!/^[a-z0-9.\-]+$/.test(m)) return withCors(request, json({ error: "bad_model" }, 400));
  const s = await getSession(env, request);
  if (!s) return withCors(request, json({ error: "login_required", public: "/history/" + m + ".json" }, 401));
  const v = env.KV ? await env.KV.get("history:" + m) : null;
  if (!v) return withCors(request, json({ error: "not_found" }, 404));
  await bump(env, "history_full", m);
  return withCors(request, new Response(v, { status: 200, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "private, max-age=600" } }));
}
