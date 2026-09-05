import { sha256, createSession, bump, safeReturn } from "../../_lib.js";

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code"), state = url.searchParams.get("state");
  if (!code || !state) return new Response("缺少参数", { status: 400 });
  const raw = await env.KV.get(`oauth:state:${state}`); if (!raw) return new Response("登录已过期，请重试。", { status: 400, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  await env.KV.delete(`oauth:state:${state}`);
  const st = JSON.parse(raw);

  const tok = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST", headers: { "Accept": "application/json", "Content-Type": "application/json", "User-Agent": "sinanlab" },
    body: JSON.stringify({ client_id: env.GITHUB_CLIENT_ID, client_secret: env.GITHUB_CLIENT_SECRET, code, redirect_uri: `${env.SITE_ORIGIN}/api/auth/github/callback` }),
  }).then((r) => r.json());
  if (!tok.access_token) return new Response("GitHub 没有返回令牌，请重试。", { status: 502, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  const gh = { Authorization: `Bearer ${tok.access_token}`, "User-Agent": "sinanlab", Accept: "application/vnd.github+json" };
  const me = await fetch("https://api.github.com/user", { headers: gh }).then((r) => r.json());
  if (!me.id) return new Response("读取 GitHub 用户失败。", { status: 502 });
  let email = me.email || null;
  if (!email) {
    const emails = await fetch("https://api.github.com/user/emails", { headers: gh }).then((r) => r.json()).catch(() => []);
    const p = Array.isArray(emails) ? emails.find((e) => e.primary && e.verified) || emails.find((e) => e.verified) : null;
    email = p ? p.email : null;
  }
  const emailHash = email ? await sha256(email.toLowerCase()) : null;

  // 身份 → 用户
  const uid = String(me.id);
  let ident = await env.DB.prepare("SELECT user_id FROM identities WHERE provider='github' AND provider_uid=?").bind(uid).first();
  let userId = ident ? ident.user_id : null;
  if (!userId) {
    const open = await env.DB.prepare("SELECT value FROM flags WHERE key='SIGNUP_OPEN'").first();
    if (open && open.value === "0") return new Response("暂未开放新用户注册。", { status: 403, headers: { "Content-Type": "text/plain; charset=utf-8" } });
    // 同邮箱已有账号则合并
    if (emailHash) { const u = await env.DB.prepare("SELECT id FROM users WHERE email_hash=?").bind(emailHash).first(); if (u) userId = u.id; }
    if (!userId) {
      userId = crypto.randomUUID();
      await env.DB.prepare("INSERT INTO users(id, handle, email, email_hash, avatar_url) VALUES (?,?,?,?,?)").bind(userId, me.login, email, emailHash, me.avatar_url || null).run();
      await bump(env, "signup");
    }
    await env.DB.prepare("INSERT INTO identities(provider, provider_uid, user_id, raw_json) VALUES ('github', ?, ?, ?)").bind(uid, userId, JSON.stringify({ login: me.login, id: me.id })).run();
  } else {
    await env.DB.prepare("UPDATE users SET handle=COALESCE(handle,?), avatar_url=?, last_seen_at=datetime('now') WHERE id=?").bind(me.login, me.avatar_url || null, userId).run();
  }
  const banned = await env.DB.prepare("SELECT status FROM users WHERE id=?").bind(userId).first();
  if (banned && banned.status !== "active") return new Response("该账号不可用。", { status: 403 });

  // 登录前用户点的“关注”：登录后自动完成
  if (st.watch) {
    const [kind, key] = String(st.watch).split(":");
    if ((kind === "site" || kind === "model") && key) {
      await env.DB.prepare("INSERT OR IGNORE INTO watches(user_id, kind, key) VALUES (?,?,?)").bind(userId, kind, key.slice(0, 120)).run();
      await bump(env, "watch", kind);
    }
  }
  const { cookie } = await createSession(env, request, userId);
  await bump(env, "login", "github");
  return new Response(null, { status: 302, headers: { Location: safeReturn(env, st.return_to), "Set-Cookie": cookie } });
}
