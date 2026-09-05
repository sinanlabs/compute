# -*- coding: utf-8 -*-
"""生成分享图（og.png 1200×630）与每个模型页的分享图。纯 PIL，不依赖浏览器。"""
import os, io, json, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "img")
FONT_CJK = "/System/Library/Fonts/Supplemental/Songti.ttc"
FONT_LAT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

def font(size, cjk=True, bold=True):
    try:
        if cjk: return ImageFont.truetype(FONT_CJK, size, index=1 if bold else 0)
        return ImageFont.truetype(FONT_LAT if bold else FONT_LAT.replace(" Bold", ""), size)
    except Exception:
        return ImageFont.load_default()

def canvas():
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (4, 6, 17))
    glow = Image.new("RGB", (W, H), (4, 6, 17)); g = ImageDraw.Draw(glow)
    g.ellipse((700, 180, 1500, 900), fill=(46, 30, 130))
    g.ellipse((-200, -300, 500, 200), fill=(30, 22, 80))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    im = Image.blend(im, glow, 0.85)
    d = ImageDraw.Draw(im)
    # 地平线弧（呼应首页地球）
    arc = Image.new("RGBA", (W, H), (0, 0, 0, 0)); a = ImageDraw.Draw(arc)
    a.ellipse((250, 470, 2200, 2400), fill=(22, 60, 140, 255))
    a.ellipse((260, 486, 2190, 2390), fill=(8, 20, 60, 255))
    arc = arc.filter(ImageFilter.GaussianBlur(6))
    im.paste(arc, (0, 0), arc)
    return im, ImageDraw.Draw(im)

def brand(d, y=64):
    d.rounded_rectangle((72, y, 72 + 54, y + 54), radius=16, fill=(110, 86, 245))
    d.polygon([(99, y + 10), (110, y + 27), (99, y + 44)], fill=(255, 255, 255))
    d.polygon([(99, y + 10), (88, y + 27), (99, y + 44)], fill=(185, 173, 255))
    d.text((144, y - 2), "Sinan Compute", font=font(34, cjk=False), fill=(255, 255, 255))
    d.text((144, y + 36), "司南·算力 · SINAN LAB", font=font(18), fill=(160, 168, 200))

def og_home(stats):
    im, d = canvas(); brand(d)
    d.text((72, 200), "看清算力，才好买算力。", font=font(72), fill=(255, 255, 255))
    d.text((72, 300), "%d 个中转站的实付价，对着官方与公开市场价逐条算成比率" % stats["confirmed"], font=font(30), fill=(200, 206, 230))
    d.text((72, 350), "每个数字可点开看抓取快照 · 不收任何被测渠道的钱 · 不替你判断", font=font(26), fill=(150, 158, 190))
    x = 72
    for k, v in (("已确认中转站", str(stats["confirmed"])), ("实付报价", format(stats["quotes"], ",")), ("有报价的站", str(stats["with_quotes"]))):
        d.rounded_rectangle((x, 440, x + 300, 560), radius=18, fill=(22, 26, 58), outline=(90, 80, 160))
        d.text((x + 22, 456), k, font=font(20), fill=(160, 168, 200)); d.text((x + 22, 490), v, font=font(46, cjk=False), fill=(255, 255, 255)); x += 324
    d.text((72, 588), "compute.sinanlab.com", font=font(22, cjk=False), fill=(185, 173, 255))
    im.save(os.path.join(OUT, "og.png"), optimize=True)

def og_model(m):
    im, d = canvas(); brand(d)
    f = m["floor"]; rows = [r for r in m["rows"] if not r["held"]]
    ok = [r for r in rows if r["band"] in ("explainable", "normal")]
    d.text((72, 190), m["name"], font=font(70, cjk=False), fill=(255, 255, 255))
    d.text((72, 280), "%d 家中转站实付价 · 参考价 $%.2f / 百万输出" % (m["n_relay"], f["out"]), font=font(32), fill=(200, 206, 230))
    line = "价格说得通 %d 家 · 低于成本下限 %d 家 · 待核 %d 家" % (len(ok), sum(1 for r in rows if r["band"] == "unsustainable"), sum(1 for r in m["rows"] if r["held"]))
    d.text((72, 330), line, font=font(26), fill=(150, 158, 190))
    if ok:
        best = min(ok, key=lambda r: r["out"])
        d.rounded_rectangle((72, 420, 640, 560), radius=18, fill=(22, 26, 58), outline=(90, 80, 160))
        d.text((94, 436), "说得通的最低实付", font=font(20), fill=(160, 168, 200))
        d.text((94, 470), "$%.2f" % best["out"], font=font(56, cjk=False), fill=(255, 255, 255))
        d.text((300, 486), "/ 百万输出 · 参考价的 %.0f%%" % (best["ratio"] * 100), font=font(24), fill=(200, 206, 230))
    d.text((72, 588), "compute.sinanlab.com/m/%s" % m["id"], font=font(22, cjk=False), fill=(185, 173, 255))
    os.makedirs(os.path.join(OUT, "og"), exist_ok=True)
    im.save(os.path.join(OUT, "og", m["id"] + ".png"), optimize=True)

def main():
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    og_home(D["stats"])
    for m in D["models"]: og_model(m)
    print("分享图：og.png + %d 张模型图" % len(D["models"]))

if __name__ == "__main__":
    main()
