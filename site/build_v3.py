# -*- coding: utf-8 -*-
"""站点生成器 v2：index.html + s/<domain>.html。数据全来自 data_v2.json。

首页迭代（按体验报告）：
  · 模型芯片按厂商分组，最新一代高亮
  · 表按可信度分组排：可由折扣解释 → 贴官方 → 溢价 → 低于折扣 → 「不可持续」折叠
  · 判读标签带人话解释（点开抽屉）；价格下方直接显示抓取时间；证据按钮放大带字
  · 用量计算器：输入月用量，每行多一列「你的月成本」
  · 站点区改成可筛选表（按簇），默认只显示有报价的；卡片去黑话；点站名进详情页
  · 搜索框：站名 → 详情页；模型名 → 切芯片
  · 动态：今日新收录、真实价格变动
每站详情页：事实清单（面板/登录/通道价/可用性）、它卖的全部模型与比率、前往按钮（经 /go/）。
"""
from __future__ import unicode_literals
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data_v2.json")))
# 复用旧模板的 CSS
_old = io.open(os.path.join(HERE, "build_home.py"), encoding="utf-8").read()
CSS = """
:root{--ground:#0B0F14;--surface:#10161E;--surface2:#0E141B;--hair:#1F2A36;--hair2:#2A3644;--ink:#E8EEF3;--ink2:#A3B1BE;--ink3:#64768A;--accent:#4FD1D9;--accent-ink:#06181B;--good:#4CC38A;--warn:#E0AE4A;--crit:#E4614C}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:"IBM Plex Sans","PingFang SC","Noto Sans SC",system-ui,sans-serif;font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none} a:hover{color:#8AE3E8}
h1,h2,h3,h4{margin:0;font-weight:400}
.serif{font-family:"Instrument Serif","Noto Serif SC","Songti SC",Georgia,serif;font-weight:400}
.mono{font-family:"JetBrains Mono","IBM Plex Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.top{border-bottom:1px solid var(--hair);background:linear-gradient(180deg,rgba(79,209,217,0.04),transparent)}
.wrap{max-width:1328px;margin:0 auto;padding:0 56px}
.bar{display:flex;align-items:center;gap:28px;padding:22px 0}
.brand{display:flex;align-items:center;gap:12px}
.brand h1{font-family:"Instrument Serif","Noto Serif SC",serif;font-size:22px;line-height:1;letter-spacing:.01em}
.brand .sub{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.22em;color:var(--ink3);margin-top:3px;text-transform:uppercase}
.nav{display:flex;gap:26px;font-size:13.5px;color:var(--ink2);margin-left:24px}
.nav a{color:var(--ink2)} .nav a.on{color:var(--ink);border-bottom:1px solid var(--accent);padding-bottom:2px}
.search{margin-left:auto;display:flex;align-items:center;gap:10px;background:var(--surface);border:1px solid var(--hair);border-radius:10px;padding:0 6px 0 14px;width:380px;height:40px}
.search input{flex:1;border:0;background:transparent;font:inherit;font-size:13.5px;color:var(--ink);outline:none}
.search input::placeholder{color:var(--ink3)}
.search button{border:0;background:var(--accent);color:var(--accent-ink);font:inherit;font-size:13px;font-weight:600;padding:6px 14px;border-radius:7px;cursor:pointer}
.pledge{display:flex;gap:28px;padding:10px 0;font-size:12px;color:var(--ink3);border-top:1px solid #141C25}
.pledge b{color:var(--ink2);font-weight:500}
main{padding:0 0 80px}
.hero{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:48px;padding:44px 0 28px;align-items:end}
.eyebrow{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.22em;color:var(--accent);text-transform:uppercase}
.hero h2{font-family:"Instrument Serif","Noto Serif SC",serif;font-size:50px;line-height:1.06;letter-spacing:-.01em;text-wrap:balance;margin-top:14px}
.hero h2 em{color:var(--accent)}
.hero p{font-size:15px;color:var(--ink2);max-width:620px;margin:14px 0 0}
.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--hair);border:1px solid var(--hair);border-radius:12px;overflow:hidden}
.kpi{background:var(--surface);padding:14px 16px;display:flex;flex-direction:column;gap:2px}
.kpi .k{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.18em;color:var(--ink3);text-transform:uppercase}
.kpi .v{font-family:"JetBrains Mono",monospace;font-size:26px;color:var(--ink)}
.kpi .v small{font-size:13px;color:var(--ink3)}
.sec{margin-top:40px}
.sechead{display:flex;align-items:baseline;gap:14px;margin-bottom:14px;flex-wrap:wrap}
.sechead h2{font-family:"Instrument Serif","Noto Serif SC",serif;font-size:26px}
.sechead .q{font-size:13px;color:var(--ink3)}
.sechead .right{margin-left:auto;font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--ink3)}
.vgroup{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.vgroup .vn{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.18em;color:var(--ink3);width:80px;text-transform:uppercase}
.chip{display:inline-flex;align-items:center;gap:6px;padding:7px 13px;border-radius:999px;border:1px solid var(--hair2);background:transparent;color:var(--ink2);font:inherit;font-size:13px;cursor:pointer}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip .n{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--ink3)}
.chip.latest{border-color:rgba(79,209,217,.45)}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);font-weight:600}
.chip[aria-pressed="true"] .n{color:var(--accent-ink);opacity:.75}
.chip.off{opacity:.55;cursor:default;border-style:dashed}
.legend{display:flex;align-items:center;gap:22px;padding:12px 0;font-size:12px;color:var(--ink3);flex-wrap:wrap}
.legend .sw{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px}
.card{background:var(--surface2);border:1px solid var(--hair);border-radius:14px;overflow:hidden}
.calc{display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:10px 20px;border-bottom:1px solid var(--hair);background:var(--surface);font-size:13px;color:var(--ink2)}
.calc input{width:70px;border:0;border-bottom:1px solid var(--accent);background:transparent;padding:2px 4px;font:inherit;font-family:"JetBrains Mono",monospace;color:var(--ink);text-align:right}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.16em;color:var(--ink3);text-transform:uppercase;font-weight:500;text-align:left;padding:10px 20px;border-bottom:1px solid var(--hair);white-space:nowrap}
td{padding:13px 20px;border-bottom:1px solid #141C25;vertical-align:middle}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:#121A23}
td.num,th.num{text-align:right;font-family:"JetBrains Mono",monospace;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.floor td{background:linear-gradient(90deg,rgba(79,209,217,.10),rgba(79,209,217,.02))}
tr.floor td:first-child{border-left:3px solid var(--accent)}
.kind{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--ink3)}
.bigout{font-family:"JetBrains Mono",monospace;font-size:17px;color:var(--ink)}
.asof{display:block;font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--ink3);margin-top:2px}
.pill{display:inline-flex;align-items:center;gap:6px;font-family:"JetBrains Mono",monospace;font-size:11.5px;padding:3px 9px;border-radius:999px;white-space:nowrap}
.pill .dot{width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block}
.pill.ref{background:rgba(79,209,217,.14);color:var(--accent)}
.pill.explainable,.pill.normal{background:rgba(76,195,138,.14);color:var(--good)}
.pill.normal{background:transparent;border:1px solid var(--hair2);color:var(--ink2)}
.pill.below_bulk{background:rgba(224,174,74,.14);color:var(--warn)}
.pill.unsustainable{background:rgba(228,97,76,.14);color:var(--crit)}
.pill.premium,.pill.far_above,.pill.held{background:transparent;border:1px solid var(--hair2);color:var(--ink3)}
.ratio{font-family:"JetBrains Mono",monospace;font-size:12px}
.ratio.explainable,.ratio.normal{color:var(--good)} .ratio.below_bulk{color:var(--warn)} .ratio.unsustainable{color:var(--crit)} .ratio.premium,.ratio.far_above{color:var(--ink3)}
.gauge{position:relative;width:120px;height:8px;border-radius:4px;display:inline-flex;vertical-align:middle}
.gauge i{display:block;height:100%}
.gauge .z1{width:7.5%;background:var(--crit);opacity:.35;border-radius:4px 0 0 4px}.gauge .z2{width:12.5%;background:var(--warn);opacity:.35}.gauge .z3{width:42.5%;background:var(--good);opacity:.3}.gauge .z4{width:37.5%;background:var(--hair);border-radius:0 4px 4px 0}
.gauge .mid{position:absolute;left:50%;top:-2px;width:1px;height:12px;background:var(--ink3)}
.gauge .needle{position:absolute;top:-5px;width:2px;height:18px;border-radius:1px}
.gauge .needle.explainable,.gauge .needle.normal{background:var(--good);box-shadow:0 0 8px var(--good)}
.gauge .needle.below_bulk{background:var(--warn);box-shadow:0 0 8px var(--warn)}
.gauge .needle.unsustainable{background:var(--crit);box-shadow:0 0 8px var(--crit)}
.gauge .needle.premium,.gauge .needle.far_above{background:var(--ink2)}
.gauge .needle.ref{background:var(--accent);box-shadow:0 0 8px var(--accent);height:18px;top:-5px}
.gcell{display:flex;align-items:center;gap:10px}
.help{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;border:1px solid var(--hair2);color:var(--ink3);font-size:10px;cursor:pointer;margin-left:6px;background:transparent}
.help:hover{border-color:var(--accent);color:var(--accent)}
.evb{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--hair2);border-radius:6px;padding:3px 8px;font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--ink2);background:transparent;cursor:pointer}
.evb:hover{border-color:var(--accent);color:var(--accent)}
details.fold{border-top:1px dashed var(--hair2);background:#0B1016}
details.fold summary{padding:12px 20px;font-size:13px;color:var(--ink2);cursor:pointer;list-style:none;display:flex;gap:12px;align-items:center}
details.fold summary::before{content:"";width:0;height:0;border-left:6px solid var(--ink3);border-top:4px solid transparent;border-bottom:4px solid transparent}
details.fold[open] summary::before{transform:rotate(90deg)}
details.fold summary b{color:var(--crit);font-family:"JetBrains Mono",monospace;font-weight:500}
.foot{display:flex;gap:22px;flex-wrap:wrap;padding:11px 20px;font-size:12px;color:var(--ink3);background:var(--surface2)}
.foot b{color:var(--ink2);font-weight:500}
.grid{display:grid;gap:12px} .g4{grid-template-columns:repeat(4,minmax(0,1fr))} .g2{grid-template-columns:repeat(2,minmax(0,1fr))}
.stat{padding:16px 18px;display:flex;flex-direction:column;gap:6px}
.stat .k{font-size:13px;color:var(--ink)} .stat .v{font-family:"JetBrains Mono",monospace;font-size:30px;color:var(--ink)} .stat .n{font-size:12px;color:var(--ink3)}
.stat.c-ultra{border-top:2px solid var(--crit)} .stat.c-cheap{border-top:2px solid var(--warn)} .stat.c-near{border-top:2px solid var(--good)} .stat.c-high{border-top:2px solid var(--ink3)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 12px;align-items:center}
.fchip{border:1px solid var(--hair2);background:transparent;color:var(--ink2);font:inherit;font-size:12.5px;padding:5px 11px;border-radius:999px;cursor:pointer}
.fchip[aria-pressed="true"]{background:var(--ink);color:var(--ground);border-color:var(--ink)}
.mtab{font-size:13.5px;padding:8px 16px}
.cl{display:inline-flex;align-items:center;gap:5px;font-family:"JetBrains Mono",monospace;font-size:11.5px;padding:2px 9px;border-radius:999px;white-space:nowrap}
.cl.ultra{background:rgba(228,97,76,.14);color:var(--crit)} .cl.cheap{background:rgba(224,174,74,.14);color:var(--warn)} .cl.near{background:rgba(76,195,138,.14);color:var(--good)} .cl.high,.cl.held{border:1px solid var(--hair2);color:var(--ink3)}
.up{font-family:"JetBrains Mono",monospace} .up.good{color:var(--good)} .up.bad{color:var(--crit)}
a.dom{color:var(--ink);font-family:"JetBrains Mono",monospace;font-weight:500} a.dom:hover{color:var(--accent)}
.go{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:var(--accent-ink);border-radius:9px;padding:9px 16px;font-weight:600;font-size:14px}
.go:hover{background:#8AE3E8;color:var(--accent-ink)}
.go.small{padding:5px 11px;font-size:12px;border-radius:7px}
.ghost{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--hair2);color:var(--ink);border-radius:9px;padding:9px 16px;font-size:14px}
.feed .row{display:grid;grid-template-columns:64px minmax(0,1fr);gap:12px;padding:12px 16px;border-bottom:1px solid #141C25}
.feed .row:last-child{border-bottom:0}
.feed .t{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--ink3);padding-top:3px}
.feed .b{font-size:13px} .feed .sub{font-size:11.5px;color:var(--ink3);margin-top:2px;word-break:break-all}
.old{color:var(--ink3);text-decoration:line-through;font-family:"JetBrains Mono",monospace} .new{color:var(--good);font-family:"JetBrains Mono",monospace}
.method{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;font-size:13px;color:var(--ink2)}
.method div{padding:14px 16px} .method b{display:block;color:var(--ink);font-size:13px;margin-bottom:4px;font-weight:500}
.scrim{position:fixed;inset:0;background:rgba(5,8,11,.55);opacity:0;pointer-events:none;transition:opacity .18s;z-index:40}
.scrim.on{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;height:100vh;width:min(480px,94vw);z-index:41;background:var(--surface);border-left:1px solid var(--hair);box-shadow:-30px 0 60px rgba(0,0,0,.55);transform:translateX(100%);transition:transform .22s;overflow-y:auto;padding:22px 26px 40px}
.drawer.on{transform:none}
@media (prefers-reduced-motion:reduce){.drawer,.scrim{transition:none}}
.drawer .close{position:absolute;top:16px;right:18px;width:30px;height:30px;border-radius:8px;border:1px solid var(--hair2);background:transparent;color:var(--ink2);font-size:18px;cursor:pointer}
.drawer .eyebrow{margin-bottom:8px}
.drawer h3{font-family:"Instrument Serif","Noto Serif SC",serif;font-size:22px;line-height:1.15}
.kv{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px 16px;font-size:13.5px;margin-top:16px;align-items:baseline}
.kv dt{color:var(--ink2)} .kv dt small{display:block;font-size:11px;color:var(--ink3)} .kv dd{margin:0;font-family:"JetBrains Mono",monospace;font-size:15px;text-align:right}
.snap{border:1px solid var(--hair);border-radius:10px;padding:12px 14px;margin-top:10px;background:var(--surface2)}
.notice{border:1px solid rgba(224,174,74,.35);background:rgba(224,174,74,.08);color:var(--warn);padding:10px 14px;border-radius:9px;font-size:13px;margin-bottom:14px}
.callout{border:1px solid var(--hair);background:var(--surface);padding:12px 16px;border-radius:12px;font-size:13px;color:var(--ink2);margin:12px 0}
.facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--hair);border:1px solid var(--hair);border-radius:14px;overflow:hidden}
.fact{background:var(--surface);padding:16px 18px;display:flex;flex-direction:column;gap:3px}
.fact .k{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.18em;color:var(--ink3);text-transform:uppercase} .fact .v{font-family:"JetBrains Mono",monospace;font-size:24px} .fact .n{font-size:11.5px;color:var(--ink3)}
.crumb{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--ink3);padding:14px 0 0} .crumb a{color:var(--ink3)}
.sitehead{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:40px;padding:26px 0 24px;align-items:start}
.sitehead h2{font-family:"JetBrains Mono",monospace;font-size:44px;letter-spacing:-.02em;line-height:1}
.sitehead h2 span{font-family:"Instrument Serif","Noto Serif SC",serif;color:var(--ink3);font-size:28px;letter-spacing:0;margin-left:10px}
.sitehead .sub{color:var(--ink2);font-size:15px;max-width:640px;margin-top:12px}
.profile{padding:20px 24px;display:flex;flex-direction:column;gap:12px}
.pruler{position:relative;height:36px}
.pruler .track{position:absolute;left:0;right:0;top:12px;height:10px;border-radius:5px;display:flex;overflow:hidden}
.pruler .track i{display:block;height:100%}
.pruler .d{position:absolute;top:13px;width:7px;height:7px;border-radius:50%;margin-left:-3px}
.pruler .med{position:absolute;top:2px;width:2px;height:30px;background:var(--ink)}
.pruler .lbl{position:absolute;font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--ink3);white-space:nowrap}
@media (max-width:900px){.wrap{padding:0 16px}.search{min-width:0;width:100%}.bar{flex-wrap:wrap}.hero{grid-template-columns:1fr}.g4,.g2,.method,.facts{grid-template-columns:1fr 1fr}.sitehead{grid-template-columns:1fr}.feed .row{grid-template-columns:1fr}.nav{display:none}}
"""

