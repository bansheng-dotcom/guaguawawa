#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告字体门禁：全篇禁用斜体，标题/表头/图注不得用衬线体。

规范来源：REPORT-STANDARD §四「排版硬规则 · 禁斜体」。

用法：
    python scripts/check_report_style.py <a.html> [b.html ...]
    python scripts/check_report_style.py --dir workspace/reports
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SERIF = re.compile(r"Georgia|Songti|SimSun|Times New Roman|\bserif\b", re.I)
HEAD_SEL = re.compile(r"(?s)([^{}]*\b(h1|h2|h3|th|figcaption)\b[^{}]*)\{([^}]*)\}")


def check(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8", errors="replace")
    errs: list[str] = []
    css = "\n".join(re.findall(r"(?s)<style[^>]*>(.*?)</style>", html))
    body = re.sub(r"(?s)<style.*?</style>", "", html)

    if re.search(r"font-style\s*:\s*(italic|oblique)", css, re.I):
        errs.append("CSS 出现 font-style: italic/oblique")
    if not re.search(r"em\s*,\s*i[^{]*\{[^}]*font-style\s*:\s*normal", css):
        errs.append("缺少「em/i 强制正体」规则")
    for sel, _, decl in HEAD_SEL.findall(css):
        if "data-theme=" in sel:
            continue  # 主题专属规则：非当前主题不参与判定
        if SERIF.search(decl) and re.search(r"\b(h1|h2|h3|th|figcaption)\b", sel):
            errs.append(f"标题/表头用了衬线体：{sel.strip()[:40]}")
    for m in re.finditer(r"(?s)<(th|figcaption)[^>]*>(.*?)</\1>", body):
        inner = m.group(2)
        if re.search(r"<(em|i)\b", inner):
            errs.append(f"<{m.group(1)}> 内出现 <em>/<i>")
    for m in re.finditer(r"(?s)<em[^>]*>(.*?)</em>", body):
        if 'class="hl"' not in m.group(0):
            errs.append("<em> 未带 .hl 高亮类（默认会斜体）")
    return list(dict.fromkeys(errs))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    files = [Path(f) for f in a.files]
    if a.dir:
        files += sorted(Path(a.dir).glob("*.html"))
    if not files:
        ap.print_help()
        return 2
    bad = 0
    print(f"{'结果':6s}{'问题':4s}  文件")
    for f in files:
        errs = check(f)
        bad += bool(errs)
        print(f"{'PASS' if not errs else 'FAIL':6s}{len(errs):>4d}  {f.name}")
        if errs and not a.quiet:
            for e in errs[:6]:
                print(f"        - {e}")
    print(f"\n合计 {len(files)} 份，违规 {bad} 份")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
