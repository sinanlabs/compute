import { makeState, safeReturn } from "../../_lib.js";

// GET /api/auth/github/start?return_to=/s/xxx&watch=site:xxx
export async function onRequestGet({ request, env }) {
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET || !env.SESSION_SECRET || !env.DB) {
    return new Response("登录尚未开通：GitHub 应用与密钥还没配置。", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  const url = new URL(request.url);
  const { state, cookie } = await makeState(env, { return_to: safeReturn(env, url.searchParams.get("return_to") || "/me"), watch: (url.searchParams.get("watch") || "").slice(0, 200) });   // 不写 KV（见 _lib.makeState）
  const gh = new URL("https://github.com/login/oauth/authorize");
  gh.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  gh.searchParams.set("redirect_uri", `${env.SITE_ORIGIN}/api/auth/github/callback`);
  gh.searchParams.set("scope", "read:user user:email");
  gh.searchParams.set("state", state);
  return new Response(null, { status: 302, headers: { Location: gh.toString(), "Set-Cookie": cookie, "Cache-Control": "no-store" } });
}
