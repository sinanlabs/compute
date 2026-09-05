// 用户系统公共库：会话、CORS、签名、JSON 响应。
export const ORIGINS = new Set([
  "https://compute.sinanlab.com", "https://robo.sinanlab.com", "https://sinanlab.com", "https://admin.sinanlab.com",
  "http://localhost:8792", "http://localhost:4322", "http://localhost:8791", "http://localhost:8793",
]);
const enc = new TextEncoder();

export function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...extra } });
}
export function withCors(req, res) {
  const o = req.headers.get("Origin");
  if (o && ORIGINS.has(o)) {
    res.headers.set("Access-Control-Allow-Origin", o);
    res.headers.set("Access-Control-Allow-Credentials", "true");
    res.headers.set("Vary", "Origin");
    res.headers.set("Access-Control-Allow-Headers", "Content-Type");
    res.headers.set("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS");
  }
  return res;
}
export function preflight(req) { return withCors(req, new Response(null, { status: 204 })); }

export function randHex(n = 32) { const b = new Uint8Array(n); crypto.getRandomValues(b); return [...b].map((x) => x.toString(16).padStart(2, "0")).join(""); }
export async function sha256(s) { const d = await crypto.subtle.digest("SHA-256", enc.encode(s)); return [...new Uint8Array(d)].map((x) => x.toString(16).padStart(2, "0")).join(""); }
export async function hmac(secret, msg) {
  const k = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const s = await crypto.subtle.sign("HMAC", k, enc.encode(msg));
  return [...new Uint8Array(s)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

export function parseCookies(req) {
  const out = {}; const c = req.headers.get("Cookie") || "";
  c.split(";").forEach((p) => { const i = p.indexOf("="); if (i > 0) out[p.slice(0, i).trim()] = decodeURIComponent(p.slice(i + 1).trim()); });
  return out;
}
export function cookieHeader(env, req, value, maxAge) {
  const host = new URL(req.url).hostname;
  const local = host === "localhost" || host === "127.0.0.1";
  const parts = [`sinan_sid=${value}`, "Path=/", "HttpOnly", "SameSite=Lax", `Max-Age=${maxAge}`];
  if (!local) { parts.push("Secure"); if (env.COOKIE_DOMAIN) parts.push(`Domain=${env.COOKIE_DOMAIN}`); }
  return parts.join("; ");
}

/** 从 cookie 取会话：格式 <sid>.<hmac(sid)>；查 D1，校验过期与吊销。 */
export async function getSession(env, req) {
  if (!env.DB || !env.SESSION_SECRET) return null;
  const raw = parseCookies(req).sinan_sid; if (!raw) return null;
  const [sid, sig] = raw.split("."); if (!sid || !sig) return null;
  if ((await hmac(env.SESSION_SECRET, sid)) !== sig) return null;
  const row = await env.DB.prepare(
    `SELECT s.id AS sid, s.expires_at, s.revoked, u.id, u.handle, u.avatar_url, u.role, u.status, u.email
     FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ?`).bind(sid).first();
  if (!row || row.revoked || row.status !== "active" || new Date(row.expires_at + "Z") < new Date()) return null;
  return { sid, user: { id: row.id, handle: row.handle, avatar_url: row.avatar_url, role: row.role, has_email: !!row.email } };
}

export async function createSession(env, req, userId) {
  const sid = randHex(32); const sig = await hmac(env.SESSION_SECRET, sid);
  const days = 30; const exp = new Date(Date.now() + days * 864e5).toISOString().slice(0, 19).replace("T", " ");
  const ua = await sha256(req.headers.get("User-Agent") || "");
  await env.DB.prepare("INSERT INTO sessions(id, user_id, expires_at, ua_hash) VALUES (?,?,?,?)").bind(sid, userId, exp, ua).run();
  return { cookie: cookieHeader(env, req, `${sid}.${sig}`, days * 86400) };
}

export async function bump(env, name, key = "") {
  try {
    const day = new Date().toISOString().slice(0, 10);
    await env.DB.prepare("INSERT INTO events(day,name,key,n) VALUES(?,?,?,1) ON CONFLICT(day,name,key) DO UPDATE SET n=n+1").bind(day, name, key).run();
  } catch (e) { /* 计数失败不影响主流程 */ }
}

export function safeReturn(env, to) {
  try { const u = new URL(to, env.SITE_ORIGIN); if (ORIGINS.has(u.origin)) return u.toString(); } catch (e) {}
  return env.SITE_ORIGIN + "/me";
}
