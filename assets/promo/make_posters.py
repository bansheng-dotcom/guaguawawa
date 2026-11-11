# -*- coding: utf-8 -*-
"""用 AI 底图 + 确定性文字排版，生成 3 张宣传海报（避免 AI 生图文字乱码）。"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = r"d:\蛙蛙呱呱\宣传图"
os.makedirs(OUT, exist_ok=True)

BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
REG = r"C:\Windows\Fonts\msyh.ttc"
W, H = 1680, 2240


def font(size, bold=True):
    return ImageFont.truetype(BOLD if bold else REG, size)


def vgrad(size, top_alpha, bottom_alpha, height_ratio=0.45, from_top=True):
    """生成纵向渐变黑色遮罩"""
    w, h = size
    grad = Image.new("L", (1, h), 0)
    hh = int(h * height_ratio)
    for y in range(hh):
        a = int(top_alpha + (bottom_alpha - top_alpha) * y / max(hh - 1, 1))
        grad.putpixel((0, y), a)
    if not from_top:
        grad = grad.transpose(Image.FLIP_TOP_BOTTOM)
    grad = grad.resize((w, h))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.putalpha(grad)
    return layer


def rounded_card(img, box, radius=40, fill=(8, 12, 10, 195)):
    card = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle(box, radius=radius, fill=fill)
    img.alpha_composite(card)


def draw_text_list(img, x, y, rows, right=1470, name_size=54, price_size=66, gap=108):
    d = ImageDraw.Draw(img)
    pf = font(price_size, True)
    nf = font(27, False)
    for i, (name, price, note) in enumerate(rows):
        yy = y + i * gap
        d.text((x, yy), name, font=font(name_size, True), fill=(240, 244, 238, 255))
        tw = d.textlength(price, font=pf)
        d.text((right - tw, yy - 10), price, font=pf, fill=(255, 214, 102, 255))
        if note:
            nw = d.textlength(note, font=nf)
            d.text((right - nw, yy + 26), note, font=nf, fill=(150, 162, 150, 210))


def base_image(name):
    p = os.path.join(BASE, name)
    im = Image.open(p).convert("RGBA")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return im


def poster_hero():
    img = base_image("veg-hero.jpg")
    img.alpha_composite(vgrad((W, H), 235, 30, 0.55, True))
    d = ImageDraw.Draw(img)

    d.text((110, 130), "I N N E R   M O N G O L I A   F R E S H", font=font(34, False), fill=(255, 214, 102, 255))
    d.text((105, 190), "当季鲜蔬", font=font(158, True), fill=(255, 255, 255, 255))
    d.text((112, 400), "内蒙古 · 呼和浩特 东瓦窑批发市场", font=font(52, False), fill=(226, 232, 224, 255))
    d.line((112, 494, 612, 494), fill=(255, 214, 102, 255), width=5)
    d.text((112, 522), "2026.11.09 行情　单位：元/公斤", font=font(38, False), fill=(188, 198, 188, 255))

    rounded_card(img, (90, 1320, 1590, 2010), 44, (8, 12, 10, 205))
    d = ImageDraw.Draw(img)
    d.text((150, 1362), "今日爆款", font=font(46, True), fill=(255, 214, 102, 255))
    d.line((150, 1442, 320, 1442), fill=(255, 214, 102, 160), width=3)
    rows = [
        ("大白菜", "0.90", ""),
        ("土豆", "1.80", ""),
        ("胡萝卜", "1.40", ""),
        ("豆角", "7.00", ""),
        ("油菜", "3.20", ""),
    ]
    draw_text_list(img, 150, 1490, rows)
    d.text((112, 2105), "产地直供　当日现采　全品类 51 个单品", font=font(38, False), fill=(235, 240, 232, 235))
    img.convert("RGB").save(os.path.join(OUT, "01_当季爆款.png"), quality=96)


def poster_mushroom():
    img = base_image("mushroom.jpg")
    img.alpha_composite(vgrad((W, H), 245, 20, 0.42, True))
    d = ImageDraw.Draw(img)
    R = 1570  # 右对齐基线，避开左侧菌堆高光

    def rtext(y, s, size, fill, bold=True):
        f = font(size, bold)
        d.text((R - d.textlength(s, font=f), y), s, font=f, fill=fill)

    rtext(135, "I N N E R   M O N G O L I A   F R E S H", 34, (255, 214, 102, 255), False)
    rtext(195, "菌菇专区", 150, (255, 255, 255, 255))
    rtext(395, "火锅季 · 鲜菇正当时", 54, (232, 238, 228, 255), False)
    d.line((R - 448, 492, R, 492), fill=(255, 214, 102, 255), width=5)
    rtext(520, "2026.11.09 行情　单位：元/公斤", 38, (188, 198, 188, 255), False)

    rounded_card(img, (90, 1320, 1590, 2010), 44, (8, 12, 10, 208))
    d = ImageDraw.Draw(img)
    d.text((150, 1362), "鲜菇价目", font=font(46, True), fill=(255, 214, 102, 255))
    d.line((150, 1442, 320, 1442), fill=(255, 214, 102, 160), width=3)
    rows = [
        ("茶树菇", "12.60", ""),
        ("香菇", "10.00", ""),
        ("平菇", "8.00", ""),
        ("杏鲍菇", "8.00", ""),
        ("金针菇", "1.80", ""),
    ]
    draw_text_list(img, 150, 1490, rows)
    d.text((112, 2105), "产地直供　冷链到店　每日质检", font=font(38, False), fill=(235, 240, 232, 235))
    img.convert("RGB").save(os.path.join(OUT, "02_菌菇专区.png"), quality=96)


def poster_origin():
    img = base_image("origin.jpg")
    d = ImageDraw.Draw(img)
    # 天空压一层暖色暗调，保证白字可读
    img.alpha_composite(vgrad((W, H), 150, 10, 0.40, True))

    d.text((110, 150), "F R O M   F I E L D   T O   T A B L E", font=font(34, False), fill=(80, 46, 20, 255))
    d.text((105, 210), "从田间", font=font(150, True), fill=(48, 34, 22, 255))
    d.text((105, 390), "到餐桌", font=font(150, True), fill=(48, 34, 22, 255))
    d.text((112, 610), "高原冷凉蔬菜 · 产地直发", font=font(52, False), fill=(72, 52, 34, 255))

    # 货源地标签
    tags = ["山东", "河北张北", "宁夏", "包头", "赤峰", "乌兰察布"]
    x, y = 110, 760
    tf = font(42, True)
    for t in tags:
        tw = d.textlength(t, font=tf)
        d.rounded_rectangle((x, y, x + tw + 56, y + 82), radius=41, fill=(255, 255, 255, 210))
        d.text((x + 28, y + 14), t, font=tf, fill=(40, 46, 34, 255))
        x += tw + 80
        if x > 1200:
            x = 110
            y += 108

    rounded_card(img, (90, 1640, 1590, 2020), 44, (8, 12, 10, 200))
    d = ImageDraw.Draw(img)
    d.text((150, 1688), "主要货源地", font=font(44, True), fill=(255, 214, 102, 255))
    d.text((150, 1768), "山东 · 河北 · 宁夏 · 包头 · 赤峰 · 乌兰察布", font=font(40, False), fill=(236, 240, 232, 255))
    d.text((150, 1842), "夏秋本地高原菜，冬春外调设施菜", font=font(36, False), fill=(186, 196, 184, 255))
    d.text((150, 1912), "依据：呼和浩特市农牧局公开信息", font=font(30, False), fill=(150, 160, 148, 255))

    d.text((112, 2090), "全品类 51 个单品　批发价 0.90 元/公斤起", font=font(40, False), fill=(255, 255, 255, 240))
    img.convert("RGB").save(os.path.join(OUT, "03_产地直供.png"), quality=96)


poster_hero()
poster_mushroom()
poster_origin()
print("OK", os.listdir(OUT))
