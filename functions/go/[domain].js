// /go/<域名> —— 出站跳转。默认直达站方链接；只有后台开关 REFERRAL_ENABLED=1 且该站在 site_overrides 里填了推广链接时才带推广参数。
// 只计点击数（events 表按天按站累加），不存 IP、不传 Referer。
export async function onRequestGet({ params, env, request }) {
  const domain = String(params.domain || "").toLowerCase().replace(/\/+$/, "");
  if (!/^[a-z0-9.\-]+$/.test(domain)) return new Response("bad domain", { status: 400 });
  let rec = null;
  try {
    const res = await env.ASSETS.fetch(new URL("/go_links.json", request.url));
    const all = await res.json();
    rec = Array.isArray(all) ? all.find((x) => x.domain === domain) : all[domain];
  } catch (e) {}
  if (!rec) return new Response("not found", { status: 404 });
  let target = rec.url;
  if (env.DB) {
    try {
      const f = await env.DB.prepare("SELECT value FROM flags WHERE key='REFERRAL_ENABLED'").first();
      if (f && f.value === "1") {
        const o = await env.DB.prepare("SELECT referral_url, hidden FROM site_overrides WHERE domain=?").bind(domain).first();
        if (o && o.referral_url) target = o.referral_url;
      }
      const day = new Date().toISOString().slice(0, 10);
      await env.DB.prepare("INSERT INTO events(day,name,key,n) VALUES(?,?,?,1) ON CONFLICT(day,name,key) DO UPDATE SET n=n+1").bind(day, "go", domain).run();
    } catch (e) {}
  } else if (env.REFERRAL_ENABLED === "1" && rec.referral_url) target = rec.referral_url;
  return new Response(null, { status: 302, headers: { Location: target, "Referrer-Policy": "no-referrer", "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow" } });
}
