# -*- coding: utf-8 -*-
"""把三份 HTML 报告导出为 PDF（Chromium 打印引擎，A4，保留背景色与分页规则）。

- 打印前强制展开 <details>（附录 B/C 也要进 PDF）
- 页脚带「第 X / Y 页」，页眉留空
- 导出后用 PyMuPDF 复核：页数、文字可提取、关键串在位、首页渲染成图
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
FILES = [
    ("内蒙古水果市场调研与数据分析报告.html", "内蒙古水果市场调研与数据分析报告.pdf", "内蒙古水果调研与数据分析"),
    ("内蒙古水果经营报告.html", "内蒙古水果经营报告.pdf", "内蒙古水果经营报告"),
    ("内蒙古水果链路优化报告.html", "内蒙古水果链路优化报告.pdf", "内蒙古水果链路优化报告"),
]
FOOTER = """
<div style="width:100%;font-size:8px;color:#64748B;padding:0 12mm;display:flex;justify-content:space-between;">
  <span>{title}</span><span>第 <span class="pageNumber"></span> / <span class="totalPages"></span> 页</span>
</div>
"""


def export() -> list[tuple[Path, int]]:
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1400})
        for src, dst, title in FILES:
            page.goto((ROOT / src).as_uri())
            page.wait_for_timeout(600)
            # 附录默认折叠，打印前全部展开
            page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
            page.emulate_media(media="print")
            page.wait_for_timeout(300)
            pdf_path = ROOT / dst
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=FOOTER.format(title=title),
                margin={"top": "12mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
                prefer_css_page_size=False,
            )
            doc = pymupdf.open(pdf_path)
            out.append((pdf_path, doc.page_count))
            print(f"{dst}: {doc.page_count} 页, {pdf_path.stat().st_size/1024:.0f} KB")
            doc.close()
        browser.close()
    return out


def verify(results: list[tuple[Path, int]]) -> None:
    checks = {
        "内蒙古水果市场调研与数据分析报告.pdf": ["内蒙古水果市场调研与数据分析报告", "保留率", "附录 A", "C10", "35,404.72"],
        "内蒙古水果经营报告.pdf": ["内蒙古水果经营报告", "单位经济", "TAM", "0.75"],
        "内蒙古水果链路优化报告.pdf": ["内蒙古水果链路优化报告", "TCO", "断点", "验收标准"],
    }
    print("\n== 复核 ==")
    for path, pages in results:
        doc = pymupdf.open(path)
        text = "".join(pg.get_text() for pg in doc)
        missing = [k for k in checks.get(path.name, []) if k not in text]
        imgs = doc[0].get_images()
        print(f"{path.name}: {pages} 页, 文本 {len(text):,} 字, 首页图 {len(imgs)} 个, 关键串缺失 {missing or '无'}")
        # 首页与中页渲染，供人工看版式
        for idx, tag in ((0, "p1"), (min(3, pages - 1), "p4"), (pages - 1, "plast")):
            pix = doc[idx].get_pixmap(dpi=110)
            shot = ROOT / "screens" / f"{path.stem}_{tag}.png"
            pix.save(str(shot))
        doc.close()


if __name__ == "__main__":
    verify(export())
