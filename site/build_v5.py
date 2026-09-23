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
DIST = os.environ.get("SINAN_DIST") or os.path.join(HERE, "dist")
BASE = "https://compute.sinanlab.com"
D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
MEDIA = json.load(io.open(os.path.join(HERE, "media.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "media.json")) else None
GEN_DATE = D["generated_at"][:10]
D_MODELS = {m["id"]: m for m in D["models"]}

LABEL = {"unsustainable": "数学上不可持续", "below_bulk": "低于常见批量折扣", "explainable": "价格说得通", "normal": "与公开价接近", "premium": "高于公开价", "far_above": "显著高于公开价"}
BANDC = {"unsustainable": "#F04438", "below_bulk": "#F79009", "explainable": "#17B26A", "normal": "#17B26A", "premium": "#6E56F5", "far_above": "#9AA0B8"}
DISCLAIMER = "此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。"

def _safe_snip(v):
    """上游自述原文的兜底：含禁用词 / 像 base64 / 带标签的片段不上页。"""
    try:
        from core.wording import BANNED as _B
        low = str(v).lower()
        if any(w.lower() in low for w in _B): return None
    except Exception: pass
    if re.search(r"[A-Za-z0-9+/=]{24,}|[<>{}\[\]]|https?://", str(v)): return None
    return str(v)

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
.brand .mark{width:36px;height:36px;border-radius:10px;background:#07070B url(/brand/sinanlab-mark.svg) center/28px 28px no-repeat;box-shadow:0 8px 18px -10px rgba(7,7,11,.6);flex:none}
.subbox{display:flex;gap:24px;align-items:center;flex-wrap:wrap;margin-top:44px;padding:22px 26px;border:1px solid var(--hair);border-radius:18px;background:var(--card)}.subbox>div{flex:1 1 320px}.subform{display:flex;gap:8px;align-items:center;flex-wrap:wrap;flex:1 1 320px;justify-content:flex-end}.subform input{flex:1 1 220px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit;font-size:14px;background:var(--card);color:var(--ink)}.subform .sub{flex-basis:100%;text-align:right}
.mv{font-family:var(--mono);font-size:11px;border-radius:999px;padding:2px 7px;flex:none;background:var(--ground-2);color:var(--ink-2)}.mv.up{background:#DCFAE6;color:#067647}.mv.down{background:#FEE4E2;color:#B42318}.mv.new{background:#EDE9FE;color:#5B3FD6}.mv.same{opacity:.7}
.repfoot{margin-top:18px;padding-top:12px;border-top:1px dashed var(--hair-2);display:flex;gap:10px;align-items:center;flex-wrap:wrap}.rep{background:none;border:1px solid var(--hair-2);border-radius:999px;padding:4px 10px;font:inherit;font-size:12px;color:var(--ink-2);cursor:pointer}.rep:hover{border-color:var(--ink);color:var(--ink)}.repform{flex-basis:100%;display:grid;gap:8px;margin-top:6px}.repform textarea,.repform input{width:100%;padding:8px 10px;border:1px solid var(--hair-2);border-radius:10px;font:inherit;font-size:13px;background:var(--card);color:var(--ink)}
.pollrow{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:12px}.pollrow .btn[disabled]{opacity:.5;cursor:default}
.pledge{display:flex;flex-wrap:wrap;gap:8px 22px;margin:14px 0 0;padding:12px 16px;border:1px dashed var(--hair-2);border-radius:14px;font-size:12.5px;color:var(--ink-2)}.pledge b{color:var(--ink);margin-right:6px}
.brandband{background:#07070B;border-radius:18px;padding:26px 32px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;margin-top:44px}.brandband img{width:480px;max-width:100%;height:auto;display:block}.brandband span{color:#B8A4FA;font-size:13px;letter-spacing:.08em;margin-left:auto}
.rkmini{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:14px}.rkmini .card{padding:16px 18px}.rkmini h4{margin:0;font-size:13.5px}.rkmini .q{font-size:11.5px;color:var(--ink-3);margin-top:3px;line-height:1.5;min-height:34px}.rkmini ol{list-style:none;margin:12px 0 0;padding:0}.rkmini li{display:flex;align-items:baseline;gap:8px;padding:6px 0;border-top:1px solid var(--hair);font-size:13px}.rkmini li .no{font-family:var(--mono);font-size:11px;color:var(--ink-3);width:18px}.rkmini li a{font-weight:600}.rkmini li .val{margin-left:auto;font-family:var(--mono);font-size:12px}
.det{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}.det .card{padding:18px 20px}.det .k{font-size:12px;color:var(--ink-3);letter-spacing:.04em}.det .v{font-family:var(--mono);font-size:26px;font-weight:600;margin-top:6px}.det .v small{font-size:12px;color:var(--ink-3);font-weight:400;margin-left:4px}.det p{font-size:12.5px;color:var(--ink-2);line-height:1.6;margin:8px 0 0}
.prods{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}.prods a.card{padding:18px 20px;display:block}.prods b{display:block;font-size:15px}.prods p{margin:6px 0 0;font-size:12.5px;color:var(--ink-3);line-height:1.55}
@media (max-width:860px){.rkmini,.det,.prods{grid-template-columns:1fr 1fr}}@media (max-width:560px){.rkmini,.det,.prods{grid-template-columns:1fr}}
.brand b{font-size:17px;font-weight:700;letter-spacing:-.01em;display:block}.brand small{display:block;font-size:10.5px;color:var(--ink-3);font-weight:500;letter-spacing:.04em;margin-top:1px}
.sect{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);padding:14px 10px 6px;font-weight:600}
.nav{display:flex;align-items:center;gap:11px;padding:10px 12px;border-radius:12px;color:var(--ink-2);font-weight:500;transition:background .25s var(--ease),color .25s var(--ease),transform .25s var(--ease);white-space:nowrap}
.nav svg{width:18px;height:18px;flex:none;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.nav:hover{background:var(--ground);color:var(--ink);transform:translateX(2px)}
.nav.on{background:linear-gradient(135deg,#7A63FF,#5642DF);color:#fff;box-shadow:0 10px 22px -12px rgba(75,54,214,.8)}
.nav .badge{margin-left:auto;font-family:var(--mono);font-size:10.5px;background:var(--ground);color:var(--ink-2);padding:2px 7px;border-radius:999px}.nav.on .badge{background:rgba(255,255,255,.2);color:#fff}
.robo{margin-top:auto;border-radius:16px;padding:14px;background:linear-gradient(160deg,#FFF6E8,#FFE9C7);border:1px solid #FFE1B3;position:relative;overflow:hidden;display:block}
.robo .gl{position:absolute;right:-14px;top:-14px;width:54px;height:54px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#FFD27A,#F79009 60%,#C96A00);box-shadow:inset -8px -10px 18px rgba(120,60,0,.35)}
.robo b{font-size:13px;display:block;position:relative;padding-right:40px}.robo p{margin:4px 0 0;font-size:12px;color:#7A4B00;max-width:130px}
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
.hero{min-height:500px;border-radius:24px;overflow:hidden;position:relative;background:radial-gradient(600px 300px at 12% 0%,rgba(110,86,245,.28),transparent 60%),#07070B;color:#fff;box-shadow:0 2px 6px rgba(20,22,50,.1),0 30px 60px -24px rgba(10,10,40,.7);isolation:isolate}
.hero canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
.hero .stars{pointer-events:none}.hero #gl{cursor:grab;z-index:1}.hero #gl:active{cursor:grabbing}
.hero .scrim{position:absolute;inset:0;background:linear-gradient(100deg,rgba(7,7,11,.72) 0%,rgba(7,7,11,.35) 42%,rgba(7,7,11,0) 68%);pointer-events:none}
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
.chips{display:flex;flex-direction:column;gap:0;padding:10px 24px 6px}
.chips .vrow{display:grid;grid-template-columns:104px 1fr;gap:10px 14px;align-items:center;padding:8px 0;border-top:1px solid var(--hair)}.chips .vrow:first-child{border-top:0}
.chips .vc{display:flex;flex-wrap:wrap;gap:8px}.chips .vrow.tail{border-top:1px dashed var(--hair)}
.chips .vn{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}
@media (max-width:560px){.chips .vrow{grid-template-columns:1fr;gap:6px}}
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
@media (max-width:860px){.app{grid-template-columns:1fr}.rail{position:static;height:auto;flex-direction:row;flex-wrap:nowrap;overflow-x:auto;gap:4px;padding:10px 12px;align-items:center}.rail .sect,.rail .robo{display:none}.rail .brand{padding:4px 8px;flex:none}.rail .brand small{display:none}.nav{padding:8px 10px;font-size:13px;flex:none}.nav .badge{display:none}.main{padding:16px}.hero{min-height:560px}.hero .txt{padding:26px 24px 30px;max-width:none}.hero h1{font-size:32px}.hero .scrim{background:linear-gradient(180deg,rgba(7,7,11,.75) 0%,rgba(7,7,11,.3) 50%,transparent 75%)}.hero .tag{display:none}.fams{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}.asof{display:none}.bento{grid-template-columns:1fr 1fr}.facts{grid-template-columns:1fr 1fr}.sitehead h1{font-size:22px}}
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
var REPFOOT='<div class="repfoot"><button class="rep" data-kind="quote">这条数据有误？报错</button><span class="sub" id="repmsg"></span></div>';
function openD(eye,title,html){document.getElementById("deye").textContent=eye;document.getElementById("dtitle").textContent=title;document.getElementById("dbody").innerHTML=html+REPFOOT;drawer.classList.add("on");scrim.classList.add("on");settleNeedles(drawer);}
document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest(".rep"):null;if(!b)return;var host=b.parentNode;if(host.querySelector("textarea"))return;var ctx=b.dataset.ctx||(document.getElementById("dtitle")||{}).textContent||document.title;var key=b.dataset.key||ctx;
host.insertAdjacentHTML("beforeend",'<div class="repform"><textarea rows="3" placeholder="'+(b.dataset.kind==="plan"?"把你买的套餐名、价格、周期、额度填进去，我们匿名汇总后按站显示中位价":"哪里不对？例如：该站 9 月 15 日面板显示 2.5 元/$，你们记的是 1.5。")+'">'+(b.dataset.tpl||"")+'</textarea><input placeholder="佐证链接（可选，http 开头）"><div style="display:flex;gap:8px;align-items:center"><button class="btn p" type="button">提交</button><span class="sub"></span></div></div>');
var f=host.querySelector(".repform"),ta=f.querySelector("textarea"),url=f.querySelector("input"),go=f.querySelector("button"),M=f.querySelector("span");
go.addEventListener("click",function(){var n=ta.value.trim();if(n.length<4){M.textContent="写一句哪里不对。";return;}M.textContent="提交中…";fetch("/api/report",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind:b.dataset.kind||"other",key:key,context:ctx,note:n,url:url.value.trim()})}).then(function(r){return r.json();}).then(function(j){if(j.ok){f.innerHTML='<span class="sub">已收到，核对后会记进 <a href="/corrections">修正日志</a>，署你的名。谢谢。</span>';}else if(j.error==="login_required"){M.innerHTML='报错需要登录（防刷）。<a href="/login?return_to='+encodeURIComponent(location.pathname)+'">登录 →</a>';}else{M.textContent={too_many_requests:"今天提交太多了",bad_url:"佐证链接要以 http 开头",note_too_short:"再多写几个字"}[j.error]||"出错了";}}).catch(function(){M.textContent="网络错误";});});});
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
  note.innerHTML='黑线 = 该站实付 · 紫虚线 = 最低公开参考价 · 记录 '+S.length+' 个变价点'+(full?'（全部历史）':'（最近 7 天，<a href="/login?return_to='+encodeURIComponent(location.pathname)+'" style="color:var(--p-ink)">登录</a>看全部）');}
 if(HISTC[m]){paint(HISTC[m]);return;}
 fetch(full?"/api/history/"+m:"/history/"+m+".json",{credentials:"include"}).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(j){HISTC[m]=j;paint(j);}).catch(function(){if(full){fetch("/history/"+m+".json").then(function(r){return r.json();}).then(function(j){HISTC[m]=j;paint(j);}).catch(function(){note.textContent="暂无走势数据。";});}else{note.textContent="暂无走势数据。";}});}
var _openD=openD;openD=function(eye,title,html){_openD(eye,title,html);var cv=document.querySelector("#dbody canvas.hist");if(cv)drawHist(cv);};
document.addEventListener("click",function(e){var h=e.target.closest?e.target.closest(".help"):null;if(h){openD("这个标签什么意思",LABEL[h.dataset.help]||"",helpHtml(h.dataset.help));return;}});
/* 搜索 */
(function(){var q=document.getElementById("q");if(!q||!D.site_index)return;var dl=document.getElementById("qlist");D.site_index.forEach(function(s){var o=document.createElement("option");o.value=s.d;dl.appendChild(o);});(D.model_index||[]).forEach(function(m){var o=document.createElement("option");o.value=m.name;dl.appendChild(o);});
q.addEventListener("keydown",function(e){if(e.key!=="Enter")return;var v=q.value.trim().toLowerCase();if(!v)return;var s=D.site_index.filter(function(x){return x.d.indexOf(v)>=0||(x.n||"").toLowerCase().indexOf(v)>=0;})[0];if(s){location.href="/s/"+s.d;return;}var m=(D.model_index||[]).filter(function(x){return x.name.toLowerCase().indexOf(v)>=0||x.id.indexOf(v)>=0;})[0];if(m){location.href="/#m="+m.id;if(location.pathname==="/"||location.pathname==="/index.html")location.reload();return;}openD("没找到",q.value,"<p>既不是收录的站，也不是有报价的模型。试试域名（如 toapis.cn）或模型名（如 DeepSeek V4）。</p>");});})();
/* ========== 登录 · 关注 · 公告 ========== */
(function(){var box=document.getElementById("auth");if(!box)return;var ME=null;
function loginUrl(watch){return "/login?return_to="+encodeURIComponent(location.pathname+location.search)+(watch?"&watch="+encodeURIComponent(watch):"");}
function render(){if(ME&&ME.user){box.innerHTML='<div class="menu"><a href="/me" style="display:flex;align-items:center;gap:8px">'+(ME.user.avatar_url?'<img src="'+esc(ME.user.avatar_url)+'" alt="">':'')+'<span style="font-size:13px">'+esc(ME.user.handle||"我")+'</span></a><div class="dd"><a href="/me">我的关注</a><a href="/api/auth/logout?return_to='+encodeURIComponent(location.pathname)+'">退出登录</a></div></div>';}
 else if(ME&&ME.login){box.innerHTML='<a class="lang" href="'+loginUrl("")+'">登录</a><a class="lang" href="'+loginUrl("")+'&mode=signup" style="margin-left:6px">注册</a>';}
 else{box.innerHTML='<span class="lang" title="账号系统接入中" style="opacity:.55;cursor:default">登录 · 即将开放</span>';}
 document.querySelectorAll(".watch").forEach(function(b){if(!b.dataset.key)return;var on=!!(ME&&ME.user&&(ME.watches||[]).some(function(w){return w.kind===b.dataset.kind&&w.key===b.dataset.key;}));b.classList.toggle("on",on);b.textContent=on?"已关注 ✓":(b.dataset.kind==="site"?"关注这个站":"关注这个模型");});
 var al=document.getElementById("alerts");if(al){if(!ME||!ME.user){al.textContent="登录后可以开启邮件提醒。";}else{fetch("/api/prefs",{credentials:"include"}).then(function(r){return r.json();}).then(function(p){if(!p.mail_ready){al.textContent="邮件服务接入中。";return;}if(!p.has_email){al.textContent="你的 GitHub 没有可验证的邮箱，暂时无法开启邮件提醒。";return;}var q=new URLSearchParams(location.search).get("alerts");al.innerHTML='<label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer"><input type="checkbox" id="emailon" style="margin-top:3px" '+(p.email_on?'checked':'')+'> <span>'+(q==="off"?"已通过邮件里的链接关闭提醒。勾上可重新开启。":"邮件提醒：关注对象有变动时发到我的 GitHub 邮箱（每天最多一封）")+'</span></label>';document.getElementById("emailon").addEventListener("change",function(e){fetch("/api/prefs",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({email_on:e.target.checked?1:0})}).then(function(r){return r.json();}).then(function(x){al.querySelector("span").textContent=x.ok?(x.email_on?"已开启邮件提醒 ✓ 关注对象有变动时发到你的 GitHub 邮箱":"已关闭邮件提醒"):"保存失败，请刷新重试";});});}).catch(function(){al.textContent="读取设置失败，请刷新。";});}}
 var ml=document.getElementById("melist");if(ml){if(!ME||!ME.user){ml.innerHTML='<h2 class="sec">还没登录</h2><p class="lead">登录后这里是你关注的站和模型。不设密码：邮箱验证码，或用 Google / GitHub 账号。</p>'+(ME&&ME.login?'<a class="btn p" style="margin-top:14px" href="'+loginUrl("")+'">登录 →</a>':'<div class="callout" style="margin-top:12px">账号系统接入中，开放后即可登录。</div>');}
  else{var ws=ME.watches||[];ml.innerHTML='<h2 class="sec">关注 · '+ws.length+'</h2>'+(ws.length?ws.map(function(w){return '<div class="row"><span class="pill none">'+(w.kind==="site"?"站":"模型")+'</span><a class="dom" href="'+(w.kind==="site"?"/s/"+esc(w.key):"/#m="+esc(w.key))+'">'+esc(w.key)+'</a><button class="evb x watch on" data-kind="'+esc(w.kind)+'" data-key="'+esc(w.key)+'">取消关注</button></div>';}).join(""):'<div class="callout" style="margin-top:12px">还没有关注任何站或模型。到站点页或模型账本点“关注”。</div>');ml.querySelectorAll(".watch").forEach(function(b){b.textContent="取消关注";});}}}
window.__renderAuth=render;
fetch("/api/me",{credentials:"include"}).then(function(r){return r.json();}).then(function(m){ME=m;window.__ME=m;render();}).catch(function(){ME={user:null,login:false};render();});
document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest(".watch"):null;if(!b||!b.dataset.key)return;e.preventDefault();var kind=b.dataset.kind,key=b.dataset.key;
 if(!ME||!ME.user){if(ME&&ME.login){openD("登录后帮你记住它",key,'<p style="font-size:14px;line-height:1.7">登录后这个'+(kind==="site"?"站":"模型")+'会出现在你的关注列表，价格、可达率或探针结果变化时提醒你。不设密码：邮箱验证码，或用 Google / GitHub 账号。</p><a class="btn p" style="margin-top:14px" href="'+loginUrl(kind+":"+key)+'">登录并关注 →</a><p class="disc">Google / GitHub 登录只读取公开资料与邮箱；邮箱只用于登录识别与你自己开启的提醒；所有价格数据不登录也全部可见。</p>');}else{openD("账号系统接入中",key,"<p>开放后这里可以一键关注并收到变化提醒。所有价格数据不登录也全部可见。</p>");}return;}
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
 if(ref)h+='<div class="ref">$'+ref.price.toFixed(3)+'<small>/ '+(mod==="video"?"秒":"张")+' 官方 · '+esc(ref.model)+'</small></div><div class="meta">'+f.n_sites+' 站 · '+f.n_rows+' 条报价'+(mod==="video"&&f.default_clip?' · 按次报价按 1 次 = '+f.default_clip+' 秒折成每秒'+(f.n_assumed?'（'+f.n_assumed+' 条）':''):'')+'</div>';
 else h+='<div class="none">无官方参考价，只列报价，不出比率。'+esc(f.ref_missing||"")+'</div><div class="meta">'+f.n_sites+' 站 · '+f.n_rows+' 条报价</div>';
 if(range){var lo=Math.min(2,range[0])/2*100,hi=Math.min(2,range[1])/2*100;h+='<div class="rng"><i style="left:'+lo.toFixed(1)+'%;width:'+Math.max(2,hi-lo).toFixed(1)+'%"></i></div><div class="rl"><span>实付最低 '+pctm(range[0])+'</span><span>最高 '+pctm(range[1])+'</span></div>';}
 if(rec.length){h+='<table><thead><tr><th>站</th><th class="num">实付</th><th class="num">几成</th></tr></thead><tbody>'+rec.slice(0,6).map(function(r){return '<tr><td><a class="dom" href="/s/'+esc(r.site)+'">'+esc(r.site)+'</a></td><td class="num">'+(r.val!=null?(r.val<0.01?r.val.toFixed(4):r.val.toFixed(3)):(r.eff!=null?r.eff.toFixed(3):"—"))+' <span class="sub" style="display:inline">'+(r.val!=null?(f.canon_unit||(mod==="video"?"$/秒":"$/张")):(r.unit==="per_second"?"$/秒":"$/次"))+(r.val_basis==="assumed"?"<i title=\"按该族默认时长折算\" style=\"font-style:normal;opacity:.6\"> ≈</i>":"")+'</span></td><td class="num">'+(r.ratio!=null?'<span class="r '+r.band+'">'+pctm(r.ratio)+'</span>':'—')+'</td></tr>';}).join("")+'</tbody></table>'+(rec.length>6?'<div class="sub">还有 '+(rec.length-6)+' 条 · 数据文件 media.json</div>':'');}
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
    "pindex": '<path d="M3 17l5-6 4 3 4-5 5 4"/><path d="M3 21h18"/>',
    "gpu": '<rect x="4" y="6" width="16" height="12" rx="2"/><path d="M8 10h3v4H8zM13 10h3v4h-3zM2 9v6M22 9v6"/>',
    "report": '<path d="M6 3h9l4 4v14H6z"/><path d="M9 12h6M9 16h6M9 8h3"/>',
    "verify": '<path d="M12 3l7 3v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "press": '<path d="M4 6h16v12H4z"/><path d="M8 10h8M8 14h5"/>',
    "api": '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M14 5l-4 14"/>',
    "life": '<path d="M3 17l5-6 4 3 5-8 4 5"/><path d="M3 21h18"/>',
    "gov": '<path d="M4 10h16M6 10v8M10 10v8M14 10v8M18 10v8M3 18h18M12 3l9 7H3z"/>',
    "fix": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><circle cx="12" cy="12" r="4"/>',
    "method": '<path d="M4 6h16M4 12h10M4 18h7"/>',
    "data": '<path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="9"/>',
}

import hashlib as _hl
# ---------- 主题：SINAN_THEME=coast（三色：深蓝 #457ea9 · 沙金 #d4bc95 · 浅蓝 #cce0f4）----------
# 只替换颜色与阴影，不动版式；用环境变量切换，正式站默认不受影响。
COAST = [
    ("--ground:#F2F3F9;--ground-2:#E9EAF3;--card:#FFFFFF;--hair:#E6E7F0;--hair-2:#D5D7E6;--ink:#0F1222;--ink-2:#5A6079;--ink-3:#9AA0B8;",
     "--ground:#eef4fa;--ground-2:#e1ecf6;--card:rgba(255,255,255,.9);--hair:#d6e4f0;--hair-2:#c0d4e6;--ink:#14283a;--ink-2:#48607a;--ink-3:#849db3;--sand:#d4bc95;--sand-soft:#f3ebdd;--sand-deep:#b3945f;"),
    ("--p:#6E56F5;--p-deep:#4B36D6;--p-soft:#EEEBFF;--p-ink:#3A2AA8;", "--p:#457ea9;--p-deep:#35678c;--p-soft:#cce0f4;--p-ink:#2b5878;"),
    ("--robo:#F79009;", "--robo:#b3945f;"),
    ("--shadow-1:0 1px 2px rgba(20,22,50,.04),0 8px 24px -12px rgba(20,22,50,.12);--shadow-2:0 2px 6px rgba(20,22,50,.06),0 24px 48px -20px rgba(55,40,160,.22);",
     "--shadow-1:0 1px 2px rgba(20,50,80,.04),0 10px 28px -14px rgba(69,126,169,.28);--shadow-2:0 2px 6px rgba(20,50,80,.06),0 26px 52px -20px rgba(69,126,169,.36);"),
    ("--ease:cubic-bezier(.22,1,.36,1);--spring:cubic-bezier(.34,1.4,.64,1);--r:18px;", "--ease:cubic-bezier(.22,1,.36,1);--spring:cubic-bezier(.34,1.4,.64,1);--r:22px;"),
    ("html,body{margin:0;background:var(--ground);", "html,body{margin:0;background:radial-gradient(1200px 640px at 0% 0%,#cce0f4 0%,rgba(204,224,244,.55) 35%,transparent 70%),radial-gradient(900px 520px at 100% 26%,rgba(212,188,149,.30),transparent 62%),radial-gradient(700px 420px at 60% 100%,rgba(204,224,244,.6),transparent 70%),var(--ground);"),
    (".rail{position:sticky;top:0;height:100vh;background:var(--card);", ".rail{position:sticky;top:0;height:100vh;background:rgba(255,255,255,.66);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);"),
    (".nav.on{background:linear-gradient(135deg,#7A63FF,#5642DF);color:#fff;box-shadow:0 10px 22px -12px rgba(75,54,214,.8)}", ".nav.on{background:linear-gradient(135deg,#5b95c1,#457ea9);color:#fff;box-shadow:0 10px 22px -12px rgba(69,126,169,.85)}"),
    (".robo{margin-top:auto;border-radius:16px;padding:14px;background:linear-gradient(160deg,#FFF6E8,#FFE9C7);border:1px solid #FFE1B3;", ".robo{margin-top:auto;border-radius:16px;padding:14px;background:linear-gradient(160deg,#f7f0e4,#e8d7b8);border:1px solid #d4bc95;"),
    ("background:radial-gradient(circle at 35% 30%,#FFD27A,#F79009 60%,#C96A00);box-shadow:inset -8px -10px 18px rgba(120,60,0,.35)", "background:radial-gradient(circle at 35% 30%,#f2e2c4,#d4bc95 60%,#a8864f);box-shadow:inset -8px -10px 18px rgba(90,60,20,.35)"),
    (".robo p{margin:4px 0 0;font-size:12px;color:#7A4B00;", ".robo p{margin:4px 0 0;font-size:12px;color:#6a5030;"),
    (".card{background:var(--card);border:1px solid var(--hair);border-radius:var(--r);box-shadow:var(--shadow-1)}", ".card{background:var(--card);border:1px solid var(--hair);border-radius:var(--r);box-shadow:var(--shadow-1);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}"),
    ("background:radial-gradient(600px 300px at 12% 0%,rgba(110,86,245,.28),transparent 60%),#07070B;color:#fff;box-shadow:0 2px 6px rgba(20,22,50,.1),0 30px 60px -24px rgba(10,10,40,.7);",
     "background:radial-gradient(700px 340px at 12% 0%,rgba(69,126,169,.6),transparent 60%),radial-gradient(500px 300px at 100% 100%,rgba(212,188,149,.28),transparent 60%),#0b1a28;color:#fff;box-shadow:0 2px 6px rgba(20,40,60,.12),0 30px 60px -24px rgba(11,26,40,.7);"),
    (".hero .scrim{position:absolute;inset:0;background:linear-gradient(100deg,rgba(7,7,11,.72) 0%,rgba(7,7,11,.35) 42%,rgba(7,7,11,0) 68%);", ".hero .scrim{position:absolute;inset:0;background:linear-gradient(100deg,rgba(11,26,40,.78) 0%,rgba(11,26,40,.38) 42%,rgba(11,26,40,0) 68%);"),
    (".btn.p{background:var(--p);color:#fff;box-shadow:0 10px 22px -12px rgba(75,54,214,.9)}", ".btn.p{background:linear-gradient(135deg,#5b95c1,#457ea9);color:#fff;box-shadow:0 10px 22px -12px rgba(69,126,169,.9)}"),
    (".btn.w{background:#fff;color:var(--p-deep);", ".btn.w{background:linear-gradient(135deg,#f3e9d8,#d4bc95);color:#3d2f18;"),
    (".brandband{background:#07070B;", ".brandband{background:#0b1a28;"),
    (".search{flex:1;max-width:520px;min-width:240px;display:flex;align-items:center;gap:10px;background:var(--card);", ".search{flex:1;max-width:520px;min-width:240px;display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.8);"),
]
if os.environ.get("SINAN_THEME") == "coast":
    _n = 0
    for _a, _b in COAST:
        if _a in CSS: CSS = CSS.replace(_a, _b); _n += 1
        else: print("主题：找不到片段", _a[:60])
    # 追加：沙金作点缀（榜单序号、侧栏分组标题、选中的模型胶囊），让三色都出现
    CSS += "\n.rkmini li .no{color:#b3945f;font-weight:600}.sect{color:#b3945f}.chip.on,.chip[aria-pressed=true]{background:linear-gradient(135deg,#5b95c1,#457ea9);border-color:transparent;color:#fff;box-shadow:0 8px 18px -10px rgba(69,126,169,.8)}.subbox{background:linear-gradient(135deg,rgba(255,255,255,.92),rgba(243,235,221,.9));border-color:#e6d7bd}.mv.up{background:#dcefe4;color:#1b6b45}.pledge{border-color:#d4bc95;background:rgba(243,235,221,.35)}"
    # 亮版首屏：浅蓝渐变 + 沙金光晕，深色文字；地球缩小放右侧（画布缩到右半区，着色器按画布尺寸画球）；星空隐藏
    CSS += "\n.hero{background:radial-gradient(640px 360px at 6% 0%,rgba(69,126,169,.34),transparent 62%),radial-gradient(560px 340px at 100% -10%,rgba(212,188,149,.62),transparent 64%),linear-gradient(135deg,#cce0f4 0%,#e4eef8 46%,#f4efe4 100%);color:var(--ink);box-shadow:0 2px 6px rgba(20,40,60,.06),0 30px 60px -28px rgba(69,126,169,.45);border:1px solid rgba(255,255,255,.7)}"
    CSS += ".hero .stars{display:none}.hero .scrim{background:linear-gradient(100deg,rgba(228,238,248,.72) 0%,rgba(228,238,248,.42) 40%,rgba(228,238,248,0) 62%)}"
    CSS += ".hero .eyebrow{color:var(--p-deep);opacity:1}.hero h1{color:var(--ink)}.hero p{color:var(--ink-2)}.hero .stat{background:rgba(255,255,255,.66);border:1px solid rgba(69,126,169,.28);color:var(--ink);backdrop-filter:blur(10px)}.hero .stat b{color:var(--p-deep)}.hero .tag{color:var(--ink-3);opacity:.9}"
    CSS += ".hero .btn.w{background:linear-gradient(135deg,#5b95c1,#457ea9);color:#fff;box-shadow:0 12px 24px -12px rgba(69,126,169,.9)}.hero .btn.g{background:rgba(255,255,255,.72);color:var(--p-deep);border:1px solid rgba(69,126,169,.35);backdrop-filter:blur(8px)}.hero .btn.g:hover{background:rgba(255,255,255,.95)}.hero .cta .btn.g:last-child{background:linear-gradient(135deg,#f0e4cf,#d4bc95);color:#3d2f18;border:0}.hero .cta .btn.g:last-child:hover{background:linear-gradient(135deg,#eadcc2,#cbb086)}"
    # 榜单四张小卡 → 三色胶囊块：深蓝 / 沙金 / 浅蓝 / 藏青，各带同色柔光影
    CSS += ".rkmini .card{border:0;border-radius:30px;padding:20px 22px 18px;color:#fff;backdrop-filter:none}.rkmini .card:nth-child(1){background:linear-gradient(135deg,#5b95c1,#457ea9);box-shadow:0 28px 44px -24px rgba(69,126,169,.95)}.rkmini .card:nth-child(2){background:linear-gradient(135deg,#e4d2ad,#d4bc95);color:#3d2f18;box-shadow:0 28px 44px -24px rgba(180,150,100,.9)}.rkmini .card:nth-child(3){background:linear-gradient(135deg,#e2edf8,#cce0f4);color:#1f3a52;box-shadow:0 28px 44px -24px rgba(120,160,200,.75)}.rkmini .card:nth-child(4){background:linear-gradient(135deg,#3f7398,#2b5878);box-shadow:0 28px 44px -24px rgba(43,88,120,.95)}"
    CSS += ".rkmini h4{color:inherit}.rkmini .q{color:inherit;opacity:.78}.rkmini li{border-top-color:rgba(255,255,255,.3)}.rkmini .card:nth-child(2) li,.rkmini .card:nth-child(3) li{border-top-color:rgba(20,40,60,.14)}.rkmini li .no{color:inherit;opacity:.65;font-weight:600}.rkmini li a,.rkmini li .val{color:inherit}.rkmini .card a.more,.rkmini .card .more{color:inherit;opacity:.85}"
    CSS = CSS.replace(".tile.high .orb{background:radial-gradient(circle at 32% 30%,#C9BEFF,#6E56F5 55%,#2E1E9C);box-shadow:inset -14px -18px 28px rgba(30,10,110,.4)}", ".tile.high .orb{background:radial-gradient(circle at 32% 30%,#cce0f4,#457ea9 55%,#2b5878);box-shadow:inset -14px -18px 28px rgba(20,50,80,.4)}")
    CSS = CSS.replace("linear-gradient(135deg,#0B0D1F 0%,#1B1650 55%,#3A2AA8 100%)", "linear-gradient(135deg,#0b1a28 0%,#1f4262 55%,#457ea9 100%)")
    CSS = CSS.replace("#6E56F5", "#457ea9").replace("rgba(110,86,245", "rgba(69,126,169").replace("rgba(75,54,214", "rgba(69,126,169")
    APP_JS = APP_JS.replace("#6E56F5", "#457ea9")
    BANDC["premium"] = "#457ea9"
    print("主题 coast：替换 %d / %d 处，追加沙金点缀 + 亮版首屏（地球全幅）+ 胶囊榜卡 + 紫色残留清理" % (_n, len(COAST)))

def _asset_v():
    return _hl.sha1((CSS + APP_JS + EARTH_JS).encode("utf-8")).hexdigest()[:10]

def shell(title, desc, path, body, active="", page="", crumbs=None, extra_head="", scripts="", og_image="/img/og.png", jsonld=None):
    st = D["stats"]
    canonical = BASE + path
    nav = "".join('<a class="nav%s" href="%s"><svg viewBox="0 0 24 24">%s</svg>%s%s</a>' % (" on" if active == k else "", h, ICONS[k], lbl, ('<span class="badge">%s</span>' % b) if b else "")
                  for k, h, lbl, b in [("home", "/", "模型账本", str(len(D["models"]))), ("sites", "/sites", "中转站", str(st["confirmed"])), ("media", "/media", "图像 · 视频", ""), ("rank", "/rank", "司南榜", ""), ("pindex", "/price-index", "Token 价格指数", ""), ("gpu", "/gpu", "算力租赁", ""), ("report", "/report", "月报", ""), ("check", "/check", "测试模型真伪", ""), ("life", "/survival", "站点存续", ""), ("verify", "/verify", "申请核验", "")])
    nav2 = "".join('<a class="nav%s" href="%s"><svg viewBox="0 0 24 24">%s</svg>%s</a>' % (" on" if active == k else "", h, ICONS[k], lbl)
                   for k, h, lbl in [("method", "/method", "口径与定义"), ("api", "/api-docs", "开放数据与接口"), ("gov", "/governance", "指数治理"), ("fix", "/corrections", "修正日志"), ("press", "/press", "媒体与研究者")])
    crumb = '<div class="crumb"><a href="https://sinanlab.com">← 司南实验室</a>%s</div>' % "".join(" › " + ('<a href="%s">%s</a>' % (c[1], esc(c[0])) if len(c) > 1 and c[1] else esc(c[0])) for c in (crumbs or []))
    head = tpl(u"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{title}}</title><meta name="description" content="{{desc}}"><link rel="canonical" href="{{canonical}}"><meta property="og:site_name" content="Sinan Compute"><meta property="og:type" content="website"><meta property="og:title" content="{{title}}"><meta property="og:description" content="{{desc}}"><meta property="og:url" content="{{canonical}}"><meta property="og:image" content="{{og}}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{{og}}">{{ld}}<meta name="theme-color" content="#07070B"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="sitemap" href="/sitemap.xml"><link rel="stylesheet" href="/assets/app.css?v={{v}}">{{extra}}</head><body data-page="{{page}}">""",
               title=esc(title), desc=esc(desc), canonical=canonical, v=_asset_v(), extra=extra_head, page=page, og=BASE + og_image,
               ld=("".join('<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False).replace("</", "<\\/") for x in (jsonld or []))))
    search = '<label class="search"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9AA0B8" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="q" placeholder="查一个站（toapis.cn）或一个模型（DeepSeek V4），回车" list="qlist"><datalist id="qlist"></datalist><kbd>/</kbd></label>'
    asof = '<div class="asof"><i></i><span>数据 %s · USD/CNY %.2f</span></div>' % (D["generated_at"][:16].replace("T", " "), D["fx"]["rate"])
    footer = SUBSCRIBE_BOX + u"""<div class="brandband"><img src="/brand/sinanlab-lockup.png" srcset="/brand/sinanlab-lockup@2x.png 2x" width="480" height="123" alt="SinanLab · 司南实验室" loading="lazy"><span>方向清晰，判断有据。</span></div><footer class="ft"><div class="in"><span>© 2026 Sinan Lab · 司南实验室</span><a href="https://sinanlab.com/constitution">为什么可信</a><a href="https://sinanlab.com/disclosure">收入透明</a><a href="https://github.com/sinanlabs/compute" rel="noopener">GitHub</a><a href="https://sinanlab.com/privacy">隐私政策</a><a href="https://sinanlab.com/disclaimer">免责声明</a><a href="/method">方法论</a><a href="/method#data">数据下载</a><a href="https://sinanlab.com/">母站 sinanlab.com</a><a href="mailto:hello@sinanlab.com">hello@sinanlab.com</a><span style="margin-left:auto">每个数字可追溯来源 · 不收任何被测渠道的钱</span></div></footer>"""
    drawer = u"""<div class="scrim" id="scrim"></div><aside class="drawer" id="drawer" role="dialog" aria-modal="true"><button class="x" id="dx" aria-label="关闭">×</button><div class="eyebrow" id="deye" style="color:var(--p)">证据链</div><h3 id="dtitle"></h3><div id="dbody"></div></aside>"""
    rail = tpl(u"""<aside class="rail"><a class="brand" href="/"><span class="mark"></span><div><b>Sinan Compute</b><small>司南·算力 · SINAN LAB</small></div></a><div class="sect">测量</div>{{nav}}<div class="sect">底层</div>{{nav2}}<a class="robo" href="https://robo.sinanlab.com"><span class="gl"></span><b>Sinan Robo</b><p>开源具身模型的可审计索引</p></a></aside>""", nav=nav, nav2=nav2)
    return head + '<div class="app">' + rail + '<div class="main"><div class="top">' + (search if page != "index" else search) + asof + '<div class="auth" id="auth"></div></div>' + (crumb if crumbs else "") + body + footer + '</div></div>' + drawer + '<script src="/assets/app.js?v=%s" defer></script><script>try{if(location.pathname==="/"&&/[?&]code=/.test(location.search)&&/[?&]state=/.test(location.search)){fetch("/api/x/callback"+location.search).then(function(r){return r.json();}).then(function(j){document.body.insertAdjacentHTML("afterbegin","<div style=\\"position:fixed;top:0;left:0;right:0;z-index:99;background:#07070B;color:#F5F5F7;padding:12px 18px;font-size:14px\\">"+(j.ok?"X 授权完成，令牌已保存。可以关掉这个页面。":"X 授权失败："+(j.error||"")+(j.detail?" "+JSON.stringify(j.detail).slice(0,160):""))+"</div>");history.replaceState(null,"","/");});}}catch(e){};try{var _l=document.documentElement.lang==="en"?"en":"zh";fetch("/api/hit?t=pv&l="+_l+"&p="+encodeURIComponent(location.pathname),{method:"POST"});if(!sessionStorage.getItem("sess")){sessionStorage.setItem("sess","1");fetch("/api/hit?t=sess&l="+_l,{method:"POST"});}var _pg=location.pathname.replace(/^\/en(?=\/|$)/,"")||"/";var _bp=_pg==="/"?"home":(_pg.indexOf("/rank")===0?"rank":_pg.indexOf("/report")===0?"report":_pg.indexOf("/price-index")===0?"index":"");if(_bp&&"IntersectionObserver" in window){var _els=_bp==="home"?document.querySelectorAll(".rkmini .card"):document.querySelectorAll("section.card");var _seen={},_tm={}; function _title(el){var h=el.querySelector("h4,h2.sec,h2");return h?h.textContent.trim().slice(0,40):"";} var _io=new IntersectionObserver(function(es){es.forEach(function(e){var k=_title(e.target);if(!k)return;if(e.intersectionRatio>=0.5){if(!_seen[k]&&!_tm[k])_tm[k]=setTimeout(function(){_seen[k]=1;fetch("/api/hit?t=board&k="+encodeURIComponent(_bp+":"+k),{method:"POST"});},1500);}else if(_tm[k]){clearTimeout(_tm[k]);_tm[k]=null;}});},{threshold:[0.5]}); _els.forEach(function(el){if(_title(el))_io.observe(el);}); document.addEventListener("click",function(ev){var a=ev.target.closest?ev.target.closest("a"):null;if(!a)return;var sec=a.closest(_bp==="home"?".rkmini .card":"section.card");if(!sec)return;var k=_title(sec);if(k)fetch("/api/hit?t=boardclick&k="+encodeURIComponent(_bp+":"+k),{method:"POST",keepalive:true});});}}catch(e){};try{if(document.referrer){var _h=new URL(document.referrer).hostname;if(!/(^|\\.)sinanlab\\.com$/.test(_h)&&!sessionStorage.getItem("ref"))fetch("/api/hit?r="+encodeURIComponent(_h)+"&p="+encodeURIComponent(location.pathname),{method:"POST"}).then(function(){sessionStorage.setItem("ref","1");});}}catch(e){}</script>%s</body></html>' % (GEN_DATE.replace("-", ""), scripts)

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
    chips = []   # 按厂商一行一组：左列厂商名，右列该厂商的模型芯片（最新两代默认显示，旧版本折叠）
    for v, ids in D["groups"].items():
        row = []
        for mid in ids:
            m = next((x for x in D["models"] if x["id"] == mid), None)
            if not m: continue
            row.append('<button class="chip%s" data-id="%s" aria-pressed="%s">%s<span class="n">%d 家</span></button>' % ("" if m["is_latest"] else " old", esc(m["id"]), "true" if m["id"] == default else "false", esc(m["name"]), m["n_relay"]))
        if row: chips.append('<div class="vrow"><span class="vn">%s</span><div class="vc">%s</div></div>' % (esc(D["vendor_name"].get(v, v)), "".join(row)))
    n_old = sum(1 for m in D["models"] if not m["is_latest"])
    if n_old: chips.append('<div class="vrow tail"><span class="vn"></span><div class="vc"><button class="chip more" id="more" data-label="展开 %d 个旧版本">展开 %d 个旧版本</button></div></div>' % (n_old, n_old))
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
    # 榜单预览：四张榜各取前三
    RK = D.get("rank") or {}
    def mini(title, q, rows, val):
        lis = "".join('<li><span class="no">%02d</span><a href="/s/%s">%s</a><span class="val">%s</span></li>' % (i + 1, esc(r["domain"]), esc(r.get("name") or r["domain"]), val(r)) for i, r in enumerate(rows[:3]))
        return '<div class="card"><h4>%s</h4><div class="q">%s</div><ol>%s</ol></div>' % (title, q, lis or '<li><span class="sub">样本不足，本期空缺</span></li>')
    rkmini = (mini("响应榜", "可达率 ≥99% 的站里首字节延迟最低", RK.get("fast", []), lambda r: "%dms" % r["p50"]) +
              mini("价格优势榜", "最新代模型说得通区间内实付中位数最低", RK.get("price", []), lambda r: "%d%%" % round(r["median"] * 100)) +
              mini("多模态价格优势榜", "图像 / 视频报价说得通区间内实付中位数最低", (RK.get("media") or {}).get("price", []), lambda r: "%d%%" % round(r["median"] * 100)) +
              mini("双旗舰榜", "同时在说得通区间卖 GPT-6 Astra 与 Claude Fable 5.1，按两者实付之和", RK.get("dual", []), lambda r: "$%s" % fmt(r["sum"])))
    # 检测三层
    det = ('<div class="card"><div class="k">T0 · 24h 可达</div><div class="v">%d<small>/ %d 站</small></div><p>过去 24 小时从美国西部探测节点能连上的站；每站每天多次探测，记首字节延迟。</p></div>'
           '<div class="card"><div class="k">T1 · 一致性探针</div><div class="v">%d<small>组 站×模型</small></div><p>用我们的 Key 向同一模型发固定探针串，比对 token 计数：%d 组与其他渠道一致，%d 组不一致，其余样本不足。</p></div>'
           '<div class="card"><div class="k">T2 · 能力抽样</div><div class="v">%d<small>组 站×模型</small></div><p>30 道机器判分小题，本站答对数与同模型多渠道中位数比；%d 组低于中位。</p></div>'
           % (st["reachable"], st["confirmed"], st.get("probed_pairs", 0), st.get("probe_consistent", 0), st.get("probe_divergent", 0), st.get("cap_pairs", 0), st.get("cap_below", 0)))
    pistrip = ""
    if PI and PI.get("latest"):
        L_ = PI["latest"]
        pistrip = ('<a class="card pad rise" href="/price-index" style="--i:3.2;margin-top:18px;display:flex;flex-wrap:wrap;gap:10px 26px;align-items:baseline"><span class="eyebrow" style="color:var(--p)">司南 Token 价格指数 · %s</span>'
                   '<span><b style="font-family:var(--mono);font-size:22px">%d%%</b> <span class="sub">全市场：市场中位实付是官方价的几成</span></span>%s<span class="sub" style="margin-left:auto">每日更新 · 可引用 · 看指数 →</span></a>'
                   % (PI["generated_at"][:10], round(L_["all"]["ratio"] * 100), "".join('<span><b style="font-family:var(--mono)">%d%%</b> <span class="sub">%s</span></span>' % (round(L_[k]["ratio"] * 100), n_) for k, n_ in (("flagship", "旗舰"), ("mid", "中档"), ("flash", "快速")) if L_.get(k))))
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
<div class="txt"><div class="eyebrow">实付比率 · 司南榜每周出刊 · 一致性检测 · 用你的 Key 自测</div><h1>看清算力，<br>才好买算力。</h1>
<p>我们把 <span class="mono">{{n}}</span> 个中转站的实付价，对着官方与公开市场价逐条算成比率；再用自己的 Key 做可达、一致性、能力三层检测，每周出一期司南榜。每个数字都能点开看来源。不收任何被测渠道的钱，也不替你判断。</p>
<div class="cta"><a class="btn w" href="#ledger">查一个模型</a><a class="btn g" href="/rank">看司南榜</a><a class="btn g" href="/check">用我的 Key 自测</a></div></div>
<div class="stat"><b data-count="{{quotes_raw}}">{{quotes}}</b><small>条实付报价 · 24h 内</small></div><div class="tag">地球影像 NASA BLUE MARBLE · BLACK MARBLE<br>实时大气散射 · 拖动转动地球</div></section>
<div class="kpis">{{kpis}}</div>
{{pledge}}
{{pistrip}}
<section class="rise" id="rank" style="--i:3.5;margin-top:22px"><div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap"><div><div class="eyebrow" style="color:var(--p)">司南榜 · {{week}}</div><h2 class="sec" style="margin-top:4px">本周司南榜</h2><p class="lead" style="margin-top:4px">每张榜只回答一个可测量的问题，按测量值排序，每周一出刊；不含任何商业变量，不构成推荐。</p></div><a class="btn o" href="/rank" style="margin-left:auto">看全部 12 张榜 →</a></div><div class="rkmini">{{rkmini}}</div></section>
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
<section class="rise" id="detect" style="--i:4.5;margin-top:22px"><div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap"><div><div class="eyebrow" style="color:var(--p)">检测 · 三层 · 全部可复现</div><h2 class="sec" style="margin-top:4px">不只比价，还测得到什么</h2><p class="lead" style="margin-top:4px">用我们自己的 Key 每天测；判定只有一致 / 不一致 / 样本不足，这是一致性测量，不是真伪判定。</p></div><a class="btn p" href="/check" style="margin-left:auto">用我的 Key 测一个站 →</a></div><div class="det">{{det}}</div></section>
<div class="grid2" style="margin-top:22px"><div class="bento rise" id="bento" style="--i:5">{{tiles}}</div>
<section class="card feed rise" style="--i:6"><h3>今日变动</h3>{{feed}}</section></div>
<section class="card pad rise" style="margin-top:18px;--i:7;display:flex;flex-wrap:wrap;gap:14px;align-items:center"><div><h2 class="sec">图像 · 视频</h2><p class="lead">Seedance、Veo、Kling、Hailuo 等按秒 / 按张的实付价，与官方价放一起。</p></div><a class="btn p" href="/media" style="margin-left:auto">看图像与视频账本 →</a></section>
<section class="rise" style="--i:8;margin-top:22px"><div class="eyebrow" style="color:var(--p)">SinanLab · 司南实验室</div><h2 class="sec" style="margin-top:4px">三个站，一把尺</h2><div class="prods"><a class="card" href="/"><b>Sinan Compute · 司南·算力</b><p>模型 API 中转站的实付价、可达率、一致性与能力检测，每周司南榜。</p></a><a class="card" href="https://robo.sinanlab.com"><b>Sinan Robo · 司南·机脑</b><p>开源具身模型（VLA）的许可证、权重、可上机器人本体，做成可审计的索引与榜单。</p></a><a class="card" href="https://sinanlab.com/"><b>母站 sinanlab.com</b><p>为什么可信、收入透明、隐私政策，以及两个站的订阅与账号。</p></a></div></section>
<noscript><div class="notice" style="margin-top:18px">本页的模型切换、证据抽屏需要 JavaScript。上面的表格是默认模型 {{dmname}} 的静态版本；全部站点见 <a href="/sites">站点总表</a>。</div></noscript>
<script id="d" type="application/json">{{data}}</script>""",
        n=st["confirmed"], quotes=format(st["quotes"], ","), quotes_raw=st["quotes"], kpis=kpi_html, week=esc(RK.get("week", "")), rkmini=rkmini, det=det, pistrip=pistrip, pledge=PLEDGE, mlinks="".join('<a href="/m/%s">%s</a>' % (esc(m["id"]), esc(m["name"])) for m in D["models"]), chips="".join(chips), rows=ssr_ledger_rows(dm), disc=DISCLAIMER, tiles=tiles_html, feed=feed_html, dmname=esc(dm["name"]), data=jsdata(light))
    desc = "司南实验室出品。%d 个中转站的模型 API 实付价对着官方与公开市场价逐条算成比率，%s 条报价，每个数字可追溯抓取快照。不收任何被测渠道的钱。" % (st["confirmed"], format(st["quotes"], ","))
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Sinan Compute", "alternateName": "司南·算力", "url": BASE + "/", "inLanguage": "zh-CN",
           "publisher": {"@type": "Organization", "name": "Sinan Lab", "alternateName": "司南实验室", "url": "https://sinanlab.com", "logo": BASE + "/brand/sinanlab-mark.png", "email": "hello@sinanlab.com"},
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
    _f = PROBE_TXT.get(pb["status"])   # cap_only 等没有 T1 计数的状态不出这行小字
    txt = (_f % (pb["ok"], pb["n"])) if _f else ""
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
        if s.get("panel") == "sub2api" and not cl: pic = '<span class="pill none">订阅型（Sub2API）· 套餐价需登录</span>'
        if s.get("verified"): pic = '<span class="pill" style="background:#07070B;color:#F5F5F7;margin-right:6px" title="7 天内一致性探针、能力抽样、可达均通过">经司南核验</span>' + pic
        if s.get("dead"): pic += '<span class="pill" style="background:#EEF0F6;color:var(--ink-2);margin-left:6px">7 天未连通</span>'
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
    submit_card = u"""<section class="card pad rise" id="submit" style="--i:3;margin-top:18px"><h2 class="sec">提交一个中转站</h2><p class="lead">你知道的站还没在总表里？填域名，我们当晚做一次面板确认，命中就收录。只收域名，不收任何推广参数；收录与否只看能不能确认它是模型 API 中转站，与谁提交无关。</p>
<div id="sub-gate" class="callout" style="margin-top:12px">正在读取登录状态…</div>
<div id="sub-form" style="display:none;margin-top:12px"><div style="display:flex;gap:10px;flex-wrap:wrap"><input id="sub-dom" placeholder="例如 toapis.cn" style="flex:1;min-width:220px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit;font-size:14px;background:var(--card)"><button class="btn p" id="sub-go">提交</button></div><p class="sub" id="sub-msg" style="margin-top:8px"></p><div id="sub-mine" class="sub" style="margin-top:6px"></div></div>
<script>(function(){var g=document.getElementById("sub-gate"),f=document.getElementById("sub-form"),M=document.getElementById("sub-msg");var ST={pending:"待核对（当晚处理）",confirmed:"已确认收录",already_listed:"已在总表",no_panel:"可达但不是可确认的中转面板",unreachable:"连不上"};
function mine(){fetch("/api/submit",{credentials:"include"}).then(function(r){return r.json();}).then(function(j){var it=j.items||[];if(!it.length)return;document.getElementById("sub-mine").innerHTML="我提交过的："+it.slice(0,8).map(function(x){return esc(x.domain)+"（"+(ST[x.status]||x.status)+"）";}).join(" · ");});}
fetch("/api/me",{credentials:"include"}).then(function(r){return r.json();}).then(function(m){if(m&&m.user){g.style.display="none";f.style.display="";mine();}else{g.innerHTML='提交需要登录（用来防刷）。<a href="/login?return_to=/sites%23submit" style="color:var(--p-ink)">登录 →</a>';}}).catch(function(){g.textContent="暂时无法读取登录状态。";});
document.getElementById("sub-go").addEventListener("click",function(){var v=document.getElementById("sub-dom").value.trim();if(!v)return;M.textContent="提交中…";fetch("/api/submit",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({domain:v})}).then(function(r){return r.json();}).then(function(j){if(j.ok){M.textContent=(j.duplicate?"这个站已经在队列里：":"已收到：")+j.domain+"，"+(ST[j.status]||j.status)+"。";document.getElementById("sub-dom").value="";mine();}else{M.textContent={bad_domain:"域名格式不对",too_many_requests:"今天提交太多了，明天再来",login_required:"请先登录"}[j.error]||"出错了";}}).catch(function(){M.textContent="网络错误，请重试。";});});})();</script></section>"""
    body = body + submit_card
    return shell("中转站总表 · Sinan Compute", "%d 个经面板指纹确认的模型 API 中转站：价格画像、在卖模型数、24h 可达率、首次收录日期。" % st["confirmed"], "/sites", body, active="sites", page="sites", crumbs=[("中转站总表",)])

# ------------------------------------------------------------------ 站点页
def build_site(s):
    f = s.get("facts") or {}; av = s.get("avail") or {}; cl = s["cluster"]; held = bool(cl and cl["code"] == "held")
    price = ("%s 元 / $1" % f["price"] + ((" · Stripe %s" % f["stripe"]) if f.get("stripe") not in (None, 8) else "")) if f.get("price") is not None else "未暴露"
    sv = s.get("survive") or {}
    svn = ""
    if sv:
        svn = {"premium": "主流后缀", "budget": "低价后缀", "other": "其他后缀"}.get(sv.get("tld"), "后缀未知")
        if sv.get("icp") is not None: svn += " · " + ("有备案" if sv["icp"] else "无备案")
        if sv.get("uptime7") is not None: svn += " · 7 天可达 %.1f%%" % sv["uptime7"]
        if sv.get("trend3d") is not None: svn += " · 近 3 天可达变化 %+.1f" % sv["trend3d"]
        svn += " · 基率见站点存续页"
    pb = s.get("pricing_basis") or {}
    pb_fact = [("计价口径", "分组 %s · 倍率 %s" % (pb.get("group") or "default", pb.get("group_ratio")),
                "该站用动态计价表达式（billing_mode=tiered_expr）：每百万 token 价 = 表达式系数 × 分组倍率，单位为站内额度。我们统一取 %s 分组%s；其他分组与长上下文档位价格不同，以站方面板为准。" % (
                 pb.get("group") or "default", ("的第一档（%s）" % pb["tier"]) if pb.get("tier") else ""), "t")] if pb else []
    ab = s.get("about") or None
    ab_fact = [("站方说明页",
                ("公开可读" + ((" · 站方 %s 更新" % ab["self_updated"]) if ab.get("self_updated") else "")) if ab else "—",
                ("站方自己写的说明，面板公开可读，我们只存快照、不核实内容%s。促销、活动与联系方式不收录。抓取 %s" % (
                    ("；写到了 " + " · ".join(ab["topics"])) if ab.get("topics") else "",
                    (ab.get("fetched") or "")[:16].replace("T", " "))) if ab else "面板没有公开可读的说明页（/api/about 为空或取不到）",
                "" if ab else "t",
                ('<div class="n"><a href="%s" rel="noopener nofollow">站方原文 ↗</a> · <a href="/snap/about/%s.txt">抓取快照</a></div>' % (esc(ab["public_url"]), esc(s["domain"]))) if ab else "")]
    facts = [
        ("价格画像", cl["name"] if cl else ("套餐制" if s.get("panel") == "sub2api" else "无比对"), ("中位 %s" % pct(s["median"])) if (cl and not held and s["median"] is not None) else (cl["help"] if cl else ("按套餐售卖订阅额度，价格需登录，本站不做套餐比价" if s.get("panel") == "sub2api" else "定价接口未公开，没有能对上参考价的模型")), "t" if not (cl and not held and s["median"] is not None) else ""),
        ("24h 可达", ("7 天未连通" if s.get("dead") else ("未测" if not av.get("n") else ("%d/%d 成功" % (round(av["uptime"] * av["n"] / 100.0), av["n"]) if av["n"] < 10 else "%.0f%%" % av["uptime"]))),
              ("连续 7 天、≥100 次探测一次都没连上；页面保留，不进任何榜" if s.get("dead") else
               ("还没有探测样本" if not av.get("n") else
                ("%s · %d 次探测 · 节点 %s%s" % (("延迟 p50 %dms" % av["ttfb_p50"]) if av.get("ttfb_p50") else "本站无成功样本，失败原因见下", av["n"], D["probe_node"], "；样本不足 10 次，只作参考" if av["n"] < 10 else "")))), "t" if s.get("dead") else ""),
        ("在卖模型", str(s["n_models"]) if s["n_models"] else "—", ("说得通 %d · 低于成本下限 %d" % (s["ok_count"], s["un_count"])) if (s["n_models"] and not held) else ("只列名义报价" if held else ("套餐制 · 模型清单需登录" if s.get("panel") == "sub2api" else "定价接口未公开，暂无报价")), ""),
        *pb_fact,
        ("充值比例", price, "面板 price 字段：每 $1 名义额度收多少元", "t"),
        ("一致性探针", ("%d / %d 一致" % (s["probe"]["consistent"], s["probe"]["pairs"])) if s.get("probe") else "—",
         ("用本站 Key 测 %d 个模型的 token 计数，与同模型其他渠道比对 · %s" % (s["probe"]["pairs"], s["probe"]["ts"])) if s.get("probe") else "尚未用 Key 探测；只有拿到该站 Key 才能测", "" if s.get("probe") else "t"),
        ("能力抽样", ("%d 个模型 · 低于中位 %d" % (len([r for r in s["models"] if (r.get("probe") or {}).get("cap")]), len([r for r in s["models"] if ((r.get("probe") or {}).get("cap") or {}).get("status") == "below"]))) if any((r.get("probe") or {}).get("cap") for r in s["models"]) else "—",
         "30 道机器判分小题，本站答对数与同模型其他渠道中位数比" if any((r.get("probe") or {}).get("cap") for r in s["models"]) else "尚未用 Key 抽样", "" if any((r.get("probe") or {}).get("cap") for r in s["models"]) else "t"),
        ("上游自述", " · ".join((s.get("upstream") or {}).get("tags") or []) or "—",
         ("站方面板公开文字里出现的说法，原文：" + " ｜ ".join("%s「%s」" % (k, _safe_snip(v)[:60]) for k, v in ((s.get("upstream") or {}).get("snippets") or {}).items() if k != "订阅制面板" and _safe_snip(v))[:300]) if (s.get("upstream") and any(k != "订阅制面板" for k in s["upstream"]["snippets"])) else ("按面板类型判定：Sub2API 面板按套餐转售订阅席位" if s.get("upstream") else "面板公开文字里没有关于上游来源的说法"), "" if s.get("upstream") else "t"),
        *ab_fact,
        ("众测", ("%d 次 · %d 个来源" % (s["crowd"]["n"], s["crowd"]["srcs"])) if s.get("crowd") else "—",
         ("一致 %d · 含前缀 %d · 不一致 %d · 失败 %d · 最近 %s" % (s["crowd"]["consistent"], s["crowd"]["prefix"], s["crowd"]["divergent"], s["crowd"]["failed"], s["crowd"]["last"] or "")) if s.get("crowd") else "还没有人用自己的 Key 测过这个站；到测试页测一次，结果匿名回流到这里", "" if s.get("crowd") else "t"),
        ("存续信号", (("域名 %s 注册" % sv["created"]) if sv.get("created") else "域名年龄未知") if sv else "—", svn, "t"),
        ("登录方式", "、".join(f.get("login") or []) or "未暴露", ("需人机验证" if f.get("turnstile") else "无人机验证") + ("，有签到" if f.get("checkin") else ""), "t"),
        ("新用户注册", {"open": "开放", "closed": "已关闭", "unknown": "未能判定"}.get((s.get("register") or {}).get("state"), "未能判定"),
         {"open": "注册接口可用（可能需要邮箱验证或人机验证）", "closed": "站方已关闭新用户注册，新用户无法使用 · %s" % ((s.get("register") or {}).get("checked") or ""), "unknown": "非标准面板或未暴露注册接口，请到站上确认"}.get((s.get("register") or {}).get("state"), "未能判定"),
         "" if (s.get("register") or {}).get("state") == "open" else "t"),
        ("面板", "%s %s" % (s.get("panel") or "—", s.get("version") or ""), "首次收录 %s · 来源 %s" % (s["first_seen"], s.get("channel") or ""), "t"),
    ]
    facts_html = "".join('<div class="card fact"><div class="k">%s</div><div class="v %s">%s</div><div class="n">%s</div>%s</div>' % (f[0], f[3], esc(f[1]), esc(f[2]), (f[4] if len(f) > 4 else "")) for f in facts)
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
    noq = ""
    if not s["models"]:
        noq = ('<div class="callout" style="margin-top:14px">这是一个 Sub2API 面板的订阅型中转站：按套餐（月付 / 次数）售卖 Claude Code、Codex 等订阅额度，价格要登录后才能看到，本站不做套餐比价。这里列的是能公开核实的事实：面板类型、注册是否开放、登录方式、24h 可达。</div>' if s.get("panel") == "sub2api" else
               '<div class="callout" style="margin-top:14px">这个站的定价接口未公开或需要登录，本站暂无它的报价。可达性与面板事实仍每小时更新。</div>')
    tbl = ('<section class="card rise" style="margin-top:16px;--i:3"><div class="pad" style="padding-bottom:6px"><h2 class="sec">它卖的模型与实付价</h2><p class="lead">%s</p></div><div class="tablewrap"><table><thead><tr><th>模型</th><th class="num">实付</th><th class="num">参考价</th><th>实付是参考价的几成</th><th>怎么看</th><th class="num">证据</th></tr></thead><tbody>%s</tbody></table></div><div class="tfoot"><span>%s</span></div></section>'
           % ("计价方式待核：只列名义报价换算的实付，不出比率、不分档。" if held else "参考价取官方与公开市场最低；几成 = 实付 ÷ 参考价。", "".join(rows), DISCLAIMER)) if s["n_models"] else ""
    body = tpl(u"""<div class="sitehead rise" style="--i:0"><div><h1>{{domain}}<span class="nm">{{name}}</span></h1></div><div style="margin-left:auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap">{{pic}}<button class="btn o watch" data-kind="site" data-key="{{domain}}">关注这个站</button><a class="btn p" href="/go/{{domain}}" target="_blank" rel="noopener nofollow">前往站点 ↗</a></div></div>
{{notice}}<div class="facts rise" style="--i:2">{{facts}}</div><div class="repfoot rise" style="--i:2.2;margin-top:10px;padding-top:0;border:0"><button class="rep" data-kind="site" data-key="{{domain}}" data-ctx="站点 {{domain}}">这个站的信息有误？报错</button>{{planbtn}}<span class="sub">报错需登录；核实后记入修正日志并署名</span></div>{{noq}}{{tbl}}
{{mlinks}}<div class="card pad rise" style="margin-top:16px;--i:3.8"><div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap"><img src="/badge/{{domain}}.svg" alt="实测徽章" width="340" height="64" style="border-radius:14px"><div style="flex:1;min-width:260px"><h2 class="sec" style="font-size:15px">站长可嵌入的实测徽章</h2><p class="lead" style="margin-top:4px">只显示测量值：24h 可达率、价格画像、日期，每天自动更新，点击回到本页。不含任何评价。</p><code style="display:block;margin-top:8px;font-size:11.5px;word-break:break-all;background:var(--ground);padding:8px 10px;border-radius:8px">&lt;a href="{{base}}/s/{{domain}}"&gt;&lt;img src="{{base}}/badge/{{domain}}.svg" alt="Sinan Compute 实测" width="340" height="64"&gt;&lt;/a&gt;</code></div></div></div>
{{rankbadge}}<div class="callout rise" style="margin-top:16px;--i:4"><b>想核实它给的是不是真模型？</b> 用你在该站的 Key 跑开源的协议一致性检测（本站探针脚本或 Veridrop）。本站只给价格与可达性的测量，不替你判断。出站链接不带任何推广参数，只记点击数。</div>
<script id="d" type="application/json">{{data}}</script>""",
        mlinks=('<div class="mlinks card rise" style="margin-top:16px;--i:3.5"><span class="vn">它在卖的主推模型</span>%s</div>' % "".join('<a href="/m/%s">%s</a>' % (esc(mm["id"]), esc(mm["name"])) for mm in D["models"] if any(r["vendor"] == s["domain"] for r in mm["rows"]))) if any(any(r["vendor"] == s["domain"] for r in mm["rows"]) for mm in D["models"]) else "",
        rankbadge=('<div class="card pad rise" style="margin-top:16px;--i:3.9"><div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap"><img src="/badge/rank/%s/%s.svg" alt="司南榜期号徽章" width="340" height="64" style="border-radius:14px"><div style="flex:1;min-width:260px"><h2 class="sec" style="font-size:15px">本期上榜：%s · %s #%02d</h2><p class="lead" style="margin-top:4px">按测量值排序的名次，带期号，永久有效；站长可嵌入，点击回到当期榜单。不构成推荐。</p><code style="display:block;margin-top:8px;font-size:11.5px;word-break:break-all;background:var(--ground);padding:8px 10px;border-radius:8px">&lt;a href="%s/rank/%s"&gt;&lt;img src="%s/badge/rank/%s/%s.svg" alt="司南榜 %s %s #%02d" width="340" height="64"&gt;&lt;/a&gt;</code></div></div></div>' % (
            esc(s["rank_badge"]["week"]), esc(s["domain"]), esc(s["rank_badge"]["week"]), esc(s["rank_badge"]["board_name"]), s["rank_badge"]["pos"], BASE, esc(s["rank_badge"]["week"]), BASE, esc(s["rank_badge"]["week"]), esc(s["domain"]), esc(s["rank_badge"]["week"]), esc(s["rank_badge"]["board_name"]), s["rank_badge"]["pos"])) if s.get("rank_badge") else "",
        base=BASE, domain=esc(s["domain"]), planbtn=(('<button class="rep" data-kind="plan" data-key="%s" data-ctx="套餐价 %s" data-tpl="套餐名：  · 价格：  元 / 月  · 每日/每周额度：  · 购买日期：  ">我买过这个站的套餐，报个价</button>' % (esc(s["domain"]), esc(s["domain"]))) if s.get("panel") == "sub2api" else ""), name=esc(s.get("name") or ""), pic=('<span class="pill %s">%s</span>' % (cl["code"], esc(cl["name"]))) if cl else '<span class="pill none">暂无报价</span>', notice=notice, facts=facts_html, noq=noq, tbl=tbl,
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
    data = u"""<h2 id="data">开放数据</h2><p>我们承诺原始数据可下载。完整的文件清单、字段说明与稳定性承诺见 <a href="/api-docs">开放数据与接口</a>。以下文件与站点同批次生成（%s）：</p><ul>
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
            u = f.get("canon_unit") or ("$/秒" if mod == "video" else "$/张")
            val = r.get("val"); basis = r.get("val_basis")
            note = {"stated": "站方标 %ss" % r.get("val_secs"), "assumed": "按默认 %ss 折算" % r.get("val_secs"), "native": ""}.get(basis, "")
            if val is None: u = ("$/秒" if r.get("unit") == "per_second" else "$/次"); val = r.get("eff"); note = "该族没有公开的默认时长，未折成每秒"
            mid = ('<td class="num">—</td><td><span class="pill held">待核</span></td>' if r.get("held") else
                   ('<td class="num"><span class="r %s">%s</span></td><td><span class="pill %s">%s</span></td>' % (r["band"], pct(r["ratio"]), r["band"], LABEL[r["band"]])) if r.get("band") else '<td class="num">—</td><td><span class="pill none">无参考</span></td>')
            out.append('<tr><td><a class="dom" href="/s/%s">%s</a><div class="sub">%s%s</div></td><td>%s</td><td class="num"><span class="big">%s</span><span class="asf">%s%s</span></td>%s</tr>'
                       % (esc(r["site"]), esc(r["site"]), esc(r.get("name") or ""), (" · " + esc(r["spec"])) if r.get("spec") else "", esc(r.get("version_label") or "—"), fmt(val) if val is not None else "—", u, ((" · " + note) if note else ""), mid))
        return "".join(out)
    def table(rs, cap):
        if not rs: return ""
        return '<section class="card rise" style="margin-top:16px"><div class="pad" style="padding-bottom:6px"><h2 class="sec">%s</h2></div><div class="tablewrap"><table><thead><tr><th>中转站</th><th>版本</th><th class="num">实付</th><th class="num">几成</th><th>怎么看</th></tr></thead><tbody>%s</tbody></table></div></section>' % (cap, rows_html(rs))
    facts = [("官方参考价", ("$%.3f / %s" % (ref["price"], unit_s)) if ref else "—", (esc(ref["model"]) + " · " + esc(ref.get("region") or "")) if ref else esc(f.get("ref_missing") or "暂无官方参考价，只列报价"), "" if ref else "t"),
             ("中转站", "%d 站 · %d 条" % (f.get("n_sites", 0), f.get("n_rows", 0)), "主推 %s，旧版本 %d 条折叠" % (" · ".join(f.get("recent_labels") or []) or "—", f.get("n_old", 0)), "t"),
             ("实付区间", ("$%.4f – $%.4f" % (f["eff_min"], f["eff_max"])) if f.get("eff_min") is not None else "—",
              "%s%s%s" % (f.get("canon_unit") or ("$/秒" if mod == "video" else "$/张"), ("，中位 $%.4f" % f["eff_med"]) if f.get("eff_med") is not None else "",
              ("；其中 %d 条是按该族默认时长折算的" % f["n_assumed"]) if f.get("n_assumed") else ""), ""),
             ("价格说得通", "%d 家" % len(ok), "低于成本下限 %d · 待核 %d" % (sum(1 for r in rec if r.get("band") == "unsustainable"), len(held)), "")]
    facts_html = "".join('<div class="card fact"><div class="k">%s</div><div class="v%s">%s</div><div class="n">%s</div></div>' % (k, (" t" if t else ""), esc(v), n) for k, v, n, t in facts)
    faq = [("%s 的官方 API 价格是多少？" % name, ("本站取官方定价页的最低档作参考：%s，每%s $%.3f（%s）。人民币标价按当日汇率折算。" % (ref["model"], unit_s, ref["price"], ref.get("region") or "")) if ref else "官方尚未公开可抓取的定价页，或本站尚未接入；接入前只列中转站报价，不出比率。"),
           ("这张表的价格是什么口径？", "视频一律折成每秒（$/秒），图像一律按每张（$/张），全站统一。站方本来就按秒报价的直接用；模型名里写了时长的（如 veo3.1-8s）按它折算；两样都没有的按该族公开的默认时长折算，并在那一行标出来。没有公开默认时长的族不折算，只列原始报价。折算只是算术，不代表该站实际生成时长。"),
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
def mv_tag(prev, key, pos):
    """与上周同一张榜比：↑n / ↓n / 新 / ＝。prev = {key: 上周名次}；prev 为 None 表示没有上周数据，不标。"""
    if prev is None: return ""
    q = prev.get(key)
    if q is None: return '<span class="mv new" title="上周未上榜">新</span>'
    d = q - pos
    if d == 0: return '<span class="mv same" title="与上周相同">＝</span>'
    return '<span class="mv %s" title="上周第 %d">%s%d</span>' % ("up" if d > 0 else "down", q, "↑" if d > 0 else "↓", abs(d))

def rank_rows(items, val, sub=None, bar=None, href="/s/%s", prev=None):
    out = []
    for i, x in enumerate(items):
        w = mv_tag(prev, x["domain"], i + 1)
        if bar is not None: w += '<span class="bar" aria-hidden="true"><i style="width:%d%%"></i></span>' % max(2, min(100, int(bar(x))))
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

def prev_rank(R, all_weeks):
    """上一期榜单 JSON（若有）。"""
    ws = sorted(set(all_weeks) | {R["week"]}); i = ws.index(R["week"])
    if i == 0: return None
    p_ = os.path.join(HERE, "rank", ws[i - 1] + ".json")
    return json.load(io.open(p_, encoding="utf-8")) if os.path.exists(p_) else None

def supply_board():
    """模型供给榜：被最多中转站上架（有效报价）的模型，附上周对比、市场中位 7 天变化、一致性探针。数据来自价格指数的逐日序列。"""
    if not PI or not PI.get("models"): return "", []
    rows = []
    for mid, m in PI["models"].items():
        ser = m["series"]; t = ser[-1]; t7 = ser[-8] if len(ser) >= 8 else ser[0]
        dm = D_MODELS.get(mid) or {}
        pbs = [r.get("probe") for r in (dm.get("rows") or []) if r.get("probe")]
        cons = sum(1 for p_ in pbs if p_["status"] == "consistent"); div = sum(1 for p_ in pbs if p_["status"] == "divergent")
        rows.append({"id": mid, "name": m["name"], "tier": m["tier"], "n": t["n"], "n7": t7["n"], "median": t["median"], "d7": ((t["median"] / t7["median"] - 1) * 100) if t7.get("median") else None, "ratio": t["ratio"], "cons": cons, "div": div})
    rows.sort(key=lambda x: (-x["n"], x["id"]))
    TZ = {"flagship": "旗舰", "mid": "中档", "flash": "快速"}
    lis = []
    for i, x in enumerate(rows[:14]):
        dn = x["n"] - x["n7"]; mv = ('<span class="mv %s">%s%d 站</span>' % ("up" if dn > 0 else "down", "+" if dn > 0 else "−", abs(dn))) if dn else '<span class="mv same">＝</span>'
        d7 = ("%+.0f%%" % x["d7"]) if x["d7"] is not None else "—"
        probe = ("一致 %d · 不一致 %d" % (x["cons"], x["div"])) if (x["cons"] or x["div"]) else "探针待 Key"
        lis.append('<li%s><span class="no">%02d</span><span class="who"><a href="/m/%s">%s</a><small>%s · 市场中位 $%s/M（官方价的 %d%%）· 7 天 %s · %s</small></span>%s<span class="bar" aria-hidden="true"><i style="width:%d%%"></i></span><span class="val">%d<small>个站在卖</small></span></li>'
                   % (' class="top"' if i < 3 else "", i + 1, esc(x["id"]), esc(x["name"]), TZ.get(x["tier"], ""), fmt(x["median"]), round(x["ratio"] * 100), d7, probe, mv, max(2, int(100 * x["n"] / rows[0]["n"])), x["n"]))
    html = board("模型供给榜", "被最多中转站上架的模型：站数 = 该模型有有效报价的站；这是供给侧的市场份额，和需求侧的用量份额是两回事。站数变化与上周比；市场中位价变化按 7 天；一致性只对我们有 Key 的站", '<ol class="rk">%s</ol>' % "".join(lis), 0.5)
    return html, rows

def build_rank(R, all_weeks, path="/rank"):
    st = D["stats"]; wk = R["week"]
    PR = prev_rank(R, all_weeks)
    def prevpos(key):
        if not PR or not isinstance(PR.get(key), list): return None
        return {x["domain"]: i + 1 for i, x in enumerate(PR[key])}
    seo = rank_metadata(R, path)
    title = seo["title"]; desc = seo["description"]
    head = u"""<div class="rkhead rise" style="--i:0"><div class="eyebrow">司南榜 · 测量榜单 · 每周一出刊</div><h1>司南榜 · %s</h1><p class="lead">过去 7 天的测量结果。每张榜只回答一个可测量的问题，按测量值排序，不含任何商业变量，不构成推荐。名次带样本量与门槛，能复算。<b>已关闭新用户注册的站不进任何榜单</b>（每日探测注册接口）。</p>
<div class="meta"><span><b>%d</b>已确认中转站</span><span><b>%s</b>实付报价</span><span><b>%d</b>进入榜单门槛的站</span><span><b>%s</b>数据日期</span><span><b>%s</b>上期</span></div><p class="sub" style="margin-top:10px">出刊：每周一北京时间早间，7 天窗口到周日为止；名次旁的 <span class="mv up">↑</span><span class="mv down">↓</span><span class="mv new">新</span> 是与上一期同一张榜的位次比较。口径见 <a href="/method">口径与定义</a>；本期 JSON：<a href="/rank/%s.json">%s.json</a>。</p></div>""" % (wk, R["n_sites"], format(R["n_quotes"] or st["quotes"], ","), R["eligible_uptime"], R["date"], (PR or {}).get("week") or "—", esc(wk), esc(wk))
    b_supply, _ = supply_board()
    fast = R["fast"]; b_fast = board("响应榜", "可达率 ≥99% 的站里首字节延迟 p50 最低（美国西部探测节点，≥24 次探测）",
               rank_rows(fast, lambda x: "%dms" % x["p50"], lambda x: "可达 %.1f%% · %d 次" % (x["uptime"], x["n"]), bar=relbar(fast, lambda x: x["p50"], True), prev=prevpos("fast")), 1)
    pr_ = R.get("price", []); b_price = board("价格优势榜", "最新代模型在说得通区间（参考价 40%–125%）内的实付中位数最低；至少 8 个可比模型；数值 = 参考价的几成",
               rank_rows(pr_, lambda x: "%d%%" % round(x["median"] * 100), lambda x: "%d 个可比模型" % x["n"], bar=relbar(pr_, lambda x: x["median"], True), prev=prevpos("price")), 2)
    fl = []
    for m in R["flagship"]:
        rows = "".join('<li%s><span class="no">%02d</span><span class="who"><a href="/s/%s">%s</a>%s</span><span class="val">$%s<small>参考价的 %d%%</small></span></li>' % (
            ' class="top"' if i == 0 else "", i + 1, esc(r["vendor"]), esc(r["vendor"]), ('<small>%s</small>' % esc(r["name"])) if r.get("name") else "", fmt(r["out"]), round(r["ratio"] * 100)) for i, r in enumerate(m["rows"]))
        fl.append('<div style="margin-top:14px"><div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap"><a href="/m/%s" style="font-weight:600">%s</a><span class="sub">参考价 $%s · 说得通区间内 %d 家</span></div><ol class="rk">%s</ol></div>' % (esc(m["id"]), esc(m["name"]), fmt(m["floor"]), m["n_inrange"], rows))
    b3 = board("新旗舰榜", "每个最新代模型，说得通区间（参考价 40%–125%）内最低实付的三家；低于成本下限的不计", "".join(fl) or '<div class="callout">样本不足，本期空缺</div>', 3)
    du = R["dual"]; b4 = board("双旗舰榜", "同时在说得通区间卖 GPT-6 Astra 与 Claude Fable 5.1 的站，按两者实付之和",
               rank_rows(du, lambda x: "$%s" % fmt(x["sum"]), lambda x: "GPT-6 $%s + Fable 5.1 $%s" % (fmt(x["gpt6"]), fmt(x["fable"])), bar=relbar(du, lambda x: x["sum"], True), prev=prevpos("dual")), 4)
    dd = R.get("dist_up", {}); low = R.get("low", [])
    b_up = board("可达榜", "过去 7 天 %d 家过门槛（≥24 次探测，在卖 ≥10 模型）：100%% 有 %d 家 · 99%%–99.9%% 有 %d 家 · 低于 99%% 有 %d 家。下面是可达率最低的 8 家" % (R["eligible_uptime"], dd.get("full", 0), dd.get("hi", 0), dd.get("low", 0)),
               rank_rows(low, lambda x: "%.1f%%" % x["uptime"], lambda x: "%d 次探测 · p50 %sms" % (x["n"], x["p50"] if x["p50"] else "—"), bar=relbar(low, lambda x: x["uptime"], False)), 5)
    vo = R["volatility"]; b5 = board("价格波动榜", "在卖 ≥20 模型的站里，7 天主流模型变价次数最多的（连续两次抓取一致才计一次）；%d/%d 家大站 7 天零变价" % (R["zero_change"], R["n_big"]),
               rank_rows(vo, lambda x: "%d 次" % x["n"], lambda x: "7 天变价", bar=relbar(vo, lambda x: x["n"], False), prev=prevpos("volatility")), 6)
    cv = R["coverage"]; b6 = board("覆盖榜", "在卖模型最多的站（有公开定价接口）", rank_rows(cv, lambda x: "%d" % x["n"], lambda x: "个模型", bar=relbar(cv, lambda x: x["n"], False), prev=prevpos("coverage")), 7)
    CRS = D.get("crowd_sites") or {}
    pr = "".join('<tr><td><a class="dom" href="/s/%s">%s</a>%s</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td><td>%s</td></tr>' % (
        esc(x["domain"]), esc(x["domain"]), ('<div class="sub">%s</div>' % esc(x["name"])) if x.get("name") else "", x["pairs"], x["consistent"], x["divergent"], x["ts"]) for x in R["probe"])
    crowd_rows = sorted(CRS.items(), key=lambda kv: -kv[1]["n"])[:20]
    crowd_html = ('<div class="pad" style="padding-top:14px;padding-bottom:6px"><h3 style="font-size:14px">众测 · 用户用自己的 Key 测过的站（30 天）</h3><p class="sub">%d 次回流 · %d 个站 · 匿名，只收计数与判定；只显示，不进核验标识。</p></div><div class="tablewrap"><table><thead><tr><th>站</th><th class="num">次数</th><th class="num">来源数</th><th class="num">一致</th><th class="num">含前缀</th><th class="num">不一致</th><th class="num">失败</th></tr></thead><tbody>%s</tbody></table></div>'
                  % (sum(v["n"] for v in CRS.values()), len(CRS), "".join('<tr><td><a class="dom" href="/s/%s">%s</a></td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td><td class="num">%d</td></tr>' % (esc(d_), esc(d_), v["n"], v["srcs"], v["consistent"], v["prefix"], v["divergent"], v["failed"]) for d_, v in crowd_rows))) if CRS else '<div class="pad" style="padding-top:12px"><p class="sub">众测：还没有回流结果。到 <a href="/check">测试页</a> 用自己的 Key 测一次，结果匿名进池子。</p></div>'
    b7 = ('<section class="card rise" style="margin-top:16px;--i:8"><div class="pad" style="padding-bottom:6px"><h2 class="sec">检测覆盖</h2><p class="lead" style="margin-top:4px">用我们自己的 Key 做过一致性探针的站。一致 = 12 条探针的 token 计数与同模型其他渠道完全相同；不一致 = 计数不同；其余为样本不足。这是一致性测量，不是真伪判定（方法论第 8 节）。</p></div><div class="tablewrap"><table><thead><tr><th>站</th><th class="num">已测模型</th><th class="num">一致</th><th class="num">不一致</th><th>日期</th></tr></thead><tbody>%s</tbody></table></div>' % (pr or '<tr><td class="dim">尚无</td></tr>')) + crowd_html + '</section>'
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
    au = R.get("audit") or []
    audit_html = ('<div class="callout" style="margin-top:12px"><b>本期待核 · %d 条</b>：%s 榜首若比第二名低 40%% 以上且只此一家，先不进榜，等核对原始条目后放行；另有 %d 条待核行（单位提示不一致 / 价格孤点 / 按规格计价）不参与比对。规则见口径与定义。</div>'
                  % (len(au), "、".join("%s（%s，$%s vs $%s）" % (esc(x["site"]), esc(x["family"]), x["value"], x["second"]) for x in au[:6]) + ("。" if au else ""), R.get("audit_open") or 0)) if (au or R.get("audit_open")) else ""
    hist = "".join('<a href="/rank/%s">%s</a>' % (esc(w), esc(w)) for w in all_weeks)
    foot = '<div class="tfoot" style="margin-top:16px"><span>按测量值排序，不构成推荐；排序不含任何商业变量。数据 %s · 窗口 7 天 · 方法见 <a href="/method">方法论</a>。永久链接 /rank/%s</span></div><div class="callout" style="margin-top:12px"><b>期号徽章</b>：响应榜、价格优势榜、双旗舰榜、覆盖榜、多模态价格优势榜上的站，可在各自站点页拿到带期号的徽章嵌入代码；徽章只显示榜名、名次、测量值与期号，点击回到当期榜单。</div><div class="mlinks card" style="margin-top:12px"><span class="vn">历次榜单</span>%s</div>' % (R["date"], esc(wk), hist)
    body = head + PLEDGE + b_supply + '<div class="rkgrid">%s%s</div>%s<div class="rkgrid">%s%s%s%s</div>%s%s%s%s' % (b_fast, b_price, b3, b4, b_up, b5, b6, media_html, audit_html, b7, foot) + cite_block("司南榜 %s" % wk, path, R["date"])
    image_head = '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:type" content="image/png"><meta property="og:image:alt" content="%s"><meta name="twitter:image:alt" content="%s">' % (esc(seo["image_alt"]), esc(seo["image_alt"]))
    return shell(title, desc, path, body, active="rank", page="rank", crumbs=[("司南榜",)], og_image=seo["image"], jsonld=[seo["jsonld"]], extra_head=image_head + '<link rel="alternate" type="application/rss+xml" title="Sinan Compute 价格变动" href="/feed.xml">')

def load_rank_weeks():
    rd = os.path.join(HERE, "rank"); return sorted([f[:-5] for f in os.listdir(rd) if f.endswith(".json")], reverse=True) if os.path.exists(rd) else []


# ------------------------------------------------------------------ 自测：用你的 Key 测一个站（Key 不出浏览器）
def build_login():
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">不设密码</div><h1 id="lg-h1" style="font-size:26px;margin-top:6px">登录司南实验室</h1><p class="lead">一个账号通用于 Compute 与 Robo。用邮箱注册或登录，也可以直接用 Google、GitHub 账号。所有价格与索引数据不登录也全部可见，登录只解锁关注、提醒、自测与历史。</p></div>
<section class="card pad rise" id="lg" style="--i:1;max-width:520px">
<h2 class="sec" id="lg-h2" style="font-size:15px">邮箱登录</h2><p class="lead" style="margin-top:4px">输入邮箱，我们发一个 6 位验证码，10 分钟内有效。第一次用会自动创建账号。</p>
<div class="lgrow"><input id="em" type="email" autocomplete="email" placeholder="you@example.com"><button class="btn p" id="em-send">发送验证码</button></div>
<div class="lgrow" id="em-step2" style="display:none"><input id="em-code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 位验证码"><button class="btn p" id="em-ok">确认</button></div><p class="sub" id="em-msg" style="margin-top:8px"></p>
<div class="lgor"><span>或用第三方账号</span></div>
<div class="lgrow" id="oauth"><a class="btn o" id="gg" href="/api/auth/google/start" style="display:none"><svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.6 2.6 30.2 0 24 0 14.6 0 6.5 5.4 2.6 13.3l7.8 6C12.3 13.2 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z"/><path fill="#FBBC05" d="M10.4 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7l-7.8-6A24 24 0 0 0 0 24c0 3.9.9 7.5 2.6 10.7l7.8-6z"/><path fill="#34A853" d="M24 48c6.2 0 11.6-2 15.4-5.6l-7.5-5.8c-2.1 1.4-4.8 2.3-7.9 2.3-6.3 0-11.7-3.7-13.6-9.2l-7.8 6C6.5 42.6 14.6 48 24 48z"/></svg> Google</a><a class="btn o" id="gh" href="/api/auth/github/start"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg> GitHub</a></div>
<p class="disc" style="margin-top:18px">登录即表示同意 <a href="https://sinanlab.com/privacy">隐私政策</a>。我们不会通过邮件索要密码；本站不设密码。第三方登录只读取公开资料与邮箱，不会代你做任何操作。</p></section>
<style>.lgrow{display:flex;gap:10px;margin-top:12px;flex-wrap:wrap}.lgrow input{flex:1;min-width:200px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit;font-size:14px;background:var(--card)}.lgrow .btn.o{display:inline-flex;align-items:center;gap:8px;flex:1;justify-content:center}.lgor{display:flex;align-items:center;gap:12px;margin-top:20px;color:var(--ink-3);font-size:12px}.lgor:before,.lgor:after{content:"";flex:1;border-top:1px solid var(--hair)}</style>
<script>(function(){var q=new URLSearchParams(location.search),rt=q.get("return_to")||"/me",watch=q.get("watch")||"",signup=q.get("mode")==="signup";var tail="?return_to="+encodeURIComponent(rt)+(watch?"&watch="+encodeURIComponent(watch):"");
if(signup){document.getElementById("lg-h1").textContent="注册司南实验室";document.getElementById("lg-h2").textContent="用邮箱注册";document.title=document.title.replace("登录","注册");}
document.getElementById("gh").href="/api/auth/github/start"+tail;document.getElementById("gg").href="/api/auth/google/start"+tail;
fetch("/api/me",{credentials:"include"}).then(function(r){return r.json();}).then(function(m){if(m&&m.user){location.replace(rt);return;}var me=m&&m.methods||{};if(me.google)document.getElementById("gg").style.display="";if(!me.github)document.getElementById("gh").style.display="none";if(!me.email){document.getElementById("em-send").disabled=true;document.getElementById("em-msg").textContent="邮箱登录暂不可用，请先用第三方账号。";}}).catch(function(){});
var ERR={bad_email:"邮箱格式不对",too_many_requests:"发得太频繁了，10 分钟后再试",send_failed:"发送失败，请稍后再试",expired:"验证码已过期，请重新发送",wrong_code:"验证码不对",too_many_tries:"错误次数太多，请重新发送验证码",signup_closed:"暂未开放新用户注册",banned:"该账号不可用",email_login_unavailable:"邮箱登录暂不可用"};
var token=null,M=document.getElementById("em-msg");
document.getElementById("em-send").addEventListener("click",function(){var v=document.getElementById("em").value.trim();if(!v)return;M.textContent="发送中…";
 fetch("/api/auth/email/start",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:v})}).then(function(r){return r.json();}).then(function(j){if(j.ok){token=j.token;document.getElementById("em-step2").style.display="";M.textContent="验证码已发到 "+j.masked+"，10 分钟内有效。";document.getElementById("em-code").focus();}else{M.textContent=ERR[j.error]||"出错了："+(j.error||"");}}).catch(function(){M.textContent="网络错误，请重试。";});});
document.getElementById("em-ok").addEventListener("click",function(){var c=document.getElementById("em-code").value.trim();if(!token||c.length!==6){M.textContent="请输入 6 位验证码。";return;}M.textContent="校验中…";
 fetch("/api/auth/email/verify",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:token,code:c,return_to:rt,watch:watch})}).then(function(r){return r.json();}).then(function(j){if(j.ok){M.textContent="成功，正在跳转…";location.replace(j.return_to||rt);}else{M.textContent=(ERR[j.error]||"出错了")+(j.left?"，还可以试 "+j.left+" 次":"");}}).catch(function(){M.textContent="网络错误，请重试。";});});
document.getElementById("em-code").addEventListener("keydown",function(e){if(e.key==="Enter")document.getElementById("em-ok").click();});
document.getElementById("em").addEventListener("keydown",function(e){if(e.key==="Enter")document.getElementById("em-send").click();});})();</script>
<script id="d" type="application/json">{{data}}</script>""", data=jsdata({"site_index": [{"d": s_["domain"], "n": s_["name"]} for s_ in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}))
    return shell("登录 · Sinan Compute", "用邮箱验证码、Google 或 GitHub 账号登录司南实验室，不设密码。", "/login", body, page="login", crumbs=[("登录",)], extra_head='<meta name="robots" content="noindex">')

# ------------------------------------------------------------------ 司南 Token 价格指数
PI = json.load(io.open(os.path.join(HERE, "price_index.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "price_index.json")) else None

def pi_chart(series, keys, w=860, h=260):
    """折价率折线图（内联 SVG，无依赖）。keys = [(key, label, color)]。"""
    if len(series) < 2: return ""
    pad_l, pad_r, pad_t, pad_b = 44, 16, 14, 30
    xs = list(range(len(series)))
    vals = [d[k]["ratio"] * 100 for d in series for k, _, _ in keys if d.get(k)]
    lo, hi = 0, max(100, (max(vals) // 20 + 1) * 20)
    def X(i): return pad_l + (w - pad_l - pad_r) * i / max(1, len(series) - 1)
    def Y(v): return pad_t + (h - pad_t - pad_b) * (1 - (v - lo) / (hi - lo))
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--hair)"/><text x="%d" y="%.1f" font-size="10" fill="var(--ink-3)" text-anchor="end">%d%%</text>' % (pad_l, w - pad_r, Y(v), Y(v), pad_l - 6, Y(v) + 3, v) for v in range(0, int(hi) + 1, 20))
    lines = ""
    for k, lbl, col in keys:
        pts = [(X(i), Y(d[k]["ratio"] * 100)) for i, d in enumerate(series) if d.get(k)]
        if len(pts) < 2: continue
        lines += '<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>' % (col, " ".join("%.1f,%.1f" % p for p in pts))
        lines += '<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (pts[-1][0], pts[-1][1], col)
    step = max(1, len(series) // 6)
    xt = "".join('<text x="%.1f" y="%d" font-size="10" fill="var(--ink-3)" text-anchor="middle">%s</text>' % (X(i), h - 8, series[i]["date"][5:]) for i in range(0, len(series), step))
    legend = "".join('<span style="display:inline-flex;align-items:center;gap:6px;margin-right:14px;font-size:12px"><i style="width:14px;height:3px;background:%s;display:inline-block;border-radius:2px"></i>%s</span>' % (col, lbl) for _, lbl, col in keys)
    return '<div class="sub" style="margin:8px 0 4px">%s</div><svg viewBox="0 0 %d %d" width="100%%" style="display:block;max-width:%dpx">%s%s%s</svg>' % (legend, w, h, w, grid, lines, xt)

def build_price_index():
    if not PI or not PI.get("latest"): return None
    L = PI["latest"]; S = PI["series"]; wk = S[-8] if len(S) >= 8 else S[0]; m30 = S[-31] if len(S) >= 31 else S[0]
    def chg(k, base=None):
        a, b = (L.get(k) or {}).get("level"), ((base or wk).get(k) or {}).get("level")
        return ("%+.1f%%" % ((a / b - 1) * 100)) if a and b else "—"
    def disp(tier=None):
        """站间离散度：每个模型 (p75−p25)/中位 的中位数。越大，同一模型在不同站的价差越大，比价越有价值。"""
        vals = [(m["series"][-1]["p75"] - m["series"][-1]["p25"]) / m["series"][-1]["median"] for m in PI["models"].values() if (tier is None or m["tier"] == tier) and m["series"] and m["series"][-1].get("median") and m["series"][-1].get("p75") is not None]
        return (sorted(vals)[len(vals) // 2]) if vals else None
    cards = []
    for k, nm_ in (("all", "全市场"), ("flagship", "旗舰（官方 ≥$20/M）"), ("mid", "中档（$2–20/M）"), ("flash", "快速（低于 $2/M）")):
        v = L.get(k)
        if not v: continue
        dsp = disp(None if k == "all" else k)
        cards.append('<div class="card kpi"><div class="k">%s</div><div class="v"><span>%d%%</span><small>官方价的几成</small></div><div class="n">市场中位 $%s/M ≈ ¥%s/M · %d 个模型 · 点位 %.1f · 7 天 %s · 30 天 %s · 站间离散 %s</div></div>' % (nm_, round(v["ratio"] * 100), fmt(v["price_usd"]), fmt(v["price_cny"]), v["n_models"], v["level"], chg(k), chg(k, m30), ("%d%%" % round(dsp * 100)) if dsp is not None else "—"))
        continue
        cards.append('<div class="card kpi"><div class="k">%s</div><div class="v"><span>%d%%</span><small>官方价的几成</small></div><div class="n">市场中位 $%s/M ≈ ¥%s/M · %d 个模型 · 点位 %.1f · 7 天 %s</div></div>' % (nm_, round(v["ratio"] * 100), fmt(v["price_usd"]), fmt(v["price_cny"]), v["n_models"], v.get("level") or 0, chg(k)))
    chart = pi_chart(S, [("all", "全市场", "#07070B"), ("flagship", "旗舰", "#6E56F5"), ("mid", "中档", "#B54708"), ("flash", "快速", "#067647")])
    rows = []
    for mid, m in sorted(PI["models"].items(), key=lambda kv: (-{"flagship": 3, "mid": 2, "flash": 1}[kv[1]["tier"]], -kv[1]["floor"])):
        t = m["series"][-1]; t7 = m["series"][-8] if len(m["series"]) >= 8 else m["series"][0]
        d7 = ("%+.0f%%" % ((t["median"] / t7["median"] - 1) * 100)) if t7["median"] else "—"
        rows.append('<tr><td><a href="/m/%s"><b>%s</b></a><div class="sub">%s</div></td><td class="num">$%s</td><td class="num"><b>$%s</b><div class="sub">¥%s</div></td><td class="num sub">$%s – $%s</td><td class="num sub">%s</td><td class="num">%d</td><td class="num"><span class="r">%d%%</span></td><td class="num sub">%s</td></tr>' % (
            esc(mid), esc(m["name"]), {"flagship": "旗舰", "mid": "中档", "flash": "快速"}[m["tier"]], fmt(m["floor"]), fmt(t["median"]), fmt(t["median"] * PI["fx"]), fmt(t["p25"]), fmt(t["p75"]), ("%d%%" % round((t["p75"] - t["p25"]) / t["median"] * 100)) if t.get("median") and t.get("p75") is not None else "—", t["n"], round(t["ratio"] * 100), d7))
    TT = D.get("task_tokens") or {}
    if TT:
        trs = []
        for mid, v in sorted(TT.items(), key=lambda kv: -kv[1]["out_per_task"]):
            m = PI["models"].get(mid); price = m["series"][-1]["median"] if m else None; floor = m["floor"] if m else None
            cost = lambda p: ("¥%.2f" % (v["out_per_task"] * 1000 / 1e6 * p * PI["fx"])) if p else "—"
            trs.append('<tr><td><b>%s</b></td><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td><td class="num">%s</td><td class="num sub">%d 渠道 · %d 题</td></tr>' % (esc(m["name"] if m else mid), v["out_per_task"], v["in_per_task"], cost(floor), cost(price), v["channels"], v["n_tasks"]))
        task_html = '<div class="tablewrap"><table><thead><tr><th>模型</th><th class="num">每题输出 token（中位）</th><th class="num">每题输入 token</th><th class="num">1000 题输出成本 · 官方价</th><th class="num">1000 题输出成本 · 市场中位</th><th class="num">样本</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(trs)
    else:
        task_html = '<div class="callout">数据积累中：能力抽样从 2026-09-14 起记录每题的 Token 用量，几天后这里会出现"同一件事各模型花多少 Token、多少钱"。</div>'
    embed = '&lt;a href="%s/price-index"&gt;&lt;img src="%s/badge/price-index.svg" alt="司南 Token 价格指数" width="360" height="72"&gt;&lt;/a&gt;' % (BASE, BASE)
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">司南 Token 价格指数 · 每日 · {{date}}</div><h1 style="font-size:26px;margin-top:6px">中国中转市场：每百万 Token 多少钱</h1><p class="lead">Token 正在成为 AI 服务的计量与结算单位，但没有人每天发布它的市场价。我们把 {{n_sites}} 个中转站每天的实付报价压成一条可引用的序列：每个主流模型的跨站中位价、它相对官方价的折价率，以及一个不受模型进出影响的链式点位（{{base}} = 100）。</p></div>
<div class="kpis rise" style="--i:1">{{cards}}</div>
<section class="card pad rise" style="--i:2;margin-top:18px"><h2 class="sec">折价率走势</h2><p class="lead" style="margin-top:4px">市场中位实付 ÷ 官方参考价。旗舰模型长期在 15% 左右，因为多数站按"1 元充 1 美元额度"卖、名义价照抄官方价；快速档接近官方价。这是测量结果，不是对哪一档的推荐。</p>{{chart}}</section>
<section class="card rise" style="--i:3;margin-top:18px"><div class="pad" style="padding-bottom:6px"><h2 class="sec">今日各模型</h2><p class="lead" style="margin-top:4px">只计入当天有 ≥{{min_sites}} 个站报价的最新两代模型；"7 天"为市场中位价相对 7 天前的变化。</p></div>
<div class="tablewrap"><table><thead><tr><th>模型</th><th class="num">官方参考 $/M</th><th class="num">市场中位</th><th class="num">25–75 分位</th><th class="num">站间离散</th><th class="num">站数</th><th class="num">折价率</th><th class="num">7 天</th></tr></thead><tbody>{{rows}}</tbody></table></div></section>
<section class="card pad rise" style="--i:4;margin-top:18px"><h2 class="sec">任务成本：同一件事各模型花多少 Token</h2><p class="lead" style="margin-top:4px">Token 有三张账单：生产成本、市场单价、任务成本。前两张这页给了，第三张来自我们每天对各模型发的同一套 30 道小题：记录每题实际消耗的输出 token，乘上单价，就是"做这件事花多少钱"。</p>{{task}}</section>
<section class="card pad rise" style="--i:5;margin-top:18px"><h2 class="sec">口径、数据与引用</h2><p class="lead" style="margin-top:4px">{{method}}</p>
<p class="sub" style="margin-top:10px">成本层：<a href="/gpu" style="color:var(--p-ink)">算力租赁账本</a>（一张显卡租一小时多少钱）。</p>
<p class="sub" style="margin-top:10px">数据：<a href="/price-index.json" style="color:var(--p-ink)">price-index.json</a>（全部序列，每日更新）· 引用时请写"司南 Token 价格指数（Sinan Token Price Index），compute.sinanlab.com"。</p>
<div style="margin-top:12px"><img src="/badge/price-index.svg" alt="司南 Token 价格指数" width="360" height="72" style="display:block;margin-bottom:8px"><code style="display:block;font-size:11.5px;background:var(--ground-2);padding:10px 12px;border-radius:10px;word-break:break-all">{{embed}}</code></div><p class="sub" style="margin-top:10px">治理规则（口径、发布节律、变更流程、利益冲突）：<a href="/governance" style="color:var(--p-ink)">/governance</a></p></section>
{{cite}}
{{poll}}<script id="d" type="application/json">{{data}}</script>""",
        date=PI["generated_at"][:10], n_sites=D["stats"]["confirmed"], base=PI["base_date"], cards="".join(cards), chart=chart, min_sites=PI["min_sites"], rows="".join(rows), task=task_html, method=esc(PI["method"]), embed=embed, cite=cite_block("司南 Token 价格指数", "/price-index", PI["generated_at"][:10]),
        poll=POLL_BOX, data=jsdata({"site_index": [{"d": s_["domain"], "n": s_["name"]} for s_ in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}))
    return shell("司南 Token 价格指数 · 每百万 Token 多少钱 · Sinan Compute", "中国模型 API 中转市场每日 Token 价格指数：各主流模型跨站中位实付价、相对官方价的折价率、链式点位，可引用可下载。", "/price-index", body, active="pindex", page="pindex", crumbs=[("Token 价格指数",)])

def price_index_badge():
    L = PI["latest"] if PI and PI.get("latest") else None
    if not L: return None
    font = "Inter,-apple-system,Segoe UI,PingFang SC,Source Han Sans SC,Noto Sans SC,sans-serif"
    parts = " · ".join("%s %d%%" % (n, round(L[k]["ratio"] * 100)) for k, n in (("flagship", "旗舰"), ("mid", "中档"), ("flash", "快速")) if L.get(k))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="72" viewBox="0 0 360 72" role="img" aria-label="司南 Token 价格指数">'
            '<rect width="360" height="72" rx="14" fill="#07070B"/><rect x=".5" y=".5" width="359" height="71" rx="13.5" fill="none" stroke="#F5F5F7" stroke-opacity=".14"/>'
            '<g transform="translate(14 14) scale(.6875)">%s</g><line x1="68" y1="18" x2="68" y2="54" stroke="#B8A4FA" stroke-width="1"/>'
            '<text x="80" y="23" font-family="%s" font-size="11" fill="#B8A4FA">司南 Token 价格指数 · %s</text>'
            '<text x="80" y="43" font-family="%s" font-size="15" font-weight="600" fill="#F5F5F7">全市场 %d%% <tspan font-family="ui-monospace,Menlo,monospace" font-size="12" font-weight="400" fill="#B8A4FA">· 市场中位 $%s/M</tspan></text>'
            '<text x="80" y="61" font-family="%s" font-size="10.5" fill="#B8A4FA">%s</text>'
            '<text x="346" y="61" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="10" fill="#B8A4FA">点位 %.1f</text></svg>'
            % (MARK_SVG, font, PI["generated_at"][:10], font, round(L["all"]["ratio"] * 100), fmt(L["all"]["price_usd"]), font, parts, L["all"].get("level") or 0))

# ------------------------------------------------------------------ 需求探针（只计数，不推荐）
POLL_BOX = ('<section class="card pad rise" id="poll" style="margin-top:18px"><div class="eyebrow" style="color:var(--p)">一个问题 · 只计数</div><h2 class="sec" style="margin-top:4px">你需要司南代你统一调用吗？</h2>'
            '<p class="lead" style="margin-top:4px">设想：你自己持有各家的 Key，司南只负责测量、按你的条件筛选、把请求转到你选的渠道并记录延迟与成本。我们现在<b>不做</b>这件事，票数决定要不要做。</p>'
            '<div class="pollrow" id="pollrow"><button class="btn o" data-a="need">需要</button><button class="btn o" data-a="no">不需要，我只要数据</button><button class="btn o" data-a="unsure">说不准</button><span class="sub" id="pollmsg"></span></div>'
            '<script>(function(){var row=document.getElementById("pollrow"),M=document.getElementById("pollmsg");if(!row)return;try{if(localStorage.getItem("poll:byok")){row.querySelectorAll("button").forEach(function(b){b.disabled=true;});M.textContent="已记录，谢谢。";}}catch(e){}'
            'row.addEventListener("click",function(e){var b=e.target.closest("button");if(!b||b.disabled)return;fetch("/api/poll",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({q:"byok",a:b.dataset.a})}).then(function(){try{localStorage.setItem("poll:byok",b.dataset.a);}catch(e){}row.querySelectorAll("button").forEach(function(x){x.disabled=true;});M.textContent="已记录，谢谢。累计结果每周一在被引用监测里汇总。";}).catch(function(){M.textContent="没记上，稍后再试。";});});})();</script></section>')

def load_open_reports():
    p_ = os.path.join(HERE, "reports_open.json")
    return json.load(io.open(p_, encoding="utf-8")) if os.path.exists(p_) else {"open": 0, "items": [], "fixed": []}

DATA_FILES = [
    ("data_v2.json", "/data_v2.json", "每日", "模型账本主文件：40 个模型 × 每个中转站的实付价（$/百万输出）、比率、区间、抓取快照编号；每站的可达率、注册状态、探针摘要、榜单名次；当天价格变动与新收录。", "generated_at, fx{rate,as_of}, models[{id,name,vendor,floor,rows[{vendor,out,ratio,band,sids,as_of,probe}]}], sites[{domain,name,panel,cluster,median,avail{uptime,ttfb_p50},register,probe,verified,rank_badge}], stats, changes[{t,vendor,model,old,new}], new_sites, rank{...}"),
    ("price-index.json", "/price-index.json", "每日", "司南 Token 价格指数：全市场与三档（旗舰 / 中档 / 快速）的折价率与链式点位逐日序列，每个模型的市场中位价序列与样本站数。", "version, base_date, tiers, series[{date,all,flagship,mid,flash}], latest, models{id:{name,tier,official,series[{date,median,n}]}}, method"),
    ("media.json", "/media.json", "每日", "图像与视频账本：按模型族的官方参考价与各站实付价。统一口径：视频 $/秒、图像 $/张（val 字段），折算依据见 val_basis（native 站方按此口径报价 / stated 按模型名里的时长 / assumed 按该族默认时长）；原始报价与单位保留在 eff、unit。", "image[{family,name,ref,rows[...]}], video[...], held_sites, stats,val,val_basis,val_secs,canon_unit,n_assumed"),
    ("gpu.json", "/gpu.json", "每日", "算力租赁账本：主流 GPU 在 RunPod / Vast.ai / 算力互联的单卡每小时报价（美元与人民币）。", "platforms, gpus[{gpu,quotes[{platform,kind,usd,cny,n,ts}]}]"),
    ("rank/<期号>.json", "/rank/%s.json", "每周一", "司南榜某一期的完整数据（12 张榜、门槛、样本、待核）。期号形如 2026-w38，永久不变。", "week, date, n_sites, eligible_uptime, fast, price, dual, coverage, uptime, low, media, audit"),
    ("report/<月份>.json", "/report/%s.json", "每日重算，月底定稿", "月报原始数据：规模、结构、价格指数、涨跌最多的模型、可达分布、探针与核查、多模态、算力。", "month, period, final, scale, prices, reach, probes, audit, boards, media, gpu"),
    ("changes.json", "/changes.json", "每日", "价格变动的 JSON Feed（JSON Feed 1.1 格式），可被订阅器与脚本直接读取；与 feed.xml 内容相同。", "version, title, items[{id,url,title,date_published,_sinan{vendor,model,old,new}}]"),
    ("feed.xml", "/feed.xml", "每日", "价格变动 RSS。", ""),
    ("assets/tokref.json", "/assets/tokref.json", "每日", "一致性探针的公开参考计数：8 条探针串、各模型的多渠道共识计数、弱参考标记。命令行工具 sinan-probe 读它。", "version, probes[], models{id:{ref[],peers,weak}}, how"),
    ("go_links.json", "/go_links.json", "每日", "全部已确认站的域名与出站链接（不带任何推广参数）。", "{domain: url}"),
]
ROBO_FILES = [("robo.sinanlab.com/data/models.json", "https://robo.sinanlab.com/data/models.json", "每次发布", "Robo 模型索引：每个开源具身模型的许可证、参数量、权重与代码地址、输入模态、目标本体，以及每个字段的证据来源。"),
              ("robo.sinanlab.com/data/compat.json", "https://robo.sinanlab.com/data/compat.json", "每次发布", "模型 × 本体适配矩阵，每格状态（官方 / 社区验证 / 理论可行 / 不支持 / 未知）与证据。"),
              ("robo.sinanlab.com/data/embodiments.json", "https://robo.sinanlab.com/data/embodiments.json", "每次发布", "本体（机器人）索引：自由度、末端、SDK、价格区间、数据格式。"),
              ("robo.sinanlab.com/data/hardware.json", "https://robo.sinanlab.com/data/hardware.json", "每次发布", "推理硬件与租赁参考价。")]

def build_api_docs():
    wk = (load_rank_weeks() or ["2026-w38"])[0]; mo = (load_reports() or [{"month": "2026-09"}])[0]["month"]
    rows = "".join('<tr><td><b>%s</b><div class="sub">%s</div></td><td>%s</td><td><a href="%s" style="color:var(--p-ink)">%s</a></td>%s</tr>' % (esc(n), esc(d), esc(f), (u % wk) if "rank" in n else (u % mo) if "report" in n else u, ((u % wk) if "rank" in n else (u % mo) if "report" in n else u), ('<td class="sub" style="font-size:11.5px">%s</td>' % esc(k)) if k else '<td class="sub">—</td>') for n, u, f, d, k in DATA_FILES)
    rrows = "".join('<tr><td><b>%s</b><div class="sub">%s</div></td><td>%s</td><td><a href="%s" style="color:var(--p-ink)">%s</a></td></tr>' % (esc(n), esc(d), esc(f), u, esc(u)) for n, u, f, d in ROBO_FILES)
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">开放数据与接口</div><h1 style="font-size:26px;margin-top:6px">直接拿数据，不用登录，不用 Key</h1><p class="lead">司南的全部测量结果都是静态 JSON 文件，和网页同一批生成，谁都可以下载、抓取、放进自己的脚本。这一页说明每个文件是什么、多久更新、字段长什么样，以及我们对稳定性的承诺。</p>{{pledge}}</div>
<section class="card pad rise" style="--i:1"><h2 class="sec">稳定性承诺</h2><ul class="lead" style="margin-top:6px;padding-left:18px"><li>已公开的字段<b>不删、不改名、不改含义</b>；只会新增字段。需要变更时先在本页公告 30 天，并同时提供新旧两版。</li><li>每个文件顶部都有 <code>generated_at</code>（北京时间）；口径版本记在 <a href="/method" style="color:var(--p-ink)">口径与定义</a>。</li><li>文件按 Cloudflare 全球缓存分发，抓取频率不限；请在请求头里带上能联系到你的 User-Agent。</li><li>数据可自由引用与转载，注明"数据：司南实验室 compute.sinanlab.com"。不接受任何被测渠道的付费，出站链接不带推广参数。</li></ul></section>
<section class="card pad rise" style="--i:2;margin-top:18px"><h2 class="sec">Sinan Compute · 中转市场与算力</h2><div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>文件</th><th>更新</th><th>地址</th><th>主要字段</th></tr></thead><tbody>{{rows}}</tbody></table></div></section>
<section class="card pad rise" style="--i:3;margin-top:18px"><h2 class="sec">Sinan Robo · 开源具身模型</h2><div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>文件</th><th>更新</th><th>地址</th></tr></thead><tbody>{{rrows}}</tbody></table></div><p class="sub" style="margin-top:8px">两站字段的共同约定：所有价格为数字（美元或标注 cny）；所有证据为 <code>{url, fetched, source_type, note}</code>；未核实的字段为 <code>null</code>，不用默认值填空。</p></section>
<section class="card pad rise" style="--i:4;margin-top:18px"><h2 class="sec">现成的工具</h2><div class="tablewrap" style="margin-top:8px"><table><tbody>
<tr><td><b>sinan-probe</b><div class="sub">用自己的 Key 在终端测一个中转站：一致性探针、首字节延迟、回显模型名。单文件，只依赖 Python 标准库。</div></td><td><a href="https://github.com/sinanlabs/compute/tree/main/cli" style="color:var(--p-ink)">github.com/sinanlabs/compute/cli</a></td></tr>
<tr><td><b>GitHub Action · 价格盯梢</b><div class="sub">复制一个工作流文件到你的仓库，改一行模型列表，每天自动检查这些模型在中转市场的市场中位价，变动超过阈值就开 Issue。</div></td><td><a href="https://github.com/sinanlabs/compute/tree/main/templates/github-action" style="color:var(--p-ink)">templates/github-action</a></td></tr>
<tr><td><b>徽章</b><div class="sub">价格指数徽章每天自动刷新；上榜站与核验站有各自的徽章，站点页可取嵌入代码。</div></td><td><a href="/badge/price-index.svg" style="color:var(--p-ink)">/badge/price-index.svg</a></td></tr></tbody></table></div>
<p class="lead" style="margin-top:12px">用 Python 三行读价格指数：</p><pre style="font-size:12.5px;background:var(--ground-2);padding:12px 14px;border-radius:12px;overflow:auto">import json, urllib.request
pi = json.load(urllib.request.urlopen(urllib.request.Request("https://compute.sinanlab.com/price-index.json", headers={"User-Agent": "you@example.com"})))
print(pi["latest"])</pre>
<p class="sub" style="margin-top:10px">需要开发包（Python / TypeScript）、按你的口径重算、或全量历史序列：写信到 <a href="mailto:hello@sinanlab.com" style="color:var(--p-ink)">hello@sinanlab.com</a>。有人要我们就做，没人要我们不做空壳。</p></section>
{{poll}}{{cite}}<script id="d" type="application/json">{{data}}</script>""", pledge=PLEDGE, rows=rows, rrows=rrows, poll=POLL_BOX, cite=cite_block("开放数据与接口", "/api-docs", GEN_DATE), data=jsdata(LIGHT_INDEX()))
    return shell("开放数据与接口 · Sinan Compute", "司南实验室全部测量数据的文件清单、字段说明、更新频率与稳定性承诺；命令行工具与 GitHub Action 模板。", "/api-docs", body, active="api", page="api", crumbs=[("开放数据与接口",)])

def build_survival():
    SV = D.get("survival") or {}; W_ = SV.get("windows") or {}
    DIM_ZH = {"tld": "域名后缀", "icp": "ICP 备案", "register": "注册状态", "family": "面板家族", "age": "域名年龄", "uptime": "7 天可达"}
    VAL_ZH = {"premium": "主流后缀（.com .net .cn .ai …）", "budget": "低价后缀（.top .cc .xyz .vip …）", "other": "其他", "open": "开放", "closed": "关闭 / 邀请", "unknown": "未判定", "one-api": "one-api 一族", "sub2api": "Sub2API 一族", "<180d": "不满半年", "180–730d": "半年到两年", ">730d": "两年以上"}
    parts = []
    for N in ("7", "14", "30", "90"):
        w = W_.get(N)
        if not w:
            parts.append('<div class="callout" style="margin-top:12px"><b>%s 天窗口</b>：观察满 %s 天的站还不到 30 个，暂不出数。数据从 2026-09-02 起，这一栏会随时间自动填上。</div>' % (N, N)); continue
        o = w["overall"]; rows = []
        for dim, bs in w["buckets"].items():
            for k, v in bs.items():
                rows.append([DIM_ZH.get(dim, dim), VAL_ZH.get(k, k), v["n"] if v else "<30", v["dead"] if v else "—", ('<span class="r">%.1f%%</span>' % (v["rate"] * 100)) if v else "样本不足"])
        parts.append('<h3 style="font-size:15px;margin-top:20px">%s 天窗口 · 观察满 %s 天的 %d 个站里，%d 个已消失（%.1f%%）</h3>' % (N, N, o["n"], o["dead"], o["rate"] * 100) + _tbl(["特征", "取值", "#站数", "#已消失", "#比例"], rows))
    ev = SV.get("events") or []
    ev_html = _tbl(["日期", "站", "事件"], [[esc(e["at"]), '<a href="/s/%s">%s</a>' % (esc(e["domain"]), esc(e["domain"])), "消失" if e["event"] == "dead" else "恢复"] for e in ev[:50]]) if ev else '<p class="sub" style="margin-top:8px">2026-09-02 以来还没有记录到"连续 7 天未连通"的站。</p>'
    ch = SV.get("churn") or {}
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">站点存续 · 历史基率 · 每日更新</div><h1 style="font-size:26px;margin-top:6px">中转站会消失吗？消失前有什么可测的特征</h1><p class="lead">买家最怕的不是贵，是钱充进去站没了。这一页只做一件事：记录哪些站消失了（连续 7 天、80 轮以上有效探测一次都没连上），把它们消失前可以测量的特征摆出来，算出"有这种特征的站，N 天里消失了多大比例"。这是历史基率，不是对任何一家站的预测，也不是指控。样本不满 30 的桶不出数。</p>{{pledge}}</div>
<div class="kpis rise" style="--i:1"><div class="card kpi"><div class="k">已确认中转站</div><div class="v"><span>{{sites}}</span></div><div class="n">观察起点 2026-09-02</div></div><div class="card kpi"><div class="k">本月消失</div><div class="v"><span>{{dead}}</span></div><div class="n">恢复 {{rev}} · 消失 = 连续 7 天未连通</div></div><div class="card kpi"><div class="k">已知域名年龄</div><div class="v"><span>{{age}}</span></div><div class="n">按注册局公开记录或首张证书日期，每天补 150 个</div></div></div>
<section class="card pad rise" style="--i:2;margin-top:18px"><h2 class="sec">按特征看消失比例</h2><p class="lead" style="margin-top:4px">特征都是在站点页上能看到的：域名后缀、注册开不开、面板家族、域名年龄、7 天可达率（备案信息尚未采集，采集后自动加入）。窗口越长越有意义，但也需要更长的观察期；现在只有短窗口有数。</p>{{parts}}</section>
<section class="card pad rise" style="--i:3;margin-top:18px"><h2 class="sec">消失与恢复记录</h2>{{ev}}</section>
<section class="card pad rise" style="--i:4;margin-top:18px"><h2 class="sec">口径</h2><p class="lead" style="margin-top:4px">{{defn}} 域名年龄取注册局 RDAP 公开记录的注册日期；没有 RDAP 的后缀（如 .cn）退回证书透明度日志里该域名的首张证书日期，会比真实注册日期晚。每个站点页有一张"存续信号"卡，列出该站的这些特征。我们不把这些特征加权成分数，因为权重就是观点。</p></section>
<script id="d" type="application/json">{{data}}</script>""", pledge=PLEDGE, sites=ch.get("sites", D["stats"]["confirmed"]), dead=ch.get("dead_this_month", 0), rev=ch.get("revived_this_month", 0), age=SV.get("age_coverage", 0), parts="".join(parts), ev=ev_html, defn=esc(SV.get("definition") or ""), data=jsdata(LIGHT_INDEX()))
    return shell("站点存续 · 中转站消失的历史基率 · Sinan Compute", "记录消失的中转站与消失前可测的特征，给出按特征分桶的历史基率。不预测、不指控。", "/survival", body, active="life", page="life", crumbs=[("站点存续",)])

def build_governance():
    gp = os.path.join(ROOT, "docs", "INDEX-GOVERNANCE.md")
    md = io.open(gp, encoding="utf-8").read() if os.path.exists(gp) else ""
    md = "\n".join(l for l in md.splitlines() if not l.startswith("# "))
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">指数治理 · v1 · 2026-09-16 起</div><h1 style="font-size:26px;margin-top:6px">司南 Token 价格指数 · 治理规则</h1><p class="lead">为什么可以把这个指数写进合同、报告和政策里：规则先定，改规则也按规则。以下每一条都是对外承诺。</p>{{pledge}}</div>
<section class="card pad rise" style="--i:1">{{md}}</section>{{cite}}<script id="d" type="application/json">{{data}}</script>""", pledge=PLEDGE, md=md_html(md), cite=cite_block("司南 Token 价格指数治理规则", "/governance", GEN_DATE), data=jsdata(LIGHT_INDEX()))
    return shell("指数治理规则 · 司南 Token 价格指数 · Sinan Compute", "司南 Token 价格指数的口径、发布节律、变更流程、异常处理与利益冲突规则。", "/governance", body, active="gov", page="gov", crumbs=[("指数治理",)])

def build_corrections():
    R = load_open_reports()
    fixed = list(R.get("fixed") or [])
    _mp = os.path.join(HERE, "corrections_manual.json")   # 邮件 / 人工核对得来的修正，署名记录
    if os.path.exists(_mp):
        try: fixed = json.load(io.open(_mp, encoding="utf-8")) + fixed
        except Exception: pass
    fixed.sort(key=lambda x: x.get("date", ""), reverse=True)
    frows = "".join('<tr><td class="sub">%s</td><td>%s</td><td>%s → <b>%s</b></td><td class="sub">%s</td><td class="sub">%s</td></tr>' % (esc(x.get("date", "")[:10]), esc(x.get("target", "")), esc(x.get("original", "")), esc(x.get("corrected", "")), esc(x.get("reason", "")), esc(x.get("credit") or "站内核查")) for x in fixed) or '<tr><td colspan="5" class="sub">还没有已确认的修正记录。数据核查每晚自动跑，命中的行会先标"待核"而不是直接上榜。</td></tr>'
    orows = "".join('<tr><td class="sub">%s</td><td>%s</td><td>%s</td><td class="sub">%s</td></tr>' % (esc(x.get("created_at", "")[:10]), esc(x.get("kind", "") + " · " + x.get("key", "")), esc(x.get("note", "")), esc(x.get("handle") or "匿名")) for x in R.get("items") or []) or '<tr><td colspan="4" class="sub">目前没有待处理的报错。</td></tr>'
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">修正日志 · 永久公开</div><h1 style="font-size:26px;margin-top:6px">我们改过什么，谁指出的</h1><p class="lead">每个数字旁边都有"报错"。用户提交的报错进核查队列，我们核对原始快照后，要么修正并在这里署名记录，要么说明为什么维持原判。这是数据网络的开始：你指出的错，会带着你的名字留在这里。</p>{{pledge}}</div>
<section class="card pad rise" style="--i:1"><h2 class="sec">已确认的修正</h2><div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>日期</th><th>对象</th><th>修正</th><th>原因</th><th>指出者</th></tr></thead><tbody>{{frows}}</tbody></table></div></section>
<section class="card pad rise" style="--i:2;margin-top:18px"><h2 class="sec">待处理的报错 · {{n}} 条</h2><p class="sub" style="margin-top:4px">用户提交后 3 个工作日内核对。核对期间相关数字照常显示，但你可以在证据链里看到"有人报错"。</p><div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>提交</th><th>对象</th><th>说明</th><th>提交者</th></tr></thead><tbody>{{orows}}</tbody></table></div></section>
<section class="card pad rise" style="--i:3;margin-top:18px"><h2 class="sec">怎么报错</h2><p class="lead" style="margin-top:4px">在任何一个实付价、比率或站点信息旁，点开证据链，底部有"这条数据有误？报错"。需要登录（只是为了防刷），写一句哪里不对、最好附上你看到的原文链接。我们不接受"这家站很好/很差"一类的评价，只接受可核对的事实。</p></section>
<script id="d" type="application/json">{{data}}</script>""", pledge=PLEDGE, frows=frows, orows=orows, n=R.get("open", 0), data=jsdata(LIGHT_INDEX()))
    return shell("修正日志 · Sinan Compute", "司南实验室的公开修正日志：用户报错、核对结果、署名记录。", "/corrections", body, active="fix", page="fix", crumbs=[("修正日志",)])

