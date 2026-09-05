// 登录用户的提醒设置。GET → 当前设置；POST {email_on:0|1, digest} → 保存；GET ?off=<token> → 邮件里一键关闭提醒。
// 关闭令牌 = <user_id>.<hmac(SESSION_SECRET, "off:"+user_id)>，不落库。
import { getSession, json, withCors, preflight, hmac, bump } from "./_lib.js";
import { mailReady } from "./_mail.js";

export async function onRequestOptions({ request }) { return preflight(request); }
export async function offToken(env, userId) { return userId + "." + (await hmac(env.SESSION_SECRET, "off:" + userId)); }

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url); const off = url.searchParams.get("off");
  if (off) {
    const [uid, sig] = off.split(".");
    if (uid && sig && (await hmac(env.SESSION_SECRET, "off:" + uid)) === sig) {
      await env.DB.prepare("INSERT INTO alert_prefs(user_id, email_on) VALUES(?,0) ON CONFLICT(user_id) DO UPDATE SET email_on=0").bind(uid).run();
      await bump(env, "prefs", "off_by_link");
      return Response.redirect(env.SITE_ORIGIN + "/me?alerts=off", 302);
    }
    return Response.redirect(env.SITE_ORIGIN + "/me?alerts=invalid", 302);
  }
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const p = await env.DB.prepare("SELECT email_on, digest, webhook_url FROM alert_prefs WHERE user_id=?").bind(s.user.id).first();
  return withCors(request, json({ email_on: p ? !!p.email_on : false, digest: (p && p.digest) || "daily", has_email: s.user.has_email, mail_ready: mailReady(env) }));
}

export async function onRequestPost({ request, env }) {
  const s = await getSession(env, request); if (!s) return withCors(request, json({ error: "login_required" }, 401));
  const b = await request.json().catch(() => ({}));
  const on = b.email_on ? 1 : 0; const digest = ["instant", "daily", "weekly"].includes(b.digest) ? b.digest : "daily";
  if (on && !s.user.has_email) return withCors(request, json({ error: "no_email", message: "你的 GitHub 没有公开可验证的邮箱，暂时无法开启邮件提醒。" }, 400));
  await env.DB.prepare("INSERT INTO alert_prefs(user_id, email_on, digest) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET email_on=excluded.email_on, digest=excluded.digest").bind(s.user.id, on, digest).run();
  await bump(env, "prefs", on ? "on" : "off");
  return withCors(request, json({ ok: true, email_on: !!on, digest }));
}
