# -*- coding: utf-8 -*-
"""截图验收：把三份报告分段截成 PNG，供人工/视觉复核对版式与溢出。"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "screens"
SHOTS.mkdir(exist_ok=True)
FILES = ["内蒙古水果市场调研与数据分析报告.html", "内蒙古水果经营报告.html", "内蒙古水果链路优化报告.html"]
PREFIX = ["r1", "r2", "r3"]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1400}, device_scale_factor=1)
        for prefix, name in zip(PREFIX, FILES):
            page.goto((ROOT / name).as_uri())
            page.wait_for_timeout(500)
            total = page.evaluate("document.body.scrollHeight")
            print(name, "height", total)
            # 顶部 + 中段 + 尾部（滚动到位置后截视口）
            for tag, y in (("top", 0), ("mid", 1400), ("mid2", 2800), ("tail", max(0, total - 1400))):
                page.evaluate(f"window.scrollTo(0, {y})")
                page.wait_for_timeout(200)
                page.screenshot(path=str(SHOTS / f"{prefix}_{tag}.png"))
            # 检查横向溢出
            overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            print("  overflow-x:", overflow)
        browser.close()


if __name__ == "__main__":
    main()