def build_changes_json():
    items = []
    for c in (D.get("changes") or [])[:500]:
        mid = c["model"]; mname = next((m["name"] for m in D["models"] if m["id"] == mid), mid)
        items.append({"id": "%s|%s|%s" % (c["t"], c["vendor"], mid), "url": "%s/m/%s" % (BASE, mid), "title": "%s · %s：$%s → $%s /百万输出" % (c["vendor"], mname, fmt(c["old"]), fmt(c["new"])), "date_published": c["t"], "_sinan": {"vendor": c["vendor"], "model": mid, "old": c["old"], "new": c["new"], "kind": c.get("kind")}})
    return json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Sinan Compute · 中转站价格变动", "home_page_url": BASE, "feed_url": BASE + "/changes.json", "description": "连续两次抓取一致才计的实付价变动；只陈述测量，不含推荐。", "items": items}, ensure_ascii=False)

# ------------------------------------------------------------------ 订阅框（全站页脚）
SUBSCRIBE_BOX = ('<section class="subbox" id="subscribe"><div><div class="eyebrow" style="color:var(--p)">每周一封</div><h2 class="sec" style="margin-top:4px">订阅司南周报</h2><p class="sub" style="margin-top:4px">本周司南榜、价格指数、主流模型变价、新收录与失联的站。只陈述测量，不含推荐，随时一键退订。</p></div>'
                 '<form class="subform" id="subform" novalidate><input type="email" id="sub-email" placeholder="你的邮箱" autocomplete="email" required><button class="btn p" type="submit">订阅</button><span class="sub" id="sub-msg"></span></form>'
                 '<script>(function(){var f=document.getElementById("subform"),M=document.getElementById("sub-msg");if(!f)return;f.addEventListener("submit",function(e){e.preventDefault();var v=document.getElementById("sub-email").value.trim();if(!/^[^\\s@]+@[^\\s@]+\\.[a-zA-Z]{2,}$/.test(v)){M.textContent="邮箱格式不对";return;}M.textContent="发送中…";'
                 'fetch("/api/subscribe",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:v,lang:document.documentElement.lang==="en"?"en":"zh"})}).then(function(r){return r.json();}).then(function(j){M.textContent=j.ok?(j.state==="already"?"这个邮箱已经订阅了。":"已发确认邮件，点邮件里的按钮完成订阅。"):(j.error==="mail_not_ready"?"邮件服务接入中，稍后再试。":"没成功，请稍后再试。");}).catch(function(){M.textContent="网络错误，请重试。";});});})();</script></section>')

