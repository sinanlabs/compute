// POST /api/auth/email/start {email} → 发 6 位验证码到邮箱（Resend）。返回 {token, masked}。
import { json, withCors, preflight } from "../../_lib.js";
import { sendMail, mailReady } from "../../_mail.js";
import { issue, mask } from "../_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) {
  if (!mailReady(env) || !env.SESSION_SECRET) return withCors(request, json({ error: "email_login_unavailable" }, 503));
  const b = await request.json().catch(() => ({}));
  const email = String(b.email || "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) || email.length > 120) return withCors(request, json({ error: "bad_email" }, 400));
  const r = await issue(env, request, "email", email);
  if (r.error) return withCors(request, json({ error: r.error }, 429));
  const html = `<div style="font-family:-apple-system,Segoe UI,PingFang SC,Helvetica,Arial,sans-serif;max-width:480px;margin:0 auto;padding:28px 24px;color:#111">
<div style="font-size:13px;color:#666;letter-spacing:.06em">SinanLab · 司南实验室</div>
<h2 style="font-size:18px;margin:14px 0 6px">登录验证码 / Sign-in code</h2>
<p style="font-size:14px;line-height:1.7;color:#444">在登录页输入下面这 6 位数字，10 分钟内有效。如果不是你在登录，忽略这封邮件即可。<br>Enter this code on the sign-in page within 10 minutes. If this wasn't you, just ignore this email.</p>
<div style="font-family:ui-monospace,Menlo,monospace;font-size:34px;letter-spacing:.28em;font-weight:600;background:#07070B;color:#F5F5F7;border-radius:12px;padding:18px 20px;text-align:center;margin:18px 0">${r.code}</div>
<p style="font-size:12px;color:#888;line-height:1.6">compute.sinanlab.com · 我们不会通过邮件索要密码；本站不设密码。</p></div>`;
  const m = await sendMail(env, { to: email, subject: `司南实验室登录验证码 ${r.code}`, html, text: `司南实验室登录验证码：${r.code}（10 分钟内有效）`, tags: ["otp"] });
  if (!m.ok) return withCors(request, json({ error: "send_failed", detail: m.error }, 502));
  return withCors(request, json({ ok: true, token: r.token, masked: mask("email", email) }));
}
