// GET /api/x/start —— 管理员发起 X（推特）OAuth 2.0 授权（PKCE）。授权码只活 30 秒，所以换取必须在线上回调里立刻完成，不能经人手转贴。
import { getSession, json } from "../_lib.js";
const REDIRECT = "https://compute.sinanlab.com/";
const SCOPES = "tweet.read tweet.write users.read offline.access";
function b64url(buf) { return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
export async function onRequestGet({ request, env }) {
  const s = await getSession(env, request);
  if (!s || s.user.role !== "admin") return json({ error: "admin_only" }, 403);
  if (!env.X_CLIENT_ID) return json({ error: "no_client_id" }, 500);
  const rnd = crypto.getRandomValues(new Uint8Array(48)); const verifier = b64url(rnd);
  const challenge = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const state = b64url(crypto.getRandomValues(new Uint8Array(16)));
  await env.KV.put("x:pkce:" + state, verifier, { expirationTtl: 600 });
  const q = new URLSearchParams({ response_type: "code", client_id: env.X_CLIENT_ID, redirect_uri: REDIRECT, scope: SCOPES, state, code_challenge: challenge, code_challenge_method: "S256" });
  return Response.redirect("https://x.com/i/oauth2/authorize?" + q.toString(), 302);
}