# ------------------------------------------------------------------ 引用块与底线声明（全站复用）
def cite_block(title, path, date):
    zh = "司南实验室，《%s》，%s，%s%s（访问日期 ____）" % (title, date, BASE, path)
    en = "Sinan Lab, \"%s\", %s, %s%s (accessed ____)" % (title, date, BASE, path)
    return ('<section class="card pad rise" style="margin-top:18px"><h2 class="sec">引用本页</h2><p class="lead" style="margin-top:4px">数据可自由引用与转载，请注明来源并保留链接。我们不收任何被测渠道的钱、不卖排位、出站链接不带推广参数，引用时可放心标注为独立第三方测量。</p>'
            '<div style="display:grid;gap:8px;margin-top:10px"><code style="display:block;font-size:12px;background:var(--ground-2);padding:10px 12px;border-radius:10px;word-break:break-all">%s</code><code style="display:block;font-size:12px;background:var(--ground-2);padding:10px 12px;border-radius:10px;word-break:break-all">%s</code></div>'
            '<p class="sub" style="margin-top:10px">媒体、研究机构、金融机构需要原始数据或定制口径，写信到 <a href="mailto:hello@sinanlab.com" style="color:var(--p-ink)">hello@sinanlab.com</a>，见 <a href="/press" style="color:var(--p-ink)">媒体与研究者</a>。</p></section>' % (esc(zh), esc(en)))

