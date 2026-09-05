// 一次性验证码登录（邮箱 / 手机共用）。码只存哈希在 KV，10 分钟过期，最多试 5 次；同一目标 10 分钟内最多发 3 次，同一 IP 每小时 20 次。
import { json, withCors, randHex, sha256, createSession, bump, safeReturn } from "../_lib.js";

const TTL = 600;
export function code6() { const b = new Uint32Array(1); crypto.getRandomValues(b); return String(b[0] % 1000000).padStart(6, "0"); }
export function ip(req) { return req.headers.get("CF-Connecting-IP") || "0.0.0.0"; }

export async function rateLimit(env, key, limit, ttl) {
  const k = `rl:${key}`; const n = parseInt((await env.KV.get(k)) || "0", 10) + 1;
  await env.KV.put(k, String(n), { expirationTtl: ttl });
  return n <= limit;
}

/** 生成并登记验证码；返回 {token, code}，由调用方负责把 code 发出去。 */
export async function issue(env, req, channel, target) {
  const th = await sha256(target);
  if (!(await rateLimit(env, `${channel}:${th}`, 3, TTL))) return { error: "too_many_requests" };
  if (!(await rateLimit(env, `ip:${ip(req)}`, 20, 3600))) return { error: "too_many_requests" };
  const token = randHex(16), code = code6();
  await env.KV.put(`otp:${token}`, JSON.stringify({ channel, target, hash: await sha256(code + token), tries: 0 }), { expirationTtl: TTL });
  return { token, code };
}

/** 校验验证码；成功则找到或创建用户并建会话，返回 Response。 */
export async function redeem(env, req, body) {
  const token = String(body.token || ""), code = String(body.code || "").replace(/\D/g, "");
  if (!/^[0-9a-f]{32}$/.test(token) || code.length !== 6) return withCors(req, json({ error: "bad_request" }, 400));
  const raw = await env.KV.get(`otp:${token}`); if (!raw) return withCors(req, json({ error: "expired" }, 400));
  const st = JSON.parse(raw);
  if ((await sha256(code + token)) !== st.hash) {
    st.tries += 1;
    if (st.tries >= 5) { await env.KV.delete(`otp:${token}`); return withCors(req, json({ error: "too_many_tries" }, 429)); }
    await env.KV.put(`otp:${token}`, JSON.stringify(st), { expirationTtl: TTL });
    return withCors(req, json({ error: "wrong_code", left: 5 - st.tries }, 400));
  }
  await env.KV.delete(`otp:${token}`);
  const { channel, target } = st; const th = await sha256(target);

  let ident = await env.DB.prepare("SELECT user_id FROM identities WHERE provider=? AND provider_uid=?").bind(channel, th).first();
  let userId = ident ? ident.user_id : null;
  if (!userId) {
    const open = await env.DB.prepare("SELECT value FROM flags WHERE key='SIGNUP_OPEN'").first();
    if (open && open.value === "0") return withCors(req, json({ error: "signup_closed" }, 403));
    // 同邮箱 / 同手机已有账号（比如 GitHub 带来的邮箱）→ 合并到那个账号
    const col = channel === "email" ? "email_hash" : "phone_hash";
    const u = await env.DB.prepare(`SELECT id FROM users WHERE ${col}=?`).bind(th).first();
    if (u) userId = u.id;
    if (!userId) {
      userId = crypto.randomUUID();
      const handle = channel === "email" ? target.split("@")[0].slice(0, 24) : "用户" + target.slice(-4);
      if (channel === "email") await env.DB.prepare("INSERT INTO users(id, handle, email, email_hash) VALUES (?,?,?,?)").bind(userId, handle, target, th).run();
      else await env.DB.prepare("INSERT INTO users(id, handle, phone_hash) VALUES (?,?,?)").bind(userId, handle, th).run();
      await bump(env, "signup", channel);
    } else if (channel === "phone") {
      await env.DB.prepare("UPDATE users SET phone_hash=COALESCE(phone_hash,?) WHERE id=?").bind(th, userId).run();
    }
    await env.DB.prepare("INSERT OR IGNORE INTO identities(provider, provider_uid, user_id, raw_json) VALUES (?,?,?,?)").bind(channel, th, userId, JSON.stringify({ masked: mask(channel, target) })).run();
  } else {
    await env.DB.prepare("UPDATE users SET last_seen_at=datetime('now') WHERE id=?").bind(userId).run();
  }
  const u2 = await env.DB.prepare("SELECT status FROM users WHERE id=?").bind(userId).first();
  if (!u2 || u2.status !== "active") return withCors(req, json({ error: "banned" }, 403));
  if (body.watch) {
    const [kind, key] = String(body.watch).split(":");
    if ((kind === "site" || kind === "model") && key) { await env.DB.prepare("INSERT OR IGNORE INTO watches(user_id, kind, key) VALUES (?,?,?)").bind(userId, kind, key.slice(0, 120)).run(); await bump(env, "watch", kind); }
  }
  const { cookie } = await createSession(env, req, userId);
  await bump(env, "login", channel);
  return withCors(req, json({ ok: true, return_to: safeReturn(env, body.return_to || "/me") }, 200, { "Set-Cookie": cookie }));
}

export function mask(channel, t) {
  if (channel === "email") { const [a, b] = t.split("@"); return (a.length <= 2 ? a[0] + "*" : a.slice(0, 2) + "***") + "@" + b; }
  return t.slice(0, 3) + "****" + t.slice(-4);
}
