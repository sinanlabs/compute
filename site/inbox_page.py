# -*- coding: utf-8 -*-
"""
来信箱页面：把 hello@sinanlab.com 收到的所有来信 + 我们的回信做成一个本机网页，给 Eric 直接看（2026-10-13 起）。

Eric 的要求：来信不转发到他邮箱，在 Claude 对话里贴原文；但翻对话找旧信太累 → 做一个随时能打开的"来信箱"。
页面只写在本机（/Users/eric/SinanLab/来信箱.html），不上线：里面有发件人邮箱。密钥在收信时已打码。
值班脚本 inbox_duty.py 每次 show / reply / mark 后自动重写这个页面，不用单独跑。
手动刷新：python3 site/inbox_page.py
"""
import os, io, re, glob, html, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(os.path.dirname(ROOT), "来信箱.html")
SENT = os.path.join(ROOT, "data", "mail")
BJ = dt.timezone(dt.timedelta(hours=8))

# 状态 → (分组, 显示文字, 颜色类)
STATUS = {
    "waiting_owner": (0, "等你拍板", "red"),
    "new": (1, "待处理", "amber"), "triaged": (1, "待处理", "amber"), "error": (1, "待处理·存档出错", "amber"),
    "replied": (2, "已回复", "green"),
    "closed": (3, "已办结", "gray"), "ignored": (3, "不用回（垃圾/通知）", "gray"),
}
GROUPS = ["等你拍板", "还没处理", "已回复", "不用回 / 已办结"]
CATEGORY = {"key": "发来 Key", "correction": "数据纠错", "verify": "申请核验", "takedown": "要求下架", "press": "媒体",
            "partner": "合作/推广", "spam": "垃圾/推销", "other": "其他"}   # 与 inbox_triage.RULES 对应；只是关键词初判


