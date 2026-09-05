/**
 * /go/<domain> 出站跳转 —— Cloudflare Worker（方案里的主站技术栈）。
 *
 * 做三件事：
 *   1. 查 go_links.json：domain -> { url, referral_url, label }
 *   2. 302 跳到目标。有 referral_url 且已启用推广时跳它，否则跳原站
 *   3. KV 计数 outbound:<domain>，每日汇总回 relay_candidate.outbound_clicks（公开事实）
 *
 * 宪法约束（写死，不可配置）：
 *   - 检测报告页 / 质量测量页不得放本入口（宪法第 4 条），只在站点事实页与比价表的「前往」列
 *   - 带 referral 的入口必须渲染为「广告」标识 + rel="sponsored nofollow"（宪法第 2 条）
 *   - 排序 / 判读永不读 referral 字段（宪法第 1 条）
 *   - 点击数按站公开；推广收入占比按季公开（宪法第 5 条）
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const m = url.pathname.match(/^\/go\/([a-z0-9.-]+)\/?$/i);
    if (!m) return new Response("not found", { status: 404 });
    const domain = m[1].toLowerCase();

    const links = await env.LINKS.get("go_links", { type: "json" }); // 由 export_go_links.py 生成后写入 KV
    const rec = links && links[domain];
    if (!rec) return new Response("unknown site", { status: 404 });

    const referralOn = env.REFERRAL_ENABLED === "1" && rec.referral_url;
    const target = referralOn ? rec.referral_url : rec.url;

    // 计数（不存任何用户信息：不存 IP、不存 UA、不存 Referer）
    const key = "outbound:" + domain;
    const cur = parseInt((await env.COUNTS.get(key)) || "0", 10);
    await env.COUNTS.put(key, String(cur + 1));

    return new Response(null, {
      status: 302,
      headers: {
        Location: target,
        "Referrer-Policy": "no-referrer",          // 不把我们的页面地址泄给站方
        "Cache-Control": "no-store",
        "X-Robots-Tag": "noindex, nofollow",
      },
    });
  },
};
