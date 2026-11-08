# -*- coding: utf-8 -*-
"""一人公司 · 报告深度层（Report Depth Layer）。

解决「报告全面但厚度/深度不足」的工程方案：

    厚度（Volume）  = 图表 + 多表 + 分层小节 + 证据附录，而不是三段文字
    深度（Depth）   = 一次出具跑通「体检 → 趋势 → 结构拆解 → 帕累托下钻 →
                      分布形态 → 统计检验 → 外部对齐」全链路，每层都有可复算数字

设计纪律（对齐 REP-001 / META-001）：
    1. **零虚构**：所有图表坐标、表格数值都来自角色技能的真实 result，
       本模块只做「result → 图形/表格」的确定性投影。
    2. **零依赖**：复用 `agents/core/charts/chart_lib.py`（48 型 SVG 渲染器，
       纯标准库），不引入 matplotlib / plotly / 前端框架。
    3. **可降级**：任一图渲染失败只丢该图并留 note，绝不拖垮整份报告。
    4. **可打印**：SVG 全部走 CSS 变量上色，随报告主题色联动，导出 PDF 不失真。
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence

_AGENTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHARTS = os.path.join(_AGENTS, "core", "charts")
for _p in (_AGENTS, _CHARTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_LIB = None


def _lib():
    """惰性加载 48 型图表库（chart_lib 会断言 48/48 全覆盖，失败即降级）。"""
    global _LIB
    if _LIB is None:
        try:
            import chart_lib  # noqa: PLC0415
            _LIB = chart_lib
        except Exception:  # noqa: BLE001  图表库不可用不应阻断报告
            _LIB = False
    return _LIB or None


# chart_lib 用到的 CSS 变量（自 core/report_renderer.py 的色板对齐，注入报告 :root）
CHART_CSS_VARS = """
  --critical: #B33A32; --watch: #8A6500; --healthy: #19704B;
  --paper: #ffffff; --ink: #1f2933; --muted: #6b7280;
  --line: #e5e7eb; --line-strong: #cbd5e1;
  --surface: #f8fafc; --surface-strong: #eef2f7;
  --critical-soft: #fdf2f2; --watch-soft: #fefce8; --healthy-soft: #f0fdf4;
  --series-context: #94a3b8; --series-reference: #64748b;
