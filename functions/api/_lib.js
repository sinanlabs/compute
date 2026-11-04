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

// ---- OAuth state：签名后放在 state 参数里，不再写 KV ----
// 2026-11-04：KV 免费额度每天 1,000 次写入被访问计数用光，登录写不进 state 就 1101，后台进不去。
// state = base64url(JSON{r 回跳, w 关注, p 来源, n 随机数, e 过期秒}) + "." + hmac；同时下发 oas=<n> cookie，回调时比对，绑定发起登录的浏览器。
const b64u = (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64u = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
export async function makeState(env, payload, ttl = 600) {
  const n = randHex(12);
  const body = b64u(enc.encode(JSON.stringify({ ...payload, n, e: Math.floor(Date.now() / 1000) + ttl })));
  return { state: body + "." + (await hmac(env.SESSION_SECRET, "oauth-state|" + body)), cookie: `oas=${n}; Path=/api/auth; HttpOnly; Secure; SameSite=Lax; Max-Age=${ttl}` };
}
/** 校验 state：签名对、没过期、和本浏览器的 oas cookie 一致。返回 payload 或 null。 */
export async function readState(env, req, state) {
  const [body, sig] = String(state || "").split(".");
  if (!body || !sig || (await hmac(env.SESSION_SECRET, "oauth-state|" + body)) !== sig) return null;
  let st; try { st = JSON.parse(new TextDecoder().decode(unb64u(body))); } catch (e) { return null; }
  if (!st || !st.e || st.e < Math.floor(Date.now() / 1000)) return null;
  if (parseCookies(req).oas !== st.n) return null;
  return { return_to: st.return_to, watch: st.watch || "", provider: st.provider };
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
  let row;
  try {
    row = await env.DB.prepare(
      `SELECT s.id AS sid, s.expires_at, s.revoked, u.id, u.handle, u.avatar_url, u.role, u.status, u.email
       FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ?`).bind(sid).first();
  } catch (e) { return null; } // 数据库暂不可用（如免费额度用尽）时按未登录处理，页面照常渲染
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
