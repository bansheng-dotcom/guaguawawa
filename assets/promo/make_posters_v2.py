# -*- coding: utf-8 -*-
"""在 R10 提示词规范下由大模型生成的真实底图上叠加中文信息层。"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1680, 2240
F = "C:/Windows/Fonts/msyh.ttc"
FB = "C:/Windows/Fonts/msyhbd.ttc"
OUT = r"d:\蛙蛙呱呱\宣传图\r10_full"


def overlay(src, dst, brand, title, sub, items, note):
    img = Image.open(src).convert("RGB")
    img = img.resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(img, "RGBA")

    for y in range(0, 700):
        a = int(200 * (1 - y / 700) ** 1.4)
        d.line([(0, y), (W, y)], fill=(4, 10, 8, a))

    f_brand = ImageFont.truetype(FB, 34)
    f_title = ImageFont.truetype(FB, 138)
    f_sub = ImageFont.truetype(F, 44)
    f_name = ImageFont.truetype(F, 40)
    f_price = ImageFont.truetype(FB, 62)
    f_note = ImageFont.truetype(F, 32)

    d.text((110, 120), brand, font=f_brand, fill=(255, 194, 26))
    d.text((110, 186), title, font=f_title, fill=(255, 255, 255))
    d.text((114, 372), sub, font=f_sub, fill=(212, 224, 214))

    bar_h = 300
    top = H - bar_h
    d.rectangle([0, top, W, H], fill=(6, 12, 10, 214))
    d.line([(0, top), (W, top)], fill=(255, 194, 26, 160), width=3)

    n = len(items)
    col_w = (W - 120) // n
    for i, (name, price) in enumerate(items):
        cx = 60 + col_w * i + col_w // 2
        d.text((cx, top + 66), name, font=f_name, fill=(206, 216, 208), anchor="ma")
        d.text((cx, top + 132), price, font=f_price, fill=(255, 194, 26), anchor="ma")

    d.text((110, H - 62), note, font=f_note, fill=(150, 162, 154))
    img.save(dst, quality=95)
    print("saved", dst, img.size)


overlay(
    rf"{OUT}\poster01_baokuan.jpg", rf"{OUT}\01_当季爆款_实测版.jpg",
    "内蒙古鲜蔬 · 行情播报", "当季爆款",
    "呼和浩特东瓦窑批发市场 · 2026-11-09 监测价",
    [("大白菜", "0.90"), ("土豆", "1.80"), ("胡萝卜", "1.40"), ("油菜", "3.20"), ("豆角", "7.00")],
    "单位：元/公斤　数据来源：农业农村部批发日行情　共监测 51 个单品",
)

overlay(
    rf"{OUT}\poster02_jungu.jpg", rf"{OUT}\02_菌菇专区_实测版.jpg",
    "内蒙古鲜蔬 · 行情播报", "菌菇专区",
    "呼和浩特东瓦窑批发市场 · 2026-11-09 监测价",
    [("香菇", "10.00"), ("平菇", "8.00"), ("杏鲍菇", "8.00"), ("茶树菇", "12.60"), ("金针菇", "1.80")],
    "单位：元/公斤　菌菇类整体环比 +2.02%　共监测 5 个单品",
)

overlay(
    rf"{OUT}\poster03_chandi.jpg", rf"{OUT}\03_产地直供_实测版.jpg",
    "内蒙古鲜蔬 · 产销对接", "产地直供",
    "从田间到餐桌 · 主要货源地",
    [("山东", "设施菜"), ("张北", "冷凉菜"), ("宁夏", "叶菜"), ("乌兰察布", "马铃薯"), ("赤峰", "根茎类")],
    "产地价为商业询价数据，公开渠道仅 4 个品类可查，采购前需向产区代办索取报价单",
)
