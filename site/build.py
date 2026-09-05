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
CSS = re.search(r"<style>(.*?)</style>", _old, re.S).group(1)
CSS += """
.vgroup{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.vgroup .vn{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);font-family:"IBM Plex Mono",monospace;min-width:70px}
.chip.latest{border-color:var(--accent);color:var(--accent)}
.chip .n{opacity:.7}
details.fold{border-top:1px dashed var(--line);background:var(--surface-2)}
details.fold summary{padding:10px 16px;font-size:13px;color:var(--ink-2);cursor:pointer;list-style:none;display:flex;gap:10px;align-items:center}
details.fold summary::before{content:"▸";color:var(--ink-3)} details.fold[open] summary::before{content:"▾"}
.help{display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;border:1px solid var(--line);color:var(--ink-3);font-size:10px;cursor:pointer;margin-left:4px;background:var(--surface)}
.help:hover{border-color:var(--accent);color:var(--accent)}
.evb{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--line);border-radius:6px;padding:2px 8px;font-size:11.5px;color:var(--ink-2);background:var(--surface-2);cursor:pointer;font-family:"IBM Plex Mono",monospace}
.evb:hover{border-color:var(--accent);color:var(--accent)}
.asof{font-size:11px;color:var(--ink-3);font-family:"IBM Plex Mono",monospace;display:block;margin-top:2px}
.calc{display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:10px 16px;border-bottom:1px solid var(--line-soft);background:var(--surface-2);font-size:13px}
.calc label{display:flex;gap:6px;align-items:center;color:var(--ink-2)}
.calc input{width:80px;border:1px solid var(--line);border-radius:6px;padding:4px 8px;font:inherit;font-family:"IBM Plex Mono",monospace;background:var(--surface);color:var(--ink)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center}
.fchip{border:1px solid var(--line);background:var(--surface);color:var(--ink-2);font:inherit;font-size:12.5px;padding:5px 11px;border-radius:999px;cursor:pointer}
.fchip[aria-pressed="true"]{background:var(--ink);color:var(--surface);border-color:var(--ink)}
.cl{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;padding:2px 9px;border-radius:999px;font-family:"IBM Plex Mono",monospace;white-space:nowrap}
.cl.ultra{background:var(--crit-soft);color:var(--crit)} .cl.cheap{background:var(--warn-soft);color:var(--warn)}
.cl.near{background:var(--good-soft);color:var(--good)} .cl.high,.cl.held{background:var(--surface-2);color:var(--ink-3);border:1px solid var(--line)}
.up{font-family:"IBM Plex Mono",monospace} .up.good{color:var(--good)} .up.bad{color:var(--crit)}
a.dom{color:var(--ink);text-decoration:none;font-family:"IBM Plex Mono",monospace;font-weight:600} a.dom:hover{color:var(--accent);text-decoration:underline}
.go{display:inline-flex;align-items:center;gap:6px;background:var(--accent);color:#fff;border-radius:7px;padding:7px 14px;text-decoration:none;font-weight:600;font-size:13.5px}
.go:hover{background:var(--accent-2)}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.fact{padding:12px 14px} .fact .k{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-family:"IBM Plex Mono",monospace}
.fact .v{font-size:15px;margin-top:3px} .fact .n{font-size:12px;color:var(--ink-3);margin-top:2px}
.crumb{font-size:12.5px;color:var(--ink-3);margin-bottom:14px} .crumb a{color:var(--ink-3)}
.sitehead{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;margin-bottom:18px}
.sitehead h2{font-size:26px;font-family:"IBM Plex Mono",monospace}
.sitehead .sub{color:var(--ink-2);font-size:14px;margin-top:4px}
.notice{border-left:3px solid var(--warn);background:var(--warn-soft);color:var(--warn);padding:10px 14px;border-radius:0 7px 7px 0;font-size:13px;margin-bottom:14px}
.callout{border-left:3px solid var(--accent);background:var(--surface-2);padding:11px 14px;border-radius:0 7px 7px 0;font-size:13px;color:var(--ink-2);margin:12px 0}
.hide{display:none}
@media (max-width:900px){.facts{grid-template-columns:1fr 1fr}}
"""

HEAD = u"""<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>%s</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>%s</style>"""

