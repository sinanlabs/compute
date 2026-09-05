// 邮件订阅（不需要登录）：POST {email, lang} → 存 pending → 发确认信（双重确认）。
// 令牌不落库：t = <email_hash>.<hmac(SESSION_SECRET, "confirm:"+email_hash)>，退订同理前缀 "unsub:"。
import { json, withCors, preflight, sha256, hmac, bump } from "./_lib.js";
import { sendMail, layout, btn, esc, mailReady } from "./_mail.js";

const RX = /^[^\s@]{1,64}@[^\s@]{1,255}\.[a-zA-Z]{2,}$/;
export async function onRequestOptions({ request }) { return preflight(request); }

export async function confirmToken(env, emailHash) { return emailHash + "." + (await hmac(env.SESSION_SECRET, "confirm:" + emailHash)); }
export async function unsubToken(env, emailHash) { return emailHash + "." + (await hmac(env.SESSION_SECRET, "unsub:" + emailHash)); }

export async function onRequestPost({ request, env }) {
  if (!mailReady(env) || !env.SESSION_SECRET) return withCors(request, json({ error: "mail_not_ready" }, 503));
  const b = await request.json().catch(() => ({}));
  const email = String(b.email || "").trim().toLowerCase().slice(0, 254);
  const lang = b.lang === "en" ? "en" : "zh";
  if (!RX.test(email)) return withCors(request, json({ error: "bad_email" }, 400));
  const h = await sha256(email);
  const row = await env.DB.prepare("SELECT status, created_at FROM subscribers WHERE email_hash=?").bind(h).first();
  if (row && row.status === "active") return withCors(request, json({ ok: true, state: "already" }));
  if (row && row.status === "pending" && (Date.now() - new Date(row.created_at + "Z").getTime()) < 10 * 60e3) return withCors(request, json({ ok: true, state: "sent" }));
  await env.DB.prepare("INSERT INTO subscribers(email_hash,email,status,lang,created_at) VALUES(?,?,'pending',?,datetime('now')) ON CONFLICT(email_hash) DO UPDATE SET status='pending', lang=excluded.lang, created_at=datetime('now')").bind(h, email, lang).run();
  const link = `${env.SITE_ORIGIN}/api/subscribe/confirm?t=${await confirmToken(env, h)}&l=${lang}`;
  const zh = lang !== "en";
  const html = layout({
    lang,
    title: zh ? "确认订阅司南实验室" : "Confirm your Sinan Lab subscription",
    intro: zh ? "有人用这个邮箱在 sinanlab.com 申请订阅每周价格周报。如果是你，点下面的按钮确认；不是你，忽略这封邮件即可，我们不会再发。" : "Someone requested the weekly price report for this address at sinanlab.com. If that was you, confirm below; otherwise ignore this email and we will not write again.",
    body: btn(link, zh ? "确认订阅" : "Confirm subscription") + `<p style="font-size:12px;color:#9AA0B8;margin-top:14px">${zh ? "链接 24 小时内有效。" : "Link valid for 24 hours."}<br>${esc(link)}</p>`,
    footer: zh ? "本邮件由 sinanlab.com 订阅表单触发发送。" : "Sent because of a subscribe request on sinanlab.com.",
  });
  const r = await sendMail(env, { to: email, subject: zh ? "确认订阅 · Sinan Lab" : "Confirm subscription · Sinan Lab", html, text: link, tags: ["confirm"] });
  await bump(env, "mail", "confirm");
  return withCors(request, json(r.ok ? { ok: true, state: "sent" } : { error: "send_failed", detail: r.error }, r.ok ? 200 : 502));
}