PLEDGE = ('<div class="pledge"><span><b>不收被测方一分钱</b>没有付费收录、付费核验、付费加速</span><span><b>不卖排位</b>所有榜按测量值排序，没有任何商业变量</span><span><b>不带推广参数</b>出站链接只记点击数，不拿返佣</span></div>')

def load_reports():
    rd = os.path.join(HERE, "reports")
    out = []
    if os.path.exists(rd):
        for f in sorted(os.listdir(rd), reverse=True):
            if f.endswith(".json"): out.append(json.load(io.open(os.path.join(rd, f), encoding="utf-8")))
    return out

def MONTH_ZH(m): return "%d 年 %d 月" % tuple(int(x) for x in m.split("-"))
TIER_ZH = {"flagship": "旗舰", "mid": "中档", "flash": "快速"}
HOLD_ZH = {"unit_hint": "单位提示", "lone_outlier": "价格孤点", "board_margin": "榜首差距", "extreme_ratio": "极端比率", "field_drift": "字段漂移"}

def _idx_pc(snap, k):
    v = ((snap or {}).get(k) or {}).get("ratio") if snap else None
    return "—" if v is None else "%d%%" % round(v * 100)

def md_html(md):
    """极简 Markdown → HTML：段落、**粗体**、有序/无序列表、[链接](url)。用于月报叙述稿。"""
    def inline(t):
        t = esc(t); t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        return re.sub(r"\[([^\]]+)\]\((https?://[^)]+|/[^)]*)\)", r'<a href="\2" style="color:var(--p-ink)">\1</a>', t)
    out, buf, lst = [], [], None
    def flush():
        nonlocal buf, lst
        if buf: out.append('<p class="lead" style="margin-top:10px">%s</p>' % inline(" ".join(buf))); buf = []
        if lst: out.append("</%s>" % lst); lst = None
    for line in md.splitlines():
        t = line.strip()
        if not t: flush(); continue
        h = re.match(r"^(#{1,3})\s+(.*)", t)
        if h:
            flush(); lvl = len(h.group(1)); out.append('<h%d class="%s" style="margin-top:%dpx">%s</h%d>' % (min(lvl + 1, 4), "sec" if lvl <= 2 else "", 22 if lvl <= 2 else 14, inline(h.group(2)), min(lvl + 1, 4))); continue
        m = re.match(r"^(\d+)\.\s+(.*)", t); b = re.match(r"^[-*]\s+(.*)", t)
        if m or b:
            kind = "ol" if m else "ul"
            if buf: out.append('<p class="lead" style="margin-top:10px">%s</p>' % inline(" ".join(buf))); buf = []
            if lst != kind:
                if lst: out.append("</%s>" % lst)
                out.append('<%s class="lead" style="margin-top:8px;padding-left:22px">' % kind); lst = kind
            out.append("<li style=\"margin:6px 0\">%s</li>" % inline(m.group(2) if m else b.group(1)))
        else:
            if lst: out.append("</%s>" % lst); lst = None
            buf.append(t)
    flush(); return "".join(out)

