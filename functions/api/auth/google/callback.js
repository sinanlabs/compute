import { sha256, createSession, bump, safeReturn } from "../../_lib.js";
const txt = (s, status) => new Response(s, { status, headers: { "Content-Type": "text/plain; charset=utf-8" } });
export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code"), state = url.searchParams.get("state");
  if (!code || !state) return txt("缺少参数", 400);
  const raw = await env.KV.get(`oauth:state:${state}`); if (!raw) return txt("登录已过期，请重试。", 400);
  await env.KV.delete(`oauth:state:${state}`);
  const st = JSON.parse(raw);
  const tok = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ code, client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET, redirect_uri: `${env.SITE_ORIGIN}/api/auth/google/callback`, grant_type: "authorization_code" }),
  }).then((r) => r.json()).catch(() => ({}));
  if (!tok.access_token) return txt("Google 没有返回令牌，请重试。", 502);
  const me = await fetch("https://openidconnect.googleapis.com/v1/userinfo", { headers: { Authorization: `Bearer ${tok.access_token}` } }).then((r) => r.json()).catch(() => ({}));
  if (!me.sub) return txt("读取 Google 用户失败。", 502);
  const email = me.email_verified && me.email ? String(me.email).toLowerCase() : null;
  const emailHash = email ? await sha256(email) : null;
  const uid = String(me.sub);
  let ident = await env.DB.prepare("SELECT user_id FROM identities WHERE provider='google' AND provider_uid=?").bind(uid).first();
  let userId = ident ? ident.user_id : null;
  if (!userId) {
    const open = await env.DB.prepare("SELECT value FROM flags WHERE key='SIGNUP_OPEN'").first();
    if (open && open.value === "0") return txt("暂未开放新用户注册。", 403);
    if (emailHash) { const u = await env.DB.prepare("SELECT id FROM users WHERE email_hash=?").bind(emailHash).first(); if (u) userId = u.id; }   // 同邮箱账号合并
    if (!userId) {
      userId = crypto.randomUUID();
      const handle = (me.name || (email ? email.split("@")[0] : "user")).slice(0, 24);
      await env.DB.prepare("INSERT INTO users(id, handle, email, email_hash, avatar_url) VALUES (?,?,?,?,?)").bind(userId, handle, email, emailHash, me.picture || null).run();
      await bump(env, "signup", "google");
    }
    await env.DB.prepare("INSERT OR IGNORE INTO identities(provider, provider_uid, user_id, raw_json) VALUES ('google', ?, ?, ?)").bind(uid, userId, JSON.stringify({ sub: uid })).run();
  } else {
    await env.DB.prepare("UPDATE users SET avatar_url=COALESCE(avatar_url,?), last_seen_at=datetime('now') WHERE id=?").bind(me.picture || null, userId).run();
  }
  const u2 = await env.DB.prepare("SELECT status FROM users WHERE id=?").bind(userId).first();
  if (!u2 || u2.status !== "active") return txt("该账号不可用。", 403);
  if (st.watch) {
    const [kind, key] = String(st.watch).split(":");
    if ((kind === "site" || kind === "model") && key) { await env.DB.prepare("INSERT OR IGNORE INTO watches(user_id, kind, key) VALUES (?,?,?)").bind(userId, kind, key.slice(0, 120)).run(); await bump(env, "watch", kind); }
  }
  const { cookie } = await createSession(env, request, userId);
  await bump(env, "login", "google");
  return new Response(null, { status: 302, headers: { Location: safeReturn(env, st.return_to), "Set-Cookie": cookie } });
}
