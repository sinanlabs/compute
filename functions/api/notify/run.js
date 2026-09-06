// 发送任务入口：每日流水线（本机）先用 wrangler 往 notify_jobs 写一个令牌哈希，再 POST 到这里。
// body = { token, kind: test | daily | weekly, payload }
//   daily  payload = { date, changes:[{vendor, site_name, model, model_name, old, new}], new_sites:[{domain, name}] }
//   weekly payload = { week, from, to, n_changes, up, down, n_new, best:[{name, site, out, ratio}], url }
// 收件人：登录用户里开了邮件提醒且关注命中的（daily）；订阅者（daily 档收全部变动，weekly 档收周报）。
// 每次运行最多发 MAX 封（Resend 免费档每日 100）。措辞：只陈述变动，不推荐。
import { json, sha256, bump } from "../_lib.js";
import { sendMail, layout, table, btn, esc, mailReady } from "../_mail.js";
import { unsubToken } from "../subscribe.js";
import { offToken } from "../prefs.js";

const MAX = 90;
const fmt = (v) => (v == null ? "—" : v < 1 ? v.toFixed(3) : v < 100 ? v.toFixed(2) : v.toFixed(0));
const pct = (r) => (r == null ? "—" : Math.round(r * 100) + "%");

export async function onRequestPost({ request, env }) {
  if (!mailReady(env)) return json({ error: "mail_not_ready" }, 503);
  const b = await request.json().catch(() => ({}));
  const token = String(b.token || ""); if (!/^[0-9a-f]{32,128}$/.test(token)) return json({ error: "bad_token" }, 400);
  const th = await sha256(token);
  const job = await env.DB.prepare("SELECT kind, created_at, used_at FROM notify_jobs WHERE token_hash=?").bind(th).first();
  if (!job || job.used_at || job.kind !== b.kind) return json({ error: "invalid_job" }, 403);
  if (Date.now() - new Date(job.created_at + "Z").getTime() > 3600e3) return json({ error: "expired" }, 403);
  await env.DB.prepare("UPDATE notify_jobs SET used_at=datetime('now') WHERE token_hash=?").bind(th).run();

  const site = env.SITE_ORIGIN, P = b.payload || {};
  let sent = 0, failed = 0, skipped = 0; const errors = [];
  async function send(to, msg) {
    if (sent + failed >= MAX) { skipped++; return; }
    const r = await sendMail(env, { to, ...msg }); if (r.ok) sent++; else { failed++; if (errors.length < 5) errors.push(r.error); }
  }

  if (b.kind === "test") {
    const admins = (await env.DB.prepare("SELECT email, handle FROM users WHERE role='admin' AND email IS NOT NULL").all()).results || [];
    for (const a of admins) {
      await send(a.email, { subject: "邮件通道测试 · Sinan Lab", tags: ["test"], text: "Resend 通道已接通。",
        html: layout({ title: "邮件通道已接通", intro: `你好 ${esc(a.handle || "")}，这是一封测试邮件：Resend 密钥有效，发件域 sinanlab.com 正常。`, body: btn(site + "/me", "打开我的页面"), footer: "由管理员触发的一次性测试。" }) });
    }
  }

  if (b.kind === "daily") {
    const changes = Array.isArray(P.changes) ? P.changes.slice(0, 400) : [];
    const newSites = Array.isArray(P.new_sites) ? P.new_sites : [];
    const row = (c) => [`<a href="${site}/s/${esc(c.vendor)}" style="color:#3A2AA8;text-decoration:none">${esc(c.vendor)}</a>${c.site_name ? `<div style="font-size:12px;color:#9AA0B8">${esc(c.site_name)}</div>` : ""}`,
      `<a href="${site}/m/${esc(c.model)}" style="color:#0F1222;text-decoration:none">${esc(c.model_name || c.model)}</a>`, fmt(c.old), `<b>${fmt(c.new)}</b>`, c.new > c.old ? "↑" : "↓"];
    const H = ["中转站", "模型", "旧 $/M", "新 $/M", ""];
    // 1) 登录用户：关注命中
    const users = (await env.DB.prepare("SELECT u.id, u.email, u.handle FROM users u JOIN alert_prefs p ON p.user_id=u.id WHERE p.email_on=1 AND u.email IS NOT NULL AND u.status='active'").all()).results || [];
    for (const u of users) {
      const w = (await env.DB.prepare("SELECT kind, key FROM watches WHERE user_id=?").bind(u.id).all()).results || [];
      const sites = new Set(w.filter((x) => x.kind === "site").map((x) => x.key)), models = new Set(w.filter((x) => x.kind === "model").map((x) => x.key));
      const hit = changes.filter((c) => sites.has(c.vendor) || models.has(c.model));
      const hitNew = newSites.filter((n) => sites.has(n.domain));
      if (!hit.length && !hitNew.length) continue;
      const off = `${site}/api/prefs?off=${await offToken(env, u.id)}`;
      await send(u.email, { subject: `你关注的 ${hit.length} 条价格变了 · ${P.date || ""} · Sinan Compute`, tags: ["daily"], text: hit.map((c) => `${c.vendor} ${c.model} ${fmt(c.old)} → ${fmt(c.new)}`).join("\n"),
        html: layout({ title: `你关注的对象今天有 ${hit.length} 条变动`, intro: `${P.date || ""} 抓取。实付价按人民币充值通道折成美元，单位 $/百万输出 token；每个数字在站内可看抓取快照。`,
          body: (hit.length ? table(H, hit.slice(0, 60).map(row)) : "") + btn(site + "/me", "查看我的关注"),
          footer: `<a href="${off}" style="color:#9AA0B8">关闭邮件提醒</a> · <a href="${site}/me" style="color:#9AA0B8">调整关注</a>` }) });
    }
    // 2) 每日档订阅者：全部变动
    const subs = (await env.DB.prepare("SELECT email, email_hash, lang FROM subscribers WHERE status='active' AND digest='daily'").all()).results || [];
    if (changes.length) for (const s of subs) {
      const un = `${site}/api/subscribe/unsubscribe?t=${await unsubToken(env, s.email_hash)}&l=${s.lang}`;
      await send(s.email, { subject: `今日 ${changes.length} 条中转站价格变动 · ${P.date || ""} · Sinan Compute`, tags: ["daily"], text: changes.slice(0, 60).map((c) => `${c.vendor} ${c.model} ${fmt(c.old)} → ${fmt(c.new)}`).join("\n"),
        html: layout({ title: `今日 ${changes.length} 条价格变动`, intro: `${P.date || ""} 抓取；只计连续两次抓取一致的变动。`, body: table(H, changes.slice(0, 60).map(row)) + (changes.length > 60 ? `<p style="font-size:12px;color:#9AA0B8">还有 ${changes.length - 60} 条，见站内。</p>` : "") + btn(site + "/", "打开账本"),
          footer: `<a href="${un}" style="color:#9AA0B8">退订</a>` }) });
    }
  }

  if (b.kind === "audit") {
    // 数据核查日报：只发给管理员。payload = { date, summary, unknown_fields:[{field,sites,example}], lone_outliers:[...], board_audit:[...], open_holds }
    const admins = (await env.DB.prepare("SELECT email, handle FROM users WHERE role='admin' AND email IS NOT NULL").all()).results || [];
    const uf = (P.unknown_fields || []).slice(0, 12).map((f) => [esc(f.field), String(f.sites), esc((f.example || []).join(", "))]);
    const lo = (P.lone_outliers || []).slice(0, 12).map((x) => [esc(x.site), esc(x.family), esc(x.name), "$" + x.value, "$" + x.second, "$" + x.median]);
    const ba = (P.board_audit || []).slice(0, 12).map((x) => [esc(x.site), esc(x.board + "/" + x.family), esc(x.name), "$" + x.value, "$" + x.second]);
    const body = `<p style="font-size:14px;line-height:1.7">${esc(P.summary || "")}</p>`
      + (ba.length ? `<h3 style="font-size:14px;margin:18px 0 6px">榜首差距待核</h3>` + table(["站", "榜", "型号", "榜首", "第二"], ba) : "")
      + (lo.length ? `<h3 style="font-size:14px;margin:18px 0 6px">价格孤点待核</h3>` + table(["站", "族", "型号", "该站", "第二", "族中位"], lo) : "")
      + (uf.length ? `<h3 style="font-size:14px;margin:18px 0 6px">解析器不认识的字段</h3>` + table(["字段", "站数", "例"], uf) : "")
      + `<p style="font-size:12px;color:#9AA0B8;margin-top:16px">放行：python3 core/quality_audit.py --clear ID 备注 · 未放行待核共 ${Number(P.open_holds || 0)} 条</p>`;
    for (const a of admins) {
      await send(a.email, { subject: `数据核查 ${P.date || ""} · 待核 ${Number(P.open_holds || 0)} · 新孤点 ${lo.length} · 榜首待核 ${ba.length}`, tags: ["audit"],
        text: P.summary || "", html: layout({ title: "数据核查日报", intro: `${P.date || ""} 夜间流水线核查结果。`, body, footer: "只发管理员，不对外。" }) });
    }
  }

  if (b.kind === "post") {
    // linux.do 发帖稿：payload = { date, posts:[{kind, title, text}] }，只发管理员，正文原样放 <pre> 里方便复制
    const admins = (await env.DB.prepare("SELECT email, handle FROM users WHERE role='admin' AND email IS NOT NULL").all()).results || [];
    const posts = Array.isArray(P.posts) ? P.posts.slice(0, 6) : [];
    const body = posts.map((p) => `<h3 style="font-size:14px;margin:18px 0 6px">${esc(p.kind)} · ${esc(p.title)}</h3><pre style="white-space:pre-wrap;font:13px/1.6 ui-monospace,Menlo,monospace;background:#F5F5F7;border-radius:10px;padding:14px">${esc(p.text)}</pre>`).join("");
    for (const a of admins) {
      await send(a.email, { subject: `今日发帖稿 ${P.date || ""} · ${posts.length} 篇（${posts.map((p) => p.kind).join(" / ")}）`, tags: ["post"],
        text: posts.map((p) => p.text).join("\n\n==========\n\n"), html: layout({ title: "今日发帖稿（复制即可）", intro: "由当天数据自动生成，已过措辞自检。复制【标题】与【正文】到 linux.do 对应分类即可。", body, footer: "只发管理员，不对外。" }) });
    }
  }

  if (b.kind === "weekly") {
    const url = P.url || `${site}/weekly/${P.week || ""}`;
    const best = Array.isArray(P.best) ? P.best.slice(0, 10) : [];
    const bodyZh = `<p style="font-size:14px;line-height:1.8;margin:0 0 10px">${esc(P.from || "")} 到 ${esc(P.to || "")}：<b>${P.n_changes || 0}</b> 条价格变动（涨 ${P.up || 0} · 降 ${P.down || 0}），新收录 <b>${P.n_new || 0}</b> 站。</p>` +
      (best.length ? `<div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#9AA0B8;margin-top:12px">本周各模型说得通的最低实付</div>` + table(["模型", "站", "$/M 输出", "几成"], best.map((x) => [esc(x.name), `<a href="${site}/s/${esc(x.site)}" style="color:#3A2AA8;text-decoration:none">${esc(x.site)}</a>`, fmt(x.out), pct(x.ratio)])) : "") + btn(url, "看完整周报");
    const bodyEn = `<p style="font-size:14px;line-height:1.8;margin:0 0 10px">${esc(P.from || "")} to ${esc(P.to || "")}: <b>${P.n_changes || 0}</b> price changes (${P.up || 0} up · ${P.down || 0} down), <b>${P.n_new || 0}</b> newly indexed sites.</p>` +
      (best.length ? `<div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#9AA0B8;margin-top:12px">Lowest in-range effective price per model this week</div>` + table(["Model", "Site", "$/M out", "Ratio"], best.map((x) => [esc(x.name), `<a href="${site}/en/s/${esc(x.site)}" style="color:#3A2AA8;text-decoration:none">${esc(x.site)}</a>`, fmt(x.out), pct(x.ratio)])) : "") + btn(url.replace(site + "/", site + "/en/"), "Full weekly report");
    const subs = (await env.DB.prepare("SELECT email, email_hash, lang FROM subscribers WHERE status='active'").all()).results || [];
    for (const s of subs) {
      const en = s.lang === "en"; const un = `${site}/api/subscribe/unsubscribe?t=${await unsubToken(env, s.email_hash)}&l=${s.lang}`;
      await send(s.email, { subject: en ? `Relay price weekly ${P.week || ""} · Sinan Compute` : `中转站价格周报 ${P.week || ""} · Sinan Compute`, tags: ["weekly"], text: url,
        html: layout({ lang: s.lang, title: en ? `Weekly ${P.week || ""}` : `价格周报 ${P.week || ""}`, intro: en ? "Auto-generated from daily fetches; measurements only." : "由每日抓取自动生成；只陈述测量，不含推荐。", body: en ? bodyEn : bodyZh,
          footer: `<a href="${un}" style="color:#9AA0B8">${en ? "Unsubscribe" : "退订"}</a>` }) });
    }
    const users = (await env.DB.prepare("SELECT u.id, u.email FROM users u JOIN alert_prefs p ON p.user_id=u.id WHERE p.email_on=1 AND u.email IS NOT NULL AND u.status='active'").all()).results || [];
    const subHashes = new Set(subs.map((s) => s.email_hash));
    for (const u of users) {
      if (subHashes.has(await sha256(u.email.toLowerCase()))) continue;   // 既订阅又登录的只发一封
      const off = `${site}/api/prefs?off=${await offToken(env, u.id)}`;
      await send(u.email, { subject: `中转站价格周报 ${P.week || ""} · Sinan Compute`, tags: ["weekly"], text: url,
        html: layout({ title: `价格周报 ${P.week || ""}`, intro: "由每日抓取自动生成；只陈述测量，不含推荐。", body: bodyZh, footer: `<a href="${off}" style="color:#9AA0B8">关闭邮件提醒</a>` }) });
    }
  }

  const result = { kind: b.kind, sent, failed, skipped, errors };
  await env.DB.prepare("UPDATE notify_jobs SET result_json=? WHERE token_hash=?").bind(JSON.stringify(result), th).run();
  await bump(env, "mail", b.kind);
  return json(result);
}