def load_analysis(month, lang="zh"):
    p_ = os.path.join(HERE, "reports", month + (".analysis.en.md" if lang == "en" else ".analysis.md"))
    if not os.path.exists(p_): return {}
    sec, cur = {}, None
    for line in io.open(p_, encoding="utf-8"):
        m = re.match(r"^## \[(\w+)\]\s*(.*)", line)
        if m: cur = m.group(1); sec[cur] = {"title": m.group(2).strip(), "md": []}; continue
        if cur: sec[cur]["md"].append(line.rstrip("\n"))
    return {k: {"title": v["title"], "html": md_html("\n".join(v["md"]))} for k, v in sec.items()}

def _tbl(head, rows, note=""):
    return '<div class="tablewrap" style="margin-top:12px"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>%s' % ("".join("<th%s>%s</th>" % (' class="num"' if h.startswith("#") else "", esc(h.lstrip("#"))) for h in head), "".join("<tr>%s</tr>" % "".join("<td%s>%s</td>" % (' class="num"' if head[i].startswith("#") else "", c) for i, c in enumerate(r)) for r in rows), ('<p class="sub" style="margin-top:6px">%s</p>' % note) if note else "")

def build_report(Rp, first_issue=False, lang="zh"):
    m = Rp["month"]; sc = Rp["scale"]; pr = Rp["prices"]; idx = pr["index"]; p0, p1 = Rp["period"]; ST = Rp.get("structure") or {}
    A = load_analysis(m, lang)
    title = "中国模型 API 中转市场月报 · %s%s" % (MONTH_ZH(m), "（创刊号）" if first_issue else "")
    pn = sc.get("panels") or {}
    one = sum(v for k, v in pn.items() if "one-api" in k or "new-api" in k); sub = pn.get("sub2api", 0); agg = sum(v for k, v in pn.items() if k in ("multimodal-aggregator", "multi-vendor"))
    org = ST.get("origin") or {}
    kp = [("已确认中转站", "%s" % sc["confirmed_now"], "订阅制（Sub2API 一族）%d · 按量制（one-api 一族）%d" % (sub, one)),
          ("海外闭源模型 · 中转中位折价率", _idx_pc({"x": {"ratio": org.get("foreign_median")}}, "x"), "%d 个模型；国产模型中位 %s（%d 个）" % (org.get("n_foreign", 0), _idx_pc({"x": {"ratio": org.get("domestic_median")}}, "x"), org.get("n_domestic", 0))),
          ("价格指数点位", "%.1f → %.1f" % (((idx.get("first") or {}).get("all") or {}).get("level") or 100, ((idx.get("last") or {}).get("all") or {}).get("level") or 100), "折价率快照 %s → %s（受样本构成影响）" % (_idx_pc(idx.get("first"), "all"), _idx_pc(idx.get("last"), "all"))),
          ("主流模型变价", "%d 次" % pr["mainstream_changes"], "涨 %d · 降 %d；国产降 %d 涨 %d" % (pr["ups"], pr["downs"], (ST.get("change_dirs") or {}).get("domestic:down", 0), (ST.get("change_dirs") or {}).get("domestic:up", 0)))]
    kpis = "".join('<div class="card kpi"><div class="k">%s</div><div class="v"><span>%s</span></div><div class="n">%s</div></div>' % (k, v, n) for k, v, n in kp)
    chart = pi_chart(idx["series"], [("all", "全市场", "#07070B"), ("flagship", "旗舰", "#6E56F5"), ("mid", "中档", "#B54708"), ("flash", "快速", "#067647")]) if len(idx.get("series") or []) >= 2 else ""
    def sec(key, num, default_title, computed=""):
        a = A.get(key) or {}
        return '<section class="card pad rise" style="--i:%d;margin-top:18px"><h2 class="sec">%s</h2>%s%s</section>' % (num + 1, esc(a.get("title") or default_title), a.get("html", ""), computed)
    # ---- 计算表
    T = {}
    T["scale"] = _tbl(["面板家族", "#站数", "#注册开放", "#关闭", "#未判定", "#有公开报价", "#报价中位折价率"], [[esc(x["panel"]), x["n"], x["open"], x["closed"], x["unknown"], x["with_quotes"], ("%d%%" % round(x["median_ratio"] * 100)) if x.get("median_ratio") else "—"] for x in (ST.get("panels") or [])[:6]], "面板家族按公开接口指纹判定；Sub2API 一族的套餐价在登录之后，本期无公开报价。") \
        + _tbl(["登录方式", "#one-api 一族", "#Sub2API 一族"], [[esc(k), (ST.get("logins") or {}).get("one-api", {}).get(k, 0), (ST.get("logins") or {}).get("sub2api", {}).get(k, 0)] for k in ("邮箱", "GitHub", "LINUX DO", "Google", "OIDC", "Discord", "Telegram", "微信")]) \
        + _tbl(["顶级域", "#站数"] , [[".%s" % esc(t), n] for t, n in (ST.get("tld") or [])[:8]]) \
        + _tbl(["收录来源", "#本期站数"], [[esc(k.replace("directory:", "名录：")), v] for k, v in list((sc.get("by_channel") or {}).items())[:8]])
    orows = sorted(org.get("rows") or [], key=lambda r: r["ratio"])
    T["prices"] = chart + _tbl(["模型", "厂商", "档", "#官方 $/M", "#中转中位 $/M", "#折价率", "#站数"], [[esc(r["name"]), esc(r["vendor"]), TIER_ZH.get(r["tier"], ""), fmt(r["official"]), fmt(r["median"]), '<span class="r">%d%%</span>' % round(r["ratio"] * 100), r["n"]] for r in orows], "折价率 = 中转市场中位实付 ÷ 官方参考价；国产 / 海外按厂商注册地划分。") \
        + _tbl(["档", "#报价数", "#低于成本下限", "#低于批量折扣", "#说得通", "#接近公开价", "#高于公开价", "#显著高于"], [[TIER_ZH.get(t, t), v["n"]] + ["%d%%" % round(100 * v["share"].get(k, 0)) for k in ("unsustainable", "below_bulk", "explainable", "normal", "premium", "far_above")] for t, v in (ST.get("bands_by_tier") or {}).items()], "区间定义见口径文档第 3 节：<15% 低于成本下限 · 15–40% 低于常见批量折扣 · 40–80% 说得通 · 80–125% 接近公开价 · 125–200% 高于 · >200% 显著高于。") \
        + _tbl(["充值比例（元 / 每 1 美元名义额度）", "#站数", "#占比"], [["%.2g" % k, v, "%d%%" % round(100 * v / max(1, (ST.get("topup") or {}).get("sites", 1)))] for k, v in ((ST.get("topup") or {}).get("dist") or [])[:8]], "每站取最常见的充值比例；%d 个有公开报价的站。1.0 = 1 元换 1 美元额度（实付约为官方价的 15%%）；6.8–7.3 ≈ 按真实汇率 1:1。" % (ST.get("topup") or {}).get("sites", 0)) \
        + '<h3 style="font-size:14px;margin-top:18px">期内市场中位价变化最大的模型</h3>' + _tbl(["模型", "#期初 → 期末 $/M", "#变化", "#站数 · 官方价的"], [[esc(x["name"]) + '<div class="sub">%s</div>' % TIER_ZH.get(x.get("tier"), ""), "$%s → $%s" % (fmt(x["from"]), fmt(x["to"])), '<span class="r">%+.0f%%</span>' % x["pct"], "%d 站 · %d%%" % (x["n"], round(x["ratio"] * 100))] for x in (pr["movers_down"][:5] + pr["movers_up"][:5])])
    reach = Rp.get("reach") or {}; dd = reach.get("dist") or {}; pb = Rp.get("probes") or {}; au = Rp.get("audit") or {"open_by_reason": {}, "cleared_this_month": 0}
    T["reach"] = _tbl(["#过门槛站数", "#7 天 100%", "#99%–99.9%", "#低于 99%", "#我方故障轮次剔除"], [[reach.get("eligible"), dd.get("full"), dd.get("hi"), dd.get("low"), Rp.get("scale", {}).get("outage_rounds_excluded") or "—"]]) \
        + _tbl(["可达率最低", "#7 天可达", "#探测次数", "#握手 p50"], [[esc(x["domain"]), "%.1f%%" % x["uptime"], x["n"], "%sms" % (x["p50"] or "—")] for x in (reach.get("low") or [])[:5]]) \
        + _tbl(["探针", "#站×模型组", "#一致", "#不一致", "#能力抽样组", "#低于中位"], [["本期", pb.get("pairs", "—"), pb.get("consistent", "—"), pb.get("divergent", "—"), pb.get("cap_pairs", "—"), pb.get("cap_below", "—")]]) \
        + _tbl(["数据核查 · 待核原因", "#条数"], [[HOLD_ZH.get(k, k), v] for k, v in au["open_by_reason"].items()] + [["本期放行", au.get("cleared_this_month", 0)]])
    med = ST.get("media") or {}
    def mrows(mod): return [[esc(f["name"]), f["sites"], f["cmp"], ("$%s" % fmt(f["ref"])) if f.get("ref") else "—", ("$%s" % fmt(f["eff_med"])) if f.get("eff_med") else "—", ('<span class="r">%d%%</span>' % round(f["ratio"] * 100)) if f.get("ratio") else "—", "%d / %d" % ((f.get("bands") or {}).get("unsustainable", 0) + (f.get("bands") or {}).get("below_bulk", 0), (f.get("bands") or {}).get("premium", 0) + (f.get("bands") or {}).get("far_above", 0))] for f in sorted(med.get(mod, []), key=lambda f: -(f.get("cmp") or 0))]
    T["media"] = _tbl(["视频模型族", "#站数", "#可比报价", "#官方参考 $/秒", "#族中位实付 $/秒", "#中位 ÷ 参考", "#低于折扣线 / 高于公开价"], mrows("video")) + _tbl(["图像模型族", "#站数", "#可比报价", "#官方参考 $/张", "#族中位实付 $/张", "#中位 ÷ 参考", "#低于折扣线 / 高于公开价"], mrows("image"), "参考价取官方最低档（分辩率 / 时长），中转报价按同档折算；无官方公开价的族不出比率。")
    cf = ST.get("cost_floor") or {}
    T["gpu"] = _tbl(["GPU", "#Vast.ai 按需中位 $/h", "#RunPod 安全云 $/h"], [[esc(g["gpu"]), ("%.2f" % g["vast_median"]) if g.get("vast_median") else "—", ("%.2f" % g["runpod_secure"]) if g.get("runpod_secure") else "—"] for g in (Rp.get("gpu") or [])[:8]]) \
        + _tbl(["开源模型", "#官方 $/M", "#中转中位 $/M", "#折价率", "官方价是否低于 H100 单卡成本线（约 $%s/M）" % (fmt(cf["h100_per_m"]) if cf.get("h100_per_m") else "—")], [[esc(r["name"]), fmt(r["official"]), fmt(r["median"]), "%d%%" % round(r["ratio"] * 100), "是" if r.get("below_h100_floor") else "否"] for r in sorted(cf.get("open_models") or [], key=lambda r: r["official"])], "成本线按口径文档第 13 节假设（H100 $%s/h、3000 token/秒）粗算，只说明数量级。" % (fmt(cf["h100_hour"]) if cf.get("h100_hour") else "—"))
    note = ('<div class="callout" style="margin-top:14px">创刊号说明：本站数据从 2026-09-02 起记录，本期区间为 %s 至 %s。总表在 9 月 5 日与 9 月 8 日两次批量扩容（名录抓取、Sub2API 面板识别），期内站数曲线的跳变与折价率快照的变化均来自此；点位按共有模型链式计算，不受扩容影响。</div>' % (p0, p1)) if first_issue else ""
    summary = A.get("summary") or {}
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">司南实验室 · 月报 · {{period}}{{final}}</div><h1 style="font-size:26px;margin-top:6px">{{title}}</h1><p class="lead">每月一期。数字来自 {{n}} 个已确认中转站的每日自动测量；判断与分析由司南实验室撰写，只基于这些测量，不含对任何渠道的推荐。</p>{{pledge}}{{note}}</div>
<div class="kpis rise" style="--i:1">{{kpis}}</div>
<section class="card pad rise" style="--i:1.5;margin-top:18px"><h2 class="sec">{{stitle}}</h2>{{summary}}</section>
{{s_scale}}{{s_prices}}{{s_reach}}{{s_media}}{{s_gpu}}{{s_impl}}{{s_watch}}
<section class="card pad rise" style="--i:9;margin-top:18px"><h2 class="sec">{{mtitle}}</h2>{{method}}<p class="lead" style="margin-top:10px">全部指标定义见 <a href="/method" style="color:var(--p-ink)">口径与定义</a>；原始数据：<a href="/report/{{m}}.json" style="color:var(--p-ink)">{{m}}.json</a>、<a href="/price-index.json" style="color:var(--p-ink)">price-index.json</a>、<a href="/data_v2.json" style="color:var(--p-ink)">data_v2.json</a>。月中每天重算数字，月底定稿并标"定稿"；分析文字随定稿一并更新。</p></section>
{{cite}}<script id="d" type="application/json">{{data}}</script>""",
        period="%s 至 %s" % (p0, p1), final="（定稿）" if Rp.get("final") else "（滚动更新）", title=title, n=sc["confirmed_now"], pledge=PLEDGE, note=note, kpis=kpis,
        stitle=summary.get("title") or "本期判断", summary=summary.get("html") or '<p class="lead">本期分析撰写中。</p>',
        s_scale=sec("scale", 1, "一、规模与结构", T["scale"]), s_prices=sec("prices", 2, "二、价格", T["prices"]), s_reach=sec("reach", 3, "三、可达与检测", T["reach"]), s_media=sec("media", 4, "四、图像与视频", T["media"]), s_gpu=sec("gpu", 5, "五、算力成本层", T["gpu"]),
        s_impl=sec("implications", 6, "六、含义", "") if A.get("implications") else "", s_watch=sec("watch", 7, "七、下期观察点", "") if A.get("watch") else "",
        mtitle=(A.get("method") or {}).get("title") or "口径与修正", method=(A.get("method") or {}).get("html", ""), m=m,
        cite=cite_block(title, "/report/%s" % m, Rp["generated_at"][:10]), data=jsdata(LIGHT_INDEX()))
    return shell(title + " · Sinan Compute", "%s：%d 个中转站的实付价、Token 价格指数、可达与一致性检测、多模态与算力成本，附司南实验室的分析与判断。" % (MONTH_ZH(m), sc["confirmed_now"]), "/report/%s" % m, body, active="report", page="report", crumbs=[("月报", "/report"), (MONTH_ZH(m),)])

def LIGHT_INDEX():
    return {"site_index": [{"d": s_["domain"], "n": s_["name"]} for s_ in D["sites"]], "model_index": [{"id": m_["id"], "name": m_["name"]} for m_ in D["models"]]}

def build_report_index(reports):
    items = "".join('<a class="card pad" href="/report/%s" style="display:block"><div class="eyebrow" style="color:var(--p)">%s%s</div><h2 class="sec" style="margin-top:4px">%s</h2><p class="sub">%d 个中转站 · 新收录 %d · 主流变价 %d 次 · 全市场折价率 %s</p></a>' % (
        r["month"], MONTH_ZH(r["month"]), "" if r.get("final") else " · 滚动更新", "中国模型 API 中转市场月报" + ("（创刊号）" if i == len(reports) - 1 else ""), r["scale"]["confirmed_now"], r["scale"]["new_sites"], r["prices"]["mainstream_changes"], _idx_pc(r["prices"]["index"].get("last"), "all")) for i, r in enumerate(reports))
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">司南实验室 · 月报</div><h1 style="font-size:26px;margin-top:6px">中国模型 API 中转市场月报</h1><p class="lead">每月一期，全部来自每日自动测量，月中滚动更新、月底定稿。价格指数、市场结构、可达与检测、多模态、算力成本五个部分，附原始数据下载与引用格式。</p>{{pledge}}</div><div style="display:grid;gap:14px">{{items}}</div>{{cite}}<script id="d" type="application/json">{{data}}</script>""",
        pledge=PLEDGE, items=items, cite=cite_block("中国模型 API 中转市场月报", "/report", GEN_DATE), data=jsdata(LIGHT_INDEX()))
    return shell("中国模型 API 中转市场月报 · Sinan Compute", "司南实验室每月发布的中转市场测量报告：Token 价格指数、市场结构、可达与检测、多模态、算力成本。", "/report", body, active="report", page="report", crumbs=[("月报",)])