def header(rel=""):
    return u"""<header class="top"><div class="wrap"><div class="bar">
  <a class="brand" href="%sindex.html" style="text-decoration:none;color:inherit"><svg width="28" height="28" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="17" fill="none" stroke="var(--line)" stroke-width="1.5"/><path d="M20 9 L24 20 L20 31 Z" fill="var(--accent)"/><path d="M20 9 L16 20 L20 31 Z" fill="var(--ink-3)" opacity=".45"/><circle cx="20" cy="20" r="2" fill="var(--surface)" stroke="var(--accent)" stroke-width="1.5"/></svg>
  <div><h1>算力罗盘</h1><div class="sub">relay &amp; model api intel</div></div></a>
  <form class="search" onsubmit="return goSearch()" role="search"><input id="q" type="search" placeholder="查一个站（如 toapis.cn）或一个模型（如 DeepSeek V4）" aria-label="搜索" list="qlist"><datalist id="qlist"></datalist><button type="submit">查</button></form>
</div><div class="pledge"><span><b>不收任何人的钱</b>——没有付费墙、没有返佣、没有认证费</span><span><b>每个数字可点证据</b>——来源、抓取时间、快照哈希</span><span><b>只给事实不给推荐</b>——判断留给你</span></div></div></header>""" % rel

DRAWER = u"""<div class="scrim" id="scrim"></div><aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="详情"><button class="close" id="dclose" aria-label="关闭">×</button><div class="eyebrow" id="deye">证据链</div><h3 id="dtitle" style="font-size:17px"></h3><div id="dbody"></div></aside>"""

COMMON_JS = u"""
var KIND={official:"官方",marketplace:"公开市场",relay:"中转站"};
var LABEL={unsustainable:"数学上不可持续",below_bulk:"低于常见批量折扣",explainable:"可由批量折扣解释",normal:"与公开价接近",premium:"高于公开价",far_above:"显著高于公开价"};
function fmt(x){return x==null?"—":(x<1?x.toFixed(3):x.toFixed(2));}
function pct(r){if(r==null)return "—";var p=r*100;return (p<10?p.toFixed(1):p.toFixed(0))+"%";}
var drawer=document.getElementById("drawer"),scrim=document.getElementById("scrim");
function openD(eye,title,html){document.getElementById("deye").textContent=eye;document.getElementById("dtitle").textContent=title;document.getElementById("dbody").innerHTML=html;drawer.classList.add("on");scrim.classList.add("on");}
function closeD(){drawer.classList.remove("on");scrim.classList.remove("on");}
scrim.addEventListener("click",closeD);document.getElementById("dclose").addEventListener("click",closeD);document.addEventListener("keydown",function(e){if(e.key==="Escape")closeD();});
function snapHtml(sids){var h="";sids.forEach(function(s){var ev=D.snaps[String(s)];if(!ev)return;h+='<div class="snap"><div class="mono" style="font-size:11px;color:var(--ink-3)">快照 #'+ev.id+' · '+ev.source+'</div><div class="mono" style="font-size:12px;word-break:break-all;margin-top:3px">'+ev.url+'</div><div class="mono" style="font-size:11px;color:var(--ink-3);margin-top:3px">'+ev.fetched_at+' · sha256:'+ev.sha256.slice(0,16)+'…</div></div>';});return h;}
function helpHtml(code){return '<p style="font-size:14px;line-height:1.7">'+(D.label_help[code]||"")+'</p><p style="font-size:12.5px;color:var(--ink-3);margin-top:12px">分档只是算术区间：&lt;15% 不可持续 · 15–40% 低于折扣 · 40–75% 可由折扣解释 · 75–125% 接近 · 125–300% 溢价 · &gt;300% 显著高于。</p>';}
function relayEvidence(row,model){var f=model.floor;var h='<dl class="kv"><dt>名义价</dt><dd>'+fmt(row.nominal_out)+' USD/百万输出（面板倍率 × $2/M）</dd><dt>充值比例</dt><dd>'+row.price_field+' 元 / $1（面板 price 字段）'+(row.stripe!=null&&row.stripe!=8?'；另有 Stripe 通道 '+row.stripe+' 美元/$1':'')+'</dd><dt>汇率</dt><dd>'+D.fx.rate.toFixed(4)+'（'+D.fx.as_of+'）</dd><dt>实付</dt><dd>'+fmt(row.nominal_out)+' × '+row.price_field+' ÷ '+D.fx.rate.toFixed(2)+' = '+fmt(row.out)+' USD</dd><dt>参考价</dt><dd>'+f.vendor+' '+fmt(f.out)+' USD'+(f.cny?'（'+f.cny+' 元折算）':'')+'</dd><dt>比率</dt><dd>'+fmt(row.out)+' ÷ '+fmt(f.out)+' = '+pct(row.ratio)+'</dd></dl>';h+=snapHtml(row.sids.concat([f.sid,D.fx.sid]));h+='<p style="font-size:12.5px;color:var(--ink-3);margin-top:16px;border-top:1px solid var(--line-soft);padding-top:12px">此为算术比值，不构成对该渠道的任何指控，也不排除存在本站未收录的更低公开来源。</p>';return h;}
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
             "changes": D["changes"], "new_sites": D["new_sites"], "stats": st, "generated_at": D["generated_at"], "probe_node": D["probe_node"],
             "sites_full": {s["domain"]: {"name": s["name"], "site_url": s["site_url"], "first_seen": s["first_seen"], "channel": s["channel"], "panel": s["panel"],
                                          "version": s["version"], "cluster": s["cluster"], "median": s["median"], "avail": s["avail"], "facts": s["facts"],
                                          "ok": s["ok_count"], "un": s["un_count"],
                                          "models": [{"name": r["name"], "raw": r["raw"], "out": r["out"], "call": r["call"], "sec": r["sec"], "ratio": r["ratio"],
                                                      "band": r["band"], "floor_out": r.get("floor_out"), "mtype": r["mtype"], "sids": r["sids"], "as_of": r["as_of"]} for r in s["models"]]}
                            for s in D["sites"]}}
    body = u"""%s