"""


def render_chart(spec: Dict[str, Any]) -> Dict[str, Any]:
    """渲染单个 chart spec → {title, svg, note, ok}。失败只降级不抛。"""
    lib = _lib()
    title = spec.get("title", "图表")
    if lib is None:
        return {"title": title, "svg": "", "ok": False,
                "note": "图表库不可用（core/charts/chart_lib.py 未加载），已降级为表格。"}
    ctype = spec.get("type")
    fn = getattr(lib, "RENDERERS", {}).get(ctype) if ctype else None
    if fn is None:
        return {"title": title, "svg": "", "ok": False,
                "note": f"未知图表类型 {ctype}，已降级为表格。"}
    payload = {k: v for k, v in spec.items() if k not in ("type", "note")}
    try:
        svg = fn(payload)
    except Exception as exc:  # noqa: BLE001
        return {"title": title, "svg": "", "ok": False,
                "note": f"图表渲染失败（{type(exc).__name__}: {exc}），已降级为表格。"}
    return {"title": title, "svg": svg, "ok": True, "note": spec.get("note", "")}


# --------------------------------------------------------------------------- #
# 常见图型的确定性投影（result → chart spec）
# --------------------------------------------------------------------------- #
def line_from_series(series: Sequence[Dict[str, Any]], value_key: str = "value",
                     label_key: str = "date", name: str = "指标值",
                     title: str = "时间趋势",
                     note: str = "") -> Optional[Dict[str, Any]]:
    if not series:
        return None
    return {
        "type": "line", "title": title, "note": note,
        "xlabels": [str(s.get(label_key, "")) for s in series],
        "series": [{"name": name,
                    "values": [float(s.get(value_key, 0) or 0) for s in series],
                    "accent": True}],
    }


def waterfall_from_segments(segments: Sequence[Dict[str, Any]],
                            total_change: float,
                            title: str = "总变化归因（瀑布）",
                            label_key: str = "segment",
                            delta_key: str = "delta") -> Optional[Dict[str, Any]]:
    """期初 → 各分段 delta → 期末。首尾为总额条，中间为浮动条。"""
    if not segments:
        return None
    start = 0.0
    steps: List[Dict[str, Any]] = [
        {"label": "期初", "value": start, "kind": "start"},
    ]
    cursor = start
    for s in sorted(segments, key=lambda x: abs(float(x.get(delta_key, 0) or 0)),
                    reverse=True):
        d = float(s.get(delta_key, 0) or 0)
        steps.append({"label": str(s.get(label_key, "")), "value": cursor + d,
                      "delta": d, "kind": "delta",
                      "share": s.get("contribution_pct")})
        cursor += d
    steps.append({"label": "期末", "value": cursor, "kind": "end"})
    return {"type": "waterfall", "title": title, "steps": steps,
            "note": f"Σ 分段 delta = {cursor:,.2f}（与技能口径 total_change "
                    f"{total_change:,.2f} 对齐）"}


def pareto_from_items(items: Sequence[Dict[str, Any]],
                      threshold: float = 80.0,
                      title: str = "帕累托下钻（80/20）",
                      label_key: str = "segment",
                      value_key: str = "value") -> Optional[Dict[str, Any]]:
    if not items:
        return None
    return {"type": "pareto", "title": title, "threshold": threshold,
            "items": [{"label": str(i.get(label_key, "")),
                       "value": float(i.get(value_key, 0) or 0)} for i in items],
            "note": "柱为分项值降序，折线为累计占比，虚线为阈值参考线。"}


def grouped_bar_from_groups(groups: Sequence[Dict[str, Any]],
                            title: str = "分组合计对比",
                            label_key: str = "group",
                            value_key: str = "sum",
                            name: str = "合计") -> Optional[Dict[str, Any]]:
    if not groups:
        return None
    return {"type": "grouped_bar", "title": title,
            "categories": [str(g.get(label_key, "")) for g in groups],
            "series": [{"name": name,
                        "values": [float(g.get(value_key, 0) or 0) for g in groups],
                        "accent": True}]}


def histogram_from_values(values: Iterable[float], bins: int = 8,
                          title: str = "数值分布形态") -> Optional[Dict[str, Any]]:
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 3:
        return None
    return {"type": "histogram", "title": title, "values": vals, "bins": bins,
            "note": "等宽分箱由数据确定性计算；均值/中位为参考线。"}


def scatter_from_pairs(pairs: Sequence[Sequence[float]],
                       x_name: str = "X", y_name: str = "Y",
                       title: str = "相关性散点") -> Optional[Dict[str, Any]]:
    points = [{"x": float(p[0]), "y": float(p[1])} for p in pairs
              if p and len(p) >= 2 and p[0] is not None and p[1] is not None]
    if len(points) < 3:
        return None
    return {"type": "scatter", "title": title, "points": points,
            "x_label": x_name, "y_label": y_name,
            "note": f"{x_name} 与 {y_name} 的散点关系，OLS 趋势线为确定性拟合。"}


def slope_from_two_periods(before: Dict[str, float], after: Dict[str, float],
                           title: str = "两期结构对比（斜率图）",
                           left_label: str = "期初", right_label: str = "期末"
                           ) -> Optional[Dict[str, Any]]:
    keys = [k for k in before if k in after]
    if not keys:
        return None
    items = [{"label": k, "before": float(before[k]), "after": float(after[k]),
              "accent": k == max(keys, key=lambda x: abs(after[x] - before[x]))}
             for k in keys]
    return {"type": "slope", "title": title, "items": items,
            "left_label": left_label, "right_label": right_label}


# --------------------------------------------------------------------------- #
# 表格工具：把 result 的 list[dict] 摊成「可复算」表格
# --------------------------------------------------------------------------- #
def table(headers: Sequence[str], rows: Sequence[Sequence[Any]],
          caption: str = "") -> Dict[str, Any]:
    return {"caption": caption, "headers": list(headers),
            "rows": [[_cell(v) for v in r] for r in rows]}


def _cell(v: Any) -> str:
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 1 else f"{v:,.2f}"
    if v is None:
        return "—"
    return str(v)


def kv_table(pairs: Sequence[Sequence[Any]], caption: str = "",
             headers: Sequence[str] = ("项目", "取值", "说明")) -> Dict[str, Any]:
    return table(headers, pairs, caption)


__all__ = [
    "render_chart", "CHART_CSS_VARS",
    "line_from_series", "waterfall_from_segments", "pareto_from_items",
    "grouped_bar_from_groups", "histogram_from_values", "scatter_from_pairs",
    "slope_from_two_periods", "table", "kv_table",
]