def build_press():
    wk0 = (load_rank_weeks() or ["2026-w38"])[0]
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">媒体与研究者</div><h1 style="font-size:26px;margin-top:6px">可引用的数据、口径与联系方式</h1><p class="lead">司南实验室是 AI 基础设施的独立第三方测量者。这一页给记者、分析师、研究机构和金融机构：哪些数据可以直接引用、怎么引用、我们能提供什么、不做什么。</p>{{pledge}}</div>
<section class="card pad rise" style="--i:1"><h2 class="sec">可直接引用的公开数据（每日更新）</h2><div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>数据</th><th>说明</th><th>页面 / 文件</th></tr></thead><tbody>
<tr><td><b>司南 Token 价格指数</b></td><td>中国中转市场每百万 Token 的市场中位实付、相对官方价的折价率、链式点位；分旗舰 / 中档 / 快速三档</td><td><a href="/price-index">/price-index</a> · <a href="/price-index.json">JSON</a> · <a href="/badge/price-index.svg">徽章</a></td></tr>
<tr><td><b>司南榜</b></td><td>每周一期 12 张测量榜，永久链接 /rank/期号</td><td><a href="/rank">/rank</a> · <a href="/rank/{{wk}}.json">JSON</a></td></tr>
<tr><td><b>月报</b></td><td>市场规模、结构、价格、可达、检测、多模态、算力成本</td><td><a href="/report">/report</a></td></tr>
<tr><td><b>模型账本</b></td><td>每个主流模型在每个中转站的实付价与比率，带抓取快照</td><td><a href="/">/</a> · <a href="/data_v2.json">data_v2.json</a></td></tr>
<tr><td><b>图像 · 视频账本</b></td><td>按秒 / 按张实付价与官方参考</td><td><a href="/media">/media</a> · <a href="/media.json">media.json</a></td></tr>
<tr><td><b>算力租赁账本</b></td><td>主流 GPU 在公开平台的单卡时价</td><td><a href="/gpu">/gpu</a> · <a href="/gpu.json">gpu.json</a></td></tr></tbody></table></div></section>
<section class="card pad rise" style="--i:2;margin-top:18px"><h2 class="sec">引用格式</h2><p class="lead" style="margin-top:4px">中文：司南实验室，《页面标题》，日期，链接。英文：Sinan Lab, "Title", date, URL. 每个数据页底部都有可复制的引用文本。转载图表请保留"数据：司南实验室 compute.sinanlab.com"。</p></section>
<section class="card pad rise" style="--i:3;margin-top:18px"><h2 class="sec">我们能提供的</h2><ul class="lead" style="margin-top:4px;padding-left:18px"><li>按你的口径重算：指定模型集合、时间窗或站点集合的价格与可达统计</li><li>历史序列：全部报价的有效区间可逐日重建（公开文件只留 7 天，登录后可取全量）</li><li>方法核对：每个数字的抓取快照编号可提供原文</li><li>Token 采购、词元贷等场景的市场价参考：以 Token 价格指数为基准的定制说明</li></ul>
<p class="lead" style="margin-top:10px"><b>我们不做的：</b>不接受任何被测渠道的付费收录、付费核验或付费排位；不提供"推荐哪家"的结论；不出售用户数据。</p></section>
<section class="card pad rise" style="--i:4;margin-top:18px"><h2 class="sec">联系方式与素材</h2><p class="lead" style="margin-top:4px">邮箱 <a href="mailto:hello@sinanlab.com" style="color:var(--p-ink)">hello@sinanlab.com</a>（媒体与研究请求 48 小时内回复）。标志文件：<a href="/brand/sinanlab-lockup.png">横标 PNG</a>；使用规范见母站 <a href="https://sinanlab.com/about">关于</a>。</p></section>
<script id="d" type="application/json">{{data}}</script>""", wk=wk0, pledge=PLEDGE, data=jsdata(LIGHT_INDEX()))
    return shell("媒体与研究者 · Sinan Compute", "司南实验室的可引用数据、口径、引用格式与联系方式。", "/press", body, active="press", page="press", crumbs=[("媒体与研究者",)])

def build_verify():
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">经司南核验 · 免费 · 面向站长</div><h1 style="font-size:26px;margin-top:6px">让你的站带上"经司南核验"标识</h1><p class="lead">你给我们一把小额度的 Key，我们每天用它跑一致性探针与能力抽样。连续 7 天满足条件，站点页出现"经司南核验"标识，并给你一枚可嵌入的徽章。全程免费，不收任何费用，也不接受付费加速。</p>{{pledge}}</div>
<div class="grid2" style="margin-top:0"><section class="card pad rise" style="--i:1"><h2 class="sec">核验条件（公开、可复核）</h2><ul class="lead" style="margin-top:6px;padding-left:18px"><li>一致性探针：至少 5 个模型有结果，全部与同模型其他渠道的共识计数一致，7 天内没有"不一致"</li><li>能力抽样：30 道机器判分小题，答对数不低于同模型多渠道中位数减 2</li><li>可达：7 天可达率 ≥ 99%</li><li>新用户注册开放（关闭注册的站不发标识）</li></ul><p class="sub" style="margin-top:10px">任何一天不满足，标识自动摘除，满足后自动恢复。标识只陈述"这几项测量在这段时间通过"，不是对该站的推荐或担保。</p></section>
<section class="card pad rise" style="--i:2"><h2 class="sec">申请</h2><div id="vf-gate" class="callout">正在读取登录状态…</div>
<div id="vf-form" style="display:none"><label style="display:block;margin-top:8px"><span class="sub">站点域名</span><input id="vf-dom" placeholder="例如 toapis.cn" class="vf-in"></label>
<label style="display:block;margin-top:10px"><span class="sub">联系方式（邮箱或 Telegram，用来对接 Key）</span><input id="vf-contact" placeholder="you@example.com" class="vf-in"></label>
<label style="display:block;margin-top:10px"><span class="sub">订阅套餐与价格（可选，Sub2API 类站请填；会以"站方自报"公开显示）</span><input id="vf-plan" placeholder="例如：Pro 月卡 68 元/月，日限 $20；Max 月卡 168 元/月" class="vf-in"></label>
<label style="display:block;margin-top:10px"><span class="sub">备注（可选）</span><input id="vf-note" placeholder="例如：Key 已发邮件" class="vf-in"></label>
<div style="display:flex;gap:10px;align-items:center;margin-top:12px"><button class="btn p" id="vf-go">提交申请</button><span class="sub" id="vf-msg"></span></div>
<p class="sub" style="margin-top:12px"><b>Key 怎么给</b>：提交后把一把余额 20 元左右、只开放你要核验的模型的 Key 发到 <a href="mailto:hello@sinanlab.com" style="color:var(--p-ink)">hello@sinanlab.com</a>，邮件标题写域名。我们不在网页上收 Key。每天探测花费不到 1 元，余额用完标识会自动摘除，请及时续费。</p>
<div id="vf-mine" class="sub" style="margin-top:8px"></div></div></section></div>
<style>.vf-in{width:100%;margin-top:6px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit;font-size:14px;background:var(--card);color:var(--ink)}</style>
<script>(function(){var g=document.getElementById("vf-gate"),f=document.getElementById("vf-form"),M=document.getElementById("vf-msg");var ST={pending:"已收到，等待 Key",keyed:"Key 已接入，探测中",verified:"核验通过",failed:"未通过（见邮件）"};function esc2(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
function mine(){fetch("/api/verify",{credentials:"include"}).then(function(r){return r.json();}).then(function(j){var it=j.items||[];if(!it.length)return;document.getElementById("vf-mine").innerHTML="我的申请："+it.map(function(x){return esc2(x.domain)+"（"+(ST[x.status]||x.status)+"）";}).join(" · ");});}
fetch("/api/me",{credentials:"include"}).then(function(r){return r.json();}).then(function(m){if(m&&m.user){g.style.display="none";f.style.display="";mine();}else{g.innerHTML='申请需要登录。<a href="/login?return_to=/verify" style="color:var(--p-ink)">登录 →</a>';}}).catch(function(){g.textContent="暂时无法读取登录状态。";});
document.getElementById("vf-go").addEventListener("click",function(){var d=document.getElementById("vf-dom").value.trim(),c=document.getElementById("vf-contact").value.trim(),n=document.getElementById("vf-note").value.trim();var pl=document.getElementById("vf-plan").value.trim();if(pl)n=("套餐自报："+pl+(n?" ｜ "+n:"")).slice(0,300);if(!d||!c){M.textContent="域名和联系方式都要填。";return;}M.textContent="提交中…";
fetch("/api/verify",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({domain:d,contact:c,note:n})}).then(function(r){return r.json();}).then(function(j){if(j.ok){M.textContent="已收到：把 Key 发到 hello@sinanlab.com，标题写 "+j.domain+"。";mine();}else{M.textContent={bad_domain:"域名格式不对",not_listed:"这个站还没在总表里，先到总表页提交收录",too_many_requests:"提交太频繁",login_required:"请先登录"}[j.error]||"出错了";}}).catch(function(){M.textContent="网络错误，请重试。";});});})();</script>
<script id="d" type="application/json">{{data}}</script>""", pledge=PLEDGE, data=jsdata(LIGHT_INDEX()))
    return shell("申请核验 · 经司南核验标识 · Sinan Compute", "站长免费申请：交一把小额 Key，连续 7 天一致性探针与能力抽样通过，站点页出现经司南核验标识并获得可嵌入徽章。", "/verify", body, active="verify", page="verify", crumbs=[("申请核验",)])

