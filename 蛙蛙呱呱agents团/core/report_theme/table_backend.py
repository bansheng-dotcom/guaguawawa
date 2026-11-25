# -*- coding: utf-8 -*-
"""表格后端（P5-4 · table）：图表不可用时的无障碍降级。

为什么需要：图型有前置条件（见 `core.chart_fit`），缺数据时要**显式降级**，
不能画一张空白图糊过去。表格同时是无障碍（屏幕阅读器）与黑白打印的兜底。
"""
from __future__ import annotations

from typing import Any, Dict, List

from core import data_standard as ds
from core.report_theme import tokens as _tokens


def _esc(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_table(dataset: ds.Dataset | Dict[str, Any],
                 spec: ds.ChartSpec | Dict[str, Any] | None = None,
                 max_rows: int = 100) -> str:
    """Dataset → 可访问 HTML 表格（caption + th scope + 数值右对齐）。"""
    d = dataset if isinstance(dataset, ds.Dataset) else ds.Dataset.from_dict(dataset)
    cs = None
    if spec is not None:
        cs = spec if isinstance(spec, ds.ChartSpec) else ds.ChartSpec.from_dict(spec)
    tk = _tokens.DEFAULT_TOKENS
    caption = (cs.option.get("title") if cs else "") or d.name
    unit = (cs.option.get("unit") if cs else "") or ""
    obs = d.observations[:max_rows]
    cols = ["metric_id", "entity", "period", "value", "unit"]
    head = "".join("<th scope=\"col\">%s</th>" % _esc(c) for c in cols)
    rows: List[str] = []
    for o in obs:
        cells = [o.metric_id, o.entity, o.period, "%.2f" % o.value, o.unit]
        tds = []
        for i, c in enumerate(cells):
            align = " style=\"text-align:right\"" if i in (3,) else ""
            tds.append("<td%s>%s</td>" % (align, _esc(c)))
        rows.append("<tr>%s</tr>" % "".join(tds))
    if not rows:
        rows.append("<tr><td colspan=\"%d\">无数据（%s）</td></tr>"
                    % (len(cols), _esc("表格降级")))
    note = ""
    if len(d.observations) > max_rows:
        note = ("<p class=\"table-note\">仅显示前 %d / %d 行</p>"
                % (max_rows, len(d.observations)))
    style = ("border-collapse:collapse;font-size:12px;color:%s"
             % tk["color"]["ink"])
    return ("<figure class=\"chart-table\" role=\"group\" aria-label=\"%s\">"
            "<table style=\"%s\"><caption>%s%s</caption><thead><tr>%s</tr></thead>"
            "<tbody>%s</tbody></table>%s</figure>"
            % (_esc(caption), style, _esc(caption),
               ("（%s）" % _esc(unit)) if unit else "",
               head, "".join(rows), note))


def fallback_note(fit: Dict[str, Any], chosen: str) -> str:
    """当选定图型不满足前置条件时，写清「缺什么、改用哪型」。"""
    for c in fit.get("candidates") or []:
        if c.get("type") == chosen and not (c.get("preconditions") or {}).get("ok"):
            miss = "、".join((c.get("preconditions") or {}).get("missing") or [])
            return "%s 前置不足（%s），已降级为 %s" % (
                chosen, miss or "未知", c.get("fallback") or "table")
    return ""
