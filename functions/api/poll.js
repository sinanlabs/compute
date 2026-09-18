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
  // 结果缓存 5 分钟：每次页面加载都查一遍会白白消耗 D1 读取额度
  const cache = caches.default; const ck = new Request("https://compute.sinanlab.com/api/poll?q=" + q, { method: "GET" });
  const hit = await cache.match(ck); if (hit) return withCors(request, new Response(hit.body, hit));
  let out = {}, degraded = false;
  try { const r = await env.DB.prepare("SELECT key a, SUM(n) n FROM events WHERE name=? GROUP BY key").bind("poll:" + q).all(); for (const x of r.results || []) out[x.a] = x.n; }
  catch (e) { degraded = true; }
  const res = json({ q, counts: out, ...(degraded ? { degraded: true } : {}) });
  if (!degraded) { const c = new Response(res.body, res); c.headers.set("Cache-Control", "public, max-age=300"); await cache.put(ck, c.clone()); return withCors(request, c); }
  return withCors(request, res);
}