HEAD = u"""<!doctype html><html lang="zh-CN" data-static="1"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>%s</title><meta name="description" content="司南实验室出品。对比 GPU 租赁与模型 API 价格，持续测量渠道质量，所有数据可追溯来源。不收任何被测渠道的钱。"><meta property="og:site_name" content="Sinan Compute"><meta property="og:type" content="website"><meta name="theme-color" content="#0B0F14"><link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>@font-face{font-family:"Instrument Serif";font-style:normal;font-weight:400;font-display:swap;src:url(/fonts/InstrumentSerif-latin.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}@font-face{font-family:"Instrument Serif";font-style:italic;font-weight:400;font-display:swap;src:url(/fonts/InstrumentSerif-italic-latin.woff2) format("woff2")}@font-face{font-family:"JetBrains Mono";font-style:normal;font-weight:400 600;font-display:swap;src:url(/fonts/JetBrainsMono-latin.woff2) format("woff2")}@font-face{font-family:"IBM Plex Sans";font-style:normal;font-weight:400 600;font-display:swap;src:url(/fonts/IBMPlexSans-latin.woff2) format("woff2")}</style>
<style>%s</style>"""

def header(rel="", active="model"):
    def nav(key, label):
        return '<a class="%s" href="%s">%s</a>' % ("on" if key == active else "", {"model": rel+"index.html", "site": rel+"index.html#sites", "media": rel+"media.html", "feed": rel+"index.html#feed", "method": rel+"index.html#method"}[key], label)
    return u"""<header class="top"><div class="wrap"><div class="bar">
  <a class="brand" href="%sindex.html"><svg width="30" height="30" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="17.5" fill="none" stroke="#2A3644" stroke-width="1.2"/><path d="M20 5v4M20 31v4M5 20h4M31 20h4" stroke="#64768A" stroke-width="1.2" stroke-linecap="round"/><path d="M20 9 L24.5 20 L20 31 Z" fill="#4FD1D9"/><path d="M20 9 L15.5 20 L20 31 Z" fill="#2A3644"/><circle cx="20" cy="20" r="2.2" fill="#0B0F14" stroke="#4FD1D9" stroke-width="1.4"/></svg>
  <div><h1>Sinan Compute</h1><div class="sub">司南·算力 · Sinan Lab</div></div></a>
  <nav class="nav">%s%s%s%s%s<a href="https://robo.sinanlab.com" style="color:var(--ink3)">Sinan Robo <span class="kind">即将上线</span></a><a href="https://sinanlab.com" style="color:var(--ink3)">← 司南实验室</a></nav>
  <form class="search" onsubmit="return goSearch()" role="search"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64768A" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><input id="q" type="search" placeholder="查一个站（toapis.cn）或一个模型（DeepSeek V4）" aria-label="搜索" list="qlist"><datalist id="qlist"></datalist><button type="submit">查</button></form>
</div><div class="pledge"><span><b>不收任何人的钱</b> — 没有付费墙、返佣、认证费</span><span><b>每个数字可点证据</b> — 来源、抓取时间、快照哈希</span><span><b>只给事实不给推荐</b> — 判断留给你</span></div></div></header>""" % (rel, nav("model","模型比价"), nav("site","站点"), nav("media","图像与视频"), nav("feed","动态"), nav("method","方法"))

