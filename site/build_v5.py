# -*- coding: utf-8 -*-
"""Sinan Compute 站点生成器 v5（定稿视觉：亮色卡片仪表盘 + 近地轨道地球）。

输入：site/data_v2.json（export_data.py）、site/media.json（export_media.py）、docs/METHOD.md
输出：site/dist/ —— index.html · media.html · sites.html · method.html · 404.html · s/<域名>.html
      · assets/{app.css,app.js,earth.js} · fonts/ · img/ · data_v2.json · media.json · go_links.json · robots.txt · sitemap.xml · favicon.svg
规则：所有链接不带 .html（Cloudflare Pages 自动映射）；每个页面独立 description；措辞不含判断词与购买建议；
      待核站只列名义报价不出比率；无报价站说明“定价接口未公开”。
"""
from __future__ import unicode_literals
import os, io, json, re, shutil, html as H
from rank_seo import rank_metadata
try:
    import markdown
except Exception:
    markdown = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(HERE, "dist")
BASE = "https://compute.sinanlab.com"
D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
MEDIA = json.load(io.open(os.path.join(HERE, "media.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "media.json")) else None
GEN_DATE = D["generated_at"][:10]

LABEL = {"unsustainable": "数学上不可持续", "below_bulk": "低于常见批量折扣", "explainable": "价格说得通", "normal": "与公开价接近", "premium": "高于公开价", "far_above": "显著高于公开价"}
BANDC = {"unsustainable": "#F04438", "below_bulk": "#F79009", "explainable": "#17B26A", "normal": "#17B26A", "premium": "#6E56F5", "far_above": "#9AA0B8"}
DISCLAIMER = "此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。"

def esc(s):
    if s is None: return ""
    if not isinstance(s, str): s = json.dumps(s, ensure_ascii=False)
    return H.escape(s, quote=True)

def fmt(x):
    if x is None: return "—"
    return ("%.3f" % x) if x < 1 else ("%.2f" % x)

def pct(r):
    if r is None: return "—"
    p = r * 100
    return ("%.1f%%" % p) if p < 10 else ("%.0f%%" % p)

def tpl(s, **kw):
    for k, v in kw.items(): s = s.replace("{{" + k + "}}", v if isinstance(v, str) else str(v))
    return s

def jsdata(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

# ------------------------------------------------------------------ CSS
CSS = r"""
@font-face{font-family:"Sora";font-style:normal;font-weight:400 700;font-display:swap;src:url(/fonts/Sora-latin.woff2) format("woff2")}
@font-face{font-family:"JetBrains Mono";font-style:normal;font-weight:400 600;font-display:swap;src:url(/fonts/JetBrainsMono-latin.woff2) format("woff2")}
:root{--ground:#F2F3F9;--ground-2:#E9EAF3;--card:#FFFFFF;--hair:#E6E7F0;--hair-2:#D5D7E6;--ink:#0F1222;--ink-2:#5A6079;--ink-3:#9AA0B8;
--p:#6E56F5;--p-deep:#4B36D6;--p-soft:#EEEBFF;--p-ink:#3A2AA8;--good:#17B26A;--good-soft:#E6F7EF;--warn:#F79009;--warn-soft:#FFF3E0;--crit:#F04438;--crit-soft:#FDECEC;--robo:#F79009;
--shadow-1:0 1px 2px rgba(20,22,50,.04),0 8px 24px -12px rgba(20,22,50,.12);--shadow-2:0 2px 6px rgba(20,22,50,.06),0 24px 48px -20px rgba(55,40,160,.22);
--ease:cubic-bezier(.22,1,.36,1);--spring:cubic-bezier(.34,1.4,.64,1);--r:18px;
--sans:"Sora","Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,Menlo,monospace}
*{box-sizing:border-box}html,body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}button{font:inherit;color:inherit}::selection{background:var(--p-soft);color:var(--p-ink)}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.app{display:grid;grid-template-columns:232px 1fr;min-height:100vh}
.rail{position:sticky;top:0;height:100vh;background:var(--card);border-right:1px solid var(--hair);padding:22px 16px;display:flex;flex-direction:column;gap:6px;overflow:auto}
.brand{display:flex;align-items:center;gap:11px;padding:4px 8px 22px}
.brand .mark{width:34px;height:34px;border-radius:11px;background:linear-gradient(145deg,#8B77FF,#4B36D6);box-shadow:0 8px 18px -8px rgba(75,54,214,.7),inset 0 1px 0 rgba(255,255,255,.35);position:relative;flex:none}
.brand .mark:after{content:"";position:absolute;inset:9px 12px;border-radius:2px 2px 8px 8px;background:linear-gradient(#fff,#E9E6FF);transform:rotate(-28deg);box-shadow:0 2px 4px rgba(0,0,0,.25)}
.brand b{font-size:17px;font-weight:700;letter-spacing:-.01em;display:block}.brand small{display:block;font-size:10.5px;color:var(--ink-3);font-weight:500;letter-spacing:.04em;margin-top:1px}
.sect{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);padding:14px 10px 6px;font-weight:600}
.nav{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:12px;color:var(--ink-2);font-weight:500;transition:background .25s var(--ease),color .25s var(--ease),transform .25s var(--ease);white-space:nowrap}
.nav svg{width:18px;height:18px;flex:none;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.nav:hover{background:var(--ground);color:var(--ink);transform:translateX(2px)}
.nav.on{background:linear-gradient(135deg,#7A63FF,#5642DF);color:#fff;box-shadow:0 10px 22px -12px rgba(75,54,214,.8)}
.nav .badge{margin-left:auto;font-family:var(--mono);font-size:10.5px;background:var(--ground);color:var(--ink-2);padding:2px 7px;border-radius:999px}.nav.on .badge{background:rgba(255,255,255,.2);color:#fff}
.robo{margin-top:auto;border-radius:16px;padding:14px;background:linear-gradient(160deg,#FFF6E8,#FFE9C7);border:1px solid #FFE1B3;position:relative;overflow:hidden;display:block}
.robo .gl{position:absolute;right:-18px;top:-18px;width:76px;height:76px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#FFD27A,#F79009 60%,#C96A00);box-shadow:inset -8px -10px 18px rgba(120,60,0,.35)}
.robo b{font-size:13px;display:block}.robo p{margin:4px 0 0;font-size:12px;color:#7A4B00;max-width:130px}
.main{min-width:0;padding:22px 30px 60px}
.top{display:flex;align-items:center;gap:14px;margin-bottom:22px;flex-wrap:wrap}
.search{flex:1;max-width:520px;min-width:240px;display:flex;align-items:center;gap:10px;background:var(--card);border:1px solid var(--hair);border-radius:14px;padding:0 14px;height:46px;box-shadow:var(--shadow-1);transition:box-shadow .3s var(--ease),border-color .3s}
.search:focus-within{border-color:var(--p);box-shadow:0 0 0 4px var(--p-soft),var(--shadow-1)}
.search input{flex:1;border:0;outline:0;background:transparent;font:inherit;font-size:14px;color:var(--ink);min-width:0}
.search kbd{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);border:1px solid var(--hair-2);border-radius:6px;padding:1px 6px}
.asof{margin-left:auto;font-family:var(--mono);font-size:11.5px;color:var(--ink-3);display:flex;align-items:center;gap:8px}
.asof i{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 0 4px var(--good-soft);animation:pulse 2.4s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 3px var(--good-soft)}50%{box-shadow:0 0 0 7px rgba(23,178,106,.12)}}
.crumb{font-family:var(--mono);font-size:12px;color:var(--ink-3)}.crumb a:hover{color:var(--ink)}
.card{background:var(--card);border:1px solid var(--hair);border-radius:var(--r);box-shadow:var(--shadow-1)}.pad{padding:22px 24px}
h1,h2,h3{margin:0;letter-spacing:-.01em}h2.sec{font-size:20px;font-weight:700}
.lead{color:var(--ink-2);font-size:13.5px;margin:6px 0 0;max-width:760px}
.sub{font-size:11.5px;color:var(--ink-3);margin-top:2px}
/* hero */
.hero{min-height:500px;border-radius:24px;overflow:hidden;position:relative;background:radial-gradient(600px 300px at 12% 0%,rgba(110,86,245,.28),transparent 60%),#040611;color:#fff;box-shadow:0 2px 6px rgba(20,22,50,.1),0 30px 60px -24px rgba(10,10,40,.7);isolation:isolate}
.hero canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
.hero .stars{pointer-events:none}.hero #gl{cursor:grab;z-index:1}.hero #gl:active{cursor:grabbing}
.hero .scrim{position:absolute;inset:0;background:linear-gradient(100deg,rgba(4,6,17,.72) 0%,rgba(4,6,17,.35) 42%,rgba(4,6,17,0) 68%);pointer-events:none}
.hero .txt{position:relative;z-index:2;max-width:600px;padding:44px 48px 48px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;opacity:.85}
.hero h1{margin:14px 0 0;font-size:44px;line-height:1.12;letter-spacing:-.02em;font-weight:700;text-wrap:balance}
.hero p{margin:14px 0 0;font-size:15px;line-height:1.75;max-width:440px;color:rgba(255,255,255,.82)}
.hero .cta{display:flex;gap:10px;margin-top:26px;flex-wrap:wrap}
.hero .stat{position:absolute;right:26px;top:22px;z-index:2;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.18);backdrop-filter:blur(10px);border-radius:14px;padding:10px 14px;text-align:right}
.hero .stat b{display:block;font-family:var(--mono);font-size:22px;font-weight:600;line-height:1;color:#fff}.hero .stat small{font-size:11px;opacity:.85}
.hero .tag{position:absolute;right:26px;bottom:16px;z-index:2;font-family:var(--mono);font-size:10px;letter-spacing:.1em;opacity:.5;line-height:1.6;text-align:right;pointer-events:none}
.btn{display:inline-flex;align-items:center;gap:8px;height:42px;padding:0 18px;border-radius:12px;border:0;cursor:pointer;font-weight:600;font-size:13.5px;transition:transform .35s var(--spring),box-shadow .35s var(--ease),background .3s}
.btn:hover{transform:translateY(-2px)}.btn:active{transform:translateY(0) scale(.98)}
.btn.w{background:#fff;color:var(--p-deep);box-shadow:0 10px 20px -12px rgba(0,0,0,.4)}
.btn.g{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.3);backdrop-filter:blur(6px)}.btn.g:hover{background:rgba(255,255,255,.16)}
.btn.p{background:var(--p);color:#fff;box-shadow:0 10px 22px -12px rgba(75,54,214,.9)}.btn.p:hover{background:var(--p-deep)}
.btn.o{background:var(--card);color:var(--ink);border:1px solid var(--hair-2)}
/* kpis */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:18px}
.kpi{padding:18px 20px 16px;position:relative;overflow:hidden;transition:transform .45s var(--spring),box-shadow .45s var(--ease);display:block}
.kpi:hover{transform:translateY(-3px);box-shadow:var(--shadow-2)}
.kpi .k{font-size:12px;color:var(--ink-2);font-weight:500;display:flex;align-items:center;gap:8px}
.kpi .k i{width:26px;height:26px;border-radius:9px;display:grid;place-items:center;background:var(--p-soft);color:var(--p);flex:none}
.kpi .k i svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round}
.kpi .v{font-family:var(--mono);font-size:32px;font-weight:600;letter-spacing:-.02em;margin-top:12px;line-height:1}.kpi .v small{font-size:13px;color:var(--ink-3);font-weight:500;margin-left:4px}
.kpi .n{font-size:12px;color:var(--ink-3);margin-top:8px}
.dist{display:flex;height:8px;border-radius:999px;overflow:hidden;margin-top:12px;gap:2px}.dist i{display:block;height:100%;border-radius:3px}
.dist .c-ultra{background:var(--crit)}.dist .c-cheap{background:var(--warn)}.dist .c-near{background:var(--good)}.dist .c-high{background:var(--p)}.dist .c-held{background:var(--hair-2)}
.legend{display:flex;flex-wrap:wrap;gap:10px 14px;margin-top:10px;font-size:11.5px;color:var(--ink-2)}.legend span:before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:6px;vertical-align:1px;background:var(--c)}
/* ledger */
.ledger{margin-top:18px;overflow:hidden}
.lh{display:flex;align-items:flex-start;gap:20px;padding:22px 24px 0;flex-wrap:wrap}
.calc{margin-left:auto;display:flex;align-items:center;gap:8px;background:var(--ground);border-radius:12px;padding:8px 12px;font-size:12.5px;color:var(--ink-2);flex-wrap:wrap}
.calc input{width:58px;border:0;border-bottom:2px solid var(--p);background:transparent;font:inherit;font-family:var(--mono);color:var(--ink);text-align:right;outline:0;padding:2px 4px}
.calc .pre{border:1px solid var(--hair-2);background:var(--card);border-radius:8px;padding:3px 8px;font-size:11.5px;cursor:pointer}
.calc .pre:hover{border-color:var(--p);color:var(--p-ink)}
.chips{display:flex;gap:8px;flex-wrap:wrap;padding:16px 24px 6px;align-items:center}
.chips .vn{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);margin-right:2px}
.chip{border:1px solid var(--hair);background:var(--card);border-radius:999px;padding:7px 12px;cursor:pointer;font-size:12.5px;font-weight:500;color:var(--ink-2);display:inline-flex;gap:7px;align-items:center;transition:all .3s var(--ease)}
.chip .n{font-family:var(--mono);font-size:10.5px;color:var(--ink-3)}
.chip:hover{border-color:var(--p);color:var(--p-ink);transform:translateY(-1px)}
.chip[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:#fff;box-shadow:0 8px 18px -10px rgba(15,18,34,.6)}.chip[aria-pressed=true] .n{color:rgba(255,255,255,.65)}
.chip.old{display:none}.chips.all .chip.old{display:inline-flex}
.chip.more{border-style:dashed}
.hint{padding:0 24px 8px;font-size:12px;color:var(--ink-3)}
.mlinks{display:flex;flex-wrap:wrap;gap:6px 10px;padding:12px 24px 18px;border-top:1px solid var(--hair);font-size:12px}.mlinks .vn{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);margin-right:6px;align-self:center}.mlinks a{color:var(--ink-2);border:1px solid var(--hair);border-radius:999px;padding:3px 9px}.mlinks a:hover{color:var(--p-ink);border-color:var(--p)}
.faq dt{font-weight:600;margin-top:14px}.faq dd{margin:4px 0 0;color:var(--ink-2);font-size:13.5px}
.mhead{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;margin-bottom:16px}.mhead h1{font-size:30px;letter-spacing:-.02em}
.tablewrap{overflow-x:auto;margin-top:8px}
table{width:100%;border-collapse:collapse}
th{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);text-align:left;font-weight:500;padding:12px 16px;border-bottom:1px solid var(--hair);white-space:nowrap;background:var(--card)}
th:first-child,td:first-child{padding-left:24px}
td{padding:13px 16px;border-bottom:1px solid var(--hair);vertical-align:middle}tr:last-child td{border-bottom:0}
tbody tr:hover{background:#FAFAFE}
tr.floor td{background:var(--p-soft)}tr.floor td:first-child{border-left:3px solid var(--p);padding-left:21px}
td.num,th.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.dom{font-family:var(--mono);font-weight:500;font-size:13px}a.dom:hover{color:var(--p-ink)}
.big{font-size:16px;font-weight:600}.asf{display:block;font-size:10.5px;color:var(--ink-3);font-weight:400;margin-top:2px}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:500;padding:4px 10px;border-radius:999px;white-space:nowrap}
.pill:before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
.pill.unsustainable{background:var(--crit-soft);color:#B42318}.pill.below_bulk{background:var(--warn-soft);color:#B54708}.pill.explainable,.pill.normal{background:var(--good-soft);color:#067647}.pill.premium{background:var(--p-soft);color:var(--p-ink)}.pill.far_above{background:#EEF0F6;color:var(--ink-2)}.pill.ref{background:var(--p);color:#fff}.pill.none{background:var(--ground-2);color:var(--ink-2)}
.pill.ultra{background:var(--crit-soft);color:#B42318}.pill.cheap{background:var(--warn-soft);color:#B54708}.pill.near{background:var(--good-soft);color:#067647}.pill.high{background:var(--p-soft);color:var(--p-ink)}.probe{font-family:var(--mono);font-size:10.5px;margin-top:5px;color:var(--ink-3);max-width:240px;line-height:1.4}.probe.consistent{color:#067647}.probe.divergent{color:#B54708}.probe.failed{color:var(--ink-3)}.probe .pd{color:var(--ink-3)}
.rk{list-style:none;margin:0;padding:0}.rk li{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--hair)}.rk li:last-child{border-bottom:0}.rk .no{font-family:var(--mono);font-size:18px;font-weight:600;width:34px;color:var(--ink-3);flex:none}.rk li.top .no{color:var(--p);font-size:22px}.rk li.top .who a{font-size:15px;font-weight:600}.rk .who{flex:1;min-width:0}.rk .who a{font-family:var(--mono);font-size:13.5px;color:var(--ink)}.rk .who small{display:block;color:var(--ink-3);font-size:11.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.rk .val{font-family:var(--mono);font-size:14px;text-align:right;flex:none}.rk .val small{display:block;color:var(--ink-3);font-size:11px;font-weight:400}
.rkhead{background:linear-gradient(135deg,#0B0D1F 0%,#1B1650 55%,#3A2AA8 100%);color:#fff;border-radius:22px;padding:34px 34px 30px;position:relative;overflow:hidden}.rkhead .eyebrow{color:#B9ADFF}.rkhead h1{font-size:40px;letter-spacing:-.02em;margin:8px 0 6px}.rkhead .lead{color:rgba(255,255,255,.78);max-width:720px}.rkhead .meta{display:flex;gap:18px;flex-wrap:wrap;margin-top:18px;font-family:var(--mono);font-size:12px;color:#B9ADFF}.rkhead .meta b{color:#fff;font-size:20px;display:block;font-weight:600}
.rkgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}@media (max-width:860px){.rkgrid{grid-template-columns:1fr}.rkhead h1{font-size:30px}}.rk .bar{height:4px;border-radius:2px;background:var(--hair);width:120px;position:relative;overflow:hidden;flex:none}.rk .bar i{position:absolute;inset:0;right:auto;background:var(--p);border-radius:2px}
.pill.held{background:#EEF0F6;color:var(--ink-2);border:1px dashed var(--hair-2)}
.up{font-family:var(--mono);font-size:12.5px}.up.good{color:var(--good)}.up.bad{color:var(--crit)}
.gcell{display:inline-flex;align-items:center;gap:12px}
.gauge{position:relative;width:150px;height:14px;border-radius:999px;background:linear-gradient(90deg,#F7C9C6 0 7.5%,#FBE0C2 7.5% 20%,#D5F1E2 20% 62.5%,#E5E0FF 62.5% 100%);box-shadow:inset 0 1px 2px rgba(0,0,0,.08);flex:none}
.gauge .mid{position:absolute;left:50%;top:-3px;bottom:-3px;width:2px;background:var(--p);border-radius:2px;transform:translateX(-50%)}
.gauge .nd{position:absolute;top:-4px;width:22px;height:22px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#fff,#E9E8F5);box-shadow:0 2px 6px rgba(20,22,50,.28),inset 0 -2px 3px rgba(0,0,0,.08);transform:translateX(-50%);left:50%;transition:left .9s var(--spring)}
.gauge .nd:after{content:"";position:absolute;inset:7px;border-radius:50%;background:var(--c,var(--ink-3))}
.r{font-family:var(--mono);font-size:13px;font-weight:600;min-width:46px}.r.unsustainable{color:#B42318}.r.below_bulk{color:#B54708}.r.explainable,.r.normal{color:#067647}.r.premium{color:var(--p-ink)}.r.far_above{color:var(--ink-2)}
.evb,.help{border:1px solid var(--hair-2);background:var(--card);border-radius:9px;padding:5px 10px;font-family:var(--mono);font-size:11px;cursor:pointer;color:var(--ink-2);transition:all .25s var(--ease)}
.evb:hover,.help:hover{border-color:var(--p);color:var(--p-ink);background:var(--p-soft)}
.help{border-radius:50%;width:22px;height:22px;padding:0;display:inline-grid;place-items:center;margin-left:6px;vertical-align:middle}
.fold{border-top:1px solid var(--hair)}.fold summary{cursor:pointer;padding:14px 24px;font-size:13px;color:var(--ink-2);list-style:none;display:flex;gap:10px;align-items:center}
.fold summary::-webkit-details-marker{display:none}.fold summary:before{content:"";width:7px;height:7px;border-right:1.8px solid var(--ink-3);border-bottom:1.8px solid var(--ink-3);transform:rotate(-45deg);transition:transform .3s var(--ease)}
.fold[open] summary:before{transform:rotate(45deg)}.fold summary b{color:var(--crit);font-family:var(--mono)}
.tfoot{display:flex;flex-wrap:wrap;gap:8px 22px;padding:14px 24px;border-top:1px solid var(--hair);font-size:12px;color:var(--ink-3)}
.terms{display:flex;flex-wrap:wrap;gap:8px 18px;padding:12px 24px 0;font-size:12px;color:var(--ink-2)}.terms b{color:var(--ink);font-weight:600}
/* grid & tiles */
.grid2{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;margin-top:18px}
.bento{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.tile{padding:20px;position:relative;overflow:hidden;cursor:pointer;transform-style:preserve-3d;transition:transform .5s var(--spring),box-shadow .5s var(--ease);will-change:transform;display:block}
.tile:hover{box-shadow:var(--shadow-2)}
.tile .orb{position:absolute;right:-26px;top:-26px;width:110px;height:110px;border-radius:50%;transition:transform .7s var(--spring)}.tile:hover .orb{transform:translate(-8px,8px) scale(1.06)}
.tile.ultra .orb{background:radial-gradient(circle at 32% 30%,#FFB4AE,#F04438 55%,#9E1B14);box-shadow:inset -14px -18px 28px rgba(90,0,0,.35)}
.tile.cheap .orb{background:radial-gradient(circle at 32% 30%,#FFD9A0,#F79009 55%,#A45A00);box-shadow:inset -14px -18px 28px rgba(110,50,0,.35)}
.tile.near .orb{background:radial-gradient(circle at 32% 30%,#9FF0C8,#17B26A 55%,#0A6B3E);box-shadow:inset -14px -18px 28px rgba(0,80,40,.35)}
.tile.high .orb{background:radial-gradient(circle at 32% 30%,#C9BEFF,#6E56F5 55%,#2E1E9C);box-shadow:inset -14px -18px 28px rgba(30,10,110,.4)}
.tile .v{font-family:var(--mono);font-size:38px;font-weight:600;letter-spacing:-.02em;line-height:1}.tile .k{font-size:14px;font-weight:600;margin-top:10px}.tile .n{font-size:12px;color:var(--ink-3);margin-top:4px;max-width:210px}
.tile .go{position:absolute;right:16px;bottom:16px;width:30px;height:30px;border-radius:50%;border:1px solid var(--hair-2);display:grid;place-items:center;color:var(--ink-2);transition:all .3s var(--ease)}.tile:hover .go{background:var(--ink);color:#fff;border-color:var(--ink)}
.feed{padding:20px 22px}.feed h3{margin:0;font-size:16px;font-weight:700}
.feed .row{display:grid;grid-template-columns:52px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid var(--hair);font-size:13px}.feed .row:last-child{border-bottom:0}
.feed .t{font-family:var(--mono);font-size:11px;color:var(--ink-3);padding-top:2px}.feed .old{color:var(--ink-3);text-decoration:line-through;font-family:var(--mono)}.feed .new{color:var(--good);font-family:var(--mono);font-weight:600}
/* media */
.seg{margin-left:auto;display:inline-flex;background:var(--ground);border-radius:12px;padding:4px;position:relative}
.seg button{border:0;background:transparent;padding:7px 14px;border-radius:9px;cursor:pointer;font-weight:600;font-size:12.5px;color:var(--ink-2);position:relative;z-index:1;transition:color .3s}.seg button[aria-pressed=true]{color:var(--ink)}
.seg .ind{position:absolute;top:4px;bottom:4px;background:var(--card);border-radius:9px;box-shadow:var(--shadow-1);transition:left .45s var(--spring),width .45s var(--spring)}
.fams{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px}
.fam{border:1px solid var(--hair);border-radius:16px;padding:16px;background:linear-gradient(180deg,#FBFBFE,#fff);transition:transform .45s var(--spring),box-shadow .45s}.fam:hover{transform:translateY(-3px);box-shadow:var(--shadow-2)}
.fam .name{font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}.fam .name .cube{width:22px;height:22px;border-radius:7px;background:linear-gradient(145deg,#8B77FF,#4B36D6);box-shadow:inset 0 1px 0 rgba(255,255,255,.4),0 6px 12px -6px rgba(75,54,214,.7);flex:none}
.fam .ref{margin-top:12px;font-family:var(--mono);font-size:22px;font-weight:600}.fam .ref small{font-size:11px;color:var(--ink-3);font-weight:400;margin-left:4px}
.fam .meta{font-size:11.5px;color:var(--ink-3);margin-top:4px}
.fam .rng{margin-top:12px;height:6px;border-radius:999px;background:var(--ground-2);position:relative}.fam .rng i{position:absolute;top:0;bottom:0;border-radius:999px;background:linear-gradient(90deg,var(--good),var(--p))}
.fam .rl{display:flex;justify-content:space-between;font-family:var(--mono);font-size:11px;color:var(--ink-2);margin-top:6px}
.fam .none{margin-top:12px;font-size:12px;color:var(--ink-2);background:var(--ground);border-radius:10px;padding:8px 10px}
.fam table{font-size:12.5px;margin-top:10px}.fam th,.fam td{padding:6px 8px}.fam th:first-child,.fam td:first-child{padding-left:0}
/* site page */
.sitehead{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;margin-bottom:16px}
.sitehead h1{font-family:var(--mono);font-size:30px;letter-spacing:-.02em}.sitehead .nm{font-size:16px;color:var(--ink-2);margin-left:10px;font-family:var(--sans)}
.facts{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.fact{padding:16px 18px}.fact .k{font-size:12px;color:var(--ink-2)}.fact .v{font-family:var(--mono);font-size:22px;font-weight:600;margin-top:8px;line-height:1.1}.fact .v.t{font-family:var(--sans);font-size:15px}.fact .n{font-size:11.5px;color:var(--ink-3);margin-top:6px}
.notice{border:1px solid #F5C87A;background:var(--warn-soft);border-radius:12px;padding:12px 16px;color:#7A4B00;font-size:13px}
.callout{border:1px solid var(--hair);background:#FBFBFE;border-radius:12px;padding:12px 16px;font-size:13px;color:var(--ink-2)}
.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:16px 24px 6px}
.fchip{border:1px solid var(--hair);background:var(--card);border-radius:999px;padding:6px 12px;cursor:pointer;font-size:12.5px;font-weight:500;color:var(--ink-2)}.fchip[aria-pressed=true]{background:var(--ink);border-color:var(--ink);color:#fff}
/* drawer */
.scrim{position:fixed;inset:0;background:rgba(15,18,34,.35);backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:opacity .35s;z-index:40}
.drawer{position:fixed;top:12px;right:12px;bottom:12px;width:min(480px,94vw);background:var(--card);border-radius:22px;box-shadow:0 30px 80px -20px rgba(15,18,34,.45);transform:translateX(calc(100% + 24px));transition:transform .55s var(--spring);z-index:41;padding:26px 26px 30px;overflow:auto}
.scrim.on{opacity:1;pointer-events:auto}.drawer.on{transform:none}
.drawer .x{position:absolute;right:18px;top:18px;width:34px;height:34px;border-radius:50%;border:1px solid var(--hair);background:var(--card);cursor:pointer;font-size:18px;line-height:1}
.drawer h3{margin:8px 0 0;font-size:18px;font-weight:700;letter-spacing:-.01em;padding-right:40px}
.kv{display:grid;grid-template-columns:1fr auto;gap:10px 16px;margin:16px 0 0;font-size:13px}.kv dt{color:var(--ink-2)}.kv dt small{display:block;font-size:11px;color:var(--ink-3)}.kv dd{margin:0;font-family:var(--mono);font-size:14px;text-align:right}.kv .tot{border-top:1px solid var(--hair);padding-top:10px;color:var(--ink);font-weight:600}
.snap{border:1px solid var(--hair);border-radius:12px;padding:10px 12px;margin-top:8px;font-family:var(--mono);font-size:11px;color:var(--ink-2);word-break:break-all}.snap b{display:block;color:var(--ink);font-size:11.5px;margin-bottom:2px}
.disc{font-size:12px;color:var(--ink-3);border-top:1px solid var(--hair);padding-top:12px;margin-top:16px}
/* prose */
.prose{max-width:800px;font-size:14.5px;line-height:1.85}.prose h1{font-size:26px;margin:0 0 10px}.prose h2{font-size:20px;margin:30px 0 8px;padding-top:14px;border-top:1px solid var(--hair)}.prose h3{font-size:16px;margin:20px 0 6px}
.prose p{margin:8px 0}.prose ul,.prose ol{padding-left:22px}.prose li{margin:4px 0}.prose code{font-family:var(--mono);font-size:12.5px;background:var(--ground-2);padding:1px 6px;border-radius:6px}.prose pre{background:#0F1222;color:#E8EEF3;border-radius:12px;padding:14px 16px;overflow:auto;font-family:var(--mono);font-size:12.5px}.prose pre code{background:transparent;color:inherit;padding:0}
.prose table{font-size:13px}.prose th,.prose td{padding:8px 10px}.prose a{color:var(--p-ink);text-decoration:underline;text-decoration-color:var(--hair-2)}
.auth{display:flex;align-items:center;gap:8px}.auth img{width:28px;height:28px;border-radius:50%;border:1px solid var(--hair)}.auth .menu{position:relative}.auth .dd{position:absolute;right:0;top:34px;background:var(--card);border:1px solid var(--hair);border-radius:12px;box-shadow:var(--shadow-2);padding:6px;display:none;min-width:170px;z-index:30}.auth .menu:hover .dd,.auth .dd:hover{display:block}.auth .dd a{display:block;padding:8px 12px;border-radius:8px;font-size:13px;white-space:nowrap}.auth .dd a:hover{background:var(--ground)}
.banner{background:var(--warn-soft);border:1px solid #F5C87A;border-radius:12px;padding:10px 16px;font-size:13px;color:#7A4B00;margin-bottom:14px}
.btn.watch.on{background:var(--p-soft);border-color:var(--p);color:var(--p-ink)}
.melist .row{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--hair)}.melist .row:last-child{border-bottom:0}.melist .x{margin-left:auto}
footer.ft{border-top:1px solid var(--hair);margin-top:60px}footer.ft .in{display:flex;flex-wrap:wrap;gap:16px 20px;padding:22px 0;font-size:12.5px;color:var(--ink-3)}footer.ft a{color:var(--ink-3)}footer.ft a:hover{color:var(--ink)}
.rise{animation:rise .8s var(--ease) both;animation-delay:calc(var(--i,0)*70ms)}@keyframes rise{from{opacity:0;transform:translateY(18px) scale(.985)}}
@media (prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;transition-duration:.01ms!important}}
@media (max-width:1100px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.fams{grid-template-columns:1fr 1fr}.facts{grid-template-columns:1fr 1fr}}
@media (max-width:860px){.app{grid-template-columns:1fr}.rail{position:static;height:auto;flex-direction:row;flex-wrap:nowrap;overflow-x:auto;gap:4px;padding:10px 12px;align-items:center}.rail .sect,.rail .robo{display:none}.rail .brand{padding:4px 8px;flex:none}.rail .brand small{display:none}.nav{padding:8px 10px;font-size:13px;flex:none}.nav .badge{display:none}.main{padding:16px}.hero{min-height:560px}.hero .txt{padding:26px 24px 30px;max-width:none}.hero h1{font-size:32px}.hero .scrim{background:linear-gradient(180deg,rgba(4,6,17,.75) 0%,rgba(4,6,17,.3) 50%,transparent 75%)}.hero .tag{display:none}.fams{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}.asof{display:none}.bento{grid-template-columns:1fr 1fr}.facts{grid-template-columns:1fr 1fr}.sitehead h1{font-size:22px}}
"""

# ------------------------------------------------------------------ JS（公共）
APP_JS = r"""
var LABEL={unsustainable:"数学上不可持续",below_bulk:"低于常见批量折扣",explainable:"价格说得通",normal:"与公开价接近",premium:"高于公开价",far_above:"显著高于公开价"};
var BANDC={unsustainable:"#F04438",below_bulk:"#F79009",explainable:"#17B26A",normal:"#17B26A",premium:"#6E56F5",far_above:"#9AA0B8"};
var DISC="此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。";
function fmt(x){return x==null?"—":(x<1?x.toFixed(3):x.toFixed(2));}
function pct(r){if(r==null)return "—";var p=r*100;return (p<10?p.toFixed(1):p.toFixed(0))+"%";}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
var reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
var D=(function(){var el=document.getElementById("d");return el?JSON.parse(el.textContent):{};})();
function gauge(ratio,band){var left=Math.max(0,Math.min(2,ratio==null?1:ratio))/2*100;return '<span class="gauge"><span class="mid"></span><span class="nd" data-left="'+left.toFixed(2)+'" style="--c:'+(BANDC[band]||"#6E56F5")+'"></span></span>';}
function settleNeedles(root){requestAnimationFrame(function(){requestAnimationFrame(function(){(root||document).querySelectorAll(".nd[data-left]").forEach(function(n){n.style.left=n.dataset.left+"%";});});});}
function countUp(el,to,suffix){if(!el)return;if(reduce){el.textContent=to.toLocaleString()+(suffix||"");return;}var t0=performance.now(),dur=1100;function f(t){var k=Math.min(1,(t-t0)/dur);k=1-Math.pow(1-k,4);el.textContent=Math.round(to*k).toLocaleString()+(suffix||"");if(k<1)requestAnimationFrame(f);}requestAnimationFrame(f);}
/* 抽屉 */
var drawer=document.getElementById("drawer"),scrim=document.getElementById("scrim");
function openD(eye,title,html){document.getElementById("deye").textContent=eye;document.getElementById("dtitle").textContent=title;document.getElementById("dbody").innerHTML=html;drawer.classList.add("on");scrim.classList.add("on");settleNeedles(drawer);}
function closeD(){drawer.classList.remove("on");scrim.classList.remove("on");}
if(scrim){scrim.addEventListener("click",closeD);document.getElementById("dx").addEventListener("click",closeD);}
document.addEventListener("keydown",function(e){if(e.key==="Escape")closeD();if(e.key==="/"&&document.activeElement.tagName!=="INPUT"){var q=document.getElementById("q");if(q){e.preventDefault();q.focus();}}});
function snapHtml(sids){var S=D.snaps||{};return (sids||[]).map(function(s){var ev=S[String(s)];if(!ev)return "";return '<div class="snap"><b>快照 #'+ev.id+' · '+esc(ev.source)+'</b>'+esc(ev.url)+'<div style="margin-top:3px;color:var(--ink-3)">'+esc(ev.fetched_at)+' · sha256 '+esc(String(ev.sha256).slice(0,16))+'…</div></div>';}).join("");}
function helpHtml(code){return '<p style="font-size:14px;line-height:1.7">'+esc((D.label_help||{})[code]||"")+'</p><p style="font-size:12.5px;color:var(--ink-3);margin-top:12px">分档只是算术区间：&lt;15% 不可持续 · 15–40% 低于批量折扣 · 40–75% 说得通 · 75–125% 接近 · 125–300% 高于 · &gt;300% 显著高于。</p>';}
function relayEvidence(row,m){var f=m.floor;var h='<div class="eyebrow" style="color:var(--ink-3);margin-top:8px">换算链</div><dl class="kv"><dt>面板名义价<small>倍率 × $2 / 百万 token</small></dt><dd>'+fmt(row.nominal_out)+' USD</dd><dt>× 充值比例<small>面板 price 字段 · 每 $1 名义额度收多少元'+(row.stripe!=null&&row.stripe!=8?' · 另有 Stripe '+row.stripe:'')+'</small></dt><dd>'+row.price_field+' 元/$1</dd><dt>÷ 汇率<small>USD/CNY · '+esc(D.fx.as_of)+'</small></dt><dd>'+D.fx.rate.toFixed(4)+'</dd><dt class="tot">= 实付</dt><dd class="tot">'+fmt(row.out)+'</dd><dt>÷ 最低公开渠道价<small>'+esc(f.vendor)+'</small></dt><dd>'+fmt(f.out)+'</dd><dt class="tot">= 几成</dt><dd class="tot r '+row.band+'">'+pct(row.ratio)+'</dd></dl><div style="margin:16px 0 8px" class="gcell">'+gauge(row.ratio,row.band)+'<span class="pill '+row.band+'">'+LABEL[row.band]+'</span></div><p style="font-size:13px;color:var(--ink-2);margin:0">'+esc((D.label_help||{})[row.band]||"")+'</p><div class="eyebrow" style="margin-top:18px;color:var(--ink-3)">价格走势 · 美元/百万输出</div><canvas class="hist" data-m="'+esc(m.id)+'" data-v="'+esc(row.vendor)+'" height="130" style="width:100%;height:130px;border-radius:12px;background:var(--ground);margin-top:8px;display:block"></canvas><div class="sub" id="histnote"></div><div class="eyebrow" style="margin-top:18px;color:var(--ink-3)">快照 · 正文按哈希存档，永不覆盖</div>'+snapHtml((row.sids||[]).concat([f.sid,D.fx.sid]))+'<div class="disc">'+DISC+'</div>';return h;}
/* 价格走势小图：匿名看最近 7 天，登录看全部；数据文件本身公开 */
var HISTC={};
function drawHist(cv){var m=cv.dataset.m,v=cv.dataset.v;var note=document.getElementById("histnote");
 function T(x){return new Date(x.replace(" ","T")+":00+08:00").getTime();}
 function paint(data){var full=!!(window.__ME&&window.__ME.user);var cut=Date.now()-7*864e5;var ser=(data.vendors||{})[v]||[];var fl=data.floor||[];
  function clip(a){return full?a:a.filter(function(x,i){return T(x[0])>=cut||i===a.length-1;});}
  var S=clip(ser),F=clip(fl);if(!S.length){note.textContent="还没有这一家的历史点。";return;}
  var W=cv.clientWidth||400,Hh=130,d=devicePixelRatio||1;cv.width=W*d;cv.height=Hh*d;var ctx=cv.getContext("2d");ctx.setTransform(d,0,0,d,0,0);
  var all=S.concat(F);var ts=all.map(function(x){return T(x[0]);});var t0=Math.min.apply(null,ts),t1=Math.max(Date.now(),Math.max.apply(null,ts));if(t1-t0<3600e3)t0=t1-864e5;
  var ys=all.map(function(x){return x[1];});var y0=Math.min.apply(null,ys)*0.9,y1=Math.max.apply(null,ys)*1.1||1;
  function X(t){return 40+(T(t)-t0)/(t1-t0)*(W-56);}function Y(p){return 12+(1-(p-y0)/(y1-y0))*(Hh-32);}
  ctx.clearRect(0,0,W,Hh);ctx.strokeStyle="rgba(15,18,34,.08)";ctx.lineWidth=1;for(var i=0;i<4;i++){var yy=12+i*(Hh-32)/3;ctx.beginPath();ctx.moveTo(40,yy);ctx.lineTo(W-12,yy);ctx.stroke();}
  ctx.fillStyle="#9AA0B8";ctx.font="10px JetBrains Mono, monospace";ctx.fillText(y1.toFixed(y1<1?3:2),2,16);ctx.fillText(y0.toFixed(y0<1?3:2),2,Hh-18);
  function line(arr,color,dash){if(!arr.length)return;ctx.beginPath();ctx.setLineDash(dash||[]);ctx.strokeStyle=color;ctx.lineWidth=2;arr.forEach(function(pt,i){var x=X(pt[0]),y=Y(pt[1]);if(i===0)ctx.moveTo(x,y);else{ctx.lineTo(x,Y(arr[i-1][1]));ctx.lineTo(x,y);}});var last=arr[arr.length-1];ctx.lineTo(W-12,Y(last[1]));ctx.stroke();ctx.setLineDash([]);ctx.beginPath();ctx.arc(W-12,Y(last[1]),3.5,0,6.283);ctx.fillStyle=color;ctx.fill();}
  line(F,"#6E56F5",[4,4]);line(S,"#0F1222");
  ctx.fillStyle="#9AA0B8";ctx.fillText(new Date(t0).toISOString().slice(5,10),40,Hh-4);ctx.fillText("今天",W-36,Hh-4);
  note.innerHTML='黑线 = 该站实付 · 紫虚线 = 最低公开参考价 · 记录 '+S.length+' 个变价点'+(full?'（全部历史）':'（最近 7 天，<a href="/api/auth/github/start?return_to='+encodeURIComponent(location.pathname)+'" style="color:var(--p-ink)">登录</a>看全部）');}
 if(HISTC[m]){paint(HISTC[m]);return;}
 fetch(full?"/api/history/"+m:"/history/"+m+".json",{credentials:"include"}).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(j){HISTC[m]=j;paint(j);}).catch(function(){if(full){fetch("/history/"+m+".json").then(function(r){return r.json();}).then(function(j){HISTC[m]=j;paint(j);}).catch(function(){note.textContent="暂无走势数据。";});}else{note.textContent="暂无走势数据。";}});}
var _openD=openD;openD=function(eye,title,html){_openD(eye,title,html);var cv=document.querySelector("#dbody canvas.hist");if(cv)drawHist(cv);};
document.addEventListener("click",function(e){var h=e.target.closest?e.target.closest(".help"):null;if(h){openD("这个标签什么意思",LABEL[h.dataset.help]||"",helpHtml(h.dataset.help));return;}});
/* 搜索 */
(function(){var q=document.getElementById("q");if(!q||!D.site_index)return;var dl=document.getElementById("qlist");D.site_index.forEach(function(s){var o=document.createElement("option");o.value=s.d;dl.appendChild(o);});(D.model_index||[]).forEach(function(m){var o=document.createElement("option");o.value=m.name;dl.appendChild(o);});
q.addEventListener("keydown",function(e){if(e.key!=="Enter")return;var v=q.value.trim().toLowerCase();if(!v)return;var s=D.site_index.filter(function(x){return x.d.indexOf(v)>=0||(x.n||"").toLowerCase().indexOf(v)>=0;})[0];if(s){location.href="/s/"+s.d;return;}var m=(D.model_index||[]).filter(function(x){return x.name.toLowerCase().indexOf(v)>=0||x.id.indexOf(v)>=0;})[0];if(m){location.href="/#m="+m.id;if(location.pathname==="/"||location.pathname==="/index.html")location.reload();return;}openD("没找到",q.value,"<p>既不是收录的站，也不是有报价的模型。试试域名（如 toapis.cn）或模型名（如 DeepSeek V4）。</p>");});})();
/* ========== 登录 · 关注 · 公告 ========== */
(function(){var box=document.getElementById("auth");if(!box)return;var ME=null;
function loginUrl(watch){return "/api/auth/github/start?return_to="+encodeURIComponent(location.pathname+location.search)+(watch?"&watch="+encodeURIComponent(watch):"");}
function render(){if(ME&&ME.user){box.innerHTML='<div class="menu"><a href="/me" style="display:flex;align-items:center;gap:8px">'+(ME.user.avatar_url?'<img src="'+esc(ME.user.avatar_url)+'" alt="">':'')+'<span style="font-size:13px">'+esc(ME.user.handle||"我")+'</span></a><div class="dd"><a href="/me">我的关注</a><a href="/api/auth/logout?return_to='+encodeURIComponent(location.pathname)+'">退出登录</a></div></div>';}
 else if(ME&&ME.login){box.innerHTML='<a class="lang" href="'+loginUrl("")+'">GitHub 登录</a>';}
 else{box.innerHTML='<span class="lang" title="账号系统接入中" style="opacity:.55;cursor:default">登录 · 即将开放</span>';}
 document.querySelectorAll(".watch").forEach(function(b){if(!b.dataset.key)return;var on=!!(ME&&ME.user&&(ME.watches||[]).some(function(w){return w.kind===b.dataset.kind&&w.key===b.dataset.key;}));b.classList.toggle("on",on);b.textContent=on?"已关注 ✓":(b.dataset.kind==="site"?"关注这个站":"关注这个模型");});
 var al=document.getElementById("alerts");if(al){if(!ME||!ME.user){al.textContent="登录后可以开启邮件提醒。";}else{fetch("/api/prefs",{credentials:"include"}).then(function(r){return r.json();}).then(function(p){if(!p.mail_ready){al.textContent="邮件服务接入中。";return;}if(!p.has_email){al.textContent="你的 GitHub 没有可验证的邮箱，暂时无法开启邮件提醒。";return;}var q=new URLSearchParams(location.search).get("alerts");al.innerHTML='<label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer"><input type="checkbox" id="emailon" style="margin-top:3px" '+(p.email_on?'checked':'')+'> <span>'+(q==="off"?"已通过邮件里的链接关闭提醒。勾上可重新开启。":"邮件提醒：关注对象有变动时发到我的 GitHub 邮箱（每天最多一封）")+'</span></label>';document.getElementById("emailon").addEventListener("change",function(e){fetch("/api/prefs",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({email_on:e.target.checked?1:0})}).then(function(r){return r.json();}).then(function(x){al.querySelector("span").textContent=x.ok?(x.email_on?"已开启邮件提醒 ✓ 关注对象有变动时发到你的 GitHub 邮箱":"已关闭邮件提醒"):"保存失败，请刷新重试";});});}).catch(function(){al.textContent="读取设置失败，请刷新。";});}}
 var ml=document.getElementById("melist");if(ml){if(!ME||!ME.user){ml.innerHTML='<h2 class="sec">还没登录</h2><p class="lead">登录后这里是你关注的站和模型。不设密码，GitHub 一键登录。</p>'+(ME&&ME.login?'<a class="btn p" style="margin-top:14px" href="'+loginUrl("")+'">用 GitHub 登录 →</a>':'<div class="callout" style="margin-top:12px">账号系统接入中，开放后即可登录。</div>');}
  else{var ws=ME.watches||[];ml.innerHTML='<h2 class="sec">关注 · '+ws.length+'</h2>'+(ws.length?ws.map(function(w){return '<div class="row"><span class="pill none">'+(w.kind==="site"?"站":"模型")+'</span><a class="dom" href="'+(w.kind==="site"?"/s/"+esc(w.key):"/#m="+esc(w.key))+'">'+esc(w.key)+'</a><button class="evb x watch on" data-kind="'+esc(w.kind)+'" data-key="'+esc(w.key)+'">取消关注</button></div>';}).join(""):'<div class="callout" style="margin-top:12px">还没有关注任何站或模型。到站点页或模型账本点“关注”。</div>');ml.querySelectorAll(".watch").forEach(function(b){b.textContent="取消关注";});}}}
window.__renderAuth=render;
fetch("/api/me",{credentials:"include"}).then(function(r){return r.json();}).then(function(m){ME=m;window.__ME=m;render();}).catch(function(){ME={user:null,login:false};render();});
document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest(".watch"):null;if(!b||!b.dataset.key)return;e.preventDefault();var kind=b.dataset.kind,key=b.dataset.key;
 if(!ME||!ME.user){if(ME&&ME.login){openD("登录后帮你记住它",key,'<p style="font-size:14px;line-height:1.7">登录后这个'+(kind==="site"?"站":"模型")+'会出现在你的关注列表，价格、可达率或探针结果变化时提醒你。不设密码，GitHub 一键登录。</p><a class="btn p" style="margin-top:14px" href="'+loginUrl(kind+":"+key)+'">用 GitHub 登录并关注 →</a><p class="disc">只读取你的 GitHub 公开资料与邮箱，不会代你做任何操作；所有价格数据不登录也全部可见。</p>');}else{openD("账号系统接入中",key,"<p>开放后这里可以一键关注并收到变化提醒。所有价格数据不登录也全部可见。</p>");}return;}
 var on=b.classList.contains("on");fetch("/api/watch",{method:on?"DELETE":"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind:kind,key:key})}).then(function(r){return r.json();}).then(function(){if(on){ME.watches=(ME.watches||[]).filter(function(w){return !(w.kind===kind&&w.key===key);});}else{(ME.watches=ME.watches||[]).push({kind:kind,key:key});}render();});});
fetch("/api/flags").then(function(r){return r.json();}).then(function(f){if(f&&f.MAINTENANCE_BANNER){var d=document.createElement("div");d.className="banner";d.textContent=f.MAINTENANCE_BANNER;var top=document.querySelector(".main .top");top.parentNode.insertBefore(d,top.nextSibling);}}).catch(function(){});})();
/* ========== 首页账本 ========== */
(function(){if(document.body.dataset.page!=="index")return;
var want=(location.hash.match(/m=([^&]+)/)||[])[1]||D.default_model;var cur=D.models.some(function(m){return m.id===want;})?want:D.default_model;
var LEDGER=null;function ensureLedger(cb){if(!D.ledger||D._full){cb();return;}if(!LEDGER){LEDGER=fetch(D.ledger).then(function(r){return r.json();}).then(function(j){var have={};D.models.forEach(function(m){have[m.id]=1;});(j.models||[]).forEach(function(m){if(!have[m.id])D.models.push(m);});D.snaps=D.snaps||{};Object.keys(j.snaps||{}).forEach(function(k){if(!D.snaps[k])D.snaps[k]=j.snaps[k];});D._full=true;}).catch(function(){LEDGER=null;});}LEDGER.then(cb,cb);}
if(cur!==want)ensureLedger(function(){if(D.models.some(function(m){return m.id===want;})){cur=want;render();}});
(window.requestIdleCallback||function(f){setTimeout(f,1500);})(function(){ensureLedger(function(){});});
var cg=document.getElementById("chips");
cg.querySelectorAll(".chip[data-id]").forEach(function(b){b.addEventListener("click",function(){cur=b.dataset.id;history.replaceState(null,"","#m="+cur);ensureLedger(render);});});
var more=document.getElementById("more");if(more)more.addEventListener("click",function(){cg.classList.toggle("all");more.textContent=cg.classList.contains("all")?"收起旧版本":more.dataset.label;});
if(!cg.querySelector('.chip[data-id="'+cur+'"]:not(.old)'))cg.classList.add("all");
function usage(){return {i:+document.getElementById("c-in").value||0,o:+document.getElementById("c-out").value||0};}
function monthly(i,o){var u=usage();if(i==null||o==null)return null;return i*u.i+o*u.o;}
function rowHtml(r,m,i,idx){var mc=monthly(r.in,r.out);var up=r.uptime==null?'<span class="up">—</span>':'<span class="up '+(r.uptime>=90?"good":r.uptime<50?"bad":"")+'">'+r.uptime.toFixed(0)+'%</span>';var held=r.held;
 return '<tr style="--i:'+idx+'"><td><a class="dom" href="/s/'+esc(r.vendor)+'">'+esc(r.vendor)+'</a>'+(r.reg==="closed"?'<span class="pill" style="background:#FDECEC;color:#B42318;margin-left:6px;font-size:10.5px;padding:1px 7px">注册已关</span>':'')+(r.name?'<div class="sub">'+esc(r.name)+'</div>':'')+'</td><td class="num"><span class="big">'+fmt(r.out)+'</span><span class="asf">抓取 '+r.as_of.slice(5,16).replace("T"," ")+'</span></td><td class="num">'+fmt(r.in)+'</td><td class="num">'+(mc==null?"—":"$"+mc.toFixed(mc<10?2:0))+'</td><td style="padding-left:18px">'+(held?'<span class="pill held">计价方式待核 · 不出比率</span>':'<span class="gcell">'+gauge(r.ratio,r.band)+'<span class="r '+r.band+'">'+pct(r.ratio)+'</span></span>')+'</td><td>'+(held?'—':'<span class="pill '+r.band+'">'+LABEL[r.band]+'</span><button class="help" data-help="'+r.band+'" aria-label="解释">?</button>'+probeHtml(r.probe))+'</td><td>'+up+'</td><td class="num"><button class="evb" data-m="'+esc(m.id)+'" data-i="'+i+'">证据 ↗</button></td></tr>';}
var PROBE_TXT={consistent:"探针 · 计数一致 ",divergent:"探针 · 计数与同模型其他渠道不一致 ",no_consensus:"探针 · 已测 ",partial:"探针 · 只成功 ",failed:"探针 · 请求失败 "};
function capHtml(c){if(!c)return "";return '<div class="probe '+({in_line:"consistent",below:"divergent"}[c.status]||"failed")+'">'+"能力抽样 答对 "+c.score+"/"+c.n+(c.median!=null?" · 多渠道中位 "+c.median:" · 中位样本不足")+'</div>';}
function probeHtml(pb){if(!pb)return "";if(pb.status==="cap_only")return capHtml(pb.cap);var t=(PROBE_TXT[pb.status]||"探针 ")+pb.ok+"/"+pb.n+(pb.status==="no_consensus"?"，共识样本不足":"")+(pb.offset?" · 含固定前缀约 "+pb.offset+" token":"")+(pb.echo===false?" · 回显模型名不同":"");return '<div class="probe '+pb.status+'" title="'+esc(D.probe_help||"")+'">'+t+'<span class="pd"> · '+pb.ts.slice(5)+'</span></div>'+capHtml(pb.cap);}
function render(){document.querySelectorAll(".chip[data-id]").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.id===cur?"true":"false");});
 var m=D.models.filter(function(x){return x.id===cur;})[0];if(!m){ensureLedger(render);return;}var tb=document.querySelector("#tbl tbody");var f=m.floor;var fmc=monthly(f.in,f.out);var idx=0;
 tb.innerHTML='<tr class="floor" style="--i:0"><td><div class="dom">'+esc(f.vendor)+'</div><div class="sub">'+(f.cny?"官方定价页 · 人民币折算":"公开市场 · 供应商标价")+'</div></td><td class="num"><span class="big">'+fmt(f.out)+'</span><span class="asf">参考价</span></td><td class="num">'+fmt(f.in)+'</td><td class="num">'+(fmc==null?"—":"$"+fmc.toFixed(fmc<10?2:0))+'</td><td style="padding-left:18px"><span class="gcell">'+gauge(1,"premium")+'<span class="r" style="color:var(--p)">100%</span></span></td><td><span class="pill ref">参考基准</span></td><td>—</td><td class="num"><button class="evb" data-f="'+esc(m.id)+'">证据 ↗</button></td></tr>';
 var main=m.rows.filter(function(r){return !r.held&&["explainable","normal","premium","below_bulk"].indexOf(r.band)>=0;}),un=m.rows.filter(function(r){return !r.held&&r.band==="unsustainable";}),far=m.rows.filter(function(r){return !r.held&&r.band==="far_above";}),held=m.rows.filter(function(r){return r.held;});
 main.forEach(function(r){idx++;tb.insertAdjacentHTML("beforeend",rowHtml(r,m,m.rows.indexOf(r),idx));});
 var folds=document.getElementById("folds");folds.innerHTML="";
 function fold(title,rows){if(!rows.length)return;var d=document.createElement("details");d.className="fold";d.innerHTML='<summary>'+title+'</summary><div class="tablewrap"><table><tbody>'+rows.map(function(r,j){return rowHtml(r,m,m.rows.indexOf(r),j);}).join("")+'</tbody></table></div>';d.addEventListener("toggle",function(){settleNeedles(d);});folds.appendChild(d);}
 fold('另有 <b>'+un.length+'</b> 家实付低于该模型的成本下限（最低 '+pct(Math.min.apply(null,un.map(function(r){return r.ratio;}).concat([1])))+'）· 本站不推测成因，展开看',un);
 fold(far.length+' 家显著高于公开价',far);fold(held.length+' 家计价方式待核，只列名义报价',held);
 var mw=document.getElementById("mwatch");if(mw){mw.dataset.key=m.id;if(window.__renderAuth)window.__renderAuth();}
 document.getElementById("tfoot").innerHTML='<span><b>'+esc(m.name)+'</b> 参考价 '+esc(f.vendor)+' $'+fmt(f.out)+' / 百万输出</span><span>中转站 '+m.rows.length+' 家：说得通 '+main.length+' · 低于成本下限 '+un.length+' · 待核 '+held.length+'</span><span>'+DISC+'</span>';
 settleNeedles(tb);}
render();["c-in","c-out"].forEach(function(id){document.getElementById(id).addEventListener("input",render);});
document.querySelectorAll(".calc .pre").forEach(function(b){b.addEventListener("click",function(){document.getElementById("c-in").value=b.dataset.i;document.getElementById("c-out").value=b.dataset.o;render();});});
document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest(".evb"):null;if(!b)return;var m=D.models.filter(function(x){return x.id===(b.dataset.m||b.dataset.f);})[0];if(!m)return;
 if(b.dataset.f){openD("证据链",m.floor.vendor+" · "+m.name+" · 参考价 $"+fmt(m.floor.out)+"/百万输出",'<dl class="kv"><dt>类型</dt><dd>'+(m.floor.cny?"官方（人民币折算）":"公开市场")+'</dd></dl>'+snapHtml([m.floor.sid].concat(m.floor.cny?[D.fx.sid]:[])));return;}
 var r=m.rows[+b.dataset.i];openD("证据链",r.vendor+" · "+m.name+" · 实付 $"+fmt(r.out)+"/百万输出",relayEvidence(r,m));});
var kp=document.querySelectorAll("[data-count]");kp.forEach(function(el){countUp(el,+el.dataset.count,el.dataset.suffix||"");});
/* 卡片倾斜 */
if(!reduce&&matchMedia("(hover:hover)").matches){var bento=document.getElementById("bento");if(bento){bento.addEventListener("pointermove",function(e){var t=e.target.closest(".tile");if(!t)return;var b=t.getBoundingClientRect(),x=(e.clientX-b.left)/b.width-.5,y=(e.clientY-b.top)/b.height-.5;t.style.transform="perspective(700px) rotateX("+(-y*7)+"deg) rotateY("+(x*9)+"deg) translateY(-3px)";});bento.addEventListener("pointerout",function(e){var t=e.target.closest(".tile");if(t)t.style.transform="";});}}
})();
/* ========== 站点页 ========== */
(function(){if(document.body.dataset.page!=="site")return;var S=D.site;
document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest(".evb"):null;if(!b)return;var r=S.models[+b.dataset.i];var h='<dl class="kv"><dt>模型</dt><dd style="font-family:inherit">'+esc(r.name)+'</dd><dt>站内原名</dt><dd>'+esc(r.raw)+'</dd><dt>实付</dt><dd>'+(r.out!=null?fmt(r.out)+" $/百万输出":r.call!=null?fmt(r.call)+" $/次":r.sec!=null?fmt(r.sec)+" $/秒":"—")+'</dd>'+(r.floor_out&&!S.held?'<dt>最低公开渠道价<small>'+esc(r.floor_vendor||"")+'</small></dt><dd>'+fmt(r.floor_out)+'</dd><dt class="tot">= 几成</dt><dd class="tot r '+r.band+'">'+pct(r.ratio)+'</dd>':'')+'</dl>'+(r.band&&!S.held?'<div style="margin:16px 0 8px" class="gcell">'+gauge(r.ratio,r.band)+'<span class="pill '+r.band+'">'+LABEL[r.band]+'</span></div><p style="font-size:13px;color:var(--ink-2);margin:0">'+esc((D.label_help||{})[r.band]||"")+'</p>':'')+'<div class="eyebrow" style="margin-top:18px;color:var(--ink-3)">快照</div>'+snapHtml(r.sids)+'<div class="disc">'+DISC+'</div>';openD("证据链",S.domain+" · "+r.name,h);});
settleNeedles(document);})();
/* ========== 站点总表筛选 ========== */
(function(){if(document.body.dataset.page!=="sites")return;var filt=(location.hash.match(/c=([a-z]+)/)||[])[1]||"all",onlyQ=true;var rows=Array.from(document.querySelectorAll("#sitetbl tbody tr"));
function apply(){document.querySelectorAll(".fchip[data-f]").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.f===filt?"true":"false");});var n=0;rows.forEach(function(r){var ok=(filt==="all"||r.dataset.cl===filt)&&(!onlyQ||+r.dataset.nm>0);r.style.display=ok?"":"none";if(ok)n++;});document.getElementById("sitefoot").textContent="显示 "+n+" / "+rows.length+" 站";}
document.querySelectorAll(".fchip[data-f]").forEach(function(b){b.addEventListener("click",function(){filt=b.dataset.f;history.replaceState(null,"","#c="+filt);apply();});});
var tg=document.getElementById("tg");tg.addEventListener("click",function(){onlyQ=!onlyQ;tg.setAttribute("aria-pressed",onlyQ?"false":"true");apply();});apply();})();
/* ========== 媒体 ========== */
(function(){var fams=document.getElementById("fams");if(!fams)return;var M=null;
function pctm(r){return pct(r);}
function famHtml(f,mod,i){var ref=f.ref;var rec=(f.rows||[]).filter(function(r){return r.recent&&!r.held;});var range=(f.eff_min!=null&&f.eff_max!=null&&ref)?[f.eff_min/ref.price,f.eff_max/ref.price]:null;
 var h='<div class="fam rise" style="--i:'+(i*0.6)+'"><div class="name"><span class="cube"></span><a href="/media/'+esc(f.family)+'">'+esc(f.name||f.family||f.vendor)+'</a>'+(f.recent_labels&&f.recent_labels.length?'<span class="sub" style="margin:0 0 0 auto">主推 '+esc(f.recent_labels.join(" · "))+'</span>':'')+'</div>';
 if(ref)h+='<div class="ref">$'+ref.price.toFixed(3)+'<small>/ '+(mod==="video"?"秒":"张")+' 官方 · '+esc(ref.model)+'</small></div><div class="meta">'+f.n_sites+' 站 · '+f.n_rows+' 条报价'+(mod==="video"&&f.default_clip?' · 按次折算假设 1 次 = '+f.default_clip+' 秒':'')+'</div>';
 else h+='<div class="none">无官方参考价，只列报价，不出比率。'+esc(f.ref_missing||"")+'</div><div class="meta">'+f.n_sites+' 站 · '+f.n_rows+' 条报价</div>';
 if(range){var lo=Math.min(2,range[0])/2*100,hi=Math.min(2,range[1])/2*100;h+='<div class="rng"><i style="left:'+lo.toFixed(1)+'%;width:'+Math.max(2,hi-lo).toFixed(1)+'%"></i></div><div class="rl"><span>实付最低 '+pctm(range[0])+'</span><span>最高 '+pctm(range[1])+'</span></div>';}
 if(rec.length){h+='<table><thead><tr><th>站</th><th class="num">实付</th><th class="num">几成</th></tr></thead><tbody>'+rec.slice(0,6).map(function(r){return '<tr><td><a class="dom" href="/s/'+esc(r.site)+'">'+esc(r.site)+'</a></td><td class="num">'+(r.eff!=null?r.eff.toFixed(3):"—")+' <span class="sub" style="display:inline">'+(r.unit==="per_second"?"$/秒":"$/次")+'</span></td><td class="num">'+(r.ratio!=null?'<span class="r '+r.band+'">'+pctm(r.ratio)+'</span>':'—')+'</td></tr>';}).join("")+'</tbody></table>'+(rec.length>6?'<div class="sub">还有 '+(rec.length-6)+' 条 · 数据文件 media.json</div>':'');}
 h+='</div>';return h;}
function renderMedia(mod){var list=(M&&M[mod])||[];fams.innerHTML=list.map(function(f,i){return famHtml(f,mod,i);}).join("")||'<div class="callout">暂无数据</div>';}
var seg=document.getElementById("seg");function moveInd(){var b=seg.querySelector("[aria-pressed=true]"),i=seg.querySelector(".ind");if(!b)return;i.style.left=b.offsetLeft+"px";i.style.width=b.offsetWidth+"px";}
seg.addEventListener("click",function(e){var b=e.target.closest("button");if(!b)return;seg.querySelectorAll("button").forEach(function(x){x.setAttribute("aria-pressed",x===b?"true":"false");});moveInd();renderMedia(b.dataset.m);});
fetch("/media.json").then(function(r){return r.json();}).then(function(m){M=m;Object.keys(m.snaps||{}).forEach(function(k){D.snaps=D.snaps||{};if(!D.snaps[k])D.snaps[k]=m.snaps[k];});var a=document.getElementById("mediaasof");if(a)a.textContent="数据 "+m.generated_at.slice(0,16).replace("T"," ");renderMedia("video");requestAnimationFrame(moveInd);}).catch(function(){fams.innerHTML='<div class="callout">数据加载失败，请刷新。</div>';});
addEventListener("resize",moveInd);})();
"""

# ------------------------------------------------------------------ 地球（首页 hero）
EARTH_JS = r"""
(function(){var cv=document.getElementById("gl");if(!cv)return;var gl=cv.getContext("webgl2",{alpha:true,antialias:false,premultipliedAlpha:true});if(!gl){cv.remove();return;}
var reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
var vs="#version 300 es\nin vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
var fs=["#version 300 es","precision highp float;out vec4 O;uniform vec2 R;uniform float T;uniform vec2 M;uniform float S;uniform float HC;uniform sampler2D D;uniform sampler2D N;uniform sampler2D C;",
"mat2 rot(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}",
"vec2 isph(vec3 ro,vec3 rd,float r){float b=dot(ro,rd);float c=dot(ro,ro)-r*r;float h=b*b-c;if(h<0.)return vec2(-1.);h=sqrt(h);return vec2(-b-h,-b+h);}",
"float hash(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}",
"float noise(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}",
"float fbm(vec3 p){float a=.5,s=0.;for(int i=0;i<6;i++){s+=a*noise(p);p=p*2.07+vec3(1.7,9.2,3.1);a*=.52;}return s;}",
"vec3 geo(vec3 n){vec3 q=n;q.xy*=rot(-.41);q.xz*=rot(-(T*.012+S)-2.6);return q;}",
"vec2 equi(vec3 q){return vec2(atan(q.z,q.x)/6.28318+.5,asin(clamp(q.y,-1.,1.))/3.14159+.5);}",
"float clouds(vec3 q){if(HC>.5){vec2 uv=equi(q);uv.x+=T*.0015;float c=texture(C,uv).r;return smoothstep(.08,.85,c);}",
" vec3 w=q*2.2;w.xz*=rot(T*.004);vec3 warp=vec3(fbm(w*2.4),fbm(w*2.4+vec3(5.2,1.3,7.7)),0.)*.9;float f=fbm(w*1.5+warp);float band=.85+.15*sin(q.y*9.);return smoothstep(.47,.74,f*band+.02);}",
"void main(){vec2 uv=(gl_FragCoord.xy-.5*R)/R.y;",
" float pitch=.78+(M.y-.5)*.05,yaw=(M.x-.5)*.06,roll=.10;",
" vec3 ro=vec3(0.,0.,1.36);vec3 f=vec3(0.,sin(pitch),-cos(pitch));f.xz*=rot(yaw);",
" vec3 rgt=normalize(cross(f,vec3(0.,1.,0.)));vec3 up=cross(rgt,f);mat2 rr=rot(roll);vec2 u2=rr*uv;",
" vec3 rd=normalize(f*1.55+u2.x*rgt+u2.y*up);",
" vec3 L=normalize(vec3(-.45,.5,.8));",
" float RA=1.09;vec2 ta=isph(ro,rd,RA);if(ta.y<0.){O=vec4(0.);return;}vec2 tg=isph(ro,rd,1.0);bool ground=tg.x>0.;",
" float t0=max(ta.x,0.),t1=ground?tg.x:ta.y;",
" vec3 col=vec3(0.);float alpha=0.;",
" float bcl=dot(-ro,rd);float dc=length(ro+rd*bcl);float pxs=bcl/(R.y*1.55);float cov=clamp((1.0-dc)/pxs+.5,0.,1.);",
" if(ground){vec3 p=ro+rd*tg.x;vec3 n=p;vec3 q=geo(n);vec2 tuv=equi(q);",
"  vec3 dpx=dFdx(q),dpy=dFdy(q);vec2 gx=vec2(length(dpx)/6.28318,length(dpx)/3.14159),gy=vec2(length(dpy)/6.28318,length(dpy)/3.14159);",
"  vec3 day=pow(textureGrad(D,tuv,gx,gy).rgb,vec3(2.2));vec3 night=pow(textureGrad(N,tuv,gx,gy).rgb,vec3(2.2));",
"  float ndl=dot(n,L);float lit=clamp(ndl,0.,1.);float dayl=smoothstep(-.06,.2,ndl);",
"  float ocean=smoothstep(.015,.12,day.b-max(day.r,day.g));",
"  vec3 hv=normalize(L-rd);float spec=pow(clamp(dot(n,hv),0.,1.),220.)*ocean*dayl;float sheen=pow(clamp(dot(n,hv),0.,1.),10.)*ocean*dayl*.07;",
"  float fresO=pow(1.-clamp(dot(n,-rd),0.,1.),4.)*ocean;",
"  float cl=clouds(q);vec3 qs=geo(normalize(n+L*.03));float cls=clouds(qs);float clsh=cls;",
"  float cshade=clamp(1.+(cls-cl)*1.6,.55,1.35);",
"  vec3 g=mix(day,day*vec3(.55,.95,1.55)+vec3(0.,.02,.09),ocean)*(1.-clsh*.55);",
"  vec3 dayc=g*(lit*2.1+.02)+vec3(1.,.95,.85)*spec*1.8+vec3(.6,.75,1.)*sheen*2.+vec3(.35,.55,1.)*fresO*lit*.35;",
"  float twi=smoothstep(.22,0.,ndl)*smoothstep(-.12,.02,ndl);dayc+=vec3(1.,.45,.15)*twi*.12*(1.-cl);",
"  vec3 cloudc=mix(vec3(.62,.7,.9),vec3(1.),cshade*lit)*(lit*1.95+.03);cloudc+=vec3(1.,.5,.2)*twi*.25;",
"  float clv=cl*cl*.85+cl*.15;dayc=mix(dayc,cloudc,clv);",
"  vec3 nightc=night*vec3(1.,.72,.42)*2.4*(1.-cl*.85)+g*vec3(.5,.62,1.)*.028+vec3(.5,.6,1.)*cl*.02;",
"  col=dayc*dayl+nightc*(1.-dayl);alpha=1.;}",
" const int NS=14;float st=(t1-t0)/float(NS);vec3 sc=vec3(0.);float od=0.;",
" vec3 ray=vec3(.22,.48,1.0);vec3 low=vec3(.78,.86,1.);vec3 warm=vec3(1.,.42,.16);float mie=pow(clamp(dot(rd,L),0.,1.),14.)*.35;",
" for(int i=0;i<NS;i++){float t=t0+st*(float(i)+.5);vec3 p=ro+rd*t;float hgt=length(p)-1.;float dens=exp(-hgt/.024)*st;",
"  float mu=dot(normalize(p),L);float sun=clamp(mu*1.4+.32,0.,1.);sun*=sun;od+=dens;float tw=smoothstep(.35,-.05,mu)*smoothstep(-.3,-.02,mu);",
"  vec3 c=mix(ray,low,exp(-hgt/.011)*.7);c=mix(c,warm,tw*.55);sc+=dens*exp(-od*7.)*sun*(c+mie*vec3(1.,.9,.8));}",
" vec3 scat=sc*30.;float tr=exp(-od*4.);",
" float aA=clamp(1.-exp(-od*9.),0.,1.)*clamp(length(scat)*4.,0.,1.);",
" if(ground){vec3 gc=col*mix(1.,tr,.6)+scat;col=mix(scat,gc,cov);alpha=mix(aA,1.,cov);}else{col=scat;alpha=aA;}",
" col=1.-exp(-col*1.1);col=pow(col,vec3(.4545));col=mix(col,col*col*(3.-2.*col),.25);",
" O=vec4(col*alpha,alpha);}"].join("\n");
function sh(t,s){var o=gl.createShader(t);gl.shaderSource(o,s);gl.compileShader(o);if(!gl.getShaderParameter(o,gl.COMPILE_STATUS)){console.warn(gl.getShaderInfoLog(o));}return o;}
var pr=gl.createProgram();gl.attachShader(pr,sh(gl.VERTEX_SHADER,vs));gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(pr);if(!gl.getProgramParameter(pr,gl.LINK_STATUS)){console.warn(gl.getProgramInfoLog(pr));return;}gl.useProgram(pr);
var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);var pl=gl.getAttribLocation(pr,"p");gl.enableVertexAttribArray(pl);gl.vertexAttribPointer(pl,2,gl.FLOAT,false,0,0);
var U={};["R","T","M","S","HC","D","N","C"].forEach(function(k){U[k]=gl.getUniformLocation(pr,k);});gl.uniform1i(U.D,0);gl.uniform1i(U.N,1);gl.uniform1i(U.C,2);gl.uniform1f(U.HC,0);
var need=3,loaded=0,ready=false;function tex(unit,src,onl){var im=new Image();im.onload=function(){var t=gl.createTexture();gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,im);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.generateMipmap(gl.TEXTURE_2D);var ext=gl.getExtension("EXT_texture_filter_anisotropic");if(ext)gl.texParameterf(gl.TEXTURE_2D,ext.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(8,gl.getParameter(ext.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));if(onl)onl();loaded++;if(loaded>=need)ready=true;};im.onerror=function(){loaded++;if(loaded>=need)ready=true;};im.src=src;}
tex(0,"/img/earth_day.jpg");tex(1,"/img/earth_night.jpg");tex(2,"/img/earth_cloud.jpg",function(){gl.uniform1f(U.HC,1);});
var mx=.5,my=.5,tx=.5,ty=.5,spin=0,vel=0,drag=null;addEventListener("pointermove",function(e){tx=e.clientX/innerWidth;ty=1-e.clientY/innerHeight;if(drag){var dx=e.clientX-drag.x;drag.x=e.clientX;vel=dx*.0035;spin+=vel;}});
cv.addEventListener("pointerdown",function(e){drag={x:e.clientX};cv.setPointerCapture(e.pointerId);});cv.addEventListener("pointerup",function(){drag=null;});cv.addEventListener("pointercancel",function(){drag=null;});
function size(){var b=cv.getBoundingClientRect();var s=Math.min(devicePixelRatio||1,1.5,1400/Math.max(1,b.width));cv.width=Math.max(2,b.width*s|0);cv.height=Math.max(2,b.height*s|0);gl.viewport(0,0,cv.width,cv.height);}size();addEventListener("resize",size);
var t0=performance.now(),vis=true;new IntersectionObserver(function(es){vis=es[0].isIntersecting;}).observe(cv);
function frame(t){if(vis&&ready){mx+=(tx-mx)*.05;my+=(ty-my)*.05;if(!drag){spin+=vel;vel*=.94;}gl.uniform2f(U.R,cv.width,cv.height);gl.uniform1f(U.T,reduce?0:(t-t0)/1000);gl.uniform2f(U.M,mx,my);gl.uniform1f(U.S,spin);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);}requestAnimationFrame(frame);}requestAnimationFrame(frame);})();
/* 星空 */
(function(){var cv=document.getElementById("stars");if(!cv)return;var hero=cv.parentNode;var ctx=cv.getContext("2d");if(!ctx)return;var W,Hh,S=[];var reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
function size(){var b=hero.getBoundingClientRect(),d=Math.min(2,devicePixelRatio||1);W=b.width;Hh=b.height;cv.width=W*d;cv.height=Hh*d;ctx.setTransform(d,0,0,d,0,0);S=[];var n=Math.round(W*Hh/3800);for(var i=0;i<n;i++){S.push({x:Math.random(),y:Math.random(),z:.3+Math.random()*.7,s:.35+Math.random()*1.1,tw:Math.random()*6.28,sp:.6+Math.random()*1.6,c:Math.random()<.12?"200,215,255":Math.random()<.06?"255,225,190":"255,255,255"});}}
size();addEventListener("resize",size);var mx=0,my=0;addEventListener("pointermove",function(e){mx=e.clientX/innerWidth-.5;my=e.clientY/innerHeight-.5;});var px=0,py=0;
function frame(t){px+=(mx-px)*.04;py+=(my-py)*.04;ctx.clearRect(0,0,W,Hh);var tm=t/1000;for(var i=0;i<S.length;i++){var s=S[i];var x=s.x*W-px*14*s.z,y=s.y*Hh-py*10*s.z;var a=(.35+.65*(.5+.5*Math.sin(tm*s.sp+s.tw)))*s.z;ctx.fillStyle="rgba("+s.c+","+a.toFixed(3)+")";ctx.beginPath();ctx.arc(x,y,s.s,0,6.283);ctx.fill();if(s.s>1.25&&a>.8){ctx.fillStyle="rgba("+s.c+","+(a*.35).toFixed(3)+")";ctx.fillRect(x-s.s*3,y-.4,s.s*6,.8);ctx.fillRect(x-.4,y-s.s*3,.8,s.s*6);}}if(!reduce)requestAnimationFrame(frame);}
requestAnimationFrame(frame);})();
"""

# ------------------------------------------------------------------ 页面骨架
ICONS = {
    "home": '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    "sites": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "media": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3z"/>',
    "rank": '<path d="M8 21h8M12 17v4M6 3h12v5a6 6 0 0 1-12 0z"/><path d="M6 5H3v2a3 3 0 0 0 3 3M18 5h3v2a3 3 0 0 1-3 3"/>',
    "check": '<path d="M9 12l2 2 4-4"/><circle cx="12" cy="12" r="9"/>',
    "method": '<path d="M4 6h16M4 12h10M4 18h7"/>',
    "data": '<path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="9"/>',
}

import hashlib as _hl
def _asset_v():
    return _hl.sha1((CSS + APP_JS + EARTH_JS).encode("utf-8")).hexdigest()[:10]

def shell(title, desc, path, body, active="", page="", crumbs=None, extra_head="", scripts="", og_image="/img/og.png", jsonld=None):
    st = D["stats"]
    canonical = BASE + path
    nav = "".join('<a class="nav%s" href="%s"><svg viewBox="0 0 24 24">%s</svg>%s%s</a>' % (" on" if active == k else "", h, ICONS[k], lbl, ('<span class="badge">%s</span>' % b) if b else "")
                  for k, h, lbl, b in [("home", "/", "模型账本", str(len(D["models"]))), ("sites", "/sites", "中转站", str(st["confirmed"])), ("media", "/media", "图像 · 视频", ""), ("rank", "/rank", "司南榜", ""), ("check", "/check", "用我的 Key 测", "")])
    nav2 = "".join('<a class="nav%s" href="%s"><svg viewBox="0 0 24 24">%s</svg>%s</a>' % (" on" if active == k else "", h, ICONS[k], lbl)
                   for k, h, lbl in [("method", "/method", "口径与定义"), ("data", "/method#data", "开放数据")])
    crumb = '<div class="crumb"><a href="https://sinanlab.com">← 司南实验室</a>%s</div>' % "".join(" › " + ('<a href="%s">%s</a>' % (c[1], esc(c[0])) if len(c) > 1 and c[1] else esc(c[0])) for c in (crumbs or []))
    head = tpl(u"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{title}}</title><meta name="description" content="{{desc}}"><link rel="canonical" href="{{canonical}}"><meta property="og:site_name" content="Sinan Compute"><meta property="og:type" content="website"><meta property="og:title" content="{{title}}"><meta property="og:description" content="{{desc}}"><meta property="og:url" content="{{canonical}}"><meta property="og:image" content="{{og}}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{{og}}">{{ld}}<meta name="theme-color" content="#040611"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="sitemap" href="/sitemap.xml"><link rel="stylesheet" href="/assets/app.css?v={{v}}">{{extra}}</head><body data-page="{{page}}">""",
               title=esc(title), desc=esc(desc), canonical=canonical, v=_asset_v(), extra=extra_head, page=page, og=BASE + og_image,
               ld=("".join('<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False).replace("</", "<\\/") for x in (jsonld or []))))
    search = '<label class="search"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9AA0B8" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="q" placeholder="查一个站（toapis.cn）或一个模型（DeepSeek V4），回车" list="qlist"><datalist id="qlist"></datalist><kbd>/</kbd></label>'
    asof = '<div class="asof"><i></i><span>数据 %s · USD/CNY %.2f</span></div>' % (D["generated_at"][:16].replace("T", " "), D["fx"]["rate"])
    footer = u"""<footer class="ft"><div class="in"><span>© 2026 Sinan Lab · 司南实验室</span><a href="https://sinanlab.com/constitution">为什么可信</a><a href="https://sinanlab.com/disclosure">收入透明</a><a href="https://github.com/sinanlabs/compute" rel="noopener">GitHub</a><a href="https://sinanlab.com/privacy">隐私政策</a><a href="https://sinanlab.com/disclaimer">免责声明</a><a href="/method">方法论</a><a href="/method#data">数据下载</a><a href="https://sinanlab.com/">母站 sinanlab.com</a><a href="mailto:hello@sinanlab.com">hello@sinanlab.com</a><span style="margin-left:auto">每个数字可追溯来源 · 不收任何被测渠道的钱</span></div></footer>"""
    drawer = u"""<div class="scrim" id="scrim"></div><aside class="drawer" id="drawer" role="dialog" aria-modal="true"><button class="x" id="dx" aria-label="关闭">×</button><div class="eyebrow" id="deye" style="color:var(--p)">证据链</div><h3 id="dtitle"></h3><div id="dbody"></div></aside>"""
    rail = tpl(u"""<aside class="rail"><a class="brand" href="/"><span class="mark"></span><div><b>Sinan Compute</b><small>司南·算力 · SINAN LAB</small></div></a><div class="sect">测量</div>{{nav}}<div class="sect">底层</div>{{nav2}}<a class="robo" href="https://robo.sinanlab.com"><span class="gl"></span><b>Sinan Robo</b><p>开源具身模型的可审计索引</p></a></aside>""", nav=nav, nav2=nav2)
    return head + '<div class="app">' + rail + '<div class="main"><div class="top">' + (search if page != "index" else search) + asof + '<div class="auth" id="auth"></div></div>' + (crumb if crumbs else "") + body + footer + '</div></div>' + drawer + '<script src="/assets/app.js?v=%s" defer></script>%s</body></html>' % (GEN_DATE.replace("-", ""), scripts)

# ------------------------------------------------------------------ 首页
def gauge_html(ratio, band):
    left = max(0, min(2, 1 if ratio is None else ratio)) / 2 * 100
    return '<span class="gauge"><span class="mid"></span><span class="nd" data-left="%.2f" style="--c:%s;left:%.2f%%"></span></span>' % (left, BANDC.get(band, "#6E56F5"), left)

def ssr_ledger_rows(m):
    """服务端渲染默认模型的主表（无 JS 也能看）。"""
    f = m["floor"]
    out = ['<tr class="floor"><td><div class="dom">%s</div><div class="sub">%s</div></td><td class="num"><span class="big">%s</span><span class="asf">参考价</span></td><td class="num">%s</td><td class="num">—</td><td style="padding-left:18px"><span class="gcell">%s<span class="r" style="color:var(--p)">100%%</span></span></td><td><span class="pill ref">参考基准</span></td><td>—</td><td class="num"></td></tr>'
           % (esc(f["vendor"]), "官方定价页 · 人民币折算" if f.get("cny") else "公开市场 · 供应商标价", fmt(f["out"]), fmt(f["in"]), gauge_html(1, "premium"))]
    for r in [x for x in m["rows"] if not x["held"] and x["band"] in ("explainable", "normal", "premium", "below_bulk")]:
        up = "—" if r["uptime"] is None else '<span class="up %s">%.0f%%</span>' % ("good" if r["uptime"] >= 90 else "bad" if r["uptime"] < 50 else "", r["uptime"])
        out.append('<tr><td><a class="dom" href="/s/%s">%s</a>%s</td><td class="num"><span class="big">%s</span><span class="asf">抓取 %s</span></td><td class="num">%s</td><td class="num">—</td><td style="padding-left:18px"><span class="gcell">%s<span class="r %s">%s</span></span></td><td><span class="pill %s">%s</span></td><td>%s</td><td class="num"></td></tr>'
                   % (esc(r["vendor"]), esc(r["vendor"]), ('<div class="sub">%s</div>' % esc(r["name"])) if r.get("name") else "", fmt(r["out"]), r["as_of"][5:16].replace("T", " "), fmt(r["in"]), gauge_html(r["ratio"], r["band"]), r["band"], pct(r["ratio"]), r["band"], LABEL[r["band"]], up))
    return "".join(out)

def build_index():
    st = D["stats"]; C = st["clusters"]; prof = C["ultra"] + C["cheap"] + C["near"] + C["high"]
    default = next((m["id"] for m in D["models"] if m["is_latest"] and m["n_relay"] >= 20), D["models"][0]["id"])
    dm = next(m for m in D["models"] if m["id"] == default)
    # 芯片：按厂商分组，最新两代默认显示，其余折叠
    chips = []
    for v, ids in D["groups"].items():
        chips.append('<span class="vn">%s</span>' % esc(D["vendor_name"].get(v, v)))
        for mid in ids:
            m = next((x for x in D["models"] if x["id"] == mid), None)
            if not m: continue
            chips.append('<button class="chip%s" data-id="%s" aria-pressed="%s">%s<span class="n">%d 家</span></button>' % ("" if m["is_latest"] else " old", esc(m["id"]), "true" if m["id"] == default else "false", esc(m["name"]), m["n_relay"]))
    n_old = sum(1 for m in D["models"] if not m["is_latest"])
    if n_old: chips.append('<button class="chip more" id="more" data-label="展开 %d 个旧版本">展开 %d 个旧版本</button>' % (n_old, n_old))
    changes = D.get("changes", [])[:8]
    feed = []
    if D.get("new_sites"): feed.append(('今日', '新收录 <b>%d</b> 个站' % len(D["new_sites"]), '全部经面板指纹确认 · <a href="/sites" style="color:var(--p-ink)">看站点总表</a>'))
    for c in changes: feed.append((c["t"][5:16].replace("T", " "), '%s · %s <span class="old">%s</span> → <span class="new">%s</span>%s' % (esc(c["vendor"]), esc(c["model"]), fmt(c["old"]), fmt(c["new"]), " ↑" if c["new"] > c["old"] else " ↓"), ("中转站名义价" if c["kind"] == "relay" else "公开参考价") + " $/百万输出"))
    if not feed: feed.append((GEN_DATE[5:], "今天没有价格变动", "变更需连续两次抓取一致才发布"))
    feed_html = "".join('<div class="row"><div class="t">%s</div><div><div>%s</div><div class="sub">%s</div></div></div>' % f for f in feed)
    tiles = [("ultra", "超低价", C["ultra"], "实付中位数不到公开价的 15%"), ("cheap", "低于批量折扣", C["cheap"], "15% – 40%"), ("near", "与公开价接近", C["near"], "40% – 125%，相当于按官方价转售"), ("high", "高于公开价 / 待核", C["high"] + C["held"], "≥125%，或计价方式待核实不出比率")]
    tiles_html = "".join('<a class="card tile %s" href="/sites#c=%s"><span class="orb"></span><div class="v"><span data-count="%d">%d</span></div><div class="k">%s</div><div class="n">%s</div><span class="go">→</span></a>' % (code, code, n, n, name, note) for code, name, n, note in tiles)
    kpis = [
        ("已确认中转站", '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M4 12h16"/></svg>', st["confirmed"], "", "24h 可达 %d 站 · 全部由面板指纹确认" % st["reachable"], None),
        ("有实付报价的站", '<svg viewBox="0 0 24 24"><path d="M4 18l5-6 4 3 7-9"/></svg>', st["with_quotes"], "", "%s 条报价 · 对上参考价的进入比率" % format(st["quotes"], ","), None),
        ("实付不到公开价 15% 的站", '<svg viewBox="0 0 24 24"><path d="M5 21V4h11l-1 4h4l-2 6H8"/></svg>', C["ultra"], " / %d" % prof, "", "dist"),
        ("计价方式待核的站", '<svg viewBox="0 0 24 24"><path d="M12 8v5M12 16h.01"/><circle cx="12" cy="12" r="9"/></svg>', C["held"], "", "只列名义报价，不出比率", None),
    ]
    kpi_html = ""
    for i, (k, ico, v, suf, n, kind) in enumerate(kpis):
        body = ('<div class="dist">%s</div><div class="legend">%s</div>' % ("".join('<i class="c-%s" style="flex:%d"></i>' % (c, C[c]) for c in ("ultra", "cheap", "near", "high", "held")),
                 "".join('<span style="--c:%s">%s %d</span>' % (col, nm, C[c]) for c, nm, col in (("ultra", "超低价", "var(--crit)"), ("cheap", "低于折扣", "var(--warn)"), ("near", "接近", "var(--good)"), ("high", "高于", "var(--p)"), ("held", "待核", "var(--hair-2)"))))) if kind == "dist" else '<div class="n">%s</div>' % n
        kpi_html += '<div class="card kpi rise" style="--i:%s"><div class="k"><i>%s</i>%s</div><div class="v"><span data-count="%d">%d</span>%s</div>%s</div>' % (2 + i * 0.5, ico, k, v, v, ('<small>%s</small>' % suf) if suf else "", body)
    # 首页 HTML 只内联默认模型（约 30 KB）；40 个模型的全量账本放 assets/ledger.json，浏览器空闲时或点到别的模型时再取
    dml = [m for m in D["models"] if m["id"] == default]
    sids = {D["fx"]["sid"]}
    for m in dml:
        sids.add(m["floor"]["sid"])
        for r in m["rows"]: sids.update(r["sids"])
    light = {"models": dml, "fx": D["fx"], "snaps": {k: v for k, v in D["snaps"].items() if int(k) in sids}, "label_help": D["label_help"], "default_model": default,
             "probe_help": D.get("probe_help", ""), "ledger": "/assets/ledger.json?v=%s" % GEN_DATE.replace("-", ""),
             "site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}
    body = tpl(u"""
<section class="hero rise" style="--i:1"><canvas class="stars" id="stars"></canvas><canvas id="gl"></canvas><div class="scrim"></div>
<div class="txt"><div class="eyebrow">官方价 · 公开市场 · 中转站实付 · 逐条算成比率</div><h1>看清算力，<br>才好买算力。</h1>
<p>我们把 <span class="mono">{{n}}</span> 个中转站的实付价，对着官方与公开市场价逐条算成比率。每个数字都能点开看抓取快照。不收任何被测渠道的钱，也不替你判断。</p>
<div class="cta"><a class="btn w" href="#ledger">查一个模型</a><a class="btn g" href="/sites">查一个中转站</a></div></div>
<div class="stat"><b data-count="{{quotes_raw}}">{{quotes}}</b><small>条实付报价 · 24h 内</small></div><div class="tag">地球影像 NASA BLUE MARBLE · BLACK MARBLE<br>实时大气散射 · 拖动转动地球</div></section>
<div class="kpis">{{kpis}}</div>
<section class="card ledger rise" id="ledger" style="--i:4">
<div class="lh"><div><h2 class="sec">模型实付账本</h2><p class="lead">先点一个模型，下面的表就换成它。输出价按 $/百万 token；中转价已按人民币充值通道折成实付；参考价取官方与公开市场的最低价。</p></div>
<button class="btn o watch" id="mwatch" data-kind="model" data-key="" style="height:36px;margin-left:auto">关注这个模型</button><div class="calc" style="margin-left:0">按你的用量估月费：输入 <input id="c-in" value="5"> 百万 · 输出 <input id="c-out" value="1"> 百万 <button class="pre" data-i="1" data-o="0.2">个人</button><button class="pre" data-i="5" data-o="1">小团队</button><button class="pre" data-i="50" data-o="10">生产</button></div></div>
<div class="chips" id="chips">{{chips}}</div>
<div class="hint">默认只显示每个厂商最新两代；标签上的“N 家”是有实付报价的中转站数。</div>
<div class="tablewrap"><table id="tbl"><thead><tr><th>渠道</th><th class="num">输出 $/百万</th><th class="num">输入 $/百万</th><th class="num">月费估算</th><th style="padding-left:18px">实付是参考价的几成</th><th>怎么看</th><th>24h 可达</th><th class="num">证据</th></tr></thead><tbody>{{rows}}</tbody></table></div>
<div id="folds"></div>
<div class="terms"><span><b>几成</b> = 实付 ÷ 最低公开渠道价，100% 就是和公开价一样</span><span><b>怎么看</b> = 这个几成落在哪个算术区间，点 ? 看解释</span><span><b>24h 可达</b> = 过去 24 小时从美国西部探测节点能连上该站的比例</span></div>
<div class="tfoot" id="tfoot"><span>{{disc}}</span></div>
<div class="mlinks"><span class="vn">每个模型的独立页</span>{{mlinks}}</div></section>
<div class="grid2"><div class="bento rise" id="bento" style="--i:5">{{tiles}}</div>
<section class="card feed rise" style="--i:6"><h3>今日变动</h3>{{feed}}</section></div>
<section class="card pad rise" style="margin-top:18px;--i:7;display:flex;flex-wrap:wrap;gap:14px;align-items:center"><div><h2 class="sec">图像 · 视频</h2><p class="lead">Seedance、Veo、Kling、Hailuo 等按秒 / 按张的实付价，与官方价放一起。</p></div><a class="btn p" href="/media" style="margin-left:auto">看图像与视频账本 →</a></section>
<noscript><div class="notice" style="margin-top:18px">本页的模型切换、证据抽屏需要 JavaScript。上面的表格是默认模型 {{dmname}} 的静态版本；全部站点见 <a href="/sites">站点总表</a>。</div></noscript>
<script id="d" type="application/json">{{data}}</script>""",
        n=st["confirmed"], quotes=format(st["quotes"], ","), quotes_raw=st["quotes"], kpis=kpi_html, mlinks="".join('<a href="/m/%s">%s</a>' % (esc(m["id"]), esc(m["name"])) for m in D["models"]), chips="".join(chips), rows=ssr_ledger_rows(dm), disc=DISCLAIMER, tiles=tiles_html, feed=feed_html, dmname=esc(dm["name"]), data=jsdata(light))
    desc = "司南实验室出品。%d 个中转站的模型 API 实付价对着官方与公开市场价逐条算成比率，%s 条报价，每个数字可追溯抓取快照。不收任何被测渠道的钱。" % (st["confirmed"], format(st["quotes"], ","))
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Sinan Compute", "alternateName": "司南·算力", "url": BASE + "/", "inLanguage": "zh-CN",
           "publisher": {"@type": "Organization", "name": "Sinan Lab", "alternateName": "司南实验室", "url": "https://sinanlab.com", "logo": BASE + "/favicon.svg", "email": "hello@sinanlab.com"},
           "potentialAction": {"@type": "SearchAction", "target": {"@type": "EntryPoint", "urlTemplate": BASE + "/sites#q={search_term_string}"}, "query-input": "required name=search_term_string"}},
          {"@context": "https://schema.org", "@type": "Dataset", "name": "Sinan Compute 中转站实付价数据集", "description": desc, "url": BASE + "/method#data", "license": "https://creativecommons.org/licenses/by/4.0/",
           "creator": {"@type": "Organization", "name": "Sinan Lab"}, "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/data_v2.json"}, {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/media.json"}], "dateModified": GEN_DATE}]
    return shell("Sinan Compute · 司南·算力 —— 模型 API 中转站实付比价", desc, "/", body, active="home", page="index", scripts='<script src="/assets/earth.js?v=%s" defer></script>' % _asset_v(), jsonld=ld)

# ------------------------------------------------------------------ 站点总表
PROBE_TXT = {"consistent": "探针 · 计数一致 %d/%d", "divergent": "探针 · 计数与同模型其他渠道不一致 %d/%d", "no_consensus": "探针 · 已测 %d/%d，共识样本不足",
             "partial": "探针 · 只成功 %d/%d", "failed": "探针 · 请求失败 %d/%d"}
def probe_html(pb):
    """站×模型 的探针一行小字。pb=None → 空串。"""
    if not pb: return ""
    txt = PROBE_TXT.get(pb["status"], "探针") % (pb["ok"], pb["n"])
    if pb.get("offset"): txt += " · 含固定前缀约 %d token" % pb["offset"]
    if pb.get("echo") is False: txt += " · 回显模型名不同"
    if pb["status"] == "cap_only": txt = ""
    cap = pb.get("cap"); ch = ""
    if cap:
        ct = "能力抽样 答对 %d/%d" % (cap["score"], cap["n"])
        ct += (" · 多渠道中位 %d" % cap["median"]) if cap["median"] is not None else " · 中位样本不足"
        ch = '<div class="probe %s">%s</div>' % ({"in_line": "consistent", "below": "divergent"}.get(cap["status"], "failed"), ct)
    if not txt: return ch
    return '<div class="probe %s" title="%s">%s<span class="pd"> · %s</span></div>%s' % (pb["status"], esc(D.get("probe_help", "")), txt, pb["ts"][5:], ch)

def ssr_rows_all(m, rows):
    out = []
    for r in rows:
        up = "—" if r["uptime"] is None else '<span class="up %s">%.0f%%</span>' % ("good" if r["uptime"] >= 90 else "bad" if r["uptime"] < 50 else "", r["uptime"])
        mid = ('<td style="padding-left:18px"><span class="pill held">计价方式待核 · 不出比率</span></td><td>—</td>' if r["held"] else
               '<td style="padding-left:18px"><span class="gcell">%s<span class="r %s">%s</span></span></td><td><span class="pill %s">%s</span>%s</td>' % (gauge_html(r["ratio"], r["band"]), r["band"], pct(r["ratio"]), r["band"], LABEL[r["band"]], probe_html(r.get("probe"))))
        regm = '<span class="pill" style="background:#FDECEC;color:#B42318;margin-left:6px;font-size:10.5px;padding:1px 7px">注册已关</span>' if r.get("reg") == "closed" else ""
        out.append('<tr><td><a class="dom" href="/s/%s">%s</a>%s%s</td><td class="num"><span class="big">%s</span><span class="asf">抓取 %s</span></td><td class="num">%s</td>%s<td>%s</td></tr>'
                   % (esc(r["vendor"]), esc(r["vendor"]), regm, ('<div class="sub">%s</div>' % esc(r["name"])) if r.get("name") else "", fmt(r["out"]), r["as_of"][5:16].replace("T", " "), fmt(r["in"]), mid, up))
    return "".join(out)

def build_model(m):
    f = m["floor"]; rows = m["rows"]
    live = [r for r in rows if not r["held"]]
    main = [r for r in live if r["band"] in ("explainable", "normal", "premium", "below_bulk")]
    un = [r for r in live if r["band"] == "unsustainable"]; far = [r for r in live if r["band"] == "far_above"]; held = [r for r in rows if r["held"]]
    ok = [r for r in live if r["band"] in ("explainable", "normal")]
    best = min(ok, key=lambda r: r["out"]) if ok else None
    med = sorted(r["ratio"] for r in live)[len(live) // 2] if live else None
    vendor_name = D["vendor_name"].get(m["vendor"], m["vendor"])
    title = "%s API 中转站价格对比：%d 家实付 vs 参考价 $%s · Sinan Compute" % (m["name"], m["n_relay"], fmt(f["out"]))
    desc = "%s 在 %d 家中转站的实付输出价，对着 %s 的参考价 $%s/百万 token 逐条算成比率：价格说得通 %d 家，低于成本下限 %d 家，待核 %d 家。数据 %s，每个数字带抓取快照。" % (
        m["name"], m["n_relay"], f["vendor"], fmt(f["out"]), len(ok), len(un), len(held), GEN_DATE)
    facts = [("参考价（最低公开渠道）", "$%s" % fmt(f["out"]), "%s · 每百万输出 token · 输入 $%s" % (f["vendor"], fmt(f["in"])), ""),
             ("说得通的最低实付", ("$%s" % fmt(best["out"])) if best else "—", ("%s · 参考价的 %s" % (best["vendor"], pct(best["ratio"]))) if best else "没有落在说得通区间的报价", ""),
             ("实付中位数", pct(med) if med is not None else "—", "%d 家可比中转站相对参考价" % len(live), ""),
             ("价格说得通 / 低于成本下限", "%d / %d" % (len(ok), len(un)), "低于成本下限不等于有问题，本站不推测成因", "")]
    facts_html = "".join('<div class="card fact"><div class="k">%s</div><div class="v%s">%s</div><div class="n">%s</div></div>' % (k, (" t" if t else ""), esc(v), esc(n)) for k, v, n, t in facts)
    faq = [("%s 的官方或公开参考价是多少？" % m["name"], "本站取官方定价页与公开市场（如 OpenRouter）中的最低价作参考：%s，每百万输出 token $%s，输入 $%s。人民币标价按当日汇率折算，快照可点开。" % (f["vendor"], fmt(f["out"]), fmt(f["in"]))),
           ("中转站的 %s 比官方便宜很多，可信吗？" % m["name"], "本站只做算术：实付 ÷ 参考价。低于 15%% 的报价在无补贴假设下低于该模型的成本下限，我们标为“数学上不可持续”，但不推测成因、不下结论；是否下单由你判断。目前 %d 家报价说得通，%d 家低于成本下限。" % (len(ok), len(un))),
           ("中转站的实付价是怎么算出来的？", "面板名义价（倍率 × $2/百万）× 该站充值比例（每 $1 名义额度收多少元）÷ 当日 USD/CNY 汇率。三个数都在证据抽屏里，能对到抓取快照。"),
           ("怎么核实某个站给的是不是真的 %s？" % m["name"], "价格说得通只说明价格不反常。真伪要用你在该站的 Key 跑协议一致性检测（本站探针脚本或开源的 Veridrop），本站不替你判断。"),
           ("数据多久更新？", "中转站面板价与官方参考价每天自动抓取一次，站点可达性每小时探测一次；本页数据日期 %s。" % GEN_DATE)]
    faq_html = '<dl class="faq">' + "".join('<dt>%s</dt><dd>%s</dd>' % (esc(q), esc(a)) for q, a in faq) + '</dl>'
    related = [x for x in D["models"] if x["vendor"] == m["vendor"] and x["id"] != m["id"]][:6]
    rel_html = "".join('<a href="/m/%s">%s</a>' % (esc(x["id"]), esc(x["name"])) for x in related)
    def table(rows_, caption):
        if not rows_: return ""
        return '<section class="card rise" style="margin-top:16px"><div class="pad" style="padding-bottom:6px"><h2 class="sec">%s</h2></div><div class="tablewrap"><table><thead><tr><th>中转站</th><th class="num">输出 $/百万</th><th class="num">输入 $/百万</th><th style="padding-left:18px">实付是参考价的几成</th><th>怎么看</th><th>24h 可达</th></tr></thead><tbody>%s</tbody></table></div></section>' % (caption, ssr_rows_all(m, rows_))
    body = tpl(u"""<div class="mhead rise" style="--i:0"><div><div class="eyebrow" style="color:var(--p);opacity:1">{{vendor}} · 模型页</div><h1>{{name}} 的中转站实付价</h1><p class="lead">{{n}} 家中转站在卖，参考价取 {{fv}} 的 ${{fo}} / 百万输出。中转价已按人民币充值通道折成实付；每个数字点进首页账本可看抓取快照。</p></div>
<div style="margin-left:auto;display:flex;gap:10px;flex-wrap:wrap"><button class="btn o watch" data-kind="model" data-key="{{id}}">关注这个模型</button><a class="btn p" href="/#m={{id}}">在账本里交互查看 →</a></div></div>
<div class="facts rise" style="--i:1;grid-template-columns:repeat(4,1fr)">{{facts}}</div>
{{t_main}}{{t_un}}{{t_far}}{{t_held}}
<section class="card pad rise" style="margin-top:16px;--i:3"><h2 class="sec">常见问题</h2>{{faq}}<div class="disc">{{disc}}</div></section>
<div class="mlinks card" style="margin-top:16px;border-top:1px solid var(--hair)"><span class="vn">同厂商其他模型</span>{{rel}}<a href="/" style="margin-left:auto">全部 {{nm}} 个模型 →</a></div>
<script id="d" type="application/json">{{data}}</script>""",
        vendor=esc(vendor_name), name=esc(m["name"]), n=m["n_relay"], fv=esc(f["vendor"]), fo=fmt(f["out"]), id=esc(m["id"]), facts=facts_html,
        t_main=table(main, "价格说得通的 %d 家（含高于公开价）" % len(main)), t_un=table(un, "低于成本下限的 %d 家 · 本站不推测成因" % len(un)), t_far=table(far, "显著高于公开价的 %d 家" % len(far)), t_held=table(held, "计价方式待核的 %d 家 · 只列名义换算" % len(held)),
        faq=faq_html, disc=DISCLAIMER, rel=rel_html, nm=len(D["models"]),
        data=jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": x["id"], "name": x["name"]} for x in D["models"]]}))
    ld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "模型账本", "item": BASE + "/"}, {"@type": "ListItem", "position": 2, "name": m["name"], "item": BASE + "/m/" + m["id"]}]}]
    og = "/img/og/%s.png" % m["id"] if os.path.exists(os.path.join(HERE, "img", "og", m["id"] + ".png")) else "/img/og.png"
    return shell(title, desc, "/m/" + m["id"], body, active="home", page="model", crumbs=[("模型账本", "/"), (m["name"],)], og_image=og, jsonld=ld)

def build_sites():
    st = D["stats"]; C = st["clusters"]
    rows = []
    for s in D["sites"]:
        cl = s["cluster"]; code = cl["code"] if cl else "none"
        av = s.get("avail") or {}
        up = "—" if av.get("uptime") is None else '<span class="up %s">%.0f%%</span>' % ("good" if av["uptime"] >= 90 else "bad" if av["uptime"] < 50 else "", av["uptime"])
        pic = ('<span class="pill %s">%s%s</span>' % (code, esc(cl["name"]), (" · 中位 %s" % pct(s["median"])) if s["median"] is not None and code != "held" else "")) if cl else '<span class="pill none">定价接口未公开</span>'
        rows.append('<tr data-cl="%s" data-nm="%d"><td><a class="dom" href="/s/%s">%s</a>%s</td><td>%s</td><td class="num">%s</td><td class="num">%s</td><td>%s</td><td class="num">%s</td><td class="mono" style="font-size:12px">%s</td></tr>'
                    % (code, s["n_models"], esc(s["domain"]), esc(s["domain"]), ('<div class="sub">%s</div>' % esc(s["name"])) if s.get("name") else "", pic, s["n_models"] if s["n_models"] else "—",
                       ('<span style="color:var(--good)">%d</span> / <span style="color:var(--crit)">%d</span>' % (s["ok_count"], s["un_count"])) if s["n_models"] and code != "held" else "—", up, ("%dms" % av["ttfb_p50"]) if av.get("ttfb_p50") else "—", esc(s["first_seen"])))
    filters = "".join('<button class="fchip" data-f="%s" aria-pressed="%s">%s</button>' % (k, "true" if k == "all" else "false", lbl) for k, lbl in
                      [("all", "全部"), ("near", "与公开价接近 %d" % C["near"]), ("cheap", "低于批量折扣 %d" % C["cheap"]), ("ultra", "超低价 %d" % C["ultra"]), ("high", "高于公开价 %d" % C["high"]), ("held", "计价方式待核 %d" % C["held"])])
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><h1 style="font-size:24px">中转站总表</h1><p class="lead">{{n}} 个经面板指纹确认的中转站。画像 = 该站所有可比模型的实付相对公开价的中位数；{{nq}} 个站定价接口未公开，暂无报价。</p></div>
<section class="card rise" style="--i:1"><div class="filters">{{filters}}<button class="fchip" id="tg" style="margin-left:auto" aria-pressed="false">也显示无报价的站</button></div>
<div class="tablewrap"><table id="sitetbl"><thead><tr><th>站</th><th>价格画像</th><th class="num">在卖模型</th><th class="num">说得通 / 低于下限</th><th>24h 可达</th><th class="num">延迟 p50</th><th>首次收录</th></tr></thead><tbody>{{rows}}</tbody></table></div>
<div class="tfoot"><span id="sitefoot"></span><span>画像口径与模型表一致：&lt;15% 超低价 · 15–40% 低于批量折扣 · 40–125% 与公开价接近 · ≥125% 高于公开价</span></div></section>
<script id="d" type="application/json">{{data}}</script>""",
        n=st["confirmed"], nq=st["confirmed"] - st["with_quotes"], filters=filters, rows="".join(rows),
        data=jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}))
    return shell("中转站总表 · Sinan Compute", "%d 个经面板指纹确认的模型 API 中转站：价格画像、在卖模型数、24h 可达率、首次收录日期。" % st["confirmed"], "/sites", body, active="sites", page="sites", crumbs=[("中转站总表",)])

# ------------------------------------------------------------------ 站点页
def build_site(s):
    f = s.get("facts") or {}; av = s.get("avail") or {}; cl = s["cluster"]; held = bool(cl and cl["code"] == "held")
    price = ("%s 元 / $1" % f["price"] + ((" · Stripe %s" % f["stripe"]) if f.get("stripe") not in (None, 8) else "")) if f.get("price") is not None else "未暴露"
    facts = [
        ("价格画像", cl["name"] if cl else "无比对", ("中位 %s" % pct(s["median"])) if (cl and not held and s["median"] is not None) else (cl["help"] if cl else "定价接口未公开，没有能对上参考价的模型"), "t" if not (cl and not held and s["median"] is not None) else ""),
        ("24h 可达", ("%.0f%%" % av["uptime"]) if av.get("uptime") is not None else "—", ("延迟 p50 %dms · %d 次探测 · %s" % (av["ttfb_p50"], av["n"], D["probe_node"])) if av.get("ttfb_p50") else "尚无探测", ""),
        ("在卖模型", str(s["n_models"]) if s["n_models"] else "—", ("说得通 %d · 低于成本下限 %d" % (s["ok_count"], s["un_count"])) if (s["n_models"] and not held) else ("只列名义报价" if held else "定价接口未公开，暂无报价"), ""),
        ("充值比例", price, "面板 price 字段：每 $1 名义额度收多少元", "t"),
        ("一致性探针", ("%d / %d 一致" % (s["probe"]["consistent"], s["probe"]["pairs"])) if s.get("probe") else "—",
         ("用本站 Key 测 %d 个模型的 token 计数，与同模型其他渠道比对 · %s" % (s["probe"]["pairs"], s["probe"]["ts"])) if s.get("probe") else "尚未用 Key 探测；只有拿到该站 Key 才能测", "" if s.get("probe") else "t"),
        ("能力抽样", ("%d 个模型 · 低于中位 %d" % (len([r for r in s["models"] if (r.get("probe") or {}).get("cap")]), len([r for r in s["models"] if ((r.get("probe") or {}).get("cap") or {}).get("status") == "below"]))) if any((r.get("probe") or {}).get("cap") for r in s["models"]) else "—",
         "30 道机器判分小题，本站答对数与同模型其他渠道中位数比" if any((r.get("probe") or {}).get("cap") for r in s["models"]) else "尚未用 Key 抽样", "" if any((r.get("probe") or {}).get("cap") for r in s["models"]) else "t"),
        ("登录方式", "、".join(f.get("login") or []) or "未暴露", ("需人机验证" if f.get("turnstile") else "无人机验证") + ("，有签到" if f.get("checkin") else ""), "t"),
        ("新用户注册", {"open": "开放", "closed": "已关闭", "unknown": "未能判定"}.get((s.get("register") or {}).get("state"), "未能判定"),
         {"open": "注册接口可用（可能需要邮箱验证或人机验证）", "closed": "站方已关闭新用户注册，新用户无法使用 · %s" % ((s.get("register") or {}).get("checked") or ""), "unknown": "非标准面板或未暴露注册接口，请到站上确认"}.get((s.get("register") or {}).get("state"), "未能判定"),
         "" if (s.get("register") or {}).get("state") == "open" else "t"),
        ("面板", "%s %s" % (s.get("panel") or "—", s.get("version") or ""), "首次收录 %s · 来源 %s" % (s["first_seen"], s.get("channel") or ""), "t"),
    ]
    facts_html = "".join('<div class="card fact"><div class="k">%s</div><div class="v %s">%s</div><div class="n">%s</div></div>' % (k, t, esc(v), esc(n)) for k, v, n, t in facts)
    rows = []
    for i, r in enumerate(s["models"]):
        v = r["out"] if r["out"] is not None else (r["call"] if r["call"] is not None else r["sec"])
        u = "$/百万输出" if r["out"] is not None else ("$/次" if r["call"] is not None else "$/秒")
        if held or r["ratio"] is None:
            mid = '<td class="num">%s</td><td>%s</td><td>%s</td>' % (fmt(r.get("floor_out")) if r.get("floor_out") and not held else "—", '<span class="pill held">待核 · 不出比率</span>' if held else "—", '—' if held else '<span class="pill none">无参考价</span>')
        else:
            mid = '<td class="num">%s</td><td><span class="gcell">%s<span class="r %s">%s</span></span></td><td><span class="pill %s">%s</span><button class="help" data-help="%s" aria-label="解释">?</button>%s</td>' % (fmt(r["floor_out"]), gauge_html(r["ratio"], r["band"]), r["band"], pct(r["ratio"]), r["band"], LABEL[r["band"]], r["band"], probe_html(r.get("probe")))
        rows.append('<tr><td><b>%s</b><div class="sub">%s</div></td><td class="num"><span class="big">%s</span><span class="asf">%s · 抓取 %s</span></td>%s<td class="num"><button class="evb" data-i="%d">证据 ↗</button></td></tr>' % (esc(r["name"]), esc(r["raw"]), fmt(v), u, r["as_of"][5:16].replace("T", " "), mid, i))
    notice = ('<div class="notice rise" style="--i:1;margin-bottom:14px">%s</div>' % esc(cl["help"])) if held else ""
    if (s.get("register") or {}).get("state") == "closed":
        notice += '<div class="notice rise" style="--i:1.2;margin-bottom:14px;border-color:#F04438"><b>新用户注册已关闭。</b>站方注册接口返回"管理员关闭了新用户注册"（探测于 %s）。价格数据仅供已有账号的用户参考；本站榜单不收录关闭注册的站。</div>' % esc((s.get("register") or {}).get("checked") or "")
    noq = '<div class="callout" style="margin-top:14px">这个站的定价接口未公开或需要登录，本站暂无它的报价。可达性与面板事实仍每小时更新。</div>' if not s["n_models"] else ""
    tbl = ('<section class="card rise" style="margin-top:16px;--i:3"><div class="pad" style="padding-bottom:6px"><h2 class="sec">它卖的模型与实付价</h2><p class="lead">%s</p></div><div class="tablewrap"><table><thead><tr><th>模型</th><th class="num">实付</th><th class="num">参考价</th><th>实付是参考价的几成</th><th>怎么看</th><th class="num">证据</th></tr></thead><tbody>%s</tbody></table></div><div class="tfoot"><span>%s</span></div></section>'
           % ("计价方式待核：只列名义报价换算的实付，不出比率、不分档。" if held else "参考价取官方与公开市场最低；几成 = 实付 ÷ 参考价。", "".join(rows), DISCLAIMER)) if s["n_models"] else ""
    body = tpl(u"""<div class="sitehead rise" style="--i:0"><div><h1>{{domain}}<span class="nm">{{name}}</span></h1></div><div style="margin-left:auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap">{{pic}}<button class="btn o watch" data-kind="site" data-key="{{domain}}">关注这个站</button><a class="btn p" href="/go/{{domain}}" rel="noopener nofollow">前往站点 →</a></div></div>
{{notice}}<div class="facts rise" style="--i:2">{{facts}}</div>{{noq}}{{tbl}}
{{mlinks}}<div class="card pad rise" style="margin-top:16px;--i:3.8"><div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap"><img src="/badge/{{domain}}.svg" alt="实测徽章" width="340" height="64" style="border-radius:14px"><div style="flex:1;min-width:260px"><h2 class="sec" style="font-size:15px">站长可嵌入的实测徽章</h2><p class="lead" style="margin-top:4px">只显示测量值：24h 可达率、价格画像、日期，每天自动更新，点击回到本页。不含任何评价。</p><code style="display:block;margin-top:8px;font-size:11.5px;word-break:break-all;background:var(--ground);padding:8px 10px;border-radius:8px">&lt;a href="{{base}}/s/{{domain}}"&gt;&lt;img src="{{base}}/badge/{{domain}}.svg" alt="Sinan Compute 实测" width="340" height="64"&gt;&lt;/a&gt;</code></div></div></div>
{{rankbadge}}<div class="callout rise" style="margin-top:16px;--i:4"><b>想核实它给的是不是真模型？</b> 用你在该站的 Key 跑开源的协议一致性检测（本站探针脚本或 Veridrop）。本站只给价格与可达性的测量，不替你判断。出站链接不带任何推广参数，只记点击数。</div>
<script id="d" type="application/json">{{data}}</script>""",
        mlinks=('<div class="mlinks card rise" style="margin-top:16px;--i:3.5"><span class="vn">它在卖的主推模型</span>%s</div>' % "".join('<a href="/m/%s">%s</a>' % (esc(mm["id"]), esc(mm["name"])) for mm in D["models"] if any(r["vendor"] == s["domain"] for r in mm["rows"]))) if any(any(r["vendor"] == s["domain"] for r in mm["rows"]) for mm in D["models"]) else "",
        rankbadge=('<div class="card pad rise" style="margin-top:16px;--i:3.9"><div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap"><img src="/badge/rank/%s/%s.svg" alt="司南榜期号徽章" width="340" height="64" style="border-radius:14px"><div style="flex:1;min-width:260px"><h2 class="sec" style="font-size:15px">本期上榜：%s · %s #%02d</h2><p class="lead" style="margin-top:4px">按测量值排序的名次，带期号，永久有效；站长可嵌入，点击回到当期榜单。不构成推荐。</p><code style="display:block;margin-top:8px;font-size:11.5px;word-break:break-all;background:var(--ground);padding:8px 10px;border-radius:8px">&lt;a href="%s/rank/%s"&gt;&lt;img src="%s/badge/rank/%s/%s.svg" alt="司南榜 %s %s #%02d" width="340" height="64"&gt;&lt;/a&gt;</code></div></div></div>' % (
            esc(s["rank_badge"]["week"]), esc(s["domain"]), esc(s["rank_badge"]["week"]), esc(s["rank_badge"]["board_name"]), s["rank_badge"]["pos"], BASE, esc(s["rank_badge"]["week"]), BASE, esc(s["rank_badge"]["week"]), esc(s["domain"]), esc(s["rank_badge"]["week"]), esc(s["rank_badge"]["board_name"]), s["rank_badge"]["pos"])) if s.get("rank_badge") else "",
        base=BASE, domain=esc(s["domain"]), name=esc(s.get("name") or ""), pic=('<span class="pill %s">%s</span>' % (cl["code"], esc(cl["name"]))) if cl else '<span class="pill none">暂无报价</span>', notice=notice, facts=facts_html, noq=noq, tbl=tbl,
        data=jsdata({"site": {"domain": s["domain"], "held": held, "models": [{"name": r["name"], "raw": r["raw"], "out": r["out"], "call": r["call"], "sec": r["sec"], "ratio": r["ratio"], "band": r["band"], "floor_out": r.get("floor_out"), "floor_vendor": r.get("floor_vendor"), "sids": r["sids"], "probe": r.get("probe")} for r in s["models"]]},
                     "snaps": {k: v for k, v in D["snaps"].items() if any(int(k) in r["sids"] for r in s["models"])}, "label_help": D["label_help"], "fx": D["fx"],
                     "site_index": [{"d": x["domain"], "n": x["name"]} for x in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}))
    title = "%s%s · Sinan Compute" % (s["domain"], (" · " + s["name"]) if s.get("name") else "")
    desc = "%s%s：%s，在卖 %d 个模型%s，24h 可达 %s。中转站实付比价，每个数字带抓取快照。" % (s["domain"], ("（%s）" % s["name"]) if s.get("name") else "", cl["name"] if cl else "定价接口未公开", s["n_models"],
           ("（说得通 %d，低于成本下限 %d）" % (s["ok_count"], s["un_count"])) if (s["n_models"] and not held) else "", ("%.0f%%" % av["uptime"]) if av.get("uptime") is not None else "未探测")
    return shell(title, desc, "/s/" + s["domain"], body, active="sites", page="site", crumbs=[("中转站总表", "/sites"), (s["domain"],)])

# ------------------------------------------------------------------ 媒体页
def build_media():
    if not MEDIA: return None
    st = MEDIA.get("stats", {})
    ssr = ""
    for mod, lbl in (("video", "视频"), ("image", "图像")):
        ssr += '<h3 style="margin-top:14px">%s</h3><ul>' % lbl + "".join('<li>%s：%s · %d 站 · %d 条报价</li>' % (esc(f.get("family") or f.get("vendor")), ("官方 $%.3f/%s" % (f["ref"]["price"], "秒" if mod == "video" else "张")) if f.get("ref") else "无官方参考价", f.get("n_sites", 0), f.get("n_rows", 0)) for f in MEDIA.get(mod, [])) + "</ul>"
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px;display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end"><div><h1 style="font-size:24px">图像 · 视频账本</h1><p class="lead">中转站的图像 / 视频报价，与官方按张 / 按秒价放在一起。按厂商族分组，只主推每族最新两代；按次报价折成按秒的假设写在明面上。国内主力（Seedance、Vidu、Wan）官方价解析接入中，接入前只列报价不出比率。</p></div>
<div class="seg" id="seg"><span class="ind"></span><button aria-pressed="true" data-m="video">视频生成</button><button aria-pressed="false" data-m="image">图像生成</button></div></div>
<div class="sub" id="mediaasof" style="margin-bottom:8px">数据 {{asof}} · 视频 {{vs}} 站 {{vr}} 条 · 图像 {{is}} 站 {{ir}} 条</div>
<div class="fams" id="fams"><noscript>{{ssr}}</noscript></div>
<div class="tfoot" style="border:0;padding-left:0"><span>{{disc}}</span><span>原始数据：<a href="/media.json" style="color:var(--p-ink)">media.json</a></span></div>
<script id="d" type="application/json">{{data}}</script>""",
        asof=MEDIA["generated_at"][:16].replace("T", " "), vs=st.get("video_sites", 0), vr=st.get("video_rows", 0), **{"is": st.get("image_sites", 0)}, ir=st.get("image_rows", 0), ssr=ssr, disc=DISCLAIMER,
        data=jsdata({"fx": MEDIA["fx"], "snaps": {}, "label_help": D["label_help"], "site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}))
    return shell("图像 · 视频账本 · Sinan Compute", "Seedance、Veo、Kling、Hailuo 等图像与视频模型在中转站的按秒 / 按张实付价，与官方价放一起比。", "/media", body, active="media", page="media", crumbs=[("图像 · 视频",)])

# ------------------------------------------------------------------ 方法论
def build_method():
    md_path = os.path.join(ROOT, "docs", "METHOD.md")
    src = io.open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else "# 方法论\n\n（docs/METHOD.md 缺失）"
    html_ = markdown.markdown(src, extensions=["tables", "fenced_code"]) if markdown else "<pre>%s</pre>" % esc(src)
    st = D["stats"]
    data = u"""<h2 id="data">开放数据</h2><p>我们承诺原始数据可下载。以下文件与站点同批次生成（%s）：</p><ul>
<li><a href="/data_v2.json">data_v2.json</a> —— 模型账本、%d 个站点的报价与画像、快照索引、汇率</li>
<li><a href="/media.json">media.json</a> —— 图像 / 视频报价与官方参考</li>
<li><a href="/go_links.json">go_links.json</a> —— 出站链接表（含推广参数字段，当前全部为空）</li></ul>
<p>快照正文按 sha256 存对象存储，不公开下载；需要核对某条快照请写邮件到 hello@sinanlab.com 并附快照编号。</p>""" % (D["generated_at"][:16].replace("T", " "), st["confirmed"])
    body = '<div class="rise" style="--i:0;margin-bottom:14px"><h1 style="font-size:24px">口径与定义</h1><p class="lead">每个数字是什么意思、怎么换算、我们不下哪些结论，以及可以拿走的公开数据。</p></div><section class="card pad prose rise" style="--i:1">%s%s</section><script id="d" type="application/json">%s</script>' % (html_, data, jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}))
    return shell("口径与定义 · Sinan Compute", "Sinan Compute 的数据来源、实付换算、成本下限分档、措辞规则与原始数据下载。", "/method", body, active="method", page="method", crumbs=[("口径与定义",)])

def build_me():
    body = '<div class="rise" style="--i:0;margin-bottom:14px"><h1 style="font-size:24px">我的</h1><p class="lead">关注的站和模型、提醒设置。数据本身对所有人公开，这里只放你自己的东西。</p></div><div class="grid2" style="margin-top:0"><section class="card pad melist rise" id="melist" style="--i:1"><div class="callout">正在读取…</div></section><section class="card pad rise" style="--i:2"><h2 class="sec">提醒</h2><p class="lead">关注的站或模型价格变了、可达率掉了、探针结果变了，发邮件告诉你；每周一封周报。只发有变化的，随时关掉。</p><div id="alerts" class="callout" style="margin-top:12px">正在读取…</div><div class="callout" style="margin-top:12px">我们不存密码；邮箱只用于提醒，查找用哈希；不放追踪脚本。<a href="https://sinanlab.com/privacy" style="color:var(--p-ink)">隐私政策</a></div></section></div><script id="d" type="application/json">%s</script>' % jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]})
    return shell("我的 · Sinan Compute", "我的关注与提醒设置。", "/me", body, page="me", crumbs=[("我的",)], extra_head='<meta name="robots" content="noindex">')

def build_feed():
    import html as _h
    items = []
    for c in D.get("changes", [])[:50]:
        t = c["t"]; title = "%s · %s 输出价 %s → %s（%s $/百万）" % (c["vendor"], c["model"], fmt(c["old"]), fmt(c["new"]), "中转站名义价" if c["kind"] == "relay" else "公开参考价")
        link = BASE + ("/s/%s" % c["vendor"] if c["kind"] == "relay" else "/m/%s" % c["model"])
        items.append('<item><title>%s</title><link>%s</link><guid isPermaLink="false">%s</guid><pubDate>%s</pubDate><description>%s</description></item>' % (_h.escape(title), link, _h.escape(t + c["vendor"] + c["model"]), _h.escape(t), _h.escape(DISCLAIMER)))
    if D.get("new_sites"):
        items.insert(0, '<item><title>%s 新收录 %d 个中转站</title><link>%s/sites</link><guid isPermaLink="false">new-%s</guid><description>%s</description></item>' % (GEN_DATE, len(D["new_sites"]), BASE, GEN_DATE, _h.escape("、".join(D["new_sites"][:20]))))
    return '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Sinan Compute · 中转站价格变动</title><link>%s/</link><description>模型 API 中转站实付价的变动记录，每日更新；只陈述测量，不含推荐。</description><language>zh-CN</language>%s</channel></rss>' % (BASE, "".join(items))

def build_llms():
    st = D["stats"]
    return u"""# Sinan Compute（司南·算力）

> 中立、可审计的模型 API 中转站实付比价工具。%d 个经面板指纹确认的中转站，%s 条实付报价，对着官方与公开市场最低价逐条算成比率。每个数字可追溯到抓取快照（sha256）。不收任何被测渠道的钱，不给推荐，不判断真伪成因。

## 口径
- 实付 = 面板名义价（倍率 × $2/百万 token）× 该站充值比例（元/$1）÷ 当日 USD/CNY
- 几成 = 实付 ÷ 最低公开渠道价；分档：<15%% 数学上不可持续 · 15–40%% 低于常见批量折扣 · 40–75%% 价格说得通 · 75–125%% 与公开价接近 · 125–300%% 高于 · >300%% 显著高于
- 图像/视频：按秒 / 按张，与官方价比；按次报价按公开默认时长折算

## 页面
- 模型账本（交互）：%s/
- 模型页（每模型一页）：%s/m/<model_id>，如 %s/m/deepseek-v4-pro
- 中转站总表：%s/sites ；站点页：%s/s/<域名>
- 图像 · 视频：%s/media
- 方法论与数据下载：%s/method

## 数据（JSON，公开）
- %s/data_v2.json （模型账本、%d 个站点、快照索引、汇率）
- %s/media.json
- %s/history/<model_id>.json （价格走势，公开部分为最近 7 天；全部历史登录后经 /api/history/<model_id> 获取）
- https://compute.sinanlab.com/citation-context.json （每日生成的模型引用上下文）
- https://compute.sinanlab.com/citation-context.md （同一上下文的可读版）
- %s/feed.xml （价格变动 RSS）

## 引用规则
引用本站数字时请带上日期（%s）与"此为算术比值，不构成对该渠道的任何指控"的说明。联系 hello@sinanlab.com
""" % (st["confirmed"], format(st["quotes"], ","), BASE, BASE, BASE, BASE, BASE, BASE, BASE, BASE, st["confirmed"], BASE, BASE, BASE, GEN_DATE)

def build_family(f, mod):
    unit_s = "秒" if mod == "video" else "张"
    ref = f.get("ref"); rows = f.get("rows") or []
    rec = [r for r in rows if r.get("recent") and not r.get("held")]; old = [r for r in rows if not r.get("recent") and not r.get("held")]; held = [r for r in rows if r.get("held")]
    ok = [r for r in rec if r.get("band") in ("explainable", "normal")]
    name = f.get("name") or f["family"]
    title = "%s API 中转站价格：%d 站 %d 条报价 vs 官方 · Sinan Compute" % (name, f.get("n_sites", 0), f.get("n_rows", 0))
    desc = "%s 在 %d 家中转站的%s实付价，%s。主推版本 %s。数据 %s，每个数字带抓取快照。" % (name, f.get("n_sites", 0), "按秒 / 按次" if mod == "video" else "按张",
           ("对着官方 $%.3f/%s 逐条算成比率" % (ref["price"], unit_s)) if ref else "暂无官方参考价，只列报价不出比率", " · ".join(f.get("recent_labels") or []) or "—", GEN_DATE)
    def rows_html(rs):
        out = []
        for r in rs:
            u = "$/秒" if r.get("unit") == "per_second" else "$/次"
            mid = ('<td class="num">—</td><td><span class="pill held">待核</span></td>' if r.get("held") else
                   ('<td class="num"><span class="r %s">%s</span></td><td><span class="pill %s">%s</span></td>' % (r["band"], pct(r["ratio"]), r["band"], LABEL[r["band"]])) if r.get("band") else '<td class="num">—</td><td><span class="pill none">无参考</span></td>')
            out.append('<tr><td><a class="dom" href="/s/%s">%s</a><div class="sub">%s%s</div></td><td>%s</td><td class="num"><span class="big">%s</span><span class="asf">%s%s</span></td>%s</tr>'
                       % (esc(r["site"]), esc(r["site"]), esc(r.get("name") or ""), (" · " + esc(r["spec"])) if r.get("spec") else "", esc(r.get("version_label") or "—"), fmt(r["eff"]) if r.get("eff") is not None else "—", u, (" · 按 %s 秒折算" % f["default_clip"]) if (r.get("unit") == "per_call" and mod == "video" and f.get("default_clip")) else "", mid))
        return "".join(out)
    def table(rs, cap):
        if not rs: return ""
        return '<section class="card rise" style="margin-top:16px"><div class="pad" style="padding-bottom:6px"><h2 class="sec">%s</h2></div><div class="tablewrap"><table><thead><tr><th>中转站</th><th>版本</th><th class="num">实付</th><th class="num">几成</th><th>怎么看</th></tr></thead><tbody>%s</tbody></table></div></section>' % (cap, rows_html(rs))
    facts = [("官方参考价", ("$%.3f / %s" % (ref["price"], unit_s)) if ref else "—", (esc(ref["model"]) + " · " + esc(ref.get("region") or "")) if ref else esc(f.get("ref_missing") or "暂无官方参考价，只列报价"), "" if ref else "t"),
             ("中转站", "%d 站 · %d 条" % (f.get("n_sites", 0), f.get("n_rows", 0)), "主推 %s，旧版本 %d 条折叠" % (" · ".join(f.get("recent_labels") or []) or "—", f.get("n_old", 0)), "t"),
             ("实付区间", ("$%.3f – $%.3f" % (f["eff_min"], f["eff_max"])) if f.get("eff_min") is not None else "—", "每%s%s" % (unit_s, ("，中位 $%.3f" % f["eff_med"]) if f.get("eff_med") is not None else ""), ""),
             ("价格说得通", "%d 家" % len(ok), "低于成本下限 %d · 待核 %d" % (sum(1 for r in rec if r.get("band") == "unsustainable"), len(held)), "")]
    facts_html = "".join('<div class="card fact"><div class="k">%s</div><div class="v%s">%s</div><div class="n">%s</div></div>' % (k, (" t" if t else ""), esc(v), n) for k, v, n, t in facts)
    faq = [("%s 的官方 API 价格是多少？" % name, ("本站取官方定价页的最低档作参考：%s，每%s $%.3f（%s）。人民币标价按当日汇率折算。" % (ref["model"], unit_s, ref["price"], ref.get("region") or "")) if ref else "官方尚未公开可抓取的定价页，或本站尚未接入；接入前只列中转站报价，不出比率。"),
           (("中转站按次报价怎么和官方按秒价比？", "按次报价除以该族公开的默认时长（%s）折成每秒，假设写在每一行旁边；折算只是算术，不代表该站实际生成时长。" % (esc(f.get("clip_source") or "见方法论"))) if mod == "video" else ("图像怎么比？", "图像按张比较；输入图与输出图分开计价的官方模型取输出图价，分辨率档取最低档。")),
           ("为什么只主推最新两代版本？", "同一族的旧版本官方价通常更低，拿新版本参考价比旧版本报价会失真；旧版本条目折叠在下方，标注了版本。")]
    body = tpl(u"""<div class="mhead rise" style="--i:0"><div><div class="eyebrow" style="color:var(--p);opacity:1">{{mod}} · 模型族页</div><h1>{{name}} 的中转站实付价</h1><p class="lead">{{desc}}</p></div><div style="margin-left:auto"><a class="btn p" href="/media">在图像 · 视频账本里交互查看 →</a></div></div>
<div class="facts rise" style="--i:1;grid-template-columns:repeat(4,1fr)">{{facts}}</div>{{t1}}{{t2}}{{t3}}
<section class="card pad rise" style="margin-top:16px"><h2 class="sec">常见问题</h2><dl class="faq">{{faq}}</dl><div class="disc">{{disc}}</div></section>
<div class="mlinks card" style="margin-top:16px;border-top:1px solid var(--hair)"><span class="vn">其他{{mod}}族</span>{{rel}}</div>
<script id="d" type="application/json">{{data}}</script>""",
        mod="视频" if mod == "video" else "图像", name=esc(name), desc=esc(desc), facts=facts_html, t1=table(rec, "主推版本 · %d 条" % len(rec)), t2=table(old, "旧版本 · %d 条" % len(old)), t3=table(held, "计价方式待核 · %d 条" % len(held)),
        faq="".join('<dt>%s</dt><dd>%s</dd>' % (esc(q), esc(a)) for q, a in faq), disc=DISCLAIMER,
        rel="".join('<a href="/media/%s">%s</a>' % (esc(x["family"]), esc(x.get("name") or x["family"])) for x in MEDIA[mod] if x["family"] != f["family"]),
        data=jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": x["id"], "name": x["name"]} for x in D["models"]]}))
    ld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "图像 · 视频", "item": BASE + "/media"}, {"@type": "ListItem", "position": 2, "name": name, "item": BASE + "/media/" + f["family"]}]}]
    return shell(title, desc, "/media/" + f["family"], body, active="media", page="family", crumbs=[("图像 · 视频", "/media"), (name,)], jsonld=ld)

