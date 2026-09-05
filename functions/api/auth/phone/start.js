// POST /api/auth/phone/start {phone} → 发短信验证码（阿里云）。短信通道未配置时返回 503，页面会显示"即将开放"。
import { json, withCors, preflight } from "../../_lib.js";
import { sendSms, smsReady } from "../../_sms.js";
import { issue, mask } from "../_otp.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) {
  if (!smsReady(env) || !env.SESSION_SECRET) return withCors(request, json({ error: "phone_login_unavailable" }, 503));
  const b = await request.json().catch(() => ({}));
  let phone = String(b.phone || "").replace(/[\s-]/g, "");
  if (/^1[3-9]\d{9}$/.test(phone)) phone = "+86" + phone;
  if (!/^\+861[3-9]\d{9}$/.test(phone)) return withCors(request, json({ error: "bad_phone" }, 400));   // 首期只开中国大陆手机号
  const r = await issue(env, request, "phone", phone);
  if (r.error) return withCors(request, json({ error: r.error }, 429));
  const m = await sendSms(env, phone, r.code);
  if (!m.ok) return withCors(request, json({ error: "send_failed", detail: m.error }, 502));
  return withCors(request, json({ ok: true, token: r.token, masked: mask("phone", phone) }));
}
