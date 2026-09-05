// GET /api/subscribe/confirm?t=..&l=zh|en   GET /api/subscribe/unsubscribe?t=..
// 校验 HMAC 令牌（见 ../subscribe.js），改状态后 302 回母站订阅页，用 ?s= 告诉页面显示什么。
import { hmac, bump } from "../_lib.js";

const MOTHER = "https://sinanlab.com";
function back(lang, state) { return Response.redirect(`${MOTHER}${lang === "en" ? "/en" : ""}/subscribe?s=${state}`, 302); }

export async function onRequestGet({ request, env, params }) {
  const url = new URL(request.url);
  const t = url.searchParams.get("t") || "", lang = url.searchParams.get("l") === "en" ? "en" : "zh";
  const action = params.action === "unsubscribe" ? "unsub" : params.action === "confirm" ? "confirm" : null;
  if (!action || !env.SESSION_SECRET) return back(lang, "invalid");
  const [h, sig] = t.split(".");
  if (!h || !sig || !/^[0-9a-f]{64}$/.test(h)) return back(lang, "invalid");
  if ((await hmac(env.SESSION_SECRET, action + ":" + h)) !== sig) return back(lang, "invalid");
  const row = await env.DB.prepare("SELECT status, lang, created_at FROM subscribers WHERE email_hash=?").bind(h).first();
  if (!row) return back(lang, "invalid");
  if (action === "confirm") {
    if (row.status === "active") return back(row.lang || lang, "confirmed");
    if (Date.now() - new Date(row.created_at + "Z").getTime() > 24 * 3600e3) return back(row.lang || lang, "expired");
    await env.DB.prepare("UPDATE subscribers SET status='active', confirmed_at=datetime('now') WHERE email_hash=?").bind(h).run();
    await bump(env, "subscribe", "confirmed");
    return back(row.lang || lang, "confirmed");
  }
  await env.DB.prepare("UPDATE subscribers SET status='unsubscribed', unsubscribed_at=datetime('now') WHERE email_hash=?").bind(h).run();
  await bump(env, "subscribe", "unsubscribed");
  return back(row.lang || lang, "unsubscribed");
}
