import { getSession, cookieHeader, safeReturn } from "../_lib.js";

export async function onRequest({ request, env }) {
  const s = await getSession(env, request);
  if (s) await env.DB.prepare("UPDATE sessions SET revoked=1 WHERE id=?").bind(s.sid).run();
  const to = safeReturn(env, new URL(request.url).searchParams.get("return_to") || "/");
  return new Response(null, { status: 302, headers: { Location: to, "Set-Cookie": cookieHeader(env, request, "", 0) } });
}
