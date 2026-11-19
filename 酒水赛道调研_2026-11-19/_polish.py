#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前抛光：修掉 PDF 里表格被裁切的问题（窄视口 680px 最小宽 > 版心宽）。

只改 HTML 里的那条窄屏规则，不动核心渲染器；改完重出 PDF。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, str(ROOT))

OUT = Path(r"D:\蛙蛙呱呱\酒水赛道调研_2026-11-19\out")

OLD = ".table-wrap table { min-width: 680px; }"
NEW = ".table-wrap table { min-width: 0; }"


def main() -> int:
    html = OUT / "report.html"
    text = html.read_text(encoding="utf-8")
    if OLD in text:
        text = text.replace(OLD, NEW)
        html.write_text(text, encoding="utf-8")
        print("patched table min-width")
    else:
        print("table rule not found (already patched?)")

    from core import report_bridge
    res = report_bridge.render_pdf(str(html), str(OUT / "report.pdf"))
    print(res)
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