<main class="wrap">
<section class="sec">
  <div class="sechead"><h2>你要用哪个模型？</h2><span class="q">官方价、公开市场价、中转站实付价同一张表。先看解释得通的，再看便宜得离谱的。</span><span class="right" id="asof"></span></div>
  <div id="chipgroups"></div>
  <div class="card">
    <div class="calc"><b>按你的用量算</b><label>月输入 <input id="c-in" type="number" min="0" step="1" value="50"> 百万 token</label><label>月输出 <input id="c-out" type="number" min="0" step="1" value="10"> 百万 token</label><span style="color:var(--ink-3)">→ 表里多一列「你的月成本」</span></div>
    <div class="tablewrap"><table id="tbl"><thead><tr><th>渠道</th><th>类型</th><th class="num">输出 $/百万</th><th class="num">输入 $/百万</th><th class="num">你的月成本</th><th class="num">相对参考价</th><th>判读</th><th>可用性</th><th>证据</th></tr></thead><tbody></tbody></table></div>
    <div id="folds"></div>
    <div class="foot" id="tblfoot"></div>
  </div>
</section>

<section class="sec">
  <div class="sechead"><h2>你在用的站靠谱吗？</h2><span class="q">%d 个已确认站点，每站一页事实清单。不打分、不推荐。</span></div>
  <div class="grid g4" id="stats"></div>
  <div class="filters" id="filters" style="margin-top:14px"></div>
  <div class="card"><div class="tablewrap"><table id="sitetbl"><thead><tr><th>站</th><th>画像</th><th class="num">卖几个模型</th><th class="num">解释得通 / 不可持续</th><th>24h 可达</th><th class="num">延迟</th><th>首次收录</th><th></th></tr></thead><tbody></tbody></table></div><div class="foot" id="sitefoot"></div></div>
</section>

<section class="sec">
  <div class="sechead"><h2>今天变了什么</h2><span class="q">新收录的站、真实的价格变动。变更流从 2026-09-01 起累计。</span></div>
  <div class="card feed" id="feed"></div>
</section>

