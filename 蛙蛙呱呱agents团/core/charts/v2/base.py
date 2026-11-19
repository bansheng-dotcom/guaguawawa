# -*- coding: utf-8 -*-
"""core.charts.v2.base —— 画布、标题/脚注、坐标轴清理、SVG 序列化。

几何固定，保证多张图上下对齐：
  宽 980px；标题 13px 结论句；右上 10px 口径；左下 9px 来源；
  底部预留 52px（x 轴标签 + 来源），左侧默认 116px（类目标签）。
"""
from __future__ import annotations

import io
import re
from typing import Any, Dict, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from .theme import figure_style, font_stack, tokens  # noqa: E402

W = 980.0

# 嵌入报告时为 True：报告外框已经画了标题/单位/来源，图里不再重复一遍
EMBED = False

_FONTS = ("Microsoft YaHei", "PingFang SC", "Noto Sans SC", "SimHei")


def _apply_rc() -> None:
    matplotlib.rcParams.update(figure_style())


def canvas(height: float, theme: str, title: str = "", unit: str = "",
           source: str = "", *, subtitle: str = "", note: str = "",
           pad_l: float = 116.0, pad_r: float = 74.0,
           pad_b: float = 50.0, pad_t: float = 46.0) -> Tuple[Figure, Any, Dict[str, Any]]:
    _apply_rc()
    T = tokens(theme)

    if EMBED:
        # 报告外框负责标题/单位/来源/副标题/图注，这里只留绘图区
        title, unit, source, subtitle, note = "", "", "", "", ""
        pad_t = min(pad_t, 14.0)
        pad_b = max(pad_b - 22.0, 18.0)
    elif subtitle and pad_t <= 46.0:
        # 有口径副标题时给它让出 8px，否则会压到绘图区上沿
        pad_t = 54.0

    h = max(float(height), pad_t + pad_b + 80)
    fig = Figure(figsize=(W / 100.0, h / 100.0), dpi=100, facecolor=T["paper"])

    if title:
        fig.text(0.0, 1.0 - 12.0 / h, str(title), ha="left", va="top",
                 fontsize=13.0, fontweight="bold", color=T["ink"])
    if subtitle:
        fig.text(0.0, 1.0 - 32.0 / h, str(subtitle), ha="left", va="top",
                 fontsize=9.6, color=T["muted"])
    if unit:
        fig.text(1.0, 1.0 - 15.0 / h, str(unit), ha="right", va="top",
                 fontsize=10.0, color=T["muted"])

    l = pad_l / W
    r = 1.0 - pad_r / W
    t = 1.0 - pad_t / h
    b = pad_b / h
    ax = fig.add_axes([l, b, max(r - l, 0.1), max(t - b, 0.05)])
    # 固定视窗：不允许 autoscale 在画完图后偷偷改坐标（瀑布图被改坏过）
    ax.set_autoscale_on(False)

    if source:
        fig.text(0.0, 5.0 / h, str(source), ha="left", va="bottom",
                 fontsize=8.8, color=T["muted"])
    if note:
        fig.text(1.0, 5.0 / h, str(note), ha="right", va="bottom",
                 fontsize=8.4, color=T["muted"])
    return fig, ax, T


def bare_axes(ax, T: Dict[str, Any]) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.grid(False)


def svg_of(fig: Figure) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=False, metadata={"Date": None})
    svg = buf.getvalue()
    # 去掉 matplotlib 的 <metadata>（里面是版本号与 rdf，20 张图就是 20 遍重复）
    svg = re.sub(r"(?s)<metadata>.*?</metadata>\s*", "", svg)
    svg = re.sub(r"(?s)<!--.*?-->\s*", "", svg)
    svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>\s*", "", svg)
    svg = re.sub(r'(<svg[^>]*?)\swidth="[\d.]+pt"\s+height="[\d.]+pt"', r"\1", svg)
    svg = re.sub(r'\sdata-date="[^"]*"', "", svg)
    return font_stack(svg).strip()


def fmt_num(v: Any, *, pct: bool = False, digits: Optional[int] = None) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if pct:
        return f"{v:.1f}%".replace("-", "−")
    if digits is not None:
        s = f"{v:,.{digits}f}"
    elif abs(v) >= 1000 or float(v).is_integer():
        s = f"{v:,.0f}"
    else:
        s = f"{v:,.2f}".rstrip("0").rstrip(".")
    return s.replace("-", "−")


def label_of(bar: Dict[str, Any]) -> str:
    if bar.get("value_label") not in (None, ""):
        return str(bar["value_label"])
    return fmt_num(bar.get("value", 0), pct=bool(bar.get("pct")))


def bar_width(n: int) -> float:
    """类目越少，条越宽；但最多 0.42，避免大色块。"""
    return 0.42 if n <= 3 else (0.36 if n <= 5 else 0.30)


def style_ylabels(ax, T: Dict[str, Any], size: float = 10.6) -> None:
    """横向图的类目标签：右对齐贴在绘图区左侧，不允许压到条形上。"""
    ax.tick_params(axis="y", length=0, pad=10, labelleft=True)
    for lbl in ax.get_yticklabels():
        lbl.set_ha("right")
        lbl.set_va("center")
        lbl.set_fontsize(size)
        lbl.set_color(T["ink"])


def nice_height(n: int, *, row: float = 46.0, extra: float = 0.0,
                lo: float = 320.0, hi: float = 640.0) -> float:
    return max(lo, min(hi, 96.0 + row * n + extra))