FOOTER = u"""<footer style="border-top:1px solid var(--hair);margin-top:60px"><div class="wrap" style="display:flex;flex-wrap:wrap;gap:22px;align-items:center;padding:22px 56px;font-size:12.5px;color:var(--ink3)"><span>© 2026 Sinan Lab · 司南实验室</span><a href="https://sinanlab.com/constitution.html">中立宪法</a><a href="https://sinanlab.com/disclosure.html">返佣披露</a><a href="https://sinanlab.com/privacy.html">隐私政策</a><a href="https://sinanlab.com/disclaimer.html">免责声明</a><a href="https://sinanlab.com/">母站 sinanlab.com</a><a href="mailto:hello@sinanlab.com">hello@sinanlab.com</a><span style="margin-left:auto">每个数字可追溯来源 · 不收任何被测渠道的钱</span></div></footer>"""

DRAWER = u"""<div class="scrim" id="scrim"></div><aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="详情"><button class="close" id="dclose" aria-label="关闭">×</button><div class="eyebrow" id="deye">证据链</div><h3 id="dtitle" style="font-size:17px"></h3><div id="dbody"></div></aside>"""

COMMON_JS = u"""
var KIND={official:"官方",marketplace:"公开市场",relay:"中转站"};
var LABEL={unsustainable:"数学上不可持续",below_bulk:"低于常见批量折扣",explainable:"可由批量折扣解释",normal:"与公开价接近",premium:"高于公开价",far_above:"显著高于公开价"};
function fmt(x){return x==null?"—":(x<1?x.toFixed(3):x.toFixed(2));}
function gauge(ratio,cls){var left=Math.max(0,Math.min(2,ratio==null?1:ratio))/2*100;return '<span class="gauge"><i class="z1"></i><i class="z2"></i><i class="z3"></i><i class="z4"></i><span class="mid"></span><span class="needle '+(cls||"")+'" style="left:'+left.toFixed(2)+'%"></span></span>';}
function pct(r){if(r==null)return "—";var p=r*100;return (p<10?p.toFixed(1):p.toFixed(0))+"%";}
var drawer=document.getElementById("drawer"),scrim=document.getElementById("scrim");
function openD(eye,title,html){document.getElementById("deye").textContent=eye;document.getElementById("dtitle").textContent=title;document.getElementById("dbody").innerHTML=html;drawer.classList.add("on");scrim.classList.add("on");}
function closeD(){drawer.classList.remove("on");scrim.classList.remove("on");}
scrim.addEventListener("click",closeD);document.getElementById("dclose").addEventListener("click",closeD);document.addEventListener("keydown",function(e){if(e.key==="Escape")closeD();});
function snapHtml(sids){var h="";sids.forEach(function(s){var ev=D.snaps[String(s)];if(!ev)return;h+='<div class="snap"><div class="mono" style="font-size:11px;color:var(--ink-3)">快照 #'+ev.id+' · '+ev.source+'</div><div class="mono" style="font-size:12px;word-break:break-all;margin-top:3px">'+ev.url+'</div><div class="mono" style="font-size:11px;color:var(--ink-3);margin-top:3px">'+ev.fetched_at+' · sha256:'+ev.sha256.slice(0,16)+'…</div></div>';});return h;}
function helpHtml(code){return '<p style="font-size:14px;line-height:1.7">'+(D.label_help[code]||"")+'</p><p style="font-size:12.5px;color:var(--ink-3);margin-top:12px">分档只是算术区间：&lt;15% 不可持续 · 15–40% 低于折扣 · 40–75% 可由折扣解释 · 75–125% 接近 · 125–300% 溢价 · &gt;300% 显著高于。</p>';}
function relayEvidence(row,model){var f=model.floor;var direct=row.note&&row.note.usd_direct;var h='<div class="eyebrow" style="margin-top:14px">换算链</div><dl class="kv">'+(direct?'<dt>该站直接美元标价<small>无需充值比例换算</small></dt><dd>'+fmt(row.out)+' <small style="font-size:11px;color:var(--ink3)">USD</small></dd>':'<dt>面板名义价<small>倍率 × $2 / M</small></dt><dd>'+fmt(row.nominal_out)+' <small style="font-size:11px;color:var(--ink3)">USD</small></dd><dt>× 充值比例<small>面板 price 字段 · 每 $1 名义额度收多少元'+(row.stripe!=null&&row.stripe!=8?' · 另有 Stripe '+row.stripe+' 美元/$1':'')+'</small></dt><dd>'+row.price_field+' <small style="font-size:11px;color:var(--ink3)">元 / $1</small></dd><dt>÷ 汇率<small>USD/CNY · '+D.fx.as_of+'</small></dt><dd>'+D.fx.rate.toFixed(4)+'</dd><dt style="border-top:1px solid var(--hair2);padding-top:10px;color:var(--ink)">= 实付</dt><dd style="border-top:1px solid var(--hair2);padding-top:10px;font-size:20px">'+fmt(row.out)+'</dd>')+'<dt>÷ 最低公开渠道价<small>'+f.vendor+(f.cny?' · '+f.cny+' 元折算':'')+'</small></dt><dd>'+fmt(f.out)+'</dd><dt style="color:var(--ink)">= 比率</dt><dd style="font-size:20px" class="ratio '+row.band+'">'+pct(row.ratio)+'</dd></dl><div style="margin:14px 0 6px" class="gcell">'+gauge(row.ratio,row.band)+'<span class="pill '+row.band+'"><span class="dot"></span>'+LABEL[row.band]+'</span></div><div style="font-size:12.5px;color:var(--ink2)">'+(D.label_help[row.band]||"")+'</div><div class="eyebrow" style="margin-top:18px">快照 · 正文按哈希存对象存储，永不覆盖</div>';h+=snapHtml(row.sids.concat([f.sid,D.fx.sid]));h+='<p style="font-size:12.5px;color:var(--ink-3);margin-top:16px;border-top:1px solid var(--line-soft);padding-top:12px">此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。</p>';return h;}
function goSearch(){var v=(document.getElementById("q").value||"").trim().toLowerCase();if(!v)return false;var s=D.site_index.filter(function(x){return x.d.indexOf(v)>=0||(x.n||"").toLowerCase().indexOf(v)>=0;})[0];if(s){if(typeof SINGLE!=="undefined"&&SINGLE&&typeof siteDetailHtml==="function"){openD("站点事实清单",s.d+(s.n?" · "+s.n:""),siteDetailHtml(s.d));}else{location.href=REL+"s/"+s.d+".html";}return false;}var m=(D.model_index||[]).filter(function(x){return x.name.toLowerCase().indexOf(v)>=0||x.id.indexOf(v)>=0;})[0];if(m){location.href=REL+"index.html#m="+m.id;return false;}alert("没找到：既不是收录的站，也不是有报价的模型");return false;}
(function(){var dl=document.getElementById("qlist");D.site_index.slice(0,400).forEach(function(s){var o=document.createElement("option");o.value=s.d;dl.appendChild(o);});(D.model_index||[]).forEach(function(m){var o=document.createElement("option");o.value=m.name;dl.appendChild(o);});})();
"""