<section class="sec">
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
<script id="data" type="application/json">%s</script>
<script>
var REL="";var D=JSON.parse(document.getElementById("data").textContent);
%s
document.getElementById("asof").textContent="数据 "+D.generated_at.slice(0,16).replace("T"," ")+" · 汇率 USD/CNY "+D.fx.rate.toFixed(2);
/* chips grouped by vendor */
var cur=(location.hash.match(/m=([^&]+)/)||[])[1]||(D.models[0]&&D.models[0].id);
var cg=document.getElementById("chipgroups");
Object.keys(D.groups).forEach(function(v){var g=document.createElement("div");g.className="vgroup";g.innerHTML='<span class="vn">'+(D.vendor_name[v]||v)+'</span>';D.groups[v].forEach(function(id){var m=D.models.filter(function(x){return x.id===id;})[0];if(!m)return;var b=document.createElement("button");b.className="chip"+(m.is_latest?" latest":"");b.dataset.id=id;b.innerHTML=m.name+'<span class="n">'+m.n_relay+' 家</span>';b.addEventListener("click",function(){cur=id;location.hash="m="+id;render();});g.appendChild(b);});cg.appendChild(g);});
var off=document.createElement("div");off.className="vgroup";off.innerHTML='<span class="vn">视频</span><span class="chip off">Seedance / Kling / Veo / Wan · 按秒可比仅 1 站，接入中</span>';cg.appendChild(off);
function usage(){return {i:+document.getElementById("c-in").value||0,o:+document.getElementById("c-out").value||0};}
function monthly(inp,outp){var u=usage();if(inp==null||outp==null)return null;return inp*u.i+outp*u.o;}
function rowHtml(r,m,i){var mc=monthly(r.in,r.out);var up=r.uptime==null?'<span class="up">—</span>':'<span class="up '+(r.uptime>=90?"good":r.uptime<50?"bad":"")+'">'+r.uptime.toFixed(0)+'%%</span>';return '<tr><td><a class="dom" href="s/'+r.vendor+'.html">'+r.vendor+'</a>'+(r.name?'<div style="font-size:11.5px;color:var(--ink-3)">'+r.name+'</div>':'')+'</td><td><span class="kind">中转站</span></td><td class="num bigout">'+fmt(r.out)+'<span class="asof">抓取 '+r.as_of.slice(5).replace("T"," ")+'</span></td><td class="num">'+fmt(r.in)+'</td><td class="num">'+(mc==null?"—":"$"+mc.toFixed(mc<10?2:0))+'</td><td class="num"><span class="ratio '+r.band+'">'+pct(r.ratio)+'</span></td><td><span class="pill '+r.band+'"><span class="dot"></span>'+LABEL[r.band]+'</span><button class="help" data-help="'+r.band+'" aria-label="解释">?</button></td><td>'+up+'</td><td><button class="evb" data-m="'+m.id+'" data-i="'+i+'">证据 ↗</button></td></tr>';}
function render(){document.querySelectorAll(".chip[data-id]").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.id===cur?"true":"false");});var m=D.models.filter(function(x){return x.id===cur;})[0];if(!m)return;var tb=document.querySelector("#tbl tbody");var f=m.floor;var fmc=monthly(f.in,f.out);tb.innerHTML='<tr class="floor"><td><b class="mono">'+f.vendor+'</b></td><td><span class="kind">'+(f.cny?"官方":"公开市场")+'</span></td><td class="num bigout">'+fmt(f.out)+'</td><td class="num">'+fmt(f.in)+'</td><td class="num">'+(fmc==null?"—":"$"+fmc.toFixed(fmc<10?2:0))+'</td><td class="num"><span class="mono" style="color:var(--ink-3)">1.00×</span></td><td><span class="pill ref"><span class="dot"></span>参考价</span></td><td>—</td><td><button class="evb" data-f="'+m.id+'">证据 ↗</button></td></tr>';
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
var S=D.stats,st=document.getElementById("stats");[["已确认站点",S.confirmed,"每站一页事实清单"],["有报价的站",S.with_quotes,"其余只有面板指纹"],["24h 可达",S.reachable,"心跳探针 · "+D.probe_node],["在库报价",S.quotes.toLocaleString(),"全部带快照"]].forEach(function(x){var d=document.createElement("div");d.className="card stat";d.innerHTML='<div class="k">'+x[0]+'</div><div class="v">'+x[1]+'</div><div class="n">'+x[2]+'</div>';st.appendChild(d);});
/* site table with filters */
var CLN={ultra:"超低价",cheap:"两三折",near:"贴官方",high:"高价",held:"待核"};var filt="all",onlyQ=true;
var fl=document.getElementById("filters");[["all","全部"],["near","贴官方 "+S.clusters.near],["cheap","两三折 "+S.clusters.cheap],["ultra","超低价 "+S.clusters.ultra],["high","高价 "+S.clusters.high],["held","待核 "+S.clusters.held]].forEach(function(x){var b=document.createElement("button");b.className="fchip";b.dataset.f=x[0];b.textContent=x[1];b.setAttribute("aria-pressed",x[0]==="all"?"true":"false");b.addEventListener("click",function(){filt=x[0];renderSites();});fl.appendChild(b);});
var tg=document.createElement("button");tg.className="fchip";tg.style.marginLeft="auto";tg.textContent="也显示没报价的站";tg.addEventListener("click",function(){onlyQ=!onlyQ;tg.setAttribute("aria-pressed",onlyQ?"false":"true");renderSites();});fl.appendChild(tg);
function renderSites(){document.querySelectorAll(".fchip[data-f]").forEach(function(c){c.setAttribute("aria-pressed",c.dataset.f===filt?"true":"false");});var rows=D.sites.filter(function(s){if(onlyQ&&!s.nm)return false;if(filt==="all")return true;return s.cl&&s.cl.code===filt;});var tb=document.querySelector("#sitetbl tbody");tb.innerHTML=rows.slice(0,150).map(function(s){var up=s.up==null?"—":'<span class="up '+(s.up>=90?"good":s.up<50?"bad":"")+'">'+s.up.toFixed(0)+'%%</span>';return '<tr><td><a class="dom" href="s/'+s.d+'.html">'+s.d+'</a>'+(s.n?'<div style="font-size:11.5px;color:var(--ink-3)">'+s.n+'</div>':'')+'</td><td>'+(s.cl?'<span class="cl '+s.cl.code+'">'+s.cl.name+(s.med!=null&&s.cl.code!=="held"?' · 中位 '+pct(s.med):'')+'</span>':'<span class="cl held">无比对</span>')+'</td><td class="num">'+s.nm+'</td><td class="num"><span style="color:var(--good)">'+s.ok+'</span> / <span style="color:var(--crit)">'+s.un+'</span></td><td>'+up+'</td><td class="num">'+(s.ms?s.ms+"ms":"—")+'</td><td class="mono" style="font-size:12px">'+s.fs+'</td><td><a class="go" style="padding:4px 10px;font-size:12px" href="s/'+s.d+'.html">详情</a></td></tr>';}).join("");document.getElementById("sitefoot").innerHTML='<span>显示 '+Math.min(rows.length,150)+' / '+rows.length+' 站'+(rows.length>150?"（用搜索框直达其他站）":"")+'</span><span>画像 = 该站所有可比模型的输出价相对公开价的中位数</span>';}
renderSites();
/* feed */
var feed=document.getElementById("feed");var items=[];if(D.new_sites.length)items.push({t:D.generated_at,text:"今日新收录 <b>"+D.new_sites.length+"</b> 个站",sub:D.new_sites.slice(0,12).join(" · ")+(D.new_sites.length>12?" …":"")});
D.changes.forEach(function(c){var up=c.new>c.old;items.push({t:c.t,text:c.vendor+" · "+c.model+" 输出价 <span class=\\"old\\">"+fmt(c.old)+"</span> → <span class=\\"new\\">"+fmt(c.new)+"</span>"+(c.kind==="relay"?" 名义$/百万":" $/百万")+(up?" ↑":" ↓"),sub:c.kind==="relay"?"中转站":"公开参考价"});});
if(!items.length)items.push({t:D.generated_at,text:"今天没有价格变动",sub:"变更流从 2026-09-01 起累计"});
items.slice(0,12).forEach(function(f){var r=document.createElement("div");r.className="row";r.innerHTML='<div class="t">'+f.t.slice(5,16).replace("T"," ")+'</div><div class="b">'+f.text+'<div class="sub">'+(f.sub||"")+'</div></div>';feed.appendChild(r);});
</script>""" % (header(""), st["confirmed"], DRAWER, json.dumps(light, ensure_ascii=False).replace("</", "<\\/"), COMMON_JS)
    return HEAD % ("算力罗盘", CSS) + body

# ---------------- per-site page ----------------
def build_site(s):
    lite = {"fx": D["fx"], "snaps": {k: v for k, v in D["snaps"].items()}, "label_help": D["label_help"], "site_index": [{"d": x["domain"], "n": x["name"]} for x in D["sites"]],
            "model_index": [{"id": m["id"], "name": m["name"]} for m in D["models"]], "site": s}
    f = s["facts"] or {}; av = s.get("avail") or {}
    cl = s["cluster"]
    price_note = ""
    if f.get("price") is not None:
        price_note = "%s 元 / $1 名义额度" % f["price"] + ("（Stripe 通道 %s 美元/$1）" % f["stripe"] if f.get("stripe") not in (None, 8, 8.0) else "")
    rows_html = []
    for r in s["models"]:
        unit = "输出 $/百万" if r["out"] is not None else ("$/次" if r["call"] is not None else ("$/秒" if r["sec"] is not None else ""))
        val = r["out"] if r["out"] is not None else (r["call"] if r["call"] is not None else r["sec"])
        ratio = ("<span class='ratio %s'>%s</span>" % (r["band"], ("%.1f%%" % (r["ratio"]*100)) if r["ratio"] < 0.1 else ("%.0f%%" % (r["ratio"]*100)))) if r["ratio"] is not None else "—"
        judge = ("<span class='pill %s'><span class='dot'></span>%s</span><button class='help' data-help='%s'>?</button>" % (r["band"], {"unsustainable":"数学上不可持续","below_bulk":"低于常见批量折扣","explainable":"可由批量折扣解释","normal":"与公开价接近","premium":"高于公开价","far_above":"显著高于公开价"}[r["band"]], r["band"])) if r["band"] else "<span class='pill normal'>无公开参考价</span>"
        mt = {"text": "文本", "image": "图像", "video": "视频"}.get(r["mtype"] or "", "")
        rows_html.append("<tr><td><b>%s</b><div style='font-size:11.5px;color:var(--ink-3)'>%s%s</div></td><td class='num bigout'>%s<span class='asof'>%s</span></td><td class='num'>%s</td><td class='num'>%s</td><td>%s</td><td><button class='evb' data-sids='%s'>证据 ↗</button></td></tr>" % (
            esc(r["name"]), esc(r["raw"]), (" · " + mt) if mt else "", ("%.3f" % val) if val is not None else "—", unit + " · 抓取 " + r["as_of"][5:].replace("T", " "),
            ("%.2f" % r["floor_out"]) if r.get("floor_out") else "—", ratio, judge, ",".join(map(str, r["sids"]))))
    held_note = "<div class='notice'>该站全线报价与公开价差距异常，大概率是面板倍率基数与上游不同。我们只列它的名义报价，不出比率结论，等核实基数后再放行。</div>" if cl and cl["code"] == "held" else ""
    body = u"""%s
