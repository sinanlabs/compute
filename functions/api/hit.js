// POST /api/hit?r=<referrer host> —— 外部来源计数（只记来源域名与次数，不记用户）。写入 events(day,'ref',host)。
import { bump, withCors, preflight } from "./_lib.js";
export async function onRequestOptions({ request }) { return preflight(request); }
export async function onRequestPost({ request, env }) {
  const u = new URL(request.url); const r = (u.searchParams.get("r") || "").toLowerCase().slice(0, 120);
  const path = (u.searchParams.get("p") || "").slice(0, 120).replace(/[^\w\-./]/g, "");
  if (/^[a-z0-9.-]+\.[a-z]{2,}$/.test(r) && !/(^|\.)sinanlab\.com$/.test(r)) { await bump(env, "ref", r); if (path) await bump(env, "refpath", r + "|" + path); }
  // 页面浏览（只有真实浏览器会执行脚本，爬虫不计）：pv 按路径；sess = 本次会话第一页；lang = zh/en
  const t = u.searchParams.get("t") || ""; const site = u.searchParams.get("s") === "robo" ? "robo:" : "";
  if (t === "pv" && path) { await bump(env, "pv", site + path.replace(/^\/en(?=\/|$)/, "").replace(/\/s\/[^/]+/, "/s/*").replace(/\/m\/[^/]+/, "/m/*").replace(/\/rank\/[^/]+/, "/rank/*").replace(/\/report\/[^/]+/, "/report/*").replace(/\/media\/[^/]+/, "/media/*").replace(/\/models\/[^/]+/, "/models/*").replace(/\/hardware\/[^/]+/, "/hardware/*").replace(/\/embodiments\/[^/]+/, "/embodiments/*") || "/"); await bump(env, "pv_all", site + (u.searchParams.get("l") === "en" ? "en" : "zh")); }
  if (t === "sess") await bump(env, "sess", site + (u.searchParams.get("l") === "en" ? "en" : "zh"));
  return withCors(request, new Response(null, { status: 204 }));
}
