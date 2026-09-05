# -*- coding: utf-8 -*-
"""渲染主页 index.html。数据全部来自 home_data.json（库导出），页面不含任何手写数字。

信息层级（主次分明）：
  一、按模型比价 —— 用户的主问题「我要用 X，哪买最便宜且不是假的」。官方/公开市场/中转同表，实付口径，带判读
  二、站点 —— 「我在用的站靠谱吗」。查询 + 已确认站点卡
  三、今天变了什么 —— 回访理由
  四、方法论一句话 + 中立性
"""
from __future__ import unicode_literals
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "home_data.json")))

TEMPLATE = u"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>算力罗盘</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#EDF0F2; --surface:#FFFFFF; --surface-2:#F5F8F9;
  --line:#D5DDE1; --line-soft:#E6ECEF;
  --ink:#0E171C; --ink-2:#44555F; --ink-3:#76888F;
  --accent:#0E6A74; --accent-2:#0B565E; --accent-soft:#DFEFF0;
  --good:#1B7A4C; --good-soft:#E0F0E7; --warn:#8E6410; --warn-soft:#F6EDD9;
  --crit:#A93A2E; --crit-soft:#F7E5E2; --shadow:0 1px 2px rgba(14,23,28,.05),0 10px 28px -18px rgba(14,23,28,.3);
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --ground:#0A0F12; --surface:#111A1E; --surface-2:#162126; --line:#243238; --line-soft:#1B272C;
  --ink:#E4EDEF; --ink-2:#9FB1B8; --ink-3:#6C7F87; --accent:#4CC5CF; --accent-2:#7FD9E0; --accent-soft:#0F3439;
  --good:#4EBE86; --good-soft:#10301F; --warn:#D7A63F; --warn-soft:#332812; --crit:#E0705F; --crit-soft:#361A17;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -18px rgba(0,0,0,.8);}}
:root[data-theme="dark"]{
  --ground:#0A0F12; --surface:#111A1E; --surface-2:#162126; --line:#243238; --line-soft:#1B272C;
  --ink:#E4EDEF; --ink-2:#9FB1B8; --ink-3:#6C7F87; --accent:#4CC5CF; --accent-2:#7FD9E0; --accent-soft:#0F3439;
  --good:#4EBE86; --good-soft:#10301F; --warn:#D7A63F; --warn-soft:#332812; --crit:#E0705F; --crit-soft:#361A17;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -18px rgba(0,0,0,.8);}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:"IBM Plex Sans","PingFang SC","Noto Sans SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
h1,h2,h3{font-family:"Noto Serif SC","Songti SC",Georgia,serif;margin:0;font-weight:700;text-wrap:balance}
.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
a{color:var(--accent);text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}

.top{background:var(--surface);border-bottom:1px solid var(--line)}
.wrap{max-width:1120px;margin:0 auto;padding:0 28px}
.bar{display:flex;align-items:center;gap:16px;padding:14px 0}
.brand{display:flex;align-items:center;gap:10px}
.brand h1{font-size:18px}
.brand .sub{font-size:11px;color:var(--ink-3);letter-spacing:.14em;text-transform:uppercase;font-family:"IBM Plex Mono",monospace}
.search{margin-left:auto;display:flex;gap:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--surface-2);min-width:340px}
.search input{flex:1;border:0;background:transparent;padding:9px 12px;font:inherit;font-size:14px;color:var(--ink)}
.search button{border:0;background:var(--accent);color:#fff;font:inherit;font-size:13px;font-weight:600;padding:0 14px;cursor:pointer}
.pledge{font-size:12.5px;color:var(--ink-3);padding:0 0 12px;display:flex;gap:18px;flex-wrap:wrap}
.pledge b{color:var(--ink-2);font-weight:500}

main{padding:30px 0 80px}
.sec{margin-bottom:44px}
.sechead{display:flex;align-items:baseline;gap:14px;margin-bottom:14px;flex-wrap:wrap}
.sechead h2{font-size:22px}
.sechead .q{font-size:13.5px;color:var(--ink-3)}
.sechead .right{margin-left:auto;font-size:12px;color:var(--ink-3);font-family:"IBM Plex Mono",monospace}

.chips{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}
.chip{border:1px solid var(--line);background:var(--surface);color:var(--ink-2);font:inherit;font-size:13px;padding:6px 12px;border-radius:999px;cursor:pointer}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.chip.off{opacity:.5;cursor:default;border-style:dashed}
.chip .n{font-family:"IBM Plex Mono",monospace;font-size:11px;opacity:.75;margin-left:5px}

.card{background:var(--surface);border:1px solid var(--line);border-radius:10px}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:11px 14px;text-align:left;border-bottom:1px solid var(--line-soft);vertical-align:middle}
th{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-family:"IBM Plex Mono",monospace;font-weight:500;background:var(--surface-2);white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--surface-2)}
td.num{font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}
th.num{text-align:right}
tr.floor td{background:var(--accent-soft)}
tr.floor td:first-child{border-left:3px solid var(--accent)}
.kind{font-size:11px;font-family:"IBM Plex Mono",monospace;color:var(--ink-3);letter-spacing:.06em}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;padding:2px 9px;border-radius:999px;font-family:"IBM Plex Mono",monospace;white-space:nowrap}
.dot{width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block}
.pill.unsustainable{background:var(--crit-soft);color:var(--crit)}
.pill.below_bulk{background:var(--warn-soft);color:var(--warn)}
.pill.explainable{background:var(--good-soft);color:var(--good)}
.pill.normal{background:var(--surface-2);color:var(--ink-2);border:1px solid var(--line)}
.pill.premium,.pill.far_above{background:var(--surface-2);color:var(--ink-3);border:1px solid var(--line)}
.pill.ref{background:var(--accent-soft);color:var(--accent)}
.ev{display:inline-flex;align-items:center;justify-content:center;cursor:pointer;width:16px;height:16px;border-radius:3px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink-3);font-family:"IBM Plex Mono",monospace;font-size:9px;padding:0}
.ev:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
.bigout{font-weight:600;font-size:15px}
.ratio{font-weight:600}
.ratio.unsustainable{color:var(--crit)} .ratio.below_bulk{color:var(--warn)} .ratio.explainable{color:var(--good)}
.foot{padding:12px 16px;font-size:12.5px;color:var(--ink-3);border-top:1px solid var(--line-soft);display:flex;gap:16px;flex-wrap:wrap}
.foot b{color:var(--ink-2);font-weight:500}

