// 短信发送（阿里云 Dysms，POP RPC 签名 v1）。需要 4 个配置：SMS_ACCESS_KEY_ID / SMS_ACCESS_KEY_SECRET（Secrets），SMS_SIGN_NAME / SMS_TEMPLATE_CODE（vars）。
// 模板里必须有 ${code} 变量。四个都齐了 smsReady() 才为真，手机登录才会在页面上出现。
export function smsReady(env) { return !!(env.SMS_ACCESS_KEY_ID && env.SMS_ACCESS_KEY_SECRET && env.SMS_SIGN_NAME && env.SMS_TEMPLATE_CODE); }
const enc = (s) => encodeURIComponent(s).replace(/\+/g, "%20").replace(/\*/g, "%2A").replace(/%7E/g, "~");
async function hmacSha1B64(key, msg) {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(key), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const s = await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(s)));
}
export async function sendSms(env, phone, code) {
  if (!smsReady(env)) return { ok: false, error: "sms_not_configured" };
  const p = {
    AccessKeyId: env.SMS_ACCESS_KEY_ID, Action: "SendSms", Format: "JSON", RegionId: "cn-hangzhou", SignatureMethod: "HMAC-SHA1",
    SignatureNonce: crypto.randomUUID(), SignatureVersion: "1.0", Timestamp: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"), Version: "2017-05-25",
    PhoneNumbers: phone.replace(/^\+86/, ""), SignName: env.SMS_SIGN_NAME, TemplateCode: env.SMS_TEMPLATE_CODE, TemplateParam: JSON.stringify({ code }),
  };
  const canon = Object.keys(p).sort().map((k) => `${enc(k)}=${enc(p[k])}`).join("&");
  const sig = await hmacSha1B64(env.SMS_ACCESS_KEY_SECRET + "&", `GET&${enc("/")}&${enc(canon)}`);
  const r = await fetch(`https://dysmsapi.aliyuncs.com/?${canon}&Signature=${enc(sig)}`);
  const js = await r.json().catch(() => ({}));
  return { ok: js.Code === "OK", error: js.Code === "OK" ? null : (js.Message || js.Code || String(r.status)) };
}
