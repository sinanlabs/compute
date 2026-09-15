// GET /api/notify/optout?t=<email_hash>.<hmac>  —— 站长通知退订。记 KV optout:<hash>，永久生效。
import { hmac } from "../_lib.js";
export async function onRequestGet({ request, env }) {
  const t = new URL(request.url).searchParams.get("t") || "";
  const [h, sig] = t.split(".");
  if (!h || !sig || sig !== (await hmac(env.SESSION_SECRET, "optout:" + h))) return new Response("链接无效", { status: 400, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  await env.KV.put("optout:" + h, "1");
  return new Response("已退订：这个邮箱不会再收到司南实验室的站长通知。如需恢复，写信到 hello@sinanlab.com。", { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
