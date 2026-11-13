# -*- coding: utf-8 -*-
"""把 HTML 报告导出为 PDF（打印用），并生成一张首屏预览图。"""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent
HTML = (BASE / "个护品类数据与经营分析报告_2026-11-12.html").as_uri()
PDF = BASE / "个护品类数据与经营分析报告_2026-11-12.pdf"
PNG = BASE / "preview" / "cover.png"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=1.5)
    pg.goto(HTML, wait_until="networkidle")
    pg.screenshot(path=str(PNG))
    pg.emulate_media(media="print")
    pg.pdf(path=str(PDF), format="A4", print_background=True,
           margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
    b.close()

print(f"PDF: {PDF} ({PDF.stat().st_size/1024:.0f} KB)")
print(f"PNG: {PNG}")
