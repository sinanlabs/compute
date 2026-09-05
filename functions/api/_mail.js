// 邮件发送（Resend）。密钥只在 Pages Secrets：RESEND_API_KEY。发件域 sinanlab.com 已在 Resend 验证。
// 措辞约束：邮件只陈述测量与变动，不含推荐；每封都带一键退订 / 关闭提醒链接。
const FROM = "Sinan Lab <notify@sinanlab.com>";
const REPLY = "hello@sinanlab.com";

export function mailReady(env) { return !!env.RESEND_API_KEY; }

export async function sendMail(env, { to, subject, html, text, tags = [] }) {
  if (!env.RESEND_API_KEY) return { ok: false, error: "no_api_key" };
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: FROM, to: to, reply_to: REPLY, subject, html, text, tags: tags.map((t) => ({ name: "kind", value: t })) }),
  });
  const js = await r.json().catch(() => ({}));
  return { ok: r.ok, id: js.id, error: r.ok ? null : (js.message || js.name || String(r.status)) };
}

export function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

/** 统一外壳：品牌头 + 正文 + 页脚（退订链接）。纯内联样式，邮件客户端兼容。 */
export function layout({ title, intro, body, footer, lang = "zh" }) {
  const t = lang === "en"
    ? { brand: "Sinan Lab · Neutral measurement for AI infrastructure", disc: "Measurements only, no recommendations. Every number on the site links to its fetch snapshot." }
    : { brand: "司南实验室 · AI 基础设施的中立测量者", disc: "只陈述测量，不含推荐。站内每个数字都能点开抓取快照。" };
  return `<!doctype html><html><body style="margin:0;background:#F2F3F9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;color:#0F1222">
<div style="max-width:600px;margin:0 auto;padding:28px 16px">
  <div style="font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#6E56F5;margin-bottom:10px">${esc(t.brand)}</div>
  <div style="background:#fff;border:1px solid #E6E6EF;border-radius:16px;padding:22px 24px">
    <h1 style="font-size:20px;line-height:1.3;margin:0 0 8px">${title}</h1>
    ${intro ? `<p style="font-size:14px;line-height:1.7;color:#5A6079;margin:0 0 14px">${intro}</p>` : ""}
    ${body}
  </div>
  <p style="font-size:12px;line-height:1.7;color:#9AA0B8;margin:14px 4px 0">${esc(t.disc)}<br>${footer || ""}</p>
</div></body></html>`;
}

export function table(headers, rows) {
  const th = headers.map((h) => `<th style="text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#9AA0B8;padding:8px 8px;border-bottom:1px solid #E6E6EF;font-weight:500">${esc(h)}</th>`).join("");
  const tr = rows.map((r) => `<tr>${r.map((c) => `<td style="font-size:13.5px;padding:9px 8px;border-bottom:1px solid #F0F0F5;vertical-align:top">${c}</td>`).join("")}</tr>`).join("");
  return `<table style="width:100%;border-collapse:collapse;margin-top:6px"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
}

export function btn(href, label) {
  return `<a href="${esc(href)}" style="display:inline-block;background:#6E56F5;color:#fff;text-decoration:none;font-size:14px;font-weight:600;padding:10px 18px;border-radius:999px;margin-top:8px">${esc(label)}</a>`;
}
