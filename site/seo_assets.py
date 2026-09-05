# -*- coding: utf-8 -*-
"""生成首页、模型页、每期榜单的分享图（1200×630）。纯 PIL，不依赖浏览器。"""
import os, io, json, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from rank_seo import edition, rank_image_path

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

def brand(d, y=64, locale="zh"):
    d.rounded_rectangle((72, y, 72 + 54, y + 54), radius=16, fill=(110, 86, 245))
    d.polygon([(99, y + 10), (110, y + 27), (99, y + 44)], fill=(255, 255, 255))
    d.polygon([(99, y + 10), (88, y + 27), (99, y + 44)], fill=(185, 173, 255))
    d.text((144, y - 2), "Sinan Compute", font=font(34, cjk=False), fill=(255, 255, 255))
    d.text((144, y + 36), "SINAN LAB / RELAY MEASUREMENTS" if locale == "en" else "司南·算力 · SINAN LAB", font=font(18, cjk=locale != "en"), fill=(160, 168, 200))

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

def og_rank(rank, locale="zh", output=None):
    """A dated snapshot card, without promotional superlatives or live-data fallbacks."""
    week = edition(rank)
    relative = rank_image_path(rank, locale)
    target = os.path.join(output or OUT, relative[len("/img/"):])
    en = locale == "en"
    im, d = canvas(); brand(d, y=54, locale=locale)

    def text_line(x, y, text, size, color, width=1056, latin=False):
        # Fit translated labels and large future counts inside their own box.
        f = font(size, cjk=not (en or latin))
        while d.textbbox((0, 0), text, font=f)[2] > width and size > 14:
            size -= 1; f = font(size, cjk=not (en or latin))
        if d.textbbox((0, 0), text, font=f)[2] > width:
            raise ValueError("Rank card text does not fit")
        d.text((x, y), text, font=f, fill=color)

    muted = (164, 174, 203); white = (247, 249, 255); accent = (193, 185, 255)
    d.rounded_rectangle((864, 54, 1128, 112), radius=15, fill=(35, 30, 75), outline=(92, 79, 159))
    text_line(900, 67, week, 28, accent, width=204, latin=True)
    text_line(72, 160, "API RELAYS / WEEKLY MEASUREMENTS" if en else "API 中转站 · 周度测量", 21, accent)
    text_line(72, 209, "Sinan Rankings" if en else "司南榜", 68, white)
    text_line(72, 307, "Latency · Prices · Reachability · Model coverage" if en else "响应 · 价格 · 可达率 · 模型覆盖", 29, muted)
    metrics = (("n_sites", "已确认中转站", "Confirmed relay sites"),
               ("n_quotes", "实付报价", "Effective quotes"),
               ("eligible_uptime", "进入榜单门槛的站", "Sites meeting the threshold"))
    for i, (key, zh_label, en_label) in enumerate(metrics):
        value = rank.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Invalid rank card count: " + key)
        x = 72 + i * 360
        d.rounded_rectangle((x, 380, x + 336, 506), radius=16, fill=(19, 24, 47), outline=(58, 61, 94))
        text_line(x + 22, 396, en_label if en else zh_label, 22, muted, width=292)
        text_line(x + 22, 432, format(value, ",") if value is not None else "—", 46, white, width=292, latin=True)
    days = rank.get("window_days")
    window = str(days) if days is not None else "—"
    dated = ("Data %s · %s-day measurement window" if en else "数据日期 %s · 测量窗口 %s 天") % (rank["date"], window)
    text_line(72, 530, dated, 22, muted)
    text_line(72, 581, "Measured values, not recommendations." if en else "按测量值排序，不构成推荐。", 20, accent, width=575)
    text_line(685, 583, "compute.sinanlab.com/rank/" + week, 19, muted, width=443, latin=True)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    im.save(target, optimize=True)
    return target


def generate_rank_images(data, rank_dir=None, output=None):
    snapshots = [data["rank"]] if data.get("rank") else []
    rank_dir = rank_dir or os.path.join(HERE, "rank")
    if os.path.isdir(rank_dir):
        for filename in sorted(os.listdir(rank_dir)):
            if not filename.endswith(".json"): continue
            with io.open(os.path.join(rank_dir, filename), encoding="utf-8") as source:
                snapshot = json.load(source)
            if filename != edition(snapshot) + ".json":
                raise ValueError("Rank filename does not match its edition")
            snapshots.append(snapshot)
    generated = {}
    for snapshot in snapshots:
        for locale in ("zh", "en"):
            key = rank_image_path(snapshot, locale)
            if key not in generated:
                generated[key] = og_rank(snapshot, locale, output=output)
    return list(generated.values())


def main(rank_only=False):
    D = json.load(io.open(os.path.join(HERE, "data_v2.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    if not rank_only:
        og_home(D["stats"])
        for m in D["models"]: og_model(m)
        print("分享图：og.png + %d 张模型图" % len(D["models"]))
    ranked = generate_rank_images(D)
    print("榜单分享图：%d 张（中英文，包含历史期号）" % len(ranked))

if __name__ == "__main__":
    main(rank_only="--rank-only" in sys.argv)
