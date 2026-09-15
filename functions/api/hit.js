// POST /api/hit?r=<referrer host> —— 外部来源计数（只记来源域名与次数，不记用户）。写入 events(day,'ref',host)。
import { bump, withCors, preflight } from "./_lib.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) {
  const r = (new URL(request.url).searchParams.get("r") || "").toLowerCase().slice(0, 120);
  if (/^[a-z0-9.-]+\.[a-z]{2,}$/.test(r) && !/(^|\.)sinanlab\.com$/.test(r)) await bump(env, "ref", r);
  return withCors(request, new Response(null, { status: 204 }));
}
