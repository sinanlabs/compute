import { randHex, safeReturn } from "../../_lib.js";
// GET /api/auth/google/start?return_to=…&watch=…  —— Google 账号登录（OpenID Connect）。需要 GOOGLE_CLIENT_ID（vars）与 GOOGLE_CLIENT_SECRET（Secrets）。
export async function onRequestGet({ request, env }) {
  if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET || !env.SESSION_SECRET || !env.KV || !env.DB) {
    return new Response("Google 登录尚未开通：应用与密钥还没配置。", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  const url = new URL(request.url);
  const state = randHex(16);
  await env.KV.put(`oauth:state:${state}`, JSON.stringify({ return_to: safeReturn(env, url.searchParams.get("return_to") || "/me"), watch: url.searchParams.get("watch") || "", provider: "google" }), { expirationTtl: 600 });
  const g = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  g.searchParams.set("client_id", env.GOOGLE_CLIENT_ID);
  g.searchParams.set("redirect_uri", `${env.SITE_ORIGIN}/api/auth/google/callback`);
  g.searchParams.set("response_type", "code");
  g.searchParams.set("scope", "openid email profile");
  g.searchParams.set("state", state);
  g.searchParams.set("prompt", "select_account");
  return Response.redirect(g.toString(), 302);
}