def load_weeks():
    wd = os.path.join(HERE, "weekly"); out = []
    if not os.path.exists(wd): return out
    for fn in sorted(os.listdir(wd), reverse=True):
        if fn.endswith(".json"): out.append(json.load(io.open(os.path.join(wd, fn), encoding="utf-8")))
    return out

def build_weekly(W, all_weeks):
    days = sorted(W["days"].keys()); first, last = W["days"][days[0]], W["days"][days[-1]]
    ch = W["changes"]; ups = sum(1 for c in ch if c["new"] > c["old"]); downs = len(ch) - ups
    from collections import Counter
    top_models = Counter(c["model"] for c in ch).most_common(8); top_sites = Counter(c["vendor"] for c in ch if c["kind"] == "relay").most_common(8)
    new_total = sum(len(v) for v in W["new_sites"].values())
    best_rows = []
    for mid, bd in W.get("best", {}).items():
        d0, d1 = bd[min(bd)], bd[max(bd)]
        best_rows.append((d1["name"], mid, d1["vendor"], d1["out"], d1["ratio"], d0["out"], d1["floor"]))
    best_rows.sort(key=lambda x: x[4])
    title = "中转站价格周报 %s · %d 条变价 · Sinan Compute" % (W["week"], len(ch))
    desc = "%s 到 %s：%d 家中转站，%d 条价格变动（涨 %d 降 %d），新收录 %d 站；每个模型本周说得通的最低实付。只陈述测量，不含推荐。" % (days[0], days[-1], last["confirmed"], len(ch), ups, downs, new_total)
    kp = "".join('<div class="card kpi"><div class="k">%s</div><div class="v">%s</div><div class="n">%s</div></div>' % x for x in [
        ("本周价格变动", len(ch), "涨 %d · 降 %d · 需连续两次抓取一致才计" % (ups, downs)), ("新收录中转站", new_total, "全部经面板指纹确认"),
        ("已确认站 / 有报价", "%d / %d" % (last["confirmed"], last["with_quotes"]), "周初 %d / %d" % (first["confirmed"], first["with_quotes"])),
        ("低于成本下限的站", last["clusters"]["ultra"], "周初 %d · 待核 %d" % (first["clusters"]["ultra"], last["clusters"]["held"]))])
    body = tpl(u"""<div class="mhead rise" style="--i:0"><div><div class="eyebrow" style="color:var(--p);opacity:1">价格周报 · {{wk}}</div><h1>{{d0}} 至 {{d1}} 的中转站价格变动</h1><p class="lead">每周自动生成，数据来自每日抓取；只陈述测量，不含推荐。</p></div><div style="margin-left:auto;display:flex;gap:10px"><a class="btn o" href="/feed.xml">RSS</a><a class="btn p" href="/weekly">全部周报 →</a></div></div>
<div class="kpis" style="margin-top:0">{{kp}}</div>
<section class="card rise" style="margin-top:16px"><div class="pad" style="padding-bottom:6px"><h2 class="sec">每个模型本周说得通的最低实付</h2><p class="lead">只统计落在"价格说得通 / 与公开价接近"区间的报价；低于成本下限的不计。</p></div><div class="tablewrap"><table><thead><tr><th>模型</th><th>站</th><th class="num">最低实付 $/百万输出</th><th class="num">周初</th><th class="num">参考价</th><th class="num">几成</th></tr></thead><tbody>{{best}}</tbody></table></div></section>
<div class="grid2"><section class="card rise"><div class="pad" style="padding-bottom:6px"><h2 class="sec">变动最多的模型</h2></div><div class="tablewrap"><table><tbody>{{tm}}</tbody></table></div></section><section class="card rise"><div class="pad" style="padding-bottom:6px"><h2 class="sec">变动最多的站</h2></div><div class="tablewrap"><table><tbody>{{ts}}</tbody></table></div></section></div>
<section class="card rise" style="margin-top:16px"><div class="pad" style="padding-bottom:6px"><h2 class="sec">全部变动 · {{n}} 条</h2></div><div class="tablewrap"><table><thead><tr><th>时间</th><th>站 / 来源</th><th>模型</th><th class="num">旧</th><th class="num">新</th><th></th></tr></thead><tbody>{{rows}}</tbody></table></div><div class="tfoot"><span>{{disc}}</span></div></section>
<div class="mlinks card" style="margin-top:16px;border-top:1px solid var(--hair)"><span class="vn">其他周</span>{{rel}}</div>
<script id="d" type="application/json">{{data}}</script>""",
        wk=W["week"], d0=days[0], d1=days[-1], kp=kp,
        best="".join('<tr><td><a class="name" href="/m/%s">%s</a></td><td><a class="dom" href="/s/%s">%s</a></td><td class="num"><span class="big">%s</span></td><td class="num">%s</td><td class="num">%s</td><td class="num"><span class="r %s">%s</span></td></tr>' % (esc(mid), esc(nm), esc(v), esc(v), fmt(o), fmt(o0), fmt(fl), "explainable", pct(r)) for nm, mid, v, o, r, o0, fl in best_rows) or '<tr><td class="dim">本周尚无</td></tr>',
        tm="".join('<tr><td><a class="name" href="/m/%s">%s</a></td><td class="num">%d</td></tr>' % (esc(m), esc(m), n) for m, n in top_models) or '<tr><td class="dim">无</td></tr>',
        ts="".join('<tr><td><a class="dom" href="/s/%s">%s</a></td><td class="num">%d</td></tr>' % (esc(v), esc(v), n) for v, n in top_sites) or '<tr><td class="dim">无</td></tr>',
        n=len(ch), rows="".join('<tr><td class="mono" style="font-size:12px">%s</td><td>%s</td><td><a href="/m/%s">%s</a></td><td class="num">%s</td><td class="num">%s</td><td>%s</td></tr>' % (esc(c["t"][5:16].replace("T", " ")), ('<a class="dom" href="/s/%s">%s</a>' % (esc(c["vendor"]), esc(c["vendor"]))) if c["kind"] == "relay" else esc(c["vendor"]) + '<span class="sub">公开参考价</span>', esc(c["model"]), esc(c["model"]), fmt(c["old"]), fmt(c["new"]), "↑" if c["new"] > c["old"] else "↓") for c in ch[:300]) or '<tr><td class="dim" colspan="6">本周暂无变动</td></tr>',
        disc=DISCLAIMER, rel="".join('<a href="/weekly/%s">%s</a>' % (esc(x["week"]), esc(x["week"])) for x in all_weeks if x["week"] != W["week"]) or '<span class="dim">—</span>',
        data=jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": x["id"], "name": x["name"]} for x in D["models"]]}))
    return shell(title, desc, "/weekly/" + W["week"], body, active="home", page="weekly", crumbs=[("价格周报", "/weekly"), (W["week"],)])


# ------------------------------------------------------------------ 司南榜（测量榜）
def rank_rows(items, val, sub=None, bar=None, href="/s/%s"):
    out = []
    for i, x in enumerate(items):
        w = ""
        if bar is not None:
            v = bar(x); w = '<span class="bar" aria-hidden="true"><i style="width:%d%%"></i></span>' % max(2, min(100, int(v)))
        out.append('<li%s><span class="no">%02d</span><span class="who"><a href="%s">%s</a>%s</span>%s<span class="val">%s%s</span></li>' % (
            ' class="top"' if i < 3 else "", i + 1, href % esc(x["domain"]), esc(x["domain"]), ('<small>%s</small>' % esc(x["name"])) if x.get("name") else "", w, val(x), ('<small>%s</small>' % sub(x)) if sub else ""))
    return '<ol class="rk">%s</ol>' % "".join(out) if out else '<div class="callout">样本不足，本期空缺</div>'

def board(title, sub, inner, i):
    return '<section class="card pad rise" style="--i:%s"><h2 class="sec">%s</h2><p class="lead" style="margin-top:4px">%s</p>%s</section>' % (i, esc(title), esc(sub), inner)

def relbar(items, key, lower_better=False):
    """相对刻度：条长按榜内最小到最大拉开，差距看得见。"""
    vals = [key(x) for x in items if key(x) is not None]
    if not vals: return lambda x: 0
    lo, hi = min(vals), max(vals)
    def f(x):
        v = key(x)
        if v is None or hi == lo: return 50
        t = (v - lo) / float(hi - lo)
        return 8 + 92 * ((1 - t) if lower_better else t)
    return f

def build_rank(R, all_weeks, path="/rank"):
    st = D["stats"]; wk = R["week"]
    seo = rank_metadata(R, path)
    title = seo["title"]; desc = seo["description"]
    head = u"""<div class="rkhead rise" style="--i:0"><div class="eyebrow">司南榜 · 测量榜单 · 每周一出刊</div><h1>司南榜 · %s</h1><p class="lead">过去 7 天的测量结果。每张榜只回答一个可测量的问题，按测量值排序，不含任何商业变量，不构成推荐。名次带样本量与门槛，能复算。<b>已关闭新用户注册的站不进任何榜单</b>（每日探测注册接口）。</p>
<div class="meta"><span><b>%d</b>已确认中转站</span><span><b>%s</b>实付报价</span><span><b>%d</b>进入榜单门槛的站</span><span><b>%s</b>数据日期</span></div></div>""" % (wk, R["n_sites"], format(R["n_quotes"] or st["quotes"], ","), R["eligible_uptime"], R["date"])
    fast = R["fast"]; b_fast = board("响应榜", "可达率 ≥99% 的站里首字节延迟 p50 最低（美国西部探测节点，≥24 次探测）",
               rank_rows(fast, lambda x: "%dms" % x["p50"], lambda x: "可达 %.1f%% · %d 次" % (x["uptime"], x["n"]), bar=relbar(fast, lambda x: x["p50"], True)), 1)
    pr_ = R.get("price", []); b_price = board("价格优势榜", "最新代模型在说得通区间（参考价 40%–125%）内的实付中位数最低；至少 8 个可比模型；数值 = 参考价的几成",
               rank_rows(pr_, lambda x: "%d%%" % round(x["median"] * 100), lambda x: "%d 个可比模型" % x["n"], bar=relbar(pr_, lambda x: x["median"], True)), 2)
    fl = []
    for m in R["flagship"]:
        rows = "".join('<li%s><span class="no">%02d</span><span class="who"><a href="/s/%s">%s</a>%s</span><span class="val">$%s<small>参考价的 %d%%</small></span></li>' % (
            ' class="top"' if i == 0 else "", i + 1, esc(r["vendor"]), esc(r["vendor"]), ('<small>%s</small>' % esc(r["name"])) if r.get("name") else "", fmt(r["out"]), round(r["ratio"] * 100)) for i, r in enumerate(m["rows"]))
        fl.append('<div style="margin-top:14px"><div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap"><a href="/m/%s" style="font-weight:600">%s</a><span class="sub">参考价 $%s · 说得通区间内 %d 家</span></div><ol class="rk">%s</ol></div>' % (esc(m["id"]), esc(m["name"]), fmt(m["floor"]), m["n_inrange"], rows))
    b3 = board("新旗舰榜", "每个最新代模型，说得通区间（参考价 40%–125%）内最低实付的三家；低于成本下限的不计", "".join(fl) or '<div class="callout">样本不足，本期空缺</div>', 3)
    du = R["dual"]; b4 = board("双旗舰榜", "同时在说得通区间卖 GPT-6 Astra 与 Claude Fable 5.1 的站，按两者实付之和",
               rank_rows(du, lambda x: "$%s" % fmt(x["sum"]), lambda x: "GPT-6 $%s + Fable 5.1 $%s" % (fmt(x["gpt6"]), fmt(x["fable"])), bar=relbar(du, lambda x: x["sum"], True)), 4)
    dd = R.get("dist_up", {}); low = R.get("low", [])
    b_up = board("可达榜", "过去 7 天 %d 家过门槛（≥24 次探测，在卖 ≥10 模型）：100%% 有 %d 家 · 99%%–99.9%% 有 %d 家 · 低于 99%% 有 %d 家。下面是可达率最低的 8 家" % (R["eligible_uptime"], dd.get("full", 0), dd.get("hi", 0), dd.get("low", 0)),
               rank_rows(low, lambda x: "%.1f%%" % x["uptime"], lambda x: "%d 次探测 · p50 %sms" % (x["n"], x["p50"] if x["p50"] else "—"), bar=relbar(low, lambda x: x["uptime"], False)), 5)
    vo = R["volatility"]; b5 = board("价格波动榜", "在卖 ≥20 模型的站里，7 天主流模型变价次数最多的（连续两次抓取一致才计一次）；%d/%d 家大站 7 天零变价" % (R["zero_change"], R["n_big"]),
               rank_rows(vo, lambda x: "%d 次" % x["n"], lambda x: "7 天变价", bar=relbar(vo, lambda x: x["n"], False)), 6)
    cv = R["coverage"]; b6 = board("覆盖榜", "在卖模型最多的站（有公开定价接口）", rank_rows(cv, lambda x: "%d" % x["n"], lambda x: "个模型", bar=relbar(cv, lambda x: x["n"], False)), 7)
    pr = "".join('<tr><td><a class="dom" href="/s/%s">%s</a>%s</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td><td>%s</td></tr>' % (
        esc(x["domain"]), esc(x["domain"]), ('<div class="sub">%s</div>' % esc(x["name"])) if x.get("name") else "", x["pairs"], x["consistent"], x["divergent"], x["ts"]) for x in R["probe"])
    b7 = '<section class="card rise" style="margin-top:16px;--i:8"><div class="pad" style="padding-bottom:6px"><h2 class="sec">检测覆盖</h2><p class="lead" style="margin-top:4px">用我们自己的 Key 做过一致性探针的站。一致 = 12 条探针的 token 计数与同模型其他渠道完全相同；不一致 = 计数不同；其余为样本不足。这是一致性测量，不是真伪判定（方法论第 8 节）。</p></div><div class="tablewrap"><table><thead><tr><th>站</th><th class="num">已测模型</th><th class="num">一致</th><th class="num">不一致</th><th>日期</th></tr></thead><tbody>%s</tbody></table></div></section>' % (pr or '<tr><td class="dim">尚无</td></tr>')
    MR = R.get("media") or {}
    def fam_block(items, unit_zh):
        out = []
        for f in items:
            rows = "".join('<li%s><span class="no">%02d</span><span class="who"><a href="/s/%s">%s</a>%s</span><span class="val">$%s<small>%s · 参考价的 %d%%</small></span></li>' % (
                ' class="top"' if i == 0 else "", i + 1, esc(r["site"]), esc(r["site"]), ('<small>%s</small>' % esc(r["name"])) if r.get("name") else "", fmt(r["value"]), unit_zh, round(r["ratio"] * 100)) for i, r in enumerate(f["rows"]))
            out.append('<div style="margin-top:14px"><div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap"><a href="/media/%s" style="font-weight:600">%s</a><span class="sub">官方参考 $%s%s · 说得通区间内 %d 条 · %s 站在卖</span></div><ol class="rk">%s</ol></div>' % (
                esc(f["family"]), esc(f["name"]), fmt(f["ref"]) if f.get("ref") else "—", unit_zh, f["n_inrange"], f.get("n_sites") or "—", rows))
        return "".join(out) or '<div class="callout">样本不足，本期空缺</div>'
    b_v = board("视频合理价榜", "每个有官方参考价的视频族，说得通区间（参考价 40%–125%）内每秒实付最低的三家；按次报价已按公开默认时长折成每秒", fam_block(MR.get("video", []), "/秒"), 9)
    b_i = board("图像合理价榜", "每个有官方参考价的图像族，说得通区间内每张实付最低的三家；分辨率取官方最低档", fam_block(MR.get("image", []), "/张"), 10)
    mc = MR.get("coverage", []); b_mc = board("多模态覆盖榜", "在卖图像 / 视频模型族最多的站（按族计，不按条）", rank_rows(mc, lambda x: "%d" % x["n"], lambda x: "个图像 / 视频族", bar=relbar(mc, lambda x: x["n"], False)), 11)
    mpz = MR.get("price", []); b_mp = board("多模态价格优势榜", "图像 / 视频报价在说得通区间内的实付中位数最低；至少 5 条可比报价；数值 = 官方参考价的几成", rank_rows(mpz, lambda x: "%d%%" % round(x["median"] * 100), lambda x: "%d 条可比报价" % x["n"], bar=relbar(mpz, lambda x: x["median"], True)), 12)
    media_html = '<div class="rise" style="--i:8.5;margin-top:26px"><div class="eyebrow" style="color:var(--p)">多模态 · 图像与视频</div><h2 style="font-size:22px;margin:6px 0 0">按秒、按张，对着官方价比</h2><p class="lead">Seedance、Kling、Veo、Hailuo、Vidu、Wan 与 Nano Banana、Seedream、Qwen-Image、FLUX 在中转站的实付，与官方按秒 / 按张价放在同一把尺上。这是别处没有的数据。</p></div><div class="rkgrid">%s%s</div><div class="rkgrid">%s%s</div>' % (b_v, b_i, b_mc, b_mp)
    hist = "".join('<a href="/rank/%s">%s</a>' % (esc(w), esc(w)) for w in all_weeks)
    foot = '<div class="tfoot" style="margin-top:16px"><span>按测量值排序，不构成推荐；排序不含任何商业变量。数据 %s · 窗口 7 天 · 方法见 <a href="/method">方法论</a>。永久链接 /rank/%s</span></div><div class="callout" style="margin-top:12px"><b>期号徽章</b>：响应榜、价格优势榜、双旗舰榜、覆盖榜、多模态价格优势榜上的站，可在各自站点页拿到带期号的徽章嵌入代码；徽章只显示榜名、名次、测量值与期号，点击回到当期榜单。</div><div class="mlinks card" style="margin-top:12px"><span class="vn">历次榜单</span>%s</div>' % (R["date"], esc(wk), hist)
    body = head + '<div class="rkgrid">%s%s</div>%s<div class="rkgrid">%s%s%s%s</div>%s%s%s' % (b_fast, b_price, b3, b4, b_up, b5, b6, media_html, b7, foot)
    image_head = '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:type" content="image/png"><meta property="og:image:alt" content="%s"><meta name="twitter:image:alt" content="%s">' % (esc(seo["image_alt"]), esc(seo["image_alt"]))
    return shell(title, desc, path, body, active="rank", page="rank", crumbs=[("司南榜",)], og_image=seo["image"], jsonld=[seo["jsonld"]], extra_head=image_head + '<link rel="alternate" type="application/rss+xml" title="Sinan Compute 价格变动" href="/feed.xml">')

def load_rank_weeks():
    rd = os.path.join(HERE, "rank"); return sorted([f[:-5] for f in os.listdir(rd) if f.endswith(".json")], reverse=True) if os.path.exists(rd) else []


# ------------------------------------------------------------------ 自测：用你的 Key 测一个站（Key 不出浏览器）
def build_check():
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">自测 · 登录后可用</div><h1 style="font-size:26px;margin-top:6px">用你的 Key 测一个站</h1><p class="lead">填一个中转站地址和你在该站的 Key，浏览器直接向该站发 8 条固定探针请求（每条只要 4 个输出 token，一次自测通常不到一分钱），把返回的 token 计数、回显模型名、首字节延迟，和我们从多个渠道得到的参考计数逐位比对。<b>Key 只在你的浏览器里，不上传、不落库、不经过我们的服务器。</b></p></div>
<div id="gate" class="card pad rise" style="--i:1"><div class="callout">正在读取登录状态…</div></div>
<section class="card pad rise" id="form" style="--i:1;display:none">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><label style="display:block"><span class="sub">中转站地址（域名或 https://…）</span><input id="ck-base" list="qlist" placeholder="例如 toapis.cn" style="width:100%;margin-top:6px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit"></label>
<label style="display:block"><span class="sub">你在该站的 API Key（只在本页内存里用，刷新即忘）</span><input id="ck-key" type="password" autocomplete="off" placeholder="sk-…" style="width:100%;margin-top:6px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit"></label></div>
<div style="margin-top:14px"><span class="sub">要测的模型（默认用归一后的模型 id 作为请求里的 model；站方原名不同时可改）</span><div id="ck-models" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px"></div></div>
<div style="display:flex;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap"><button class="btn p" id="ck-run">开始测试</button><span class="sub" id="ck-status"></span></div>
<datalist id="qlist"></datalist>
</section>
<section class="card rise" id="ck-out" style="--i:2;margin-top:16px;display:none"><div class="pad" style="padding-bottom:6px"><h2 class="sec">结果</h2><p class="lead" id="ck-lead"></p></div><div class="tablewrap"><table><thead><tr><th>模型</th><th>回显模型名</th><th class="num">成功</th><th class="num">首字节 p50</th><th>计数比对</th><th>判定</th></tr></thead><tbody id="ck-rows"></tbody></table></div><div class="pad" style="padding-top:8px"><button class="btn o" id="ck-report">把结果（不含 Key）提交给司南，帮助扩大检测覆盖</button> <span class="sub" id="ck-rep-status"></span><p class="disc" style="margin-top:10px">判定只有四种：一致 / 含固定前缀 / 不一致 / 无参考。标"弱参考"的模型，参考计数只来自 2 个渠道的一致结果，可信度低于 3 个以上渠道。"不一致"表示该渠道对同一输入返回的 token 计数与多渠道共识不同，成因很多（上游分流、系统提示注入、量化、缓存），本站不推测。这是一致性测量，不是真伪判定。</p></div></section>
<script id="d" type="application/json">{{data}}</script>
<script>(function(){
var D0=JSON.parse(document.getElementById("d").textContent);var gate=document.getElementById("gate"),form=document.getElementById("form");
var dl=document.getElementById("qlist");D0.site_index.forEach(function(x){var o=document.createElement("option");o.value=x.d;dl.appendChild(o);});
fetch("/api/me",{credentials:"include"}).then(function(r){return r.json();}).catch(function(){return {};}).then(function(me){
 if(!me||!me.user){gate.innerHTML='<h2 class="sec">登录后可用</h2><p class="lead">自测需要登录（GitHub 一键，不设密码），用来防滥用和让你可以把结果回流给我们。你的 Key 始终只在你自己的浏览器里。</p><a class="btn p" style="margin-top:12px" href="/api/auth/github/start?return_to=/check">用 GitHub 登录 →</a>';return;}
 gate.style.display="none";form.style.display="block";
 var TR=null;fetch("/assets/tokref.json").then(function(r){return r.json();}).then(function(t){TR=t;var box=document.getElementById("ck-models");
  D0.models.forEach(function(m){var has=TR.models[m.id]&&TR.models[m.id].ref;var lab=document.createElement("label");lab.className="chip";lab.style.cssText="display:inline-flex;gap:6px;align-items:center;cursor:pointer";lab.innerHTML='<input type="checkbox" value="'+m.id+'" '+(has?'checked':'')+'> <span>'+m.name+'</span>'+(has?'<small class="sub">参考 '+TR.models[m.id].peers+' 渠道'+(TR.models[m.id].weak?'（弱）':'')+'</small>':'<small class="sub">无参考</small>');box.appendChild(lab);});
 });
 var fmt=function(v){return v==null?"—":(v<1?v.toFixed(3):v<100?v.toFixed(2):v.toFixed(0));};
 document.getElementById("ck-run").addEventListener("click",async function(){
  var base=document.getElementById("ck-base").value.trim().replace(/^https?:\/\//,"").replace(/\/.*$/,"");var key=document.getElementById("ck-key").value.trim();
  var models=[].slice.call(document.querySelectorAll("#ck-models input:checked")).map(function(i){return i.value;});
  var st=document.getElementById("ck-status");if(!base||!key||!models.length||!TR){st.textContent="请填地址、Key，并至少选一个模型。";return;}
  document.getElementById("ck-out").style.display="block";var rows=document.getElementById("ck-rows");rows.innerHTML="";window.__CK=[];
  document.getElementById("ck-lead").textContent="被测站 "+base+" · "+models.length+" 个模型 × "+TR.probes.length+" 条探针 · 参考计数版本 "+TR.version+"（"+TR.generated_at.slice(0,10)+"）";
  for(var mi=0;mi<models.length;mi++){var m=models[mi];var name=(D0.models.filter(function(x){return x.id===m;})[0]||{}).name||m;st.textContent="正在测 "+name+" …";
   var counts=[],tt=[],echo="",ok=0,err="";
   for(var i=0;i<TR.probes.length;i++){var t0=performance.now();try{var r=await fetch("https://"+base+"/v1/chat/completions",{method:"POST",headers:{"Authorization":"Bearer "+key,"Content-Type":"application/json"},body:JSON.stringify({model:m,messages:[{role:"user",content:TR.probes[i]}],max_tokens:4})});tt.push(performance.now()-t0);
     if(!r.ok){err="HTTP "+r.status;counts.push(null);continue;}var j=await r.json();echo=j.model||echo;var u=(j.usage||{}).prompt_tokens;counts.push(u==null?null:u);if(u!=null)ok++;}catch(e){counts.push(null);tt.push(null);err=e.name==="TypeError"?"浏览器被该站拒绝跨域（CORS）或网络错误":String(e);}}
   var ref=(TR.models[m]||{}).ref,weak=!!(TR.models[m]||{}).weak,verdict="no_ref",vt="无参考",detail="";
   if(!ok){verdict="failed";vt="请求失败";detail=err;}
   else if(ref){var ds=[];for(var k=0;k<ref.length;k++){if(counts[k]!=null&&ref[k]!=null)ds.push(counts[k]-ref[k]);}var uniq=ds.filter(function(v,i,a){return a.indexOf(v)===i;});
     if(uniq.length===1&&uniq[0]===0){verdict="consistent";vt="一致";}else if(uniq.length===1){verdict="prefix";vt="含固定前缀约 "+uniq[0]+" token";}else{verdict="divergent";vt="不一致";}
     if(weak)vt+=" · 弱参考";
     detail=counts.map(function(c,k){return (c==null?"—":c)+"/"+(ref[k]==null?"—":ref[k]);}).join(" ");}
   else detail=counts.map(function(c){return c==null?"—":c;}).join(" ");
   var sorted=tt.filter(function(x){return x!=null;}).sort(function(a,b){return a-b;});var p50=sorted.length?Math.round(sorted[Math.floor(sorted.length/2)]):null;
   var cls={consistent:"explainable",prefix:"below_bulk",divergent:"unsustainable",no_ref:"held",failed:"held"}[verdict];
   rows.insertAdjacentHTML("beforeend",'<tr><td><b>'+name+'</b><div class="sub">'+m+'</div></td><td class="sub">'+(echo||"—")+'</td><td class="num">'+ok+'/'+TR.probes.length+'</td><td class="num">'+(p50==null?"—":p50+"ms")+'</td><td class="sub" style="font-family:var(--mono);font-size:11px">'+detail+'</td><td><span class="pill '+cls+'">'+vt+'</span></td></tr>');
   window.__CK.push({base:base,model:m,raw_model:m,counts:counts,echo:echo,ttfb_ms:tt,ok:ok,verdict:verdict});}
  st.textContent="完成。";});
 document.getElementById("ck-report").addEventListener("click",function(){var s=document.getElementById("ck-rep-status");if(!window.__CK||!window.__CK.length){s.textContent="先测一次。";return;}s.textContent="提交中…";Promise.all(window.__CK.map(function(x){return fetch("/api/check/report",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify(x)});})).then(function(){s.textContent="已提交 "+window.__CK.length+" 条，谢谢。结果进入待审核队列，审核后计入该站的检测覆盖。";}).catch(function(){s.textContent="提交失败，稍后再试。";});});
});})();</script>""", data=jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "models": [{"id": m["id"], "name": m["name"]} for m in D["models"] if m["is_latest"]]}))
    return shell("用我的 Key 测一个站 · Sinan Compute", "登录后用你自己的 Key 在浏览器里测一个中转站：8 条固定探针，比对 token 计数、回显模型名与延迟。Key 不上传。", "/check", body, active="check", page="check", crumbs=[("用我的 Key 测",)], extra_head='<meta name="robots" content="noindex">')

def build_weekly_index(all_weeks):
    rows = "".join('<tr><td><a class="name" href="/weekly/%s">%s</a></td><td>%s – %s</td><td class="num">%d</td><td class="num">%d</td></tr>' % (esc(w["week"]), esc(w["week"]), min(w["days"]), max(w["days"]), len(w["changes"]), sum(len(v) for v in w["new_sites"].values())) for w in all_weeks)
    body = '<div class="rise" style="--i:0;margin-bottom:14px"><h1 style="font-size:24px">中转站价格周报</h1><p class="lead">每周自动生成：价格变动、新收录、每个模型本周说得通的最低实付。订阅 <a href="/feed.xml" style="color:var(--p-ink)">RSS</a> 每天收变动。</p></div><section class="card rise"><div class="tablewrap"><table><thead><tr><th>周</th><th>日期</th><th class="num">变价</th><th class="num">新收录</th></tr></thead><tbody>%s</tbody></table></div></section><script id="d" type="application/json">%s</script>' % (rows or '<tr><td class="dim">尚无</td></tr>', jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": x["id"], "name": x["name"]} for x in D["models"]]}))
    return shell("中转站价格周报 · Sinan Compute", "每周自动生成的模型 API 中转站价格变动周报。", "/weekly", body, active="home", page="weekly", crumbs=[("价格周报",)])

def badge_svg(s):
    av = s.get("avail") or {}; cl = s.get("cluster")
    up = ("%.0f%%" % av["uptime"]) if av.get("uptime") is not None else "—"
    pic = (cl["name"] if cl else "暂无报价")
    color = {"ultra": "#F04438", "cheap": "#F79009", "near": "#17B26A", "high": "#6E56F5", "held": "#9AA0B8"}.get(cl["code"] if cl else "", "#9AA0B8")
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="340" height="64" viewBox="0 0 340 64" role="img" aria-label="Sinan Compute 实测 %s">'
            '<rect width="340" height="64" rx="14" fill="#0F1222"/><rect x="12" y="14" width="36" height="36" rx="10" fill="#6E56F5"/><path d="M30 20 L36 32 L30 44 Z" fill="#fff"/><path d="M30 20 L24 32 L30 44 Z" fill="#B9ADFF"/>'
            '<text x="60" y="27" font-family="-apple-system,Segoe UI,PingFang SC,Noto Sans SC,sans-serif" font-size="12" fill="#A3B1BE">Sinan Compute 实测 · %s</text>'
            '<text x="60" y="48" font-family="-apple-system,Segoe UI,PingFang SC,Noto Sans SC,sans-serif" font-size="14" font-weight="600" fill="#fff">24h 可达 %s</text>'
            '<rect x="%d" y="35" width="%d" height="18" rx="9" fill="%s" opacity=".18"/><text x="%d" y="48" font-family="-apple-system,Segoe UI,PingFang SC,Noto Sans SC,sans-serif" font-size="12" font-weight="600" fill="%s">%s</text>'
            '<text x="328" y="27" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="10" fill="#64768A">%s</text></svg>'
            % (esc(s["domain"]), esc(s["domain"]), up, 170, 12 * len(pic) + 20, color, 180, color, esc(pic), GEN_DATE[5:]))

def rank_badge_svg(s):
    """期号徽章：只显示期号、榜名、名次、测量值，点回榜页。"""
    b = s["rank_badge"]; label = "%s #%02d" % (b["board_name"], b["pos"])
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="340" height="64" viewBox="0 0 340 64" role="img" aria-label="司南榜 %s %s %s">'
            '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1B1650"/><stop offset="1" stop-color="#3A2AA8"/></linearGradient></defs>'
            '<rect width="340" height="64" rx="14" fill="url(#g)"/><rect x="12" y="14" width="36" height="36" rx="10" fill="#6E56F5"/><path d="M22 24h16v6a8 8 0 0 1-16 0z" fill="#fff"/><path d="M26 40h8M30 36v4" stroke="#fff" stroke-width="2"/>'
            '<text x="60" y="27" font-family="-apple-system,Segoe UI,PingFang SC,Noto Sans SC,sans-serif" font-size="12" fill="#B9ADFF">司南榜 · %s · 测量榜单</text>'
            '<text x="60" y="48" font-family="-apple-system,Segoe UI,PingFang SC,Noto Sans SC,sans-serif" font-size="15" font-weight="700" fill="#fff">%s</text>'
            '<text x="328" y="27" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="10" fill="#B9ADFF">%s</text>'
            '<text x="328" y="48" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="12" fill="#fff">%s</text></svg>'
            % (esc(b["week"]), esc(label), esc(s["domain"]), esc(b["week"]), esc(label), esc(s["domain"]), esc(b["value"])))

def build_404():
    body = '<div class="card pad rise" style="--i:0;max-width:640px"><div class="eyebrow" style="color:var(--p)">404</div><h1 style="font-size:28px;margin-top:8px">没有这个页面。</h1><p class="lead">地址可能拼错了，或者这个站还没被收录。试试上面的搜索框，或者：</p><div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap"><a class="btn p" href="/">回首页</a><a class="btn o" href="/sites">中转站总表</a><a class="btn o" href="/media">图像 · 视频</a></div></div><script id="d" type="application/json">%s</script>' % jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]})
    return shell("没有这个页面 · Sinan Compute", "页面不存在。", "/404", body, page="404")

# ------------------------------------------------------------------ main
def main():
    if os.path.exists(DIST): shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "s")); os.makedirs(os.path.join(DIST, "assets"))
    W = lambda rel, s: io.open(os.path.join(DIST, rel), "w", encoding="utf-8").write(s)
    W("assets/app.css", CSS); W("assets/app.js", APP_JS); W("assets/earth.js", EARTH_JS)
    W("index.html", build_index()); W("sites.html", build_sites()); W("me.html", build_me());
    os.makedirs(os.path.join(DIST, "m"), exist_ok=True)
    for m in D["models"]: W("m/%s.html" % m["id"], build_model(m))
    W("feed.xml", build_feed()); W("llms.txt", build_llms())
    if MEDIA:
        os.makedirs(os.path.join(DIST, "media"), exist_ok=True)
        for mod in ("video", "image"):
            for f in MEDIA.get(mod, []):
                if f.get("n_rows"): W("media/%s.html" % f["family"], build_family(f, mod))
    weeks = load_weeks()
    if weeks:
        os.makedirs(os.path.join(DIST, "weekly"), exist_ok=True)
        for w in weeks: W("weekly/%s.html" % w["week"], build_weekly(w, weeks))
        W("weekly.html", build_weekly_index(weeks))
    W("check.html", build_check())
    if os.path.exists(os.path.join(HERE, "tokref.json")): shutil.copy(os.path.join(HERE, "tokref.json"), os.path.join(DIST, "assets", "tokref.json"))
    rank_snapshots = []
    if D.get("rank"):
        rws = load_rank_weeks()
        rank_snapshots.append(D["rank"])
        W("rank.html", build_rank(D["rank"], rws))
        os.makedirs(os.path.join(DIST, "rank"), exist_ok=True)
        for wk_ in rws:
            RJ = json.load(io.open(os.path.join(HERE, "rank", wk_ + ".json"), encoding="utf-8"))
            rank_snapshots.append(RJ)
            W("rank/%s.html" % wk_, build_rank(RJ, rws, path="/rank/" + wk_))
    os.makedirs(os.path.join(DIST, "badge"), exist_ok=True)
    for s in D["sites"]: W("badge/%s.svg" % s["domain"], badge_svg(s))
    ranked = [s for s in D["sites"] if s.get("rank_badge")]
    if ranked:
        wk_ = ranked[0]["rank_badge"]["week"]
        os.makedirs(os.path.join(DIST, "badge", "rank", wk_), exist_ok=True)
        for s in ranked:
            svg = rank_badge_svg(s); W("badge/rank/%s.svg" % s["domain"], svg); W("badge/rank/%s/%s.svg" % (wk_, s["domain"]), svg)   # 最新一期 + 期号永久版
    kf = os.path.join(HERE, "indexnow.key")
    if os.path.exists(kf):
        k = io.open(kf).read().strip(); W("%s.txt" % k, k)
    W("method.html", build_method()); W("404.html", build_404())
    mp = build_media()
    if mp: W("media.html", mp)
    n = 0
    for s in D["sites"]:
        W("s/%s.html" % s["domain"], build_site(s)); n += 1
    for d_ in ("fonts", "img", "history"):
        if os.path.exists(os.path.join(HERE, d_)): shutil.copytree(os.path.join(HERE, d_), os.path.join(DIST, d_))
    if rank_snapshots:
        # Exports can refresh between seo_assets.py and this build. Generate
        # from the same objects as the HTML, not another read of live files.
        from seo_assets import generate_rank_snapshot_images
        generate_rank_snapshot_images(rank_snapshots, output=os.path.join(DIST, "img"))
    for f in ("data_v2.json", "media.json", "go_links.json"):
        if os.path.exists(os.path.join(HERE, f)): shutil.copy(os.path.join(HERE, f), os.path.join(DIST, f))
    if os.path.exists(os.path.join(HERE, "static")):   # 站长平台验证文件等原样放根目录
        for f in os.listdir(os.path.join(HERE, "static")): shutil.copy(os.path.join(HERE, "static", f), os.path.join(DIST, f))
    W("assets/ledger.json", jsdata({"models": D["models"], "snaps": D["snaps"]}))
    W("robots.txt", "User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % BASE)
    urls = [("/", "daily"), ("/sites", "daily"), ("/media", "daily"), ("/method", "weekly"), ("/weekly", "weekly"), ("/rank", "weekly")] + [("/rank/%s" % w_, "weekly") for w_ in load_rank_weeks()] + [("/m/%s" % m["id"], "daily") for m in D["models"]] + ([("/media/%s" % f["family"], "daily") for mod in ("video", "image") for f in MEDIA.get(mod, []) if f.get("n_rows")] if MEDIA else []) + [("/weekly/%s" % w["week"], "weekly") for w in load_weeks()] + [("/s/%s" % s["domain"], "daily") for s in D["sites"]]
    W("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join('  <url><loc>%s%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq></url>\n' % (BASE, u, GEN_DATE, c) for u, c in urls) + "</urlset>\n")
    W("favicon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="10" fill="#4B36D6"/><circle cx="20" cy="20" r="14" fill="none" stroke="#B9ADFF" stroke-width="1.5" opacity=".6"/><path d="M20 9 L24.5 20 L20 31 Z" fill="#fff"/><path d="M20 9 L15.5 20 L20 31 Z" fill="#B9ADFF"/><circle cx="20" cy="20" r="2.2" fill="#4B36D6" stroke="#fff" stroke-width="1.4"/></svg>')
    W("_headers", "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/assets/*\n  Cache-Control: public, max-age=604800\n/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n/img/*\n  Cache-Control: public, max-age=2592000\n")
    print("dist/ 生成完成：index · sites · media · method · 404 · 站点页 %d · 大小 index %d KB" % (n, os.path.getsize(os.path.join(DIST, "index.html")) // 1024))

if __name__ == "__main__":
    main()