def esc(s):
    # 有的面板把 version / system_name 返回成对象，统一转成字符串再转义
    if s is None: s = ""
    if not isinstance(s, str): s = json.dumps(s, ensure_ascii=False)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

# ---------------- index ----------------
def build_index():
    st = D["stats"]
    site_index = [{"d": s["domain"], "n": s["name"]} for s in D["sites"]]
    model_index = [{"id": m["id"], "name": m["name"]} for m in D["models"]]
    light = {"models": D["models"], "groups": D["groups"], "vendor_name": D["vendor_name"], "fx": D["fx"], "snaps": D["snaps"],
             "label_help": D["label_help"], "site_index": site_index, "model_index": model_index,
             "sites": [{"d": s["domain"], "n": s["name"], "cl": s["cluster"], "nm": s["n_models"], "nr": s["n_ratio"], "med": s["median"],
                        "up": (s["avail"] or {}).get("uptime"), "ms": (s["avail"] or {}).get("ttfb_p50"), "fs": s["first_seen"], "ok": s["ok_count"], "un": s["un_count"]} for s in D["sites"]],
             "changes": D["changes"], "new_sites": D["new_sites"], "stats": st, "generated_at": D["generated_at"], "probe_node": D["probe_node"]}
    body = u"""%s
<main class="wrap">
<section class="hero">
  <div><div class="eyebrow">01 · 你要用哪个模型</div><h2>官方价、公开市场价、中转站实付价，<br><em>放在同一把尺上。</em></h2><p>便宜和风险同一行。先看解释得通的，再看便宜得离谱的——那些折起来了，别急着买。</p></div>
  <div class="kpis" id="kpis"></div>
</section>
<section class="sec" style="margin-top:8px">
  <div id="chipgroups"></div>
  <div class="legend"><span class="gcell"><span class="gauge" style="width:180px"><i class="z1"></i><i class="z2"></i><i class="z3"></i><i class="z4"></i><span class="mid"></span></span><span>0%%</span><span style="color:var(--ink2)">← 相对官方价 →</span><span>200%%</span></span><span><i class="sw" style="background:var(--crit)"></i>&lt;15%% 数学上不可持续</span><span><i class="sw" style="background:var(--warn)"></i>15–40%% 低于批量折扣</span><span><i class="sw" style="background:var(--good)"></i>40–75%% 可由折扣解释 · 75–125%% 接近官方</span><span class="right" id="asof" style="margin-left:auto"></span></div>
  <div class="card">
    <div class="calc"><b style="color:var(--ink)">按你的用量算</b><label>月输入 <input id="c-in" type="number" min="0" step="1" value="50"> M token</label><label>月输出 <input id="c-out" type="number" min="0" step="1" value="10"> M token</label><span>→ 「你的月成本」列随之变化</span></div>
    <div class="tablewrap"><table id="tbl"><thead><tr><th>渠道</th><th>类型</th><th class="num">输出 $/M</th><th class="num">输入 $/M</th><th class="num">你的月成本</th><th style="padding-left:14px">相对参考价 · 罗盘尺</th><th>判读</th><th>可用性</th><th class="num">证据</th></tr></thead><tbody></tbody></table></div>
    <div id="folds"></div>
    <div class="foot" id="tblfoot"></div>
  </div>
</section>

<section class="sec" id="sites">
  <div class="sechead"><div class="eyebrow" style="margin-right:6px">02</div><h2>你在用的站靠谱吗？</h2><span class="q">%d 个已确认站点，每站一页事实清单。不打分、不推荐。</span></div>
  <div class="grid g4" id="stats"></div>
  <div class="filters" id="filters" style="margin-top:14px"></div>
  <div class="card"><div class="tablewrap"><table id="sitetbl"><thead><tr><th>站</th><th>画像</th><th class="num">卖几个模型</th><th class="num">解释得通 / 不可持续</th><th>24h 可达</th><th class="num">延迟</th><th>首次收录</th><th></th></tr></thead><tbody></tbody></table></div><div class="foot" id="sitefoot"></div></div>
</section>

<section class="sec" id="feed">
  <div class="sechead"><div class="eyebrow" style="margin-right:6px">03</div><h2>今天变了什么</h2><span class="q">新收录的站、真实的价格变动。变更流从 2026-09-01 起累计。</span></div>
  <div class="card feed" id="feed"></div>
</section>

<section class="sec" id="method">
  <div class="sechead"><h2>我们怎么算的</h2></div>
  <div class="card method">
    <div><b>实付口径</b>中转站面板价是名义美元，实付 = 名义 × 充值比例 ÷ 汇率。三者各有快照。</div>
    <div><b>参考价取最低</b>官方与公开市场里同模型最低价作分母，比率只会偏高，宁少标不多标。</div>
    <div><b>判读是算术</b>「数学上不可持续」= 无补贴假设下低于成本；不判断成因。点标签旁的 ? 看人话解释。</div>
    <div><b>待核不发布</b>全线低到 1%% 以下或高到 30 倍的站，是我们读错基数，标「计价基数待核」。</div>
    <div><b>更正不删</b>算错了公开更正，原记录保留。方法论全文见 docs/METHOD.md。</div>
  </div>
</section>
</main>
%s
%s
<script id="data" type="application/json">%s</script>
<script>
var REL="";var D=JSON.parse(document.getElementById("data").textContent);
%s
document.getElementById("asof").textContent="数据 "+D.generated_at.slice(0,16).replace("T"," ")+" · 汇率 USD/CNY "+D.fx.rate.toFixed(2);
(function(){var S=D.stats,prof=Object.keys(S.clusters).reduce(function(a,k){return a+(k==="held"?0:S.clusters[k]);},0);var el=document.getElementById("kpis");
[["已确认站点",S.confirmed,""],["基数待核 · 不出比率",S.held,"站"],["今日价格变动",D.changes.length,""],["实付 <15%% 的站",'<span style="color:var(--crit)">'+S.clusters.ultra+'</span>',"/ "+prof]].forEach(function(x){var d=document.createElement("div");d.className="kpi";d.innerHTML='<div class="k">'+x[0]+'</div><div class="v">'+x[1]+(x[2]?' <small>'+x[2]+'</small>':'')+'</div>';el.appendChild(d);});})();
/* chips grouped by vendor */
var cur=(location.hash.match(/m=([^&]+)/)||[])[1]||(D.models[0]&&D.models[0].id);
var cg=document.getElementById("chipgroups");
Object.keys(D.groups).forEach(function(v){var g=document.createElement("div");g.className="vgroup";g.innerHTML='<span class="vn">'+(D.vendor_name[v]||v)+'</span>';D.groups[v].forEach(function(id){var m=D.models.filter(function(x){return x.id===id;})[0];if(!m)return;var b=document.createElement("button");b.className="chip"+(m.is_latest?" latest":"");b.dataset.id=id;b.innerHTML=m.name+'<span class="n">'+m.n_relay+' 家</span>';b.addEventListener("click",function(){cur=id;location.hash="m="+id;render();});g.appendChild(b);});cg.appendChild(g);});
var off=document.createElement("div");off.className="vgroup";off.innerHTML='<span class="vn">视频</span><span class="chip off">Seedance / Kling / Veo / Wan · 按秒可比仅 1 站，接入中</span>';cg.appendChild(off);
function usage(){return {i:+document.getElementById("c-in").value||0,o:+document.getElementById("c-out").value||0};}
function monthly(inp,outp){var u=usage();if(inp==null||outp==null)return null;return inp*u.i+outp*u.o;}
function rowHtml(r,m,i){var mc=monthly(r.in,r.out);var up=r.uptime==null?'<span class="up">—</span>':'<span class="up '+(r.uptime>=90?"good":r.uptime<50?"bad":"")+'">'+r.uptime.toFixed(0)+'%%</span>';return '<tr><td><a class="dom" href="s/'+r.vendor+'.html">'+r.vendor+'</a>'+(r.name?'<div style="font-size:11.5px;color:var(--ink3)">'+r.name+'</div>':'')+'</td><td><span class="kind">中转站</span></td><td class="num bigout">'+fmt(r.out)+'<span class="asof">抓取 '+r.as_of.slice(5).replace("T"," ")+'</span></td><td class="num">'+fmt(r.in)+'</td><td class="num">'+(mc==null?"—":"$"+mc.toFixed(mc<10?2:0))+'</td><td style="padding-left:14px"><span class="gcell">'+gauge(r.ratio,r.band)+'<span class="ratio '+r.band+'">'+pct(r.ratio)+'</span></span></td><td><span class="pill '+r.band+'"><span class="dot"></span>'+LABEL[r.band]+'</span><button class="help" data-help="'+r.band+'" aria-label="解释">?</button></td><td>'+up+'</td><td class="num"><button class="evb" data-m="'+m.id+'" data-i="'+i+'">证据 ↗</button></td></tr>';}
function render(){document.querySelectorAll(".chip[data-id]").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.id===cur?"true":"false");});var m=D.models.filter(function(x){return x.id===cur;})[0];if(!m)return;var tb=document.querySelector("#tbl tbody");var f=m.floor;var fmc=monthly(f.in,f.out);tb.innerHTML='<tr class="floor"><td><b class="mono">'+f.vendor+'</b><div style="font-size:11.5px;color:var(--ink3)">'+(f.cny?"官方定价页":"公开市场 · 供应商标价")+'</div></td><td><span class="kind" style="color:var(--accent)">参考</span></td><td class="num bigout">'+fmt(f.out)+'</td><td class="num">'+fmt(f.in)+'</td><td class="num">'+(fmc==null?"—":"$"+fmc.toFixed(fmc<10?2:0))+'</td><td style="padding-left:14px"><span class="gcell">'+gauge(1,"ref")+'<span class="ratio" style="color:var(--accent)">1.00×</span></span></td><td><span class="pill ref"><span class="dot"></span>基准</span></td><td>—</td><td class="num"><button class="evb" data-f="'+m.id+'">证据 ↗</button></td></tr>';
var main=m.rows.filter(function(r){return !r.held&&["explainable","normal","premium","below_bulk"].indexOf(r.band)>=0;});var un=m.rows.filter(function(r){return !r.held&&r.band==="unsustainable";});var far=m.rows.filter(function(r){return !r.held&&r.band==="far_above";});var held=m.rows.filter(function(r){return r.held;});
main.forEach(function(r){tb.insertAdjacentHTML("beforeend",rowHtml(r,m,m.rows.indexOf(r)));});
var folds=document.getElementById("folds");folds.innerHTML="";
function fold(title,rows,openIt){if(!rows.length)return;var d=document.createElement("details");d.className="fold";if(openIt)d.open=true;d.innerHTML='<summary>'+title+'</summary><div class="tablewrap"><table><tbody>'+rows.map(function(r){return rowHtml(r,m,m.rows.indexOf(r));}).join("")+'</tbody></table></div>';folds.appendChild(d);}
fold('另有 <b>'+un.length+'</b> 家报价低到在无补贴假设下数学上不可能（'+pct(Math.min.apply(null,un.map(function(r){return r.ratio;}).concat([1])))+' 起）— 展开看，别急着买',un,false);
fold(far.length+' 家显著高于公开价',far,false);
fold(held.length+' 家计价基数待核（我们暂不出比率）',held,false);
document.getElementById("tblfoot").innerHTML='<span><b>'+m.name+'</b>：参考价 '+f.vendor+' $'+fmt(f.out)+'/百万输出</span><span>中转站 '+m.rows.length+' 家：解释得通 '+main.length+'，不可持续 '+un.length+'，待核 '+held.length+'</span><span>中转价为人民币充值通道实付；可用性来自 '+D.probe_node+'</span>';}
render();["c-in","c-out"].forEach(function(id){document.getElementById(id).addEventListener("input",render);});
/* 页内站点详情（单文件发布时没有 s/ 目录） */
/* 单文件模式：除本地开发和显式声明的静态部署（<html data-static="1">）外，一律页内渲染 */
var SINGLE = !(/^(localhost|127\.0\.0\.1)$/.test(location.hostname) || document.documentElement.dataset.static==="1");
function siteDetailHtml(d){var s=D.sites_full[d];if(!s)return "<p>没有这个站</p>";var f=s.facts||{},av=s.avail||{},cl=s.cluster;var price=f.price!=null?(f.price+" 元 / $1"+((f.stripe!=null&&f.stripe!=8)?"（Stripe "+f.stripe+" 美元/$1）":"")):"未暴露";
var facts=[["价格画像",cl?cl.name:"无比对",(cl&&cl.code!=="held"&&s.median!=null)?("中位 "+pct(s.median)+" · "+cl.help):(cl?cl.help:"没有能对上参考价的模型")],["24h 可达",av.uptime!=null?av.uptime.toFixed(0)+"%%":"—",av.ttfb_p50?("延迟 p50 "+av.ttfb_p50+"ms · "+av.n+" 次"):"尚无探测"],["在卖模型",s.models.length+" 个","解释得通 "+s.ok+" · 不可持续 "+s.un],["充值比例",price,"面板 price 字段"],["登录方式",(f.login||[]).join("、")||"未暴露",(f.turnstile?"需人机验证":"无人机验证")+(f.checkin?" · 有签到":"")],["面板",s.panel||"—",s.version||""],["首次收录",s.first_seen,"来源 "+(s.channel||"")]];
var h='<div style="display:flex;gap:10px;align-items:center;margin-bottom:12px">'+(cl?'<span class="cl '+cl.code+'">'+cl.name+'</span>':'')+'<a class="go" href="'+(s.site_url||("https://"+d+"/"))+'" target="_blank" rel="noopener nofollow">前往站点 →</a></div>'+(cl&&cl.code==="held"?'<div class="notice">该站全线报价与公开价差距异常，大概率是面板倍率基数与上游不同。只列名义报价，不出比率结论。</div>':'');
h+='<dl class="kv">'+facts.map(function(x){return '<dt>'+x[0]+'</dt><dd style="font-family:inherit">'+x[1]+'<div style="font-size:11.5px;color:var(--ink-3)">'+x[2]+'</div></dd>';}).join("")+'</dl>';
h+='<div class="callout" style="font-size:12.5px"><b>怎么核实它是不是真模型：</b>用你在该站的 Key 跑开源指纹/协议一致性检测（我们的探针脚本或 Veridrop）。本站不替你判断。</div>';
h+='<h4 style="margin:14px 0 6px;font-size:14px">它卖的模型与实付价</h4><div class="tablewrap"><table style="font-size:12.5px"><thead><tr><th>模型</th><th class="num">实付</th><th class="num">参考</th><th class="num">比率</th><th>判读</th></tr></thead><tbody>'+s.models.map(function(r){var v=r.out!=null?r.out:(r.call!=null?r.call:r.sec);var u=r.out!=null?"$/百万输出":(r.call!=null?"$/次":"$/秒");return '<tr><td><b>'+r.name+'</b><div style="font-size:11px;color:var(--ink-3)">'+r.raw+'</div></td><td class="num">'+(v!=null?v.toFixed(3):"—")+'<span class="asof">'+u+'</span></td><td class="num">'+(r.floor_out?r.floor_out.toFixed(2):"—")+'</td><td class="num">'+(r.ratio!=null?'<span class="ratio '+r.band+'">'+pct(r.ratio)+'</span>':"—")+'</td><td>'+(r.band?'<span class="pill '+r.band+'"><span class="dot"></span>'+LABEL[r.band]+'</span>':'<span class="pill normal">无参考</span>')+'</td></tr>';}).join("")+'</tbody></table></div>';return h;}
document.addEventListener("click",function(e){var a=e.target.closest?e.target.closest("a.dom, a.go[href^='s/']"):null;if(!a)return;var m=(a.getAttribute("href")||"").match(/^s\/(.+)\.html$/);if(!m)return;if(!SINGLE)return;e.preventDefault();var d=m[1];openD("站点事实清单",d+(D.sites_full[d]&&D.sites_full[d].name?" · "+D.sites_full[d].name:""),siteDetailHtml(d));});
document.addEventListener("click",function(e){var h=e.target.closest?e.target.closest(".help"):null;if(h){openD("这是什么意思",LABEL[h.dataset.help],helpHtml(h.dataset.help));return;}var b=e.target.closest?e.target.closest(".evb"):null;if(!b)return;var m=D.models.filter(function(x){return x.id===(b.dataset.m||b.dataset.f);})[0];if(b.dataset.f){openD("证据链",m.floor.vendor+" · "+m.name+" · 参考价 $"+fmt(m.floor.out)+"/百万输出",'<dl class="kv"><dt>类型</dt><dd>'+(m.floor.cny?"官方（人民币折算）":"公开市场")+'</dd></dl>'+snapHtml([m.floor.sid].concat(m.floor.cny?[D.fx.sid]:[])));return;}var r=m.rows[+b.dataset.i];openD("证据链",r.vendor+" · "+m.name+" · 实付 $"+fmt(r.out)+"/百万输出",relayEvidence(r,m));});
/* stats */
var S=D.stats,st=document.getElementById("stats");[["ultra","超低价",S.clusters.ultra,"实付不到公开价 15%%"],["cheap","两三折",S.clusters.cheap,"15%%–50%%"],["near","贴官方",S.clusters.near,"50%%–150%%，按官方价转售"],["high","高价 / 待核",S.clusters.high+S.clusters.held,"≥150%% 或全线异常——多为倍率基数读错，不出比率"]].forEach(function(x){var d=document.createElement("div");d.className="card stat c-"+x[0];d.innerHTML='<div class="v">'+x[2]+'</div><div class="k">'+x[1]+'</div><div class="n">'+x[3]+'</div>';st.appendChild(d);});
/* site table with filters */
var CLN={ultra:"超低价",cheap:"两三折",near:"贴官方",high:"高价",held:"待核"};var filt="all",onlyQ=true;
var fl=document.getElementById("filters");[["all","全部"],["near","贴官方 "+S.clusters.near],["cheap","两三折 "+S.clusters.cheap],["ultra","超低价 "+S.clusters.ultra],["high","高价 "+S.clusters.high],["held","待核 "+S.clusters.held]].forEach(function(x){var b=document.createElement("button");b.className="fchip";b.dataset.f=x[0];b.textContent=x[1];b.setAttribute("aria-pressed",x[0]==="all"?"true":"false");b.addEventListener("click",function(){filt=x[0];renderSites();});fl.appendChild(b);});
var tg=document.createElement("button");tg.className="fchip";tg.style.marginLeft="auto";tg.textContent="也显示没报价的站";tg.addEventListener("click",function(){onlyQ=!onlyQ;tg.setAttribute("aria-pressed",onlyQ?"false":"true");renderSites();});fl.appendChild(tg);
function renderSites(){document.querySelectorAll(".fchip[data-f]").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.f===filt?"true":"false");});var rows=D.sites.filter(function(s){if(onlyQ&&!s.nm)return false;if(filt==="all")return true;return s.cl&&s.cl.code===filt;});var tb=document.querySelector("#sitetbl tbody");tb.innerHTML=rows.slice(0,150).map(function(s){var up=s.up==null?"—":'<span class="up '+(s.up>=90?"good":s.up<50?"bad":"")+'">'+s.up.toFixed(0)+'%%</span>';return '<tr><td><a class="dom" href="s/'+s.d+'.html">'+s.d+'</a>'+(s.n?'<div style="font-size:11.5px;color:var(--ink-3)">'+s.n+'</div>':'')+'</td><td>'+(s.cl?'<span class="cl '+s.cl.code+'">'+s.cl.name+(s.med!=null&&s.cl.code!=="held"?' · 中位 '+pct(s.med):'')+'</span>':'<span class="cl held">无比对</span>')+'</td><td class="num">'+s.nm+'</td><td class="num"><span style="color:var(--good)">'+s.ok+'</span> / <span style="color:var(--crit)">'+s.un+'</span></td><td>'+up+'</td><td class="num">'+(s.ms?s.ms+"ms":"—")+'</td><td class="mono" style="font-size:12px">'+s.fs+'</td><td class="num"><a class="go small" href="s/'+s.d+'.html">详情</a></td></tr>';}).join("");document.getElementById("sitefoot").innerHTML='<span>显示 '+Math.min(rows.length,150)+' / '+rows.length+' 站'+(rows.length>150?"（用搜索框直达其他站）":"")+'</span><span>画像 = 该站所有可比模型的输出价相对公开价的中位数</span>';}
renderSites();
/* feed */
var feed=document.getElementById("feed");var items=[];if(D.new_sites.length)items.push({t:D.generated_at,text:"今日新收录 <b>"+D.new_sites.length+"</b> 个站",sub:D.new_sites.slice(0,12).join(" · ")+(D.new_sites.length>12?" …":"")});
D.changes.forEach(function(c){var up=c.new>c.old;items.push({t:c.t,text:c.vendor+" · "+c.model+" 输出价 <span class=\\"old\\">"+fmt(c.old)+"</span> → <span class=\\"new\\">"+fmt(c.new)+"</span>"+(c.kind==="relay"?" 名义$/百万":" $/百万")+(up?" ↑":" ↓"),sub:c.kind==="relay"?"中转站":"公开参考价"});});
if(!items.length)items.push({t:D.generated_at,text:"今天没有价格变动",sub:"变更流从 2026-09-01 起累计"});
items.slice(0,12).forEach(function(f){var r=document.createElement("div");r.className="row";r.innerHTML='<div class="t">'+f.t.slice(5,16).replace("T"," ")+'</div><div class="b">'+f.text+'<div class="sub">'+(f.sub||"")+'</div></div>';feed.appendChild(r);});
</script>""" % (header(""), st["confirmed"], FOOTER, DRAWER, json.dumps(light, ensure_ascii=False).replace("</", "<\\/"), COMMON_JS)
    return HEAD % ("Sinan Compute · 司南·算力 —— GPU 与模型 API 中立比价与质量测量", CSS) + '<link rel="canonical" href="https://compute.sinanlab.com/"></head><body>' + body + "</body></html>"

