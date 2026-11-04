// POST /api/hit?r=<referrer host> —— 外部来源计数（只记来源域名与次数，不记用户）。写入 events(day,'ref',host)。
import { bump, withCors, preflight, sha256, json } from "./_lib.js";
export async function onRequestOptions({ request }) { return preflight(request); }
// 限频放在实例内存里，不写 KV：2026-10-14 起每次访问都往 KV 写一次计数，访问量上来后每天 1,000 次免费写入
// 很快用光，登录（要写 KV）跟着报 1101，后台进不去（2026-11-04）。内存计数按实例算，挡单一来源刷量足够。
const SEEN = new Map(); let DAY = "";
function allow(src, limit) {
  const d = new Date().toISOString().slice(0, 10);
  if (d !== DAY) { SEEN.clear(); DAY = d; }
  const n = (SEEN.get(src) || 0) + 1; SEEN.set(src, n);
  if (SEEN.size > 50000) SEEN.clear();   // 防内存涨爆
  return n <= limit;
}
export async function onRequestPost({ request, env }) {
  // 限频：同一来源每天最多 600 次计数。计数只用于站内统计，被刷会污染数据并烧掉数据库额度。
  const src = (await sha256((request.headers.get("CF-Connecting-IP") || "") + "|" + (request.headers.get("User-Agent") || ""))).slice(0, 24);
  if (!allow(src, 600)) return withCors(request, json({ ok: false, error: "too_many" }, 429));
  const u = new URL(request.url); let r = (u.searchParams.get("r") || "").toLowerCase().slice(0, 120);
  // 没有 referrer 时前端会退而上报 utm_source（AI 产品常只带 utm_source=chatgpt.com / perplexity）。不带域名后缀的常见来源名映射成域名（2026-10-14）
  const UTM = { chatgpt: "chatgpt.com", openai: "chatgpt.com", perplexity: "perplexity.ai", copilot: "copilot.microsoft.com", bing: "www.bing.com", claude: "claude.ai", gemini: "gemini.google.com", kimi: "kimi.com", deepseek: "chat.deepseek.com", doubao: "doubao.com", yuanbao: "yuanbao.tencent.com", metaso: "metaso.cn", phind: "phind.com", you: "you.com", poe: "poe.com", grok: "grok.com" };
  if (UTM[r]) r = UTM[r];
  const path = (u.searchParams.get("p") || "").slice(0, 120).replace(/[^\w\-./]/g, "");
  if (/^[a-z0-9.-]+\.[a-z]{2,}$/.test(r) && !/(^|\.)sinanlab\.com$/.test(r)) { await bump(env, "ref", r); if (path) await bump(env, "refpath", r + "|" + path); }
  // 页面浏览（只有真实浏览器会执行脚本，爬虫不计）：pv 按路径；sess = 本次会话第一页；lang = zh/en
  const t = u.searchParams.get("t") || ""; const site = u.searchParams.get("s") === "robo" ? "robo:" : "";
  if (t === "pv" && path) { await bump(env, "pv", site + path.replace(/^\/en(?=\/|$)/, "").replace(/\/s\/[^/]+/, "/s/*").replace(/\/m\/[^/]+/, "/m/*").replace(/\/rank\/[^/]+/, "/rank/*").replace(/\/report\/[^/]+/, "/report/*").replace(/\/media\/[^/]+/, "/media/*").replace(/\/models\/[^/]+/, "/models/*").replace(/\/hardware\/[^/]+/, "/hardware/*").replace(/\/embodiments\/[^/]+/, "/embodiments/*") || "/"); await bump(env, "pv_all", site + (u.searchParams.get("l") === "en" ? "en" : "zh")); }
  if (t === "pv" && path && /^\/(en\/)?(s|m|rank|report|media|models|hardware|embodiments)\/[^/]+/.test(path)) await bump(env, "pv_detail", site + path.replace(/^\/en(?=\/)/, ""));
  if (t === "sess") await bump(env, "sess", site + (u.searchParams.get("l") === "en" ? "en" : "zh"));
  // 榜单关注度：某张榜在视口里停留 ≥1.5 秒记一次曝光；榜内点击记一次点击。k = 页面:榜名
  const k = (u.searchParams.get("k") || "").slice(0, 80).replace(/[<>"]/g, "");
  if (t === "board" && k) await bump(env, "board_view", k);
  if (t === "boardclick" && k) await bump(env, "board_click", k);
  return withCors(request, new Response(null, { status: 204 }));
}
