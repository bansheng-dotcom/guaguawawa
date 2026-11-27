# -*- coding: utf-8 -*-
"""scripts/check_report_presentation.py —— 呈现层门禁（v12 / T9）。

只查「看得见的东西」，不重复内容门禁（那是 report_quality / check_report_flow 的活）。
依据：docs/REPORT-DESIGN-CONTRACT.md 的 12 条可测规则。

  P1 无斜体：全篇不许 italic（中文伪斜体在 PDF 里糊，REPORT-STANDARD §六 R5）
  P2 打印就绪：必须有 @page + A4，且正文有分页保护（figure/section 不跨页断）
  P3 对比度：正文/次要文字对纸底 ≥ 4.5:1（WCAG AA 正文标准）
  P4 字阶：同时存在至少 4 个不同字号（标题/小标题/正文/辅助），不许全文一个字号
  P5 图四件套：每张图卡必须有 来源、单位、口径副标题；有数据轴时必须有零线/均值线文案
  P6 主题一致：不允许同时出现两套 `--ink` 定义（双主题拼在同一份 HTML 里会串色）
  P7 版心与行宽：主容器 max-width 在 680–1040px，行高 1.0–2.0
  P8 容器克制：border-radius 去重后 ≤6 档（排除 0/50%/999px 胶囊）
  P9 断行卫生：<p>/标题内不出现 <br> 手动折行
  P10 表格规范：每个 <table> 有 <thead> 且至少一个 <th>
  P11 反模式：正文不居中、字号不小于 11px、装饰性渐变不超过 1 处且仅在封面
  P12 标题层级：恰好一个 <h1>，标题层级不跳级

用法：
    python scripts/check_report_presentation.py --dir <输出目录>
    python scripts/check_report_presentation.py <report.html>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MIN_CONTRAST = 4.5
MIN_TYPE_STEPS = 4


def _rgb(hex_or_rgb: str) -> Optional[Tuple[int, int, int]]:
    s = str(hex_or_rgb or "").strip()
    m = re.match(r"^#([0-9a-fA-F]{6})$", s)
    if m:
        v = m.group(1)
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    m = re.match(r"^#([0-9a-fA-F]{3})$", s)
    if m:
        v = m.group(1)
        return int(v[0] * 2, 16), int(v[1] * 2, 16), int(v[2] * 2, 16)
    m = re.match(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", s)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _lum(rgb: Tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        x = c / 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> Optional[float]:
    a, b = _rgb(fg), _rgb(bg)
    if not a or not b:
        return None
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _vars(html: str) -> Dict[str, str]:
    """取 :root / body 里第一套令牌（--ink / --paper / --muted …）。"""
    out: Dict[str, str] = {}
    for m in re.finditer(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]*\))", html):
        out.setdefault(m.group(1), m.group(2))
    return out


def check_html(path: Path) -> Dict[str, Any]:
    html = path.read_text(encoding="utf-8", errors="replace")
    v: List[Dict[str, str]] = []

    # P1 无斜体
    if re.search(r"font-style\s*:\s*italic", html, re.I):
        v.append({"id": "P1_italic", "msg": "出现 font-style: italic（中文伪斜体在 PDF 里糊）"})

    # P2 打印就绪
    if "@page" not in html or "A4" not in html:
        v.append({"id": "P2_print", "msg": "缺 @page A4 打印规则：PDF 会按屏幕宽排版"})
    if "break-inside" not in html:
        v.append({"id": "P2_break", "msg": "缺 break-inside 控制：图表会跨页截断"})

    # P3 对比度
    tok = _vars(html)
    paper = tok.get("paper") or tok.get("theme-base") or "#FFFFFF"
    pairs = [("正文", tok.get("ink") or tok.get("theme-primary") or "#111111", paper),
             ("次要文字", tok.get("muted") or "#555555", paper),
             ("弱化文字", tok.get("faint") or tok.get("muted") or "#777777", paper)]
    contrast_rows = []
    for name, fg, bg in pairs:
        c = contrast(fg, bg)
        contrast_rows.append({"name": name, "fg": fg, "bg": bg, "ratio": c})
        if c is None:
            v.append({"id": "P3_contrast", "msg": f"{name} 色值无法解析：{fg} on {bg}"})
        elif name != "弱化文字" and c < MIN_CONTRAST:
            v.append({"id": "P3_contrast",
                      "msg": f"{name} 对比度 {c}:1 < {MIN_CONTRAST}:1（{fg} on {bg}）"})

    # P4 字阶
    sizes = set()
    for m in re.finditer(r"font-size\s*:\s*([\d.]+)\s*(px|pt)", html):
        sizes.add(round(float(m.group(1)) * (1.333 if m.group(2) == "pt" else 1), 1))
    if len(sizes) < MIN_TYPE_STEPS:
        v.append({"id": "P4_type_scale",
                  "msg": f"只有 {len(sizes)} 档字号（<{MIN_TYPE_STEPS}）：标题/正文分不出层级"})

    # P5 图四件套
    figs = re.findall(r'<figure class="fig-card"[\s\S]*?</figure>', html, re.I)
    fig_rows = []
    for i, f in enumerate(figs, 1):
        need = {
            "source": bool(re.search(r'class="fig-src"', f, re.I)),
            "unit": bool(re.search(r'class="fig-unit"', f, re.I)),
            "caption": bool(re.search(r'class="fig-sub"', f, re.I)),
        }
        fig_rows.append({"index": i, **need})
        for k, ok in need.items():
            if not ok:
                v.append({"id": "P5_figure", "msg": f"第 {i} 张图缺 {k}"})
    # 零线/均值线只在「有数据轴的图」上要求；报告没有图就不判
    if figs and "均值" not in html and "零线" not in html and "参考线" not in html:
        v.append({"id": "P5_refline", "msg": "有图但全篇没有零线/均值线说明"})

    # P6 主题一致：允许多套主题令牌共存（渲染器内联 8 套，按 body[data-theme] 切换），
    # 但**未加作用域**的 --ink 只能有一套，否则默认主题会被后定义的覆盖（串色）。
    head = html.split("body[data-theme", 1)[0]
    unscoped = re.findall(r"--ink\s*:", head)
    if len(unscoped) > 1:
        v.append({"id": "P6_theme",
                  "msg": f"默认作用域里有 {len(unscoped)} 套 --ink：主题令牌互相覆盖"})
    active = re.search(r'<body[^>]*data-theme="([^"]+)"', html)
    if not active:
        v.append({"id": "P6_theme_active", "msg": "body 没有 data-theme，主题未显式声明"})

    # P7 版心与行宽：主容器必须有 680–1040px 的 max-width；行高 1.0–2.0
    measures = [float(x) for x in re.findall(r"max-width\s*:\s*([\d.]+)px", html)]
    if not any(680 <= x <= 1040 for x in measures):
        v.append({"id": "P7_measure",
                  "msg": f"没有 680–1040px 的 max-width（实际 {measures[:4] or '无'}）：版心未定义"})
    leadings = [float(x) for x in re.findall(r"line-height\s*:\s*(1?\.[\d]+)", html)]
    bad_leading = [x for x in leadings if not 1.0 <= x <= 2.0]
    if bad_leading:
        v.append({"id": "P7_measure",
                  "msg": f"行高 {bad_leading[:4]} 不在 1.0–2.0：正文会挤或散"})

    # P8 容器克制：圆角去重后 ≤6 档（0/50%/999px 胶囊不计入档位）
    radii = set()
    for decl in re.findall(r"border-radius\s*:\s*([^;{}\"']+)", html):
        for tok in decl.replace("/", " ").split():
            tok = tok.strip().lower()
            if tok in ("0", "50%", "999px", "9999px", ""):
                continue
            for num in re.findall(r"[\d.]+", tok):
                radii.add(round(float(num), 2))
    if len(radii) > 6:
        v.append({"id": "P8_container",
                  "msg": f"出现 {len(radii)} 档 border-radius：{sorted(radii)[:8]}（>6 档，容器不克制）"})

    # P9 断行卫生：段落/标题里不用 <br> 手动折行
    br_in_p = re.findall(r"<p[^>]*>(?:(?!</p>)[\s\S])*?<br", html, re.I)
    br_in_h = re.findall(r"<h[1-6][^>]*>(?:(?!</h[1-6]>)[\s\S])*?<br", html, re.I)
    if br_in_p:
        v.append({"id": "P9_linebreak", "msg": f"{len(br_in_p)} 个段落用 <br> 手动折行"})
    if br_in_h:
        v.append({"id": "P9_linebreak", "msg": f"{len(br_in_h)} 个标题用 <br> 手动折行"})

    # P10 表格规范：有表就必须有 thead + th
    table_blocks = re.findall(r"<table[\s\S]*?</table>", html, re.I)
    for i, t in enumerate(table_blocks, 1):
        if "<thead" not in t.lower():
            v.append({"id": "P10_table", "msg": f"第 {i} 张表缺 <thead>"})
        if "<th" not in t.lower():
            v.append({"id": "P10_table", "msg": f"第 {i} 张表缺 <th> 表头"})

    # P11 反模式：正文居中、字号 <11px、装饰性渐变 >1 处或不在封面
    grad_spans = [m.start() for m in re.finditer(r"(?<!repeating-)(?:linear-gradient|radial-gradient)", html, re.I)]
    if len(grad_spans) > 1:
        v.append({"id": "P11_antipattern", "msg": f"出现 {len(grad_spans)} 处渐变背景（只允许封面 1 处）"})
    elif grad_spans:
        head = html[max(0, grad_spans[0] - 180):grad_spans[0]]
        if ".cover" not in head:
            v.append({"id": "P11_antipattern", "msg": "正文区出现渐变背景（强调失效、打印失真）"})
    if re.search(r"<p[^>]*text-align\s*:\s*center", html, re.I) or \
            re.search(r"(?:^|})\s*p\s*\{[^}]*text-align\s*:\s*center", html):
        v.append({"id": "P11_antipattern", "msg": "正文段落居中：长文阅读会丢行"})
    small = sorted({float(x) for x in re.findall(r"font-size\s*:\s*([\d.]+)px", html) if float(x) < 11})
    if small:
        v.append({"id": "P11_antipattern", "msg": f"字号 {small} < 11px：打印不可读"})

    # P12 标题层级：恰好一个 h1，且不跳级
    levels = [int(x) for x in re.findall(r"<h([1-6])[ >]", html)]
    h1_count = levels.count(1)
    if h1_count != 1:
        v.append({"id": "P12_heading", "msg": f"<h1> 出现 {h1_count} 次（应恰好 1 次）"})
    prev = 0
    for lv in levels:
        if prev and lv > prev + 1:
            v.append({"id": "P12_heading", "msg": f"标题层级跳级：h{prev} → h{lv}"})
            break
        prev = lv

    return {
        "file": str(path),
        "ok": not v,
        "violations": v,
        "figures": len(figs),
        "figure_rows": fig_rows,
        "type_steps": sorted(sizes),
        "contrast": contrast_rows,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    targets = [Path(x) for x in a.files]
    if a.dir:
        targets += sorted(Path(a.dir).glob("*.html"))
    if not targets:
        print("用法: check_report_presentation.py <report.html> | --dir <out>")
        return 2
    results = [check_html(p) for p in targets]
    for r in results:
        print(("PASS " if r["ok"] else "FAIL ") + r["file"]
              + f"  图 {r['figures']}  字阶 {len(r['type_steps'])}")
        for x in r["violations"]:
            print(f"      - [{x['id']}] {x['msg']}")
    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