def bj_full(utc_str):
    try:
        t = dt.datetime.strptime((utc_str or "")[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
        return t.astimezone(BJ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return utc_str or "?"


def load_replies():
    """data/mail/reply_*.txt → {(id 或 None, 收件人小写): [(时间, 正文)]}。2026-10-13 前的回信文件名用站名，只能按收件人对。"""
    by_id, by_to = {}, {}
    for p in sorted(glob.glob(os.path.join(SENT, "reply_*.txt"))):
        try:
            t = io.open(p, encoding="utf-8").read()
        except Exception:
            continue
        has_hdr = t.startswith("To:")
        to = (re.search(r"^To:\s*(.+)$", t, re.M) or [None, ""])[1].strip().lower() if has_hdr else ""
        body = t.split("\n\n", 1)[1] if has_hdr and "\n\n" in t else t
        item = (dt.datetime.fromtimestamp(os.path.getmtime(p), BJ).strftime("%Y-%m-%d %H:%M"), body.strip())
        mm = re.match(r"reply_(\d+)_", os.path.basename(p))
        nm = re.match(r"reply_([a-z0-9.-]+?)_\d{8}", os.path.basename(p))
        if mm: by_id.setdefault(int(mm.group(1)), []).append(item)
        elif to: by_to.setdefault(to, []).append(item)
        elif nm: by_to.setdefault("name:" + nm.group(1), []).append(item)   # 09 月的老回信：文件名只有站名、没有收件人
    return by_id, by_to


def esc(s): return html.escape(s or "", quote=True)


def build(rows, clean, split_quote, is_self):
    by_id, by_to = load_replies()
    used_to = set()
    groups = {i: [] for i in range(len(GROUPS))}
    for m in sorted(rows, key=lambda r: -int(r["id"])):
        if is_self(m.get("from_addr")): continue
        g, label, color = STATUS.get(m.get("status") or "", (1, m.get("status") or "?", "amber"))
        frm = (m.get("from_addr") or "").lower()
        reps = list(by_id.get(int(m["id"]), []))
        if not reps and frm in by_to and frm not in used_to:   # 旧格式回信：同一收件人的回信挂在最新那封上
            reps = by_to[frm]; used_to.add(frm)
        if not reps:
            hay = ((m.get("subject") or "") + " " + (m.get("site") or "")).lower()
            for k in by_to:
                if k.startswith("name:") and k[5:] in hay and k not in used_to:
                    reps = by_to[k]; used_to.add(k); break
        new, quoted = split_quote(clean(m.get("body_text") or ""))
        cat = CATEGORY.get(m.get("category") or "", m.get("category") or "")
        note = m.get("note") or ""
        search = " ".join([m.get("from_name") or "", frm, m.get("subject") or "", m.get("site") or "", new[:3000]]).lower()
        parts = ['<details class="mail" data-s="%s"%s><summary>' % (esc(search), " open" if g == 0 else ""),
                 '<span class="tag %s">%s</span>' % (color, esc(label)),
                 '<span class="subj">%s</span>' % esc(m.get("subject") or "(无主题)"),
                 '<span class="meta">#%d · %s · %s</span>' % (int(m["id"]), esc(m.get("from_name") or frm), bj_full(m.get("received_at"))),
                 '</summary><div class="body">',
                 '<p class="info">发件人：%s &lt;%s&gt; · 北京时间 %s%s%s</p>' % (
                     esc(m.get("from_name") or ""), esc(frm), bj_full(m.get("received_at")),
                     " · 类别：%s" % esc(cat) if cat else "", " · 对应站：%s" % esc(m.get("site")) if m.get("site") else "")]
        if note and g in (0, 3):
            parts.append('<div class="note"><b>%s</b>%s</div>' % ("我的建议：" if g == 0 else "说明：", esc(note)))
        parts.append('<h4>对方来信</h4><pre>%s</pre>' % esc(new[:20000] or "（正文为空）"))
        if quoted:
            parts.append('<details class="quoted"><summary>信里引用的之前往来（%d 字）</summary><pre>%s</pre></details>' % (len(quoted), esc(quoted[:20000])))
        if m.get("attachments"):
            parts.append('<p class="info">附件（只记了文件名，没下载）：%s</p>' % esc(m["attachments"]))
        for when, body in reps:
            parts.append('<h4>我们的回信 · %s</h4><pre class="reply">%s</pre>' % (when, esc(body)))
        if g == 2 and not reps:
            parts.append('<p class="info">已回复（这封的回信正文没有存档）。</p>')
        parts.append("</div></details>")
        groups[g].append("".join(parts))

    now = dt.datetime.now(BJ).strftime("%Y-%m-%d %H:%M")
    total = sum(len(v) for v in groups.values())
    secs = []
    for i, name in enumerate(GROUPS):
        if not groups[i] and i != 0: continue
        inner = "".join(groups[i]) or '<p class="empty">没有要你拍板的信。</p>'
        secs.append('<section><h2>%s <span class="n">%d</span></h2>%s</section>' % (name, len(groups[i]), inner))
    return TEMPLATE.replace("{{NOW}}", now).replace("{{TOTAL}}", str(total)).replace("{{WAIT}}", str(len(groups[0]))).replace("{{SECTIONS}}", "".join(secs))


TEMPLATE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>司南来信箱</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--mute:#6b7383;--line:#e3e6eb;--red:#c62f2f;--redbg:#fdecec;--amber:#a05a00;--amberbg:#fff3df;
--green:#1f7a44;--greenbg:#e5f5eb;--gray:#6b7383;--graybg:#eef0f3;--replybg:#f1f6ff;--notebg:#fff8e6}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--ink:#e6e8ec;--mute:#9aa2b1;--line:#2c323c;--red:#ff7b7b;--redbg:#3a1f22;
--amber:#f0b45a;--amberbg:#3a2e1a;--green:#6fd59a;--greenbg:#1b3326;--gray:#9aa2b1;--graybg:#262b33;--replybg:#1c2636;--notebg:#2e2a1c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,"PingFang SC","Hiragino Sans GB",sans-serif}
main{max-width:900px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mute);font-size:13px;margin:0 0 16px}
input{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font-size:15px;margin-bottom:8px}
h2{font-size:16px;margin:28px 0 10px}.n{color:var(--mute);font-weight:normal}
.mail{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:8px 0}
.mail>summary{cursor:pointer;padding:12px 14px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline;list-style:none}
.mail>summary::-webkit-details-marker{display:none}
.subj{font-weight:600;flex:1 1 300px;min-width:0;overflow-wrap:anywhere}.meta{color:var(--mute);font-size:13px}
.tag{font-size:12px;padding:2px 8px;border-radius:99px;white-space:nowrap}
.red{color:var(--red);background:var(--redbg)}.amber{color:var(--amber);background:var(--amberbg)}
.green{color:var(--green);background:var(--greenbg)}.gray{color:var(--gray);background:var(--graybg)}
.body{padding:0 14px 14px;border-top:1px solid var(--line)}
h4{margin:14px 0 6px;font-size:14px;color:var(--mute)}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.65 inherit;font-family:inherit;margin:0;padding:10px 12px;border-radius:8px;background:var(--bg)}
pre.reply{background:var(--replybg)}.info{color:var(--mute);font-size:13px;margin:10px 0 0}
.note{margin-top:12px;padding:10px 12px;border-radius:8px;background:var(--notebg);font-size:14px}
.quoted{margin-top:8px}.quoted>summary{cursor:pointer;color:var(--mute);font-size:13px}
.empty{color:var(--mute)}
</style></head><body><main>
<h1>司南来信箱</h1>
<p class="sub">hello@sinanlab.com 收到的全部来信，共 {{TOTAL}} 封，等你拍板 {{WAIT}} 封 · 更新于 {{NOW}} 北京 · 每次值班（北京 9/13/17/21 点）自动更新 · 密钥已打码 · 只存在本机</p>
<p class="sub">要拍板的事，去 Claude 的「司南来信值班」对话里回一句就行。</p>
<input id="q" placeholder="搜索：发件人、站名、关键词">
{{SECTIONS}}
</main>
<script>
document.getElementById('q').addEventListener('input',function(){var v=this.value.trim().toLowerCase();
document.querySelectorAll('.mail').forEach(function(d){var hit=!v||d.dataset.s.indexOf(v)>=0;d.style.display=hit?'':'none';if(v&&hit)d.open=true;});});
</script></body></html>"""


def write():
    import sys
    sys.path.insert(0, HERE)
    import inbox_triage as T
    import inbox_duty as I
    rows = T.d1("SELECT id, from_addr, from_name, subject, received_at, status, category, site, note, body_text, attachments FROM inbox_mail ORDER BY id")
    io.open(OUT, "w", encoding="utf-8").write(build(rows, I.clean, I.split_quote, T.is_self))
    return OUT


if __name__ == "__main__":
    print("来信箱已更新：" + write())
