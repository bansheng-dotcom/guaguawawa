# -*- coding: utf-8 -*-
"""门禁：48 型图表经报告渲染管线（report_renderer.render_chart）嵌入后的完整性。

验四件事（任一不满足即 exit 1）：
  1. 48 型全部走 v2 成功，不回退 v1、不抛异常（chart_stats 计数为证）；
  2. 每张图在报告里只出现一次标题：图卡 <figcaption> 给标题，SVG 内不得重复；
  3. 卡框承担口径：给 subtitle 的图必须出现 .fig-sub，给 source/note 的必须出现 .fig-src；
  4. 每张图仍是可缩放的内联 SVG（无 <img>、无外链），且带 viewBox。

用法：
    python scripts/check_chart_report_embed.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import report_renderer as RR  # noqa: E402
from core.charts.v2 import RENDERERS  # noqa: E402
from core.charts.v2 import dataset as DS  # noqa: E402
from scripts.chart_gallery_v2 import SAMPLES  # noqa: E402


def _texts(svg: str) -> str:
    return " ".join(re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S))


def main() -> int:
    keys = sorted(RENDERERS)
    sections = []
    for k in keys:
        spec = dict(SAMPLES[k])
        spec["title"] = f"[{k}] " + str(spec.get("title", ""))
        sections.append({"title": f"{k} 嵌入检查", "charts": [spec]})

    contract = {
        "doc_type": "嵌入门禁",
        "title_lines": ["48 型图表嵌入报告检查"],
        "theme": "paper",
        "sections": sections,
    }
    RR.reset_chart_stats()
    html = RR.render(contract)
    stats = RR.chart_stats()

    fails = []
    if stats["v2"] != 48 or stats["v1"] or stats["error"]:
        fails.append(f"引擎计数异常 {stats}")
    if len(re.findall(r'<figure class="fig-card">', html)) != 48:
        fails.append("fig-card 数量不是 48")
    if html.count("<svg") != 48:
        fails.append(f"内联 svg 数量 {html.count('<svg')}")
    if "<img" in html:
        fails.append("出现 <img>（应为内联 SVG）")
    # matplotlib 输出的是 pt 坐标：980px 宽 = 705.6pt，宽度固定才保证多图上下对齐
    vbs = re.findall(r'<svg[^>]*viewBox="([^"]+)"', html)
    if len(vbs) != 48:
        fails.append(f"缺 viewBox 的 SVG：{48 - len(vbs)}")
    bad_w = [v for v in vbs if not v.startswith("0 0 705.6")]
    if bad_w:
        fails.append(f"{len(bad_w)} 张图画布宽度不是 980px（{bad_w[:2]}）")

    for k in keys:
        spec = SAMPLES[k]
        start = html.find(f"[{k}] ")
        if start < 0:
            fails.append(f"{k} 标题缺失")
            continue
        seg = html[start: html.find('<figure class="fig-card">', start + 50)]
        body = seg[seg.find("<svg"):] if "<svg" in seg else ""
        if body:
            inner = _texts(body)
            # 图卡标题已在外层 figcaption；SVG 内若还有完整标题即为双标题
            if str(spec.get("title", "")) in inner:
                fails.append(f"{k} SVG 内重复标题")
        if spec.get("subtitle") and '<div class="fig-sub">' not in seg:
            fails.append(f"{k} 缺口径副标题块")
        if spec.get("source") and '<div class="fig-src">' not in seg:
            fails.append(f"{k} 缺来源/图注块")

    if fails:
        print("FAIL")
        for f in fails[:20]:
            print(" -", f)
        return 1
    print(f"PASS 48/48 · v2 {stats['v2']} · 回退 {stats['v1']} · 异常 {stats['error']} "
          f"· 卡框副标题/来源齐备 · 无双标题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