<main class="wrap">
<div class="crumb"><a href="../index.html">首页</a> › 站点 › %s</div>
<div class="sitehead"><div><h2>%s</h2><div class="sub">%s%s</div></div><div style="margin-left:auto;display:flex;gap:10px;align-items:center">%s<a class="go" href="%s" rel="noopener nofollow" target="_blank">前往站点 →</a></div></div>
%s
<div class="facts">
  <div class="card fact"><div class="k">价格画像</div><div class="v">%s</div><div class="n">%s</div></div>
  <div class="card fact"><div class="k">24h 可达</div><div class="v">%s</div><div class="n">%s</div></div>
  <div class="card fact"><div class="k">在卖模型</div><div class="v">%d 个</div><div class="n">解释得通 %d · 不可持续 %d</div></div>
  <div class="card fact"><div class="k">充值比例</div><div class="v" style="font-size:14px">%s</div><div class="n">面板 price 字段，决定实付</div></div>
  <div class="card fact"><div class="k">登录方式</div><div class="v" style="font-size:14px">%s</div><div class="n">%s</div></div>
  <div class="card fact"><div class="k">面板</div><div class="v" style="font-size:14px">%s</div><div class="n">%s</div></div>
  <div class="card fact"><div class="k">首次收录</div><div class="v" style="font-size:14px">%s</div><div class="n">来源 %s</div></div>