def verified_badge_svg(s):
    font = "Inter,-apple-system,Segoe UI,PingFang SC,Source Han Sans SC,Noto Sans SC,sans-serif"
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="72" viewBox="0 0 360 72" role="img" aria-label="经司南核验 %s">'
            '<rect width="360" height="72" rx="14" fill="#07070B"/><rect x=".5" y=".5" width="359" height="71" rx="13.5" fill="none" stroke="#F5F5F7" stroke-opacity=".14"/>'
            '<g transform="translate(14 14) scale(.6875)">%s</g><line x1="68" y1="18" x2="68" y2="54" stroke="#B8A4FA" stroke-width="1"/>'
            '<text x="80" y="29" font-family="%s" font-size="11" fill="#B8A4FA">经司南核验 · 一致性探针 · 能力抽样 · 可达</text>'
            '<text x="80" y="51" font-family="%s" font-size="15" font-weight="600" fill="#F5F5F7">%s</text>'
            '<text x="346" y="29" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="10" fill="#B8A4FA">%s</text>'
            '<text x="346" y="51" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="12" fill="#F5F5F7">7 天通过</text></svg>'
            % (esc(s["domain"]), MARK_SVG, font, font, esc(s["domain"]), GEN_DATE))

# ------------------------------------------------------------------ 算力租赁账本
GPU = json.load(io.open(os.path.join(HERE, "gpu.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "gpu.json")) else None

def build_gpu():
    if not GPU or not GPU.get("gpus"): return None
    PF = GPU["platforms"]; cols = [("runpod", "secure"), ("runpod", "community"), ("vast", "min"), ("vast", "median"), ("autodl", "min"), ("autodl", "median"), ("suanli", "starting")]
    head = "".join('<th class="num">%s<div class="sub" style="font-weight:400">%s</div></th>' % (esc(PF[pf]["name"]), esc(PF[pf]["kinds"][k])) for pf, k in cols)
    rows = []
    for g in GPU["gpus"]:
        q = {(x["platform"], x["kind"]): x for x in g["quotes"]}
        cells = ""
        for pf, k in cols:
            x = q.get((pf, k))
            if not x: cells += '<td class="num sub">—</td>'; continue
            trend = ""
            if len(x["series"]) >= 2:
                a, b = x["series"][0][1], x["series"][-1][1]
                if a: trend = '<div class="sub">%s %+.0f%%</div>' % ("%d 天" % len(x["series"]), (b / a - 1) * 100)
            cells += '<td class="num"><b>$%s</b><div class="sub">¥%s%s</div>%s</td>' % (fmt(x["usd"]), fmt(x["cny"]), (" · %d 台" % x["n"]) if x["n"] > 1 else "", trend)
        rows.append('<tr><td><b>%s</b><div class="sub">%d GB 显存</div></td>%s</tr>' % (esc(g["gpu"]), g["vram_gb"], cells))
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">算力租赁账本 · 每日 · {{date}}</div><h1 style="font-size:26px;margin-top:6px">一张显卡租一小时多少钱</h1><p class="lead">Token 的生产成本里，芯片占四到五成。这里每天记录主流 GPU 在公开租赁平台上的单卡时价：RunPod 的安全云与社区云标价、Vast.ai 按需市场的最低价与中位价（只取可靠度 ≥95% 的机器）、共绩算力官网的起步价。每个数字带抓取时间与原文快照。国内平台大多需要登录才能看到价格，接入中。</p></div>
<section class="card rise" style="--i:1"><div class="tablewrap"><table><thead><tr><th>GPU</th>{{head}}</tr></thead><tbody>{{rows}}</tbody></table></div>
<div class="tfoot"><span>单位：每卡每小时，美元为原始报价，人民币按当日汇率 {{fx}} 折算 · Vast.ai 为个人机主市场，价格随供需实时变动，中位价比最低价更能代表可得价 · 数据：<a href="/gpu.json" style="color:var(--p-ink)">gpu.json</a></span></div></section>
<section class="card pad rise" style="--i:2;margin-top:18px"><h2 class="sec">这张账本用来做什么</h2><p class="lead" style="margin-top:4px">和 <a href="/price-index" style="color:var(--p-ink)">Token 价格指数</a> 放在一起看：一边是 Token 卖多少钱，一边是造 Token 的机器租多少钱。我们对中转报价的"低于成本下限"判定，参考的成本地板就来自公开渠道价与这类租赁价，今后会把换算假设逐条写在口径与定义里。这里只记录，不做推测。</p></section>
<script id="d" type="application/json">{{data}}</script>""",
        date=GPU["generated_at"][:10], head=head, rows="".join(rows), fx="%.2f" % GPU["fx"],
        data=jsdata({"site_index": [{"d": s_["domain"], "n": s_["name"]} for s_ in D["sites"]], "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}))
    return shell("算力租赁账本 · 一张显卡租一小时多少钱 · Sinan Compute", "主流 GPU（4090 / 5090 / A100 / H100 / H200 / B200）在 RunPod、Vast.ai、共绩算力等公开租赁平台的单卡时价，每日记录，带快照。", "/gpu", body, active="gpu", page="gpu", crumbs=[("算力租赁",)])

def build_check():
    body = tpl(u"""<div class="rise" style="--i:0;margin-bottom:14px"><div class="eyebrow" style="color:var(--p)">自测 · 众测 · 不需登录</div><h1 style="font-size:26px;margin-top:6px">测试模型真伪</h1><p class="lead">填一个中转站地址和你在该站的 Key，浏览器直接向该站发 8 条固定探针请求（每条只要 4 个输出 token，一次自测通常不到一分钱），把返回的 token 计数、回显模型名、首字节延迟，和我们从多个渠道得到的参考计数逐位比对。<b>Key 只在你的浏览器里，不上传、不落库、不经过我们的服务器。</b></p><p class="callout">当前提供一致性检测，不能单凭测试结果判定模型真伪。</p></div>
<div id="gate" class="card pad rise" style="--i:1"><div class="callout">正在读取登录状态…</div></div>
<section class="card pad rise" id="form" style="--i:1;display:none">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><label style="display:block"><span class="sub">中转站地址（域名或 https://…）</span><input id="ck-base" list="qlist" placeholder="例如 toapis.cn" style="width:100%;margin-top:6px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit"></label>
<label style="display:block"><span class="sub">你在该站的 API Key（只在本页内存里用，刷新即忘）</span><input id="ck-key" type="password" autocomplete="off" placeholder="sk-…" style="width:100%;margin-top:6px;padding:10px 12px;border:1px solid var(--hair-2);border-radius:10px;font:inherit"></label></div>
<div style="margin-top:14px"><span class="sub">要测的模型（默认用归一后的模型 id 作为请求里的 model；站方原名不同时可改）</span><div id="ck-models" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px"></div></div>
<div style="display:flex;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap"><button class="btn p" id="ck-run">开始测试</button><label class="sub" style="display:inline-flex;gap:6px;align-items:center;cursor:pointer"><input type="checkbox" id="ck-consent" checked> 测完把结果（不含 Key、匿名）回流到司南众测池</label><span class="sub" id="ck-status"></span></div>
<div class="sub" id="ck-crowd" style="margin-top:10px"></div>
<datalist id="qlist"></datalist>
</section>
<section class="card rise" id="ck-out" style="--i:2;margin-top:16px;display:none"><div class="pad" style="padding-bottom:6px"><h2 class="sec">结果</h2><p class="lead" id="ck-lead"></p></div><div class="tablewrap"><table><thead><tr><th>模型</th><th>回显模型名</th><th class="num">成功</th><th class="num">首字节 p50</th><th>计数比对</th><th>判定</th></tr></thead><tbody id="ck-rows"></tbody></table></div><div class="pad" style="padding-top:8px"><button class="btn o" id="ck-report">手动回流这次结果</button> <span class="sub" id="ck-rep-status"></span><p class="disc" style="margin-top:10px">判定只有四种：一致 / 含固定前缀 / 不一致 / 无参考。标"弱参考"的模型，参考计数只来自 2 个渠道的一致结果，可信度低于 3 个以上渠道。"不一致"表示该渠道对同一输入返回的 token 计数与多渠道共识不同，成因很多（上游分流、系统提示注入、量化、缓存），本站不推测。这是一致性测量，不是真伪判定。</p></div></section>
{{poll}}<script id="d" type="application/json">{{data}}</script>
<script>(function(){
var D0=JSON.parse(document.getElementById("d").textContent);var gate=document.getElementById("gate"),form=document.getElementById("form");
var dl=document.getElementById("qlist");D0.site_index.forEach(function(x){var o=document.createElement("option");o.value=x.d;dl.appendChild(o);});
fetch("/api/me",{credentials:"include"}).then(function(r){return r.json();}).catch(function(){return {};}).then(function(me){
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
  st.textContent="完成。";if(document.getElementById("ck-consent").checked)report(true);});
 function report(auto){var s=document.getElementById("ck-rep-status");if(!window.__CK||!window.__CK.length){s.textContent="先测一次。";return;}s.textContent="回流中…";Promise.all(window.__CK.map(function(x){x.source="web";return fetch("/api/check/report",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify(x)});})).then(function(){s.textContent=(auto?"已自动回流 ":"已回流 ")+window.__CK.length+" 条（匿名，不含 Key），谢谢。明早起在该站点页的"众测"里可见。";}).catch(function(){s.textContent="回流失败，稍后再试。";});}
 document.getElementById("ck-report").addEventListener("click",function(){report(false);});
 document.getElementById("ck-base").addEventListener("change",function(){var b=this.value.trim().replace(/^https?:\/\//,"").replace(/\/.*$/,"");var c=(D0.crowd||{})[b];document.getElementById("ck-crowd").innerHTML=c?("这个站已有众测 "+c.n+" 次（来自 "+c.srcs+" 个来源）：一致 "+c.consistent+" · 含前缀 "+c.prefix+" · 不一致 "+c.divergent+" · 失败 "+c.failed+"。<a href=\"/s/"+b+"\">站点页 →</a>"):(b?"这个站还没有众测结果，你会是第一个。":"");});
});})();</script>""", poll=POLL_BOX, data=jsdata({"site_index": [{"d": s["domain"], "n": s["name"]} for s in D["sites"]], "models": [{"id": m["id"], "name": m["name"]} for m in D["models"] if m["is_latest"]], "crowd": D.get("crowd_sites") or {}}))
    return shell("测试模型真伪 · 众测 · Sinan Compute", "用你自己的 Key 在浏览器里测一个中转站：8 条固定探针，比对 token 计数、回显模型名与延迟。Key 不上传；结果匿名回流到众测池。", "/check", body, active="check", page="check", crumbs=[("测试模型真伪",)])

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

MARK_SVG = ('<path d="M26.5 9.4A23 23 0 0 0 26.5 54.6M37.5 9.4A23 23 0 0 1 37.5 54.6" fill="none" stroke="#F5F5F7" stroke-width="2" stroke-linecap="round"/>'
            '<path d="M32 10L35.2 32H28.8Z" fill="#B8A4FA"/><path d="M32 54L28.8 32H35.2Z" fill="#F5F5F7"/><circle cx="32" cy="32" r="1.6" fill="#07070B"/>')
FAVICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#07070B"/>%s</svg>' % MARK_SVG

def rank_badge_svg(s):
    """期号徽章（VI：墨黑 #07070B 底、冷白 #F5F5F7 字、淡紫 #B8A4FA 小面积点缀、简化罗盘）。只显示期号、榜名、名次、测量值。"""
    b = s["rank_badge"]; label = "%s #%02d" % (b["board_name"], b["pos"])
    font = "Inter,-apple-system,Segoe UI,PingFang SC,Source Han Sans SC,Noto Sans SC,sans-serif"
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="72" viewBox="0 0 360 72" role="img" aria-label="司南榜 %s %s %s">'
            '<rect width="360" height="72" rx="14" fill="#07070B"/><rect x=".5" y=".5" width="359" height="71" rx="13.5" fill="none" stroke="#F5F5F7" stroke-opacity=".14"/>'
            '<g transform="translate(14 14) scale(.6875)">%s</g><line x1="68" y1="18" x2="68" y2="54" stroke="#B8A4FA" stroke-width="1"/>'
            '<text x="80" y="29" font-family="%s" font-size="11" fill="#B8A4FA" letter-spacing=".3">司南榜 · %s</text>'
            '<text x="80" y="51" font-family="%s" font-size="16" font-weight="600" fill="#F5F5F7">%s</text>'
            '<text x="346" y="29" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="10" fill="#B8A4FA">%s</text>'
            '<text x="346" y="51" text-anchor="end" font-family="ui-monospace,Menlo,monospace" font-size="13" fill="#F5F5F7">%s</text></svg>'
            % (esc(b["week"]), esc(label), esc(s["domain"]), MARK_SVG, font, esc(b["week"]), font, esc(label), esc(s["domain"]), esc(b["value"])))

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
    W("check.html", build_check()); W("login.html", build_login())
    if PI and PI.get("latest"):
        W("price-index.html", build_price_index()); shutil.copy(os.path.join(HERE, "price_index.json"), os.path.join(DIST, "price-index.json"))
        os.makedirs(os.path.join(DIST, "badge"), exist_ok=True); W("badge/price-index.svg", price_index_badge())
    if GPU and GPU.get("gpus"):
        W("gpu.html", build_gpu()); shutil.copy(os.path.join(HERE, "gpu.json"), os.path.join(DIST, "gpu.json"))
    REPS = load_reports()
    if REPS:
        os.makedirs(os.path.join(DIST, "report"), exist_ok=True); W("report.html", build_report_index(REPS))
        for i, r_ in enumerate(REPS):
            W("report/%s.html" % r_["month"], build_report(r_, first_issue=(i == len(REPS) - 1))); shutil.copy(os.path.join(HERE, "reports", r_["month"] + ".json"), os.path.join(DIST, "report", r_["month"] + ".json"))
            if os.path.exists(os.path.join(HERE, "reports", r_["month"] + ".analysis.en.md")):
                os.makedirs(os.path.join(DIST, "_en_src", "report"), exist_ok=True); W("_en_src/report/%s.html" % r_["month"], build_report(r_, first_issue=(i == len(REPS) - 1), lang="en"))
    W("survival.html", build_survival()); W("governance.html", build_governance())
    W("stats.json", json.dumps({"generated_at": D["generated_at"], "stats": D["stats"], "rank_week": (D.get("rank") or {}).get("week"), "rank_date": (D.get("rank") or {}).get("date"), "changes_today": len([c for c in D.get("changes", []) if c["t"][:10] == GEN_DATE]), "new_sites_today": len(D.get("new_sites") or []), "dead": (D.get("rank") or {}).get("dead"), "verified": (D.get("rank") or {}).get("verified"), "audit_open": (D.get("rank") or {}).get("audit_open"), "survival": {k: (D.get("survival") or {}).get(k) for k in ("churn", "age_coverage")}, "crowd_sites": len(D.get("crowd_sites") or {}), "price_index": (PI or {}).get("latest"), "reports": [r_["month"] for r_ in load_reports()], "media": (MEDIA or {}).get("stats"), "gpu_n": len((GPU or {}).get("gpus") or [])}, ensure_ascii=False))
    W("press.html", build_press()); W("verify.html", build_verify()); W("api-docs.html", build_api_docs()); W("corrections.html", build_corrections()); W("changes.json", build_changes_json())
    os.makedirs(os.path.join(DIST, "badge", "verified"), exist_ok=True)
    for s_ in D["sites"]:
        if s_.get("verified"): W("badge/verified/%s.svg" % s_["domain"], verified_badge_svg(s_))
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
    ab_n = 0
    for s_ in D["sites"]:
        ab_ = s_.get("about")
        if not ab_: continue
        src_ = os.path.join(ROOT, "data", "raw", "about.%s" % s_["domain"], ab_["sha256"])
        if not os.path.exists(src_): continue
        os.makedirs(os.path.join(DIST, "snap", "about"), exist_ok=True)
        head = "# 站方说明页快照（站方自述，司南实验室未核实内容）\n# 来源 %s\n# 抓取 %s · 正文 sha256 %s\n\n" % (ab_["url"], ab_["fetched"], ab_["sha256"])
        W("snap/about/%s.txt" % s_["domain"], head + io.open(src_, encoding="utf-8").read())
        ab_n += 1
    for f in ("data_v2.json", "media.json", "go_links.json"):
        if os.path.exists(os.path.join(HERE, f)): shutil.copy(os.path.join(HERE, f), os.path.join(DIST, f))
    if os.path.exists(os.path.join(HERE, "static")):   # 站长平台验证文件等原样放根目录
        for f in os.listdir(os.path.join(HERE, "static")):
            src_ = os.path.join(HERE, "static", f); dst_ = os.path.join(DIST, f)
            if os.path.isdir(src_): shutil.copytree(src_, dst_, dirs_exist_ok=True)
            else: shutil.copy(src_, dst_)
    W("assets/ledger.json", jsdata({"models": D["models"], "snaps": D["snaps"]}))
    W("robots.txt", "User-agent: *\nAllow: /\nDisallow: /snap/\nSitemap: %s/sitemap.xml\n" % BASE)
    urls = [("/", "daily"), ("/sites", "daily"), ("/media", "daily"), ("/method", "weekly"), ("/weekly", "weekly"), ("/rank", "weekly"), ("/price-index", "daily"), ("/gpu", "daily"), ("/report", "weekly"), ("/press", "monthly"), ("/verify", "monthly"), ("/api-docs", "weekly"), ("/corrections", "weekly"), ("/survival", "daily"), ("/governance", "monthly")] + [("/report/%s" % r_["month"], "weekly") for r_ in load_reports()] + [("/rank/%s" % w_, "weekly") for w_ in load_rank_weeks()] + [("/m/%s" % m["id"], "daily") for m in D["models"]] + ([("/media/%s" % f["family"], "daily") for mod in ("video", "image") for f in MEDIA.get(mod, []) if f.get("n_rows")] if MEDIA else []) + [("/weekly/%s" % w["week"], "weekly") for w in load_weeks()] + [("/s/%s" % s["domain"], "daily") for s in D["sites"]]
    W("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join('  <url><loc>%s%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq></url>\n' % (BASE, u, GEN_DATE, c) for u, c in urls) + "</urlset>\n")
    W("favicon.svg", FAVICON)
    W("_headers", "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/assets/*\n  Cache-Control: public, max-age=604800\n/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n/img/*\n  Cache-Control: public, max-age=2592000\n/badge/*\n  Cache-Control: public, max-age=900, must-revalidate\n/snap/*\n  X-Robots-Tag: noindex\n  Content-Type: text/plain; charset=utf-8\n")
    print("dist/ 生成完成：index · sites · media · method · 404 · 站点页 %d · 站方说明页快照 %d · 大小 index %d KB" % (n, ab_n, os.path.getsize(os.path.join(DIST, "index.html")) // 1024))

if __name__ == "__main__":
    main()
