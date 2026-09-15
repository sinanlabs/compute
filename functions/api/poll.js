// 需求探针：POST {q, a} —— 匿名单选计数，写 events(day,'poll:<q>',<a>)。GET ?q= —— 累计结果（公开）。
import { json, withCors, preflight, bump } from "./_lib.js";
const Q = { byok: ["need", "no", "unsure"] };
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) {
  const b = await request.json().catch(() => ({}));
  if (!Q[b.q] || !Q[b.q].includes(b.a)) return withCors(request, json({ error: "bad_poll" }, 400));
  await bump(env, "poll:" + b.q, b.a);
  return withCors(request, json({ ok: true }));
}
export async function onRequestGet({ request, env }) {
  const q = new URL(request.url).searchParams.get("q") || "byok"; if (!Q[q]) return withCors(request, json({ error: "bad_poll" }, 400));
  const r = await env.DB.prepare("SELECT key a, SUM(n) n FROM events WHERE name=? GROUP BY key").bind("poll:" + q).all();
  const out = {}; for (const x of r.results || []) out[x.a] = x.n;
  return withCors(request, json({ q, counts: out }));
}