.grid{display:grid;gap:12px}
.g4{grid-template-columns:repeat(4,1fr)} .g2{grid-template-columns:repeat(2,1fr)}
.stat{padding:14px 16px}
.stat .k{font-size:11px;letter-spacing:.12em;color:var(--ink-3);text-transform:uppercase;font-family:"IBM Plex Mono",monospace}
.stat .v{font-family:"IBM Plex Mono",monospace;font-size:26px;font-weight:600;line-height:1.15;margin-top:4px}
.stat .n{font-size:12px;color:var(--ink-3);margin-top:2px}
.site{padding:16px 18px;display:grid;grid-template-columns:1fr auto;gap:6px 14px}
.site .dom{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:15px}
.site .meta{font-size:12.5px;color:var(--ink-3);grid-column:1/-1}
.site .lv{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--accent);letter-spacing:.1em;align-self:start}
.site .name{font-size:13px;color:var(--ink-2);grid-column:1/-1}
.feed .row{display:grid;grid-template-columns:150px 1fr;border-bottom:1px solid var(--line-soft)}
.feed .row:last-child{border-bottom:0}
.feed .t{padding:12px 14px;font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink-3);background:var(--surface-2);border-right:1px solid var(--line-soft)}
.feed .b{padding:12px 14px;font-size:13.5px}
.feed .b .sub{font-size:12px;color:var(--ink-3);margin-top:3px;word-break:break-all}
.method{font-size:13.5px;color:var(--ink-2);display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.method div{padding:14px 16px}
.method b{display:block;color:var(--ink);font-size:13px;margin-bottom:4px}

.scrim{position:fixed;inset:0;background:rgba(6,12,15,.42);opacity:0;pointer-events:none;transition:opacity .18s;z-index:40}
.scrim.on{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;height:100vh;width:min(440px,92vw);z-index:41;background:var(--surface);border-left:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(100%);transition:transform .22s;overflow-y:auto;padding:24px 26px 40px}
.drawer.on{transform:none}
@media (prefers-reduced-motion:reduce){.drawer,.scrim{transition:none}}
.drawer .close{position:absolute;top:14px;right:16px;background:none;border:0;color:var(--ink-3);font-size:22px;cursor:pointer}
.drawer .eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.16em;color:var(--accent);text-transform:uppercase;margin-bottom:8px}
.kv{display:grid;grid-template-columns:82px 1fr;gap:7px 12px;font-size:12.5px;margin-top:14px}
.kv dt{color:var(--ink-3);font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.06em;padding-top:2px}
.kv dd{margin:0;word-break:break-all;font-family:"IBM Plex Mono",monospace}
.snap{border:1px solid var(--line-soft);border-radius:7px;padding:10px 12px;margin-top:10px;background:var(--surface-2)}

