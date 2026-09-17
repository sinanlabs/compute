// GET /api/x/callback?code=&state= —— 首页脚本在跳回后几秒内调用，立刻换取用户令牌，存 KV x:oauth2（本机 social_post 用 wrangler 读）。
import { json } from "../_lib.js";
const REDIRECT = "https://compute.sinanlab.com/";
export async function onRequestGet({ request, env }) {
  const u = new URL(request.url); const code = u.searchParams.get("code") || "", state = u.searchParams.get("state") || "";
  if (!code || !state) return json({ error: "missing" }, 400);
  const verifier = await env.KV.get("x:pkce:" + state);
  if (!verifier) return json({ error: "state_unknown_or_expired" }, 400);
  if (!env.X_CLIENT_ID || !env.X_CLIENT_SECRET) return json({ error: "no_client_secret" }, 500);
  const body = new URLSearchParams({ grant_type: "authorization_code", code, redirect_uri: REDIRECT, code_verifier: verifier, client_id: env.X_CLIENT_ID });
  const r = await fetch("https://api.x.com/2/oauth2/token", { method: "POST", headers: { Authorization: "Basic " + btoa(env.X_CLIENT_ID + ":" + env.X_CLIENT_SECRET), "Content-Type": "application/x-www-form-urlencoded" }, body });
  const js = await r.json().catch(() => ({}));
  if (!r.ok) return json({ error: "exchange_failed", status: r.status, detail: js }, 502);
  await env.KV.delete("x:pkce:" + state);
  await env.KV.put("x:oauth2", JSON.stringify({ access_token: js.access_token, refresh_token: js.refresh_token || "", scope: js.scope, obtained_at: new Date().toISOString() }));
  return json({ ok: true, scope: js.scope });
}
