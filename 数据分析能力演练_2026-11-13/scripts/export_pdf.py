# -*- coding: utf-8 -*-
"""把 6 份报告与总览导出为 PDF（A4 打印版）。"""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1] / "reports"
FILES = ["00_总览", "01_数据底座体检", "02_增长量价拆解", "03_定价与门槛",
         "04_主图AB实验", "05_预算迁移因果", "06_用户留存与内容"]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for name in FILES:
        pg = b.new_page(viewport={"width": 1200, "height": 1000})
        pg.goto((BASE / f"{name}.html").as_uri(), wait_until="networkidle")
        out = BASE / f"{name}.pdf"
        pg.pdf(path=str(out), format="A4", print_background=True,
               margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
        print(name, f"{out.stat().st_size/1024:.0f} KB")
        pg.close()
    b.close()
