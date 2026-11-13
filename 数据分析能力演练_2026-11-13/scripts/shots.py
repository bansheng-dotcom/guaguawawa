# -*- coding: utf-8 -*-
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(r"D:\蛙蛙呱呱\数据分析能力演练_2026-11-13\reports")
OUT = BASE / "preview"
OUT.mkdir(exist_ok=True)
FILES = ["01_数据底座体检", "02_增长量价拆解", "03_定价与门槛", "04_主图AB实验", "05_预算迁移因果", "06_用户留存与内容"]

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for name in FILES:
        pg = b.new_page(viewport={"width": 1200, "height": 1000}, device_scale_factor=1)
        pg.goto((BASE / f"{name}.html").as_uri(), wait_until="networkidle")
        h = pg.evaluate("document.body.scrollHeight")
        path = OUT / f"{name}.png"
        if h <= 16000:
            pg.screenshot(path=str(path), full_page=True)
            print(name, h, "saved")
        else:
            print(name, h, "TOO TALL")
        pg.close()
    b.close()