</div>
<div class="callout"><b>怎么核实它是不是真模型：</b>本站不替你判断。用你在该站的 Key 跑开源的 tokenizer 指纹 / 协议一致性检测（我们的探针脚本或 Veridrop），十秒钟能看出输出分布是否与官方一致。</div>
<section class="sec" style="margin-top:22px"><div class="sechead"><h2 style="font-size:19px">它卖的模型与实付价</h2><span class="q">人民币充值通道实付 = 面板名义价 × 充值比例 ÷ 汇率 %.2f。按比率从低到高。</span></div>
<div class="card"><div class="tablewrap"><table><thead><tr><th>模型</th><th class="num">实付</th><th class="num">最低公开价</th><th class="num">相对参考价</th><th>判读</th><th>证据</th></tr></thead><tbody>%s</tbody></table></div></div></section>
</main>
%s
<script id="data" type="application/json">%s</script>
<script>var REL="../";var D=JSON.parse(document.getElementById("data").textContent);%s
document.addEventListener("click",function(e){var h=e.target.closest?e.target.closest(".help"):null;if(h){openD("这是什么意思",LABEL[h.dataset.help],helpHtml(h.dataset.help));return;}var b=e.target.closest?e.target.closest(".evb"):null;if(!b)return;openD("证据链","%s · 报价快照",snapHtml(b.dataset.sids.split(",").map(Number).concat([D.fx.sid]))+'<p style="font-size:12.5px;color:var(--ink-3);margin-top:16px">实付 = 名义 × '+(D.site.facts.price||"?")+' 元/$1 ÷ 汇率 '+D.fx.rate.toFixed(2)+'。此为算术比值，不构成对该渠道的任何指控。</p>');});</script>""" % (
        header("../"), esc(s["domain"]), esc(s["domain"]), esc(s["name"] or ""), (" · " + esc(f.get("version") or s.get("version") or "")) if (f.get("version") or s.get("version")) else "",
        ("<span class='cl %s'>%s</span>" % (cl["code"], cl["name"])) if cl else "", esc(s["site_url"] or ("https://%s/" % s["domain"])),
        held_note,
        (cl["name"] if cl else "无比对"), (("中位比率 %s · %s" % (("%.1f%%" % (s["median"]*100)) if s["median"] < 0.1 else ("%.0f%%" % (s["median"]*100)), cl["help"])) if cl and cl["code"] != "held" and s["median"] is not None else (cl["help"] if cl else "该站没有能对上公开参考价的模型")),
        ("%.0f%%" % av["uptime"]) if av.get("uptime") is not None else "—", ("延迟 p50 %sms · %d 次探测 · %s" % (av.get("ttfb_p50") or "—", av.get("n") or 0, D["probe_node"])) if av else "尚无探测数据",
        s["n_models"], s["ok_count"], s["un_count"],
        price_note or "未暴露", "、".join(f.get("login") or []) or "未暴露", ("需人机验证" if f.get("turnstile") else "无人机验证") + (" · 有签到" if f.get("checkin") else ""),
        esc(s.get("panel") or "—"), esc(f.get("version") or s.get("version") or ""), s["first_seen"], esc(s["channel"] or ""),
        D["fx"]["rate"], "".join(rows_html) or "<tr><td colspan='6' style='color:var(--ink-3)'>该站定价接口需登录或未暴露，暂无报价</td></tr>",
        DRAWER, json.dumps(lite, ensure_ascii=False).replace("</", "<\\/"), COMMON_JS, esc(s["domain"]))
    return HEAD % (s["domain"] + " · 算力罗盘", CSS) + body

def main():
    out = os.path.join(HERE, "index.html")
    io.open(out, "w", encoding="utf-8").write(build_index())
    sd = os.path.join(HERE, "s"); os.makedirs(sd, exist_ok=True)
    n = 0; total = 0
    for s in D["sites"]:
        html = build_site(s); total += len(html)
        io.open(os.path.join(sd, s["domain"] + ".html"), "w", encoding="utf-8").write(html); n += 1
    print("index.html %d KB · 站点页 %d 个（均 %d KB）" % (os.path.getsize(out) // 1024, n, total // max(n, 1) // 1024))

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
    var ratio = r.ratio!=null ? '<span class="ratio '+r.band+'">'+pct(r.ratio)+'</span>' : '—';
    var judge = r.band ? '<span class="pill '+r.band+'"><span class="dot"></span>'+LABEL[r.band]+'</span><button class="help" data-help="'+r.band+'">?</button>' : '<span class="pill normal">无参考</span>';
    var notes = [r.version_note, r.assumption].filter(Boolean).join("；");
    return '<tr><td><a class="dom" href="s/'+r.site+'.html">'+r.site+'</a></td><td><b>'+r.name+'</b>'+(r.version_label?' <span class="pill normal" style="font-size:10.5px">'+r.version_label+'</span>':'')+(notes?'<div style="font-size:11px;color:var(--ink-3)">'+notes+'</div>':'')+'</td><td class="num bigout">'+shown+'<span class="asof">'+(r.usd_direct?('该站直接美元标价'+(r.spec?' · '+r.spec:'')):('名义 '+r.nominal+' × '+r.price_field+' ÷ '+D.fx.rate.toFixed(2)))+' · 抓取 '+r.as_of.slice(5).replace("T"," ")+'</span></td><td class="num">'+ratio+'</td><td>'+judge+'</td><td><button class="evb" data-sids="'+r.sids.join(",")+(r.ref_sid?","+r.ref_sid:"")+'">证据 ↗</button></td></tr>';
  }
  function tbl(rows){return '<div class="tablewrap"><table><thead><tr><th>站</th><th>该站模型名</th><th class="num">实付</th><th class="num">相对官方</th><th>判读</th><th>证据</th></tr></thead><tbody>'+rows.map(row).join("")+'</tbody></table></div>';}
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
  <div class="sechead"><h2>图像与视频</h2><span class="q">中转站的图像/视频报价，与官方按张 / 按秒价放在一起。按次报价要折算，假设写在明面上。</span><span class="right" id="mediaasof"></span></div>
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
        header(""), MEDIA_SECTION, DRAWER, json.dumps(lite, ensure_ascii=False).replace("</", "<\\/"), json.dumps(MEDIA, ensure_ascii=False).replace("</", "<\\/"), COMMON_JS, MEDIA_JS)
    return HEAD % ("图像与视频 · 算力罗盘", CSS) + body


def _inject_media_into_index(html):
    """首页：在「你在用的站靠谱吗」之前插入媒体板块（单文件发布也能用）。"""
    if not MEDIA: return html
    marker = '<section class="sec">\n  <div class="sechead"><h2>你在用的站靠谱吗？</h2>'
    if marker not in html: return html
    html = html.replace(marker, MEDIA_SECTION + marker, 1)
    inject = ('<script id="mdata" type="application/json">%s</script>\n<script>var M=JSON.parse(document.getElementById("mdata").textContent);%s\n'
              'document.getElementById("mediaasof").textContent="数据 "+M.generated_at.slice(0,16).replace("T"," ");renderMedia("video");\n'
              'document.addEventListener("click",function(e){var b=e.target.closest?e.target.closest("#media .evb"):null;if(!b)return;e.stopImmediatePropagation();openD("证据链","报价与官方参考快照",snapHtml(b.dataset.sids.split(",").map(Number).concat([M.fx.sid]))+\'<p style="font-size:12.5px;color:var(--ink-3);margin-top:16px">此为算术比值，不构成对该渠道的任何指控。</p>\');},true);</script>'
              % (json.dumps(MEDIA, ensure_ascii=False).replace("</", "<\\/"), MEDIA_JS))
    return html.replace("</script>", "</script>\n" + inject, 1) if False else html + "\n" + inject


_orig_main = main
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
    print("index.html %d KB · 站点页 %d 个（均 %d KB）· media.html %s" % (os.path.getsize(out) // 1024, n, total // max(n, 1) // 1024, "%d KB" % (len(mp) // 1024) if mp else "—"))

if __name__ == "__main__":
    main()