@media (max-width:900px){
  .wrap{padding:0 16px} .search{min-width:0;width:100%} .bar{flex-wrap:wrap}
  .g4,.g2{grid-template-columns:1fr 1fr} .method{grid-template-columns:1fr 1fr}
  .feed .row{grid-template-columns:1fr} .feed .t{border-right:0;border-bottom:1px solid var(--line-soft)}
}
</style>

<header class="top">
  <div class="wrap">
    <div class="bar">
      <div class="brand">
        <svg width="28" height="28" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="17" fill="none" stroke="var(--line)" stroke-width="1.5"/><path d="M20 9 L24 20 L20 31 Z" fill="var(--accent)"/><path d="M20 9 L16 20 L20 31 Z" fill="var(--ink-3)" opacity=".45"/><circle cx="20" cy="20" r="2" fill="var(--surface)" stroke="var(--accent)" stroke-width="1.5"/></svg>
        <div><h1>算力罗盘</h1><div class="sub">relay &amp; model api intel</div></div>
      </div>
      <form class="search" onsubmit="return false" role="search">
        <input id="q" type="search" placeholder="查一个站（如 toapis.cn）或一个模型（如 DeepSeek V4）" aria-label="搜索">
        <button type="submit">查</button>
      </form>
    </div>
    <div class="pledge">
      <span><b>不收任何人的钱</b>——没有付费墙、没有返佣、没有认证费</span>
      <span><b>每个数字可点证据</b>——来源、抓取时间、快照哈希</span>
      <span><b>只给事实不给推荐</b>——判断留给你</span>
    </div>
  </div>
</header>

<main class="wrap">

  <!-- 一、按模型比价（主） -->
  <section class="sec">
    <div class="sechead">
      <h2>你要用哪个模型？</h2>
      <span class="q">官方价、公开市场价、中转站实付价放在同一张表里。便宜和风险同一行。</span>
      <span class="right" id="asof"></span>
    </div>
    <div class="chips" id="chips"></div>
    <div class="card">
      <div class="tablewrap">
        <table id="tbl">
          <thead><tr>
            <th>渠道</th><th>类型</th><th class="num">输出 $/百万</th><th class="num">输入 $/百万</th><th class="num">相对参考价</th><th>判读</th><th>证据</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="foot" id="tblfoot"></div>
    </div>
  </section>

  <!-- 二、站点 -->
  <section class="sec">
    <div class="sechead">
      <h2>你在用的站靠谱吗？</h2>
      <span class="q">已确认的站点。每站一页事实清单，不打分、不推荐。</span>
    </div>
    <div class="grid g4" id="stats"></div>
    <div class="grid g2" id="sites" style="margin-top:12px"></div>
  </section>

  <!-- 三、动态 -->
  <section class="sec">
    <div class="sechead">
      <h2>今天变了什么</h2>
      <span class="q">新发现的站、采集入库、价格变更。变更流从 2026-09-01 起累计。</span>
    </div>
    <div class="card feed" id="feed"></div>
  </section>

  <!-- 四、方法 -->
  <section class="sec">
    <div class="sechead"><h2>我们怎么算的</h2></div>
    <div class="card method">
      <div><b>实付口径</b>中转站面板价是名义美元，实付 = 名义 × 充值比例 ÷ 汇率。三者各有快照。</div>
      <div><b>参考价取最低</b>官方与公开市场里同模型最低价作分母，比率只会偏高，宁少标不多标。</div>
      <div><b>判读是算术</b>「数学上不可持续」= 无补贴假设下低于成本；不判断成因。</div>
      <div><b>措辞有闸</b>禁用词发不出去；质量结论必须带样本量、时间窗、置信度。</div>
      <div><b>更正不删</b>算错了公开更正，原记录保留。</div>
    </div>
  </section>
</main>

<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="证据">
  <button class="close" id="dclose" aria-label="关闭">×</button>
  <div class="eyebrow">证据链</div>
  <h3 id="dtitle" style="font-size:17px"></h3>
  <div id="dbody"></div>
</aside>