# ---------------- per-site page ----------------
def build_site(s):
    lite = {"fx": D["fx"], "snaps": {k: v for k, v in D["snaps"].items()}, "label_help": D["label_help"], "site_index": [{"d": x["domain"], "n": x["name"]} for x in D["sites"]],
            "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]], "site": s}
    f = s["facts"] or {}; av = s.get("avail") or {}
    cl = s["cluster"]
    price_note = ""
    if f.get("price") is not None:
        price_note = "%s 元 / $1" % f["price"]
    stripe_note = ("Stripe 通道 %s 美元/$1 · 决定实付" % f["stripe"]) if f.get("stripe") not in (None, 8, 8.0) else "面板 price 字段 · 决定实付"
    LBL = {"unsustainable":"数学上不可持续","below_bulk":"低于批量折扣","explainable":"可由批量折扣解释","normal":"与公开价接近","premium":"高于公开价","far_above":"显著高于公开价"}
    # 画像尺：真实比率落点
    dots = []
    ratios = [r["ratio"] for r in s["models"] if r.get("ratio") is not None]
    for r in s["models"]:
        if r.get("ratio") is None: continue
        left = max(0, min(2, r["ratio"])) / 2 * 100
        col = {"unsustainable":"var(--crit)","below_bulk":"var(--warn)","explainable":"var(--good)","normal":"var(--good)"}.get(r["band"], "var(--ink3)")
        dots.append("<span class='d' style='left:%.2f%%;background:%s' title='%s %s'></span>" % (left, col, esc(r["name"]), ("%.0f%%" % (r["ratio"]*100))))
    med_html = ""
    if s.get("median") is not None:
        ml = max(0, min(2, s["median"])) / 2 * 100
        med_html = "<span class='med' style='left:%.2f%%'></span><span class='lbl' style='left:calc(%.2f%% + 8px);top:-6px;color:var(--ink)'>中位 %s</span>" % (ml, ml, ("%.1f%%" % (s["median"]*100)) if s["median"] < 0.1 else ("%.0f%%" % (s["median"]*100)))
    profile = ""
    if ratios and not (cl and cl["code"] == "held"):
        profile = """<div class="card profile"><div style="display:flex;align-items:baseline;gap:14px"><div class="eyebrow">价格画像</div><div style="font-size:13px;color:var(--ink3)">%d 个可比模型在罗盘尺上的落点 · 每个点是一个模型 · 竖线是中位数</div></div>
        <div class="pruler"><div class="track"><i style="width:7.5%%;background:var(--crit);opacity:.35"></i><i style="width:12.5%%;background:var(--warn);opacity:.35"></i><i style="width:42.5%%;background:var(--good);opacity:.3"></i><i style="width:37.5%%;background:var(--hair)"></i></div>%s%s<span style="position:absolute;left:50%%;top:6px;width:1px;height:22px;background:var(--ink3)"></span><span class="lbl" style="left:calc(50%% + 6px);top:24px">官方 100%%</span></div></div>""" % (len(ratios), "".join(dots), med_html)
    rows_html = []
    for r in s["models"]:
        unit = "$/M 输出" if r["out"] is not None else ("$/次" if r["call"] is not None else ("$/秒" if r["sec"] is not None else ""))
        val = r["out"] if r["out"] is not None else (r["call"] if r["call"] is not None else r["sec"])
        gcell = ("<span class='gcell'><span class='gauge'><i class='z1'></i><i class='z2'></i><i class='z3'></i><i class='z4'></i><span class='mid'></span><span class='needle %s' style='left:%.2f%%'></span></span><span class='ratio %s'>%s</span></span>" % (
            r["band"], max(0, min(2, r["ratio"]))/2*100, r["band"], ("%.1f%%" % (r["ratio"]*100)) if r["ratio"] < 0.1 else ("%.0f%%" % (r["ratio"]*100)))) if r["ratio"] is not None else "<span style='color:var(--ink3)'>—</span>"
        judge = ("<span class='pill %s'><span class='dot'></span>%s</span><button class='help' data-help='%s'>?</button>" % (r["band"], LBL[r["band"]], r["band"])) if r["band"] else "<span class='pill held'>无公开参考价</span>"
        mt = {"text": "文本", "image": "图像", "video": "视频"}.get(r["mtype"] or "", "")
        rows_html.append("<tr><td><div style='font-size:14px'>%s</div><div class='kind'>%s%s · 抓取 %s</div></td><td class='num'><span class='bigout'>%s</span><span class='asof'>%s</span></td><td class='num' style='color:var(--ink2)'>%s</td><td style='padding-left:14px'>%s</td><td>%s</td><td class='num'><button class='evb' data-sids='%s'>证据 ↗</button></td></tr>" % (
            esc(r["name"]), esc(r["raw"]), (" · " + mt) if mt else "", r["as_of"][5:].replace("T", " "), ("%.3f" % val) if val is not None else "—", unit,
            ("%.2f" % r["floor_out"]) if r.get("floor_out") else "—", gcell, judge, ",".join(map(str, r["sids"]))))
    held_note = "<div class='notice'>该站全线报价与公开价差距异常，大概率是面板倍率基数与上游不同。我们只列它的名义报价，不出比率结论，等核实基数后再放行。</div>" if cl and cl["code"] == "held" else ""
    up = ("%.0f%%" % av["uptime"]) if av.get("uptime") is not None else "—"
    upc = "var(--good)" if (av.get("uptime") or 0) >= 90 else ("var(--crit)" if av.get("uptime") is not None and av["uptime"] < 50 else "var(--ink)")
    body = u"""%s
<main class="wrap">
<div class="crumb"><a href="../index.html">首页</a> › <a href="../index.html#sites">站点</a> › %s</div>
<div class="sitehead">
  <div>
    <div style="display:flex;align-items:center;gap:12px">%s<span class="mono" style="font-size:11.5px;color:var(--ink3)">%s%s · 首次收录 %s</span></div>
    <h2 style="margin-top:14px">%s%s</h2>
    <div class="sub">这个站卖 %d 个模型，能对上公开参考价的 %d 个；解释得通 %d 个，落在"数学上不可持续"区的 %d 个。</div>
    <div style="display:flex;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap"><a class="go" href="/go/%s" rel="noopener nofollow" target="_blank">前往站点 <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M9 7h8v8"/></svg></a><span class="ghost">用我的 Key 核实一致性</span><span class="mono" style="font-size:11.5px;color:var(--ink3)">经 /go/ 中转 · 只记点击数，不存 IP</span></div>
  </div>
  <div class="facts">
    <div class="fact"><div class="k">24h 可达</div><div class="v" style="color:%s">%s</div><div class="n">%s</div></div>
    <div class="fact"><div class="k">在卖模型</div><div class="v">%d</div><div class="n">解释得通 %d · 不可持续 %d</div></div>
    <div class="fact"><div class="k">充值比例</div><div class="v" style="font-size:18px">%s</div><div class="n">%s</div></div>
    <div class="fact"><div class="k">登录方式</div><div class="v" style="font-size:15px;font-family:inherit">%s</div><div class="n">%s</div></div>
  </div>
</div>
%s
%s
<section class="sec" style="margin-top:22px"><div class="sechead"><h2 style="font-size:20px">它卖的模型与实付价</h2><span class="q">人民币充值通道实付 = 面板名义价 × 充值比例 ÷ 汇率 %.2f · 按比率从低到高</span></div>
<div class="card"><div class="tablewrap"><table><thead><tr><th>模型</th><th class="num">实付</th><th class="num">最低公开价</th><th style="padding-left:14px">相对参考价 · 罗盘尺</th><th>判读</th><th class="num">证据</th></tr></thead><tbody>%s</tbody></table></div></div>
<div class="callout"><b style="color:var(--ink)">怎么核实模型一致性：</b>本站不替你判断。用你在该站的 Key 跑开源的 tokenizer 指纹 / 协议一致性检测，十秒钟能看出输出分布是否与官方一致。页面上的每个比率都是算术，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。</div>
</section>
</main>
%s
<script id="data" type="application/json">%s</script>
<script>var REL="../";var D=JSON.parse(document.getElementById("data").textContent);%s
document.addEventListener("click",function(e){var h=e.target.closest?e.target.closest(".help"):null;if(h){openD("这是什么意思",LABEL[h.dataset.help],helpHtml(h.dataset.help));return;}var b=e.target.closest?e.target.closest(".evb"):null;if(!b)return;openD("证据链","%s · 报价快照",snapHtml(b.dataset.sids.split(",").map(Number).concat([D.fx.sid]))+'<p style="font-size:12.5px;color:var(--ink3);margin-top:16px">实付 = 名义 × '+(D.site.facts.price||"?")+' 元/$1 ÷ 汇率 '+D.fx.rate.toFixed(2)+'。此为算术比值，不构成对该渠道的任何指控。</p>');});</script>""" % (
        header("../", "site"), esc(s["domain"]),
        ("<span class='cl %s'>%s%s</span>" % (cl["code"], cl["name"], (" · 中位 " + (("%.1f%%" % (s["median"]*100)) if s["median"] < 0.1 else ("%.0f%%" % (s["median"]*100)))) if (s.get("median") is not None and cl["code"] != "held") else "")) if cl else "<span class='cl held'>无比对</span>",
        esc(s.get("panel") or ""), (" " + esc(f.get("version") or s.get("version") or "")) if (f.get("version") or s.get("version")) else "", s["first_seen"],
        esc(s["domain"]), ("<span>%s</span>" % esc(s["name"])) if s.get("name") else "",
        s["n_models"], s["n_ratio"], s["ok_count"], s["un_count"],
        esc(s["domain"]),
        upc, up, ("延迟 p50 %sms · %d 次探测 · %s" % (av.get("ttfb_p50") or "—", av.get("n") or 0, D["probe_node"])) if av else "尚无探测数据",
        s["n_models"], s["ok_count"], s["un_count"],
        price_note or "未暴露", stripe_note,
        "、".join(f.get("login") or []) or "未暴露", ("需人机验证" if f.get("turnstile") else "无人机验证") + (" · 有签到" if f.get("checkin") else ""),
        held_note, profile,
        D["fx"]["rate"], "".join(rows_html) or "<tr><td colspan='6' style='color:var(--ink3)'>该站定价接口需登录或未暴露，暂无报价</td></tr>",
        DRAWER, json.dumps(lite, ensure_ascii=False).replace("</", "<\\/"), COMMON_JS, esc(s["domain"]))
    return HEAD % (s["domain"] + " · Sinan Compute", CSS) + ('<link rel="canonical" href="https://compute.sinanlab.com/s/%s.html"></head><body>' % s["domain"]) + body + FOOTER.replace("padding:22px 56px","padding:22px 0") + "</body></html>"


# ---------------- media (图像 / 视频) ----------------
MEDIA = json.load(open(os.path.join(HERE, "media.json"))) if os.path.exists(os.path.join(HERE, "media.json")) else None

MEDIA_JS = u"""
function mediaFamilyHtml(f, mod){
  var ref = f.ref ? ('<div class="fact card" style="display:inline-block;margin-right:10px"><div class="k">官方参考</div><div class="v mono">$'+f.ref.price.toFixed(3)+(mod==="video"?" / 秒":" / 张")+'</div><div class="n">'+f.ref.model+' · '+f.ref.region+' 档 · '+(f.ref.source||"")+'</div></div>')
                   : ('<div class="notice" style="display:inline-block;margin:0 10px 0 0">无官方参考价：'+(f.ref_missing||"")+'。只列报价，不出比率。</div>');
  var clip = (mod==="video" && f.default_clip) ? ('<div class="fact card" style="display:inline-block"><div class="k">按次折算假设</div><div class="v mono">1 次 = '+f.default_clip+' 秒</div><div class="n">'+(f.clip_source||"")+'</div></div>') : "";
  var stat = '<div class="fact card" style="display:inline-block;margin-right:10px"><div class="k">中转站</div><div class="v mono">'+f.n_sites+' 站 · '+f.n_rows+' 条</div><div class="n">实付 $'+(f.eff_min!=null?f.eff_min.toFixed(3):"—")+' – $'+(f.eff_max!=null?f.eff_max.toFixed(3):"—")+(mod==="video"?" / 次或秒":" / 次")+'</div></div>';
  var rec=f.rows.filter(function(r){return r.recent;}), old=f.rows.filter(function(r){return !r.recent && !r.held;});
  var main=rec.filter(function(r){return !r.held && r.band && ["explainable","normal","premium","below_bulk"].indexOf(r.band)>=0;});
  var un=rec.filter(function(r){return !r.held && r.band==="unsustainable";});
  var far=rec.filter(function(r){return !r.held && r.band==="far_above";});
  var noref=rec.filter(function(r){return !r.held && !r.band;});
  var held=f.rows.filter(function(r){return r.held;});
  var verTag = (f.recent_versions&&f.recent_versions.length) ? '<div class="fact card" style="display:inline-block;margin-right:10px"><div class="k">主推版本</div><div class="v mono">'+(f.recent_labels||f.recent_versions).join(" · ")+'</div><div class="n">该族在中转站出现的最新两代；更旧的折叠</div></div>' : "";
  function row(r){
    var shown = mod==="video" ? (r.per_s!=null ? ("$"+r.per_s.toFixed(3)+"/秒"+(r.unit==="per_call"?"*":"")) : ("$"+r.eff.toFixed(3)+"/次")) : ("$"+r.eff.toFixed(3)+"/次");
    var ratio = r.ratio!=null ? '<span class="gcell">'+gauge(r.ratio,r.band)+'<span class="ratio '+r.band+'">'+pct(r.ratio)+'</span></span>' : '<span style="color:var(--ink3)">—</span>';
    var judge = r.band ? '<span class="pill '+r.band+'"><span class="dot"></span>'+LABEL[r.band]+'</span><button class="help" data-help="'+r.band+'">?</button>' : '<span class="pill normal">无参考</span>';
    var notes = [r.version_note, r.assumption].filter(Boolean).join("；");
    return '<tr><td><a class="dom" href="s/'+r.site+'.html">'+r.site+'</a></td><td><b>'+r.name+'</b>'+(r.version_label?' <span class="pill normal" style="font-size:10.5px">'+r.version_label+'</span>':'')+(notes?'<div style="font-size:11px;color:var(--ink-3)">'+notes+'</div>':'')+'</td><td class="num bigout">'+shown+'<span class="asof">'+(r.usd_direct?('该站直接美元标价'+(r.spec?' · '+r.spec:'')):('名义 '+r.nominal+' × '+r.price_field+' ÷ '+D.fx.rate.toFixed(2)))+' · 抓取 '+r.as_of.slice(5).replace("T"," ")+'</span></td><td class="num">'+ratio+'</td><td>'+judge+'</td><td><button class="evb" data-sids="'+r.sids.join(",")+(r.ref_sid?","+r.ref_sid:"")+'">证据 ↗</button></td></tr>';
  }
  function tbl(rows){return '<div class="tablewrap"><table><thead><tr><th>站</th><th>该站模型名</th><th class="num">实付</th><th style="padding-left:14px">相对官方 · 罗盘尺</th><th>判读</th><th class="num">证据</th></tr></thead><tbody>'+rows.map(row).join("")+'</tbody></table></div>';}
  function fold(t,rows,open){return rows.length?('<details class="fold"'+(open?" open":"")+'><summary>'+t+'</summary>'+tbl(rows)+'</details>'):"";}
  var body = (main.length ? tbl(main) : "") + fold('另有 <b>'+un.length+'</b> 家报价低到在无补贴假设下数学上不可能',un,false) + fold(far.length+' 家显著高于官方',far,false)
           + fold(noref.length+' 条无官方参考，只列报价',noref, !f.ref) + fold(old.length+' 条旧版本（更早的代次，默认折叠）',old,false) + fold(held.length+' 条来自「计价基数待核」站',held,false);
  return '<div class="card" style="margin-bottom:16px"><div style="padding:14px 16px;border-bottom:1px solid var(--line-soft)"><h3 style="font-size:17px;margin-bottom:10px">'+f.name+'</h3>'+ref+verTag+stat+clip+'</div>'+body+'</div>';
}
function renderMedia(mod){
  document.querySelectorAll(".mtab").forEach(function(b){b.setAttribute("aria-pressed",b.dataset.mod===mod?"true":"false");});
  var list = M[mod]||[]; var el=document.getElementById("mediabody");
  el.innerHTML = list.length ? list.map(function(f){return mediaFamilyHtml(f, mod);}).join("") : '<p style="color:var(--ink-3)">暂无数据</p>';
  var s=M.stats; document.getElementById("mediafoot").innerHTML = mod==="video"
    ? '<span>视频：'+s.video_rows+' 条报价 · '+s.video_sites+' 站 · 可与官方比对 '+s.video_cmp+' 条</span><span>* = 按该族默认单次时长折算成每秒</span><span>官方按秒价来自 Google / Kling / MiniMax 定价页；Seedance / Vidu / Wan / Sora 官方页为前端渲染或拒绝抓取，只列报价</span>'
    : '<span>图像：'+s.image_rows+' 条报价 · '+s.image_sites+' 站 · 可与官方比对 '+s.image_cmp+' 条</span><span>官方按张价来自 Google（Nano Banana）/ BFL（FLUX，1 张按 1MP）/ Kling Image；GPT Image / Seedream / Qwen-Image / Midjourney 无可读官方按张价，只列报价</span>';
}
document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest(".mtab"):null;if(b){renderMedia(b.dataset.mod);}});
"""

MEDIA_SECTION = u"""
<section class="sec" id="media">
  <div class="sechead"><div class="eyebrow" style="margin-right:6px">02b</div><h2>图像与视频</h2><span class="q">中转站的图像/视频报价，与官方按张 / 按秒价放在一起。按次报价要折算，假设写在明面上。</span><span class="right" id="mediaasof"></span></div>
  <div class="filters"><button class="mtab fchip" data-mod="video" aria-pressed="true">视频生成</button><button class="mtab fchip" data-mod="image" aria-pressed="false">图像生成</button><span style="margin-left:auto;font-size:12.5px;color:var(--ink-3)">按厂商族分组，先有官方参考的</span></div>
  <div id="mediabody"></div>
  <div class="foot" id="mediafoot" style="border-top:0"></div>
</section>
"""


def build_media_page():
    if not MEDIA: return None
    lite = {"fx": MEDIA["fx"], "snaps": MEDIA["snaps"], "label_help": D["label_help"], "site_index": [{"d": x["domain"], "n": x["name"]} for x in D["sites"]],
            "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]]}
    body = u"""%s<main class="wrap"><div class="crumb"><a href="index.html">首页</a> › 图像与视频</div>%s</main>%s
<script id="data" type="application/json">%s</script><script id="mdata" type="application/json">%s</script>
<script>var REL="";var D=JSON.parse(document.getElementById("data").textContent);var M=JSON.parse(document.getElementById("mdata").textContent);%s%s
document.getElementById("mediaasof").textContent="数据 "+M.generated_at.slice(0,16).replace("T"," ")+" · 汇率 "+M.fx.rate.toFixed(2);renderMedia("video");
document.addEventListener("click",function(e){var h=e.target.closest?e.target.closest(".help"):null;if(h){openD("这是什么意思",LABEL[h.dataset.help],helpHtml(h.dataset.help));return;}var b=e.target.closest?e.target.closest(".evb"):null;if(!b)return;openD("证据链","报价与官方参考快照",snapHtml(b.dataset.sids.split(",").map(Number).concat([M.fx.sid]))+'<p style="font-size:12.5px;color:var(--ink-3);margin-top:16px">此为算术比值，不构成对该渠道的任何指控。</p>');});</script>""" % (
        header("", "media"), MEDIA_SECTION, DRAWER, json.dumps(lite, ensure_ascii=False).replace("</", "<\\/"), json.dumps(MEDIA, ensure_ascii=False).replace("</", "<\\/"), COMMON_JS, MEDIA_JS)
    return HEAD % ("图像与视频 · Sinan Compute", CSS) + '<link rel="canonical" href="https://compute.sinanlab.com/media.html"></head><body>' + body + FOOTER + "</body></html>"


def _inject_media_into_index(html):
    """首页：在「你在用的站靠谱吗」之前插入媒体板块（单文件发布也能用）。"""
    if not MEDIA: return html
    marker = '<section class="sec" id="sites">\n  <div class="sechead"><div class="eyebrow" style="margin-right:6px">02</div><h2>你在用的站靠谱吗？</h2>'
    if marker not in html: return html
    html = html.replace(marker, MEDIA_SECTION + marker, 1)
    inject = ('<script>var M=null;%s\n'
              'fetch("media.json").then(function(r){return r.json();}).then(function(m){M=m;Object.keys(m.snaps||{}).forEach(function(k){if(!D.snaps[k])D.snaps[k]=m.snaps[k];});'
              'document.getElementById("mediaasof").textContent="数据 "+M.generated_at.slice(0,16).replace("T"," ");renderMedia("video");}).catch(function(){document.getElementById("mediaasof").textContent="数据加载失败，请刷新";});\n'
              'document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest("#media .evb"):null;if(!b)return;e.stopImmediatePropagation();openD("证据链","报价与官方参考快照",snapHtml(b.dataset.sids.split(",").map(Number).concat([M.fx.sid]))+\'<p style="font-size:12.5px;color:var(--ink-3);margin-top:16px">此为算术比值，不构成对该渠道的任何指控。</p>\');},true);</script>'
              % (MEDIA_JS,))
    return html.replace("</script>", "</script>\n" + inject, 1) if False else html + "\n" + inject


def main():
    out = os.path.join(HERE, "index.html")
    html = _inject_media_into_index(build_index())
    io.open(out, "w", encoding="utf-8").write(html)
    sd = os.path.join(HERE, "s"); os.makedirs(sd, exist_ok=True)
    n = 0; total = 0
    for s in D["sites"]:
        h = build_site(s); total += len(h)
        io.open(os.path.join(sd, s["domain"] + ".html"), "w", encoding="utf-8").write(h); n += 1
    mp = build_media_page()
    if mp: io.open(os.path.join(HERE, "media.html"), "w", encoding="utf-8").write(mp)
    base = "https://compute.sinanlab.com"
    io.open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8").write("User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % base)
    urls = [base + "/", base + "/media.html"] + [base + "/s/%s.html" % x["domain"] for x in D["sites"]]
    io.open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join("  <url><loc>%s</loc><changefreq>daily</changefreq></url>\n" % u for u in urls) + "</urlset>\n")
    io.open(os.path.join(HERE, "favicon.svg"), "w", encoding="utf-8").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="8" fill="#0B0F14"/><circle cx="20" cy="20" r="14" fill="none" stroke="#2A3644" stroke-width="1.5"/><path d="M20 9 L24.5 20 L20 31 Z" fill="#4FD1D9"/><path d="M20 9 L15.5 20 L20 31 Z" fill="#2A3644"/><circle cx="20" cy="20" r="2.2" fill="#0B0F14" stroke="#4FD1D9" stroke-width="1.4"/></svg>')
    print("index.html %d KB · 站点页 %d 个（均 %d KB）· media.html %s" % (os.path.getsize(out) // 1024, n, total // max(n, 1) // 1024, "%d KB" % (len(mp) // 1024) if mp else "—"))

if __name__ == "__main__":
    main()
