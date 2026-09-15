# -*- coding: utf-8 -*-
"""模态分类器：按模型名把 按次/按秒 计价的模型分成 image / video / audio / other。

只有 toapis 一家在 /api/pricing 里带 model_type，其余站要靠名字。规则按族谱写，
用 toapis 的真实标签当验证集（跑 python3 core/modality.py 看精度）。分不出来的归 other，不猜。
"""
from __future__ import unicode_literals
import re

VIDEO = [
    ("veo",      r"veo"),
    ("kling",    r"kling|可灵"),
    ("seedance", r"seedance"),
    ("wan",      r"\bwan(?:x)?[-_.]?\d|wan2|wan-?3|万相.*视频|wanx-v"),
    ("happyhorse", r"happyhorse"),
    ("vidu",     r"vidu(?!-image)|viduq"),
    ("hailuo",   r"hailuo|海螺|minimax-h3|minimax.*video|video-01"),   # 2026-09-14 教训：t2v/i2v 曾放在这里，把 wan/happyhorse 全判成海螺
    ("sora",     r"sora(?!.?image)"),
    ("runway",   r"runway|gen-?[34]"),
    ("luma",     r"luma|ray-?2|dream-machine"),
    ("pika",     r"pika"),
    ("hunyuan",  r"hunyuan.*video|hunyuanvideo"),
    ("cogvideo", r"cogvideo"),
    ("jimeng-video", r"jimeng.*(video|视频|v\d)|即梦.*视频"),
    ("grok-vid", r"grok-?imagine-?video|grok.*video"),
    ("pixverse", r"pixverse(?!.*(lipsync|lip-sync|template|extend|sound))"),
    ("omni",     r"omni-flash|gemini-omni"),        # Gemini Omni Flash：toapis 标为视频生成
    ("mj-video", r"mj[-_].*video|midjourney.*video"),
    ("generic",  r"video|视频|-vid\b|t2v|i2v|r2v"),
]
IMAGE = [
    ("gpt-image",   r"gpt-image|dall-?e|gpt-4o-image|gpt-?5.*image|sora[-_]?image"),
    ("nano-banana", r"nano-?banana|gemini.*image|imagen"),
    ("seedream",    r"seedream"),
    ("jimeng-image", r"jimeng|即梦|dreamina"),
    ("flux",        r"flux"),
    ("wan-image",   r"wan(?:x)?[-_.]?\d.*(image|t2i|i2i)|wan.*image"),
    ("z-image",     r"z-?image"),
    ("qwen-image",  r"qwen-?image|万相.*图"),
    ("kling-image", r"kling.*image|kolors"),
    ("cogview",     r"cogview"),
    ("midjourney",  r"midjourney|mj[-_]|niji"),
    ("sd",          r"stable-?diffusion|sdxl|sd3|sd-?3"),
    ("ideogram",    r"ideogram"),
    ("recraft",     r"recraft"),
    ("hidream",     r"hidream"),
    ("grok-image",  r"grok-?imagine(?!-?video)|grok.*image"),
    ("hunyuan-img", r"hunyuan.*image"),
    ("generic",     r"image|img|图像|图片|绘图|-i2i\b|-t2i\b"),
]
AUDIO = [("tts", r"tts|speech|voice|whisper|audio|音|suno|music|elevenlabs|minimax-speech|cosyvoice|sambert")]
OTHER = [("embed", r"embed|rerank|moderation|search|ocr|vision-?ocr")]


def classify(name):
    n = (name or "").lower().replace("_", "-")     # nano_banana -> nano-banana
    for fam, rx in OTHER:
        if re.search(rx, n): return "other", fam
    # 名字里明确写了 image/img/t2i/i2i 且没写 video/i2v/t2v 的，先按图像判（kling-image、grok-imagine-image）
    if re.search(r"image|img|t2i|i2i|图", n) and not re.search(r"video|i2v|t2v|视频|-vid\b", n):
        for fam, rx in IMAGE:
            if re.search(rx, n): return "image", fam
    # 音频/工具类先剔（kling-audio、custom-voices、lip-sync 不是视频生成）
    if re.search(r"audio|voice|lip-?sync|lipsync|speech|tts|template|voices-list|extend", n): return "audio", "tts"
    for fam, rx in VIDEO:
        if re.search(rx, n): return "video", fam
    for fam, rx in IMAGE:
        if re.search(rx, n): return "image", fam
    for fam, rx in AUDIO:
        if re.search(rx, n): return "audio", fam
    return "other", None


if __name__ == "__main__":
    import sys, os, json
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core import db as D
    db = D.connect()
    ok = bad = 0; wrong = []
    for r in db.execute("SELECT model, conditions FROM offer_norm WHERE vendor='toapis.cn' AND superseded_by IS NULL AND unit IN ('per_call','per_second','per_mtok_out')"):
        c = json.loads(r["conditions"] or "{}"); truth = c.get("model_type")
        if truth not in ("image", "video", "text"): continue
        pred, fam = classify(c.get("raw_name") or r["model"])
        pred = "text" if pred in ("other",) and truth == "text" else pred
        if pred == truth: ok += 1
        else:
            bad += 1; wrong.append((c.get("raw_name") or r["model"], truth, pred, fam))
    print("对 toapis 真实标签验证：对 %d / 错 %d（%.0f%%）" % (ok, bad, 100.0 * ok / max(ok + bad, 1)))
    for w in wrong[:20]: print("   %-34s 真=%-6s 判=%-6s %s" % w)