<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  "use strict";
  var D = JSON.parse(document.getElementById("data").textContent);
  var KIND = {official:"官方", marketplace:"公开市场", relay:"中转站"};
  var LABEL = {unsustainable:"数学上不可持续", below_bulk:"低于常见批量折扣", explainable:"可由批量折扣解释",
               normal:"与公开价接近", premium:"高于公开价", far_above:"显著高于公开价"};

  document.getElementById("asof").textContent = "数据 " + D.generated_at.slice(0,16).replace("T"," ") + " · 汇率 USD/CNY " + D.fx.rate.toFixed(2);

  /* chips */
  var chips = document.getElementById("chips"), cur = D.models[0] ? D.models[0].id : null;
  D.models.forEach(function(m){
    var b = document.createElement("button"); b.className = "chip"; b.dataset.id = m.id;
    b.innerHTML = m.name + '<span class="n">' + m.n_relay + ' 家中转</span>';
    b.setAttribute("aria-pressed", m.id === cur ? "true" : "false");
    b.addEventListener("click", function(){ cur = m.id; render(); });
    chips.appendChild(b);
  });
  var off = document.createElement("span"); off.className = "chip off";
  off.textContent = "视频生成 · Seedance / Kling / Veo / Wan（数据接入中）";
  chips.appendChild(off);

  function fmt(x){ return x == null ? "—" : (x < 1 ? x.toFixed(3) : x.toFixed(2)); }
  function pct(r){ if (r == null) return "—"; var p = r*100; return (p < 10 ? p.toFixed(1) : p.toFixed(0)) + "%"; }

  function render(){
    document.querySelectorAll(".chip[data-id]").forEach(function(c){ c.setAttribute("aria-pressed", c.dataset.id === cur ? "true":"false"); });
    var m = D.models.filter(function(x){ return x.id === cur; })[0]; if (!m) return;
    var tb = document.querySelector("#tbl tbody"); tb.innerHTML = "";
    m.rows.forEach(function(r, i){
      var tr = document.createElement("tr"); if (r.is_floor) tr.className = "floor";
      var kind = KIND[r.kind] || r.kind;
      var judge = r.is_floor ? '<span class="pill ref"><span class="dot"></span>参考价</span>'
                : (r.band ? '<span class="pill ' + r.band + '"><span class="dot"></span>' + LABEL[r.band] + '</span>'
                : '<span class="pill normal">公开价</span>');
      var ratio = r.is_floor ? '<span class="mono" style="color:var(--ink-3)">1.00×</span>'
                : (r.ratio != null ? '<span class="ratio ' + (r.band||"") + '">' + pct(r.ratio) + '</span>' : "—");
      tr.innerHTML = '<td><b class="mono">' + r.vendor + '</b></td>'
        + '<td><span class="kind">' + kind + '</span></td>'
        + '<td class="num bigout">' + fmt(r.out) + '</td>'
        + '<td class="num">' + fmt(r.in) + '</td>'
        + '<td class="num">' + ratio + '</td>'
        + '<td>' + judge + '</td>'
        + '<td><button class="ev" data-m="' + m.id + '" data-i="' + i + '" aria-label="证据">↗</button></td>';
      tb.appendChild(tr);
    });
    var foot = document.getElementById("tblfoot");
    var relays = m.rows.filter(function(r){ return r.kind === "relay"; });
    var un = relays.filter(function(r){ return r.band === "unsustainable"; }).length;
    foot.innerHTML = '<span><b>' + m.name + '</b>：参考价 ' + m.floor_vendor + ' $' + fmt(m.floor_out) + '/百万输出</span>'
      + '<span>中转站 ' + relays.length + ' 家' + (un ? '，其中 <b style="color:var(--crit)">' + un + ' 家</b>报价在无补贴假设下数学上不可持续' : '') + '</span>'
      + '<span>中转价为人民币充值通道实付，按倍率 × 充值比例 ÷ 汇率换算</span>';
  }
  render();

  /* stats + sites */
  var S = D.stats, st = document.getElementById("stats");
  [["已确认站点", S.confirmed, "每站一页事实清单"], ["候选池", S.candidates, "含未确认"],
   ["已见域", S.seen_domains.toLocaleString(), "发现引擎去重库"], ["在库报价", S.quotes.toLocaleString(), "全部带快照"]].forEach(function(x){
    var d = document.createElement("div"); d.className = "card stat";
    d.innerHTML = '<div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div><div class="n">' + x[2] + '</div>'; st.appendChild(d);
  });
  var sites = document.getElementById("sites");
  D.sites.forEach(function(s){
    var d = document.createElement("div"); d.className = "card site";
    d.innerHTML = '<div class="dom">' + s.domain + '</div><div class="lv">L' + s.level + ' · ' + (s.panel_kind||"") + '</div>'
      + (s.entity_name ? '<div class="name">系统名「' + s.entity_name + '」</div>' : '')
      + '<div class="meta">首次发现 ' + s.first_seen_at.slice(0,10) + ' · 通道 ' + s.first_channel
      + (s.panel_version ? ' · 版本 ' + s.panel_version : '') + (s.n_quotes ? ' · 在库报价 ' + s.n_quotes + ' 条' : '') + '</div>';
    sites.appendChild(d);
  });

  /* feed */
  var feed = document.getElementById("feed");
  D.feed.forEach(function(f){
    var r = document.createElement("div"); r.className = "row";
    r.innerHTML = '<div class="t">' + f.t.slice(5,16).replace("T"," ") + '</div><div class="b">' + f.text + '<div class="sub">' + (f.sub||"") + '</div></div>';
    feed.appendChild(r);
  });

  /* evidence drawer */
  var drawer = document.getElementById("drawer"), scrim = document.getElementById("scrim");
  function close(){ drawer.classList.remove("on"); scrim.classList.remove("on"); }
  scrim.addEventListener("click", close); document.getElementById("dclose").addEventListener("click", close);
  document.addEventListener("keydown", function(e){ if (e.key === "Escape") close(); });
  document.addEventListener("click", function(e){
    var b = e.target.closest ? e.target.closest(".ev") : null; if (!b) return;
    var m = D.models.filter(function(x){ return x.id === b.dataset.m; })[0]; var r = m.rows[+b.dataset.i];
    document.getElementById("dtitle").textContent = r.vendor + " · " + m.name + " · 输出 $" + fmt(r.out) + "/百万";
    var h = '<dl class="kv"><dt>类型</dt><dd>' + (KIND[r.kind]||r.kind) + '</dd>';
    if (r.kind === "relay"){
      h += '<dt>名义价</dt><dd>' + fmt(r.note.nominal_usd) + ' USD（面板倍率 × $2/M）</dd>'
         + '<dt>充值比例</dt><dd>' + r.note.panel_price + ' 元 / $1（面板 price 字段）</dd>'
         + '<dt>汇率</dt><dd>' + D.fx.rate.toFixed(4) + '（' + D.fx.as_of + '）</dd>'
         + '<dt>实付</dt><dd>' + fmt(r.note.nominal_usd) + ' × ' + r.note.panel_price + ' ÷ ' + D.fx.rate.toFixed(2) + ' = ' + fmt(r.out) + ' USD</dd>'
         + '<dt>通道</dt><dd>' + r.note.channel + (r.note.stripe_unit_price != null && r.note.stripe_unit_price != 8 ? '；另有 Stripe 通道 ' + r.note.stripe_unit_price + ' 美元/$1' : '') + '</dd>';
    } else if (r.note.cny != null){
      h += '<dt>原价</dt><dd>' + r.note.cny + ' 元/百万（' + (r.note.tier === "idle" ? "空闲时段" : "高峰时段") + '，取最低档）</dd>';
    }
    if (r.ratio != null && !r.is_floor) h += '<dt>相对参考</dt><dd>' + fmt(r.out) + ' ÷ ' + fmt(m.floor_out) + ' = ' + pct(r.ratio) + '</dd>';
    h += '</dl>';
    r.evidence.forEach(function(ev){ if (!ev) return;
      h += '<div class="snap"><div class="mono" style="font-size:11px;color:var(--ink-3)">快照 #' + ev.id + ' · ' + ev.source + '</div>'
         + '<div class="mono" style="font-size:12px;word-break:break-all;margin-top:3px">' + ev.url + '</div>'
         + '<div class="mono" style="font-size:11px;color:var(--ink-3);margin-top:3px">' + ev.fetched_at + ' · sha256:' + ev.sha256.slice(0,16) + '…</div></div>';
    });
    h += '<p style="font-size:12.5px;color:var(--ink-3);margin-top:16px;border-top:1px solid var(--line-soft);padding-top:12px">此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。</p>';
    document.getElementById("dbody").innerHTML = h;
    drawer.classList.add("on"); scrim.classList.add("on");
  });

  /* search: 站点/模型都查 */
  document.getElementById("q").addEventListener("input", function(e){
    var v = e.target.value.trim().toLowerCase(); if (!v) return;
    var m = D.models.filter(function(x){ return x.name.toLowerCase().indexOf(v) >= 0 || x.id.indexOf(v) >= 0; })[0];
    if (m){ cur = m.id; render(); }
  });
})();
</script>
"""


def main():
    html = TEMPLATE.replace("__DATA__", json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/"))
    out = os.path.join(HERE, "index.html")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("写出 %s（%d 字节，%d 个模型，%d 个站点）" % (out, len(html), len(DATA["models"]), len(DATA["sites"])))


if __name__ == "__main__":
    main()
