# -*- coding: utf-8 -*-
"""core.charts.v2.theme —— 主题令牌 + matplotlib 基础样式。

单一事实来源：颜色从 `core.report_renderer.CSS` 的 CSS 变量里解析，
报告换主题时图跟着换，不另存一份色板。

设计约束（来自 FT Visual Vocabulary / 编辑级图表惯例）：
- 一张图只允许一个强调色，其余用灰阶；红/绿只表达“坏/好”，不表达类别；
- 不用图例，尽量直接标注；
- 去掉外框、纵网格线；只保留极细的横向参考线；
- 标题写结论，副标题写口径（单位/时间/样本）。
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict

DEFAULT_STACK = "'Microsoft YaHei', 'PingFang SC', 'Noto Sans SC', 'SimHei', sans-serif"

# 兜底（CSS 解析失败时仍能出图）
_FALLBACK = {
    "ink": "#18211D", "muted": "#5F6B64", "paper": "#FFFFFF",
    "line": "#E4E0D6", "line_strong": "#CFC9BC",
    "accent": "#1F5C4A", "accent2": "#A8894F",
    "critical": "#A8322A", "healthy": "#146B52", "watch": "#9A6A12",
    "surface": "#F4F2EB",
    "cat": ["#1F5C4A", "#C26A3A", "#B08A2E", "#3E6A8A",
            "#6B5B8E", "#2F7F7A", "#A85B6A", "#6F7A3F"],
    "context": "#B9B3A5", "reference": "#8A948D",
}


def _parse_vars(block: str) -> Dict[str, str]:
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+):\s*([^;]+);", block)}


@lru_cache(maxsize=32)
def tokens(theme: str = "paper") -> Dict[str, object]:
    """返回某主题的图表色板。CSS 变了这里自动跟着变。"""
    base: Dict[str, str] = {}
    over: Dict[str, str] = {}
    try:
        from core.report_renderer import CSS  # 延迟导入，避免循环

        m = re.search(r":root\s*\{(.*?)\}", CSS, re.S)
        if m:
            base = _parse_vars(m.group(1))
        m = re.search(r'body\[data-theme="%s"\]\s*\{(.*?)\}' % re.escape(theme), CSS, re.S)
        if m:
            over = _parse_vars(m.group(1))
    except Exception:
        pass

    def pick(name: str, default: str) -> str:
        v = over.get(name) or base.get(name) or default
        return v if str(v).startswith("#") else default

    cats = [pick(f"--cat-{i}", _FALLBACK["cat"][i - 1]) for i in range(1, 9)]
    return {
        "ink": pick("--ink", _FALLBACK["ink"]),
        "muted": pick("--muted", _FALLBACK["muted"]),
        "paper": pick("--paper", _FALLBACK["paper"]),
        "line": pick("--line", _FALLBACK["line"]),
        "line_strong": pick("--line-strong", _FALLBACK["line_strong"]),
        "accent": pick("--accent", _FALLBACK["accent"]),
        "accent2": pick("--accent-2", _FALLBACK["accent2"]),
        "critical": pick("--critical", _FALLBACK["critical"]),
        "healthy": pick("--healthy", _FALLBACK["healthy"]),
        "watch": pick("--watch", _FALLBACK["watch"]),
        "surface": pick("--surface", _FALLBACK["surface"]),
        "cat": cats,
        "context": pick("--series-context", _FALLBACK["context"]),
        "reference": pick("--series-reference", _FALLBACK["reference"]),
    }


def figure_style() -> Dict[str, object]:
    """matplotlib rcParams：字体、去负号方块、SVG 文本可选中。"""
    return {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "PingFang SC", "Noto Sans SC", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "svg.fonttype": "none",          # 文本保留为 <text>，可选中、体积小
        "svg.hashsalt": "guagua-report",
        "figure.dpi": 100,
        "savefig.dpi": 100,
        "text.antialiased": True,
        "lines.antialiased": True,
    }


def font_stack(svg: str) -> str:
    """把 matplotlib 写死的单一字体名换成回退栈。

    注意：SVG 的 style 属性用双引号包裹，字体名只能用单引号，
    否则整段 style 会被截断（text-anchor 等样式一起丢失）。
    """
    return re.sub(r"font-family:\s*[^;]+;", f"font-family: {DEFAULT_STACK};", svg)
