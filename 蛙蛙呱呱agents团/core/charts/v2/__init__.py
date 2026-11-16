# -*- coding: utf-8 -*-
"""core.charts.v2 —— 研报级图表引擎（确定性 SVG，matplotlib 后端）。

与 v1（core/charts/chart_lib.py）的关系：
- v1 是 48 型的“能画出来”，v2 是常用 16 型的“画到能直接进报告”；
- 进入 v2 前先做一次 schema 归一（v1 的 before/after、kind=delta 等写法在这里转成 v2 形），
- 数据不够或画不出来就返回 None，由调用方回退 v1 —— 48/48 能力不退化。

用法：
    from core.charts.v2 import render, supports
    svg = render({"type": "hbar", "title": "...", "bars": [...]}, theme="paper")
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import (types_b1, types_b2, types_b3, types_b4, types_bar, types_line,
               types_matrix, types_part)

RENDERERS = {
    # 比较与构成（既有 18 型）
    "hbar": types_bar.hbar,
    "vbar": types_bar.vbar,
    "dot": types_bar.dot,
    "lollipop": types_bar.dot,
    "pareto": types_bar.pareto,
    "waterfall": types_bar.waterfall,
    "bridge": types_bar.waterfall,
    "dumbbell": types_bar.dumbbell,
    "grouped_bar": types_bar.grouped_bar,
    "stacked_bar": types_bar.stacked_bar,
    "line": types_line.line,
    "area": types_line.area,
    "slope": types_line.slope,
    "small_mult": types_line.small_mult,
    "donut": types_part.donut,
    "pie": types_part.pie,
    "treemap": types_part.treemap,
    "heatmap": types_matrix.heatmap,
    # 分布与关系（b1）
    "pct_stacked": types_b1.pct_stacked,
    "histogram": types_b1.histogram,
    "box": types_b1.box,
    "violin": types_b1.violin,
    "ridgeline": types_b1.ridgeline,
    "scatter": types_b1.scatter,
    "bubble": types_b1.bubble,
    "parallel": types_b1.parallel,
    # 不确定性与目标（b2）
    "error_bar": types_b2.error_bar,
    "forest": types_b2.forest,
    "control": types_b2.control,
    "funnel": types_b2.funnel,
    "bullet": types_b2.bullet,
    "gauge": types_b2.gauge,
    "target_band": types_b2.target_band,
    "dual_axis": types_b2.dual_axis,
    "radar": types_b2.radar,
    # 流程、时间与构成（b3）
    "cal_heatmap": types_b3.cal_heatmap,
    "gantt": types_b3.gantt,
    "candlestick": types_b3.candlestick,
    "sankey": types_b3.sankey,
    "streamgraph": types_b3.streamgraph,
    "kpi_break": types_b3.kpi_break,
    "waffle": types_b3.waffle,
    "rose": types_b3.rose,
    # 地理、关系与层级（b4）
    "choropleth": types_b4.choropleth,
    "symbol_map": types_b4.symbol_map,
    "geo_flow": types_b4.geo_flow,
    "network": types_b4.network,
    "sunburst": types_b4.sunburst,
}


def _num(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalize(key: str, chart: Dict[str, Any]) -> Dict[str, Any]:
    """把 chart_lib 的历史写法转成 v2 的内部形。"""
    c = dict(chart)

    # v1 的参考线字段是 ref_line，v2 用 ref；旧契约在归一阶段统一，避免图里少一条参考线
    if not c.get("ref"):
        rl = chart.get("ref_line")
        if isinstance(rl, dict) and _num(rl.get("value")) is not None:
            c["ref"] = {"value": _num(rl.get("value")), "label": rl.get("label", "")}
        elif _num(rl) is not None:
            c["ref"] = {"value": _num(rl), "label": ""}

    if key == "slope":
        c["items"] = [
            {"label": i.get("label", ""),
             "a": i.get("a", i.get("before")),
             "b": i.get("b", i.get("after"))}
            for i in chart.get("items") or []
        ]
        c["a_label"] = chart.get("a_label") or chart.get("left_label") or "期初"
        c["b_label"] = chart.get("b_label") or chart.get("right_label") or "期末"

    elif key in ("waterfall", "bridge"):
        steps: List[Dict[str, Any]] = []
        for s in chart.get("steps") or []:
            kind = str(s.get("kind") or s.get("type") or "")
            if kind in ("start", "end", "total") or s.get("total"):
                steps.append({"label": s.get("label", ""), "value": s.get("value"), "type": "total"})
            else:
                steps.append({"label": s.get("label", ""), "value": s.get("delta", s.get("value"))})
        c["steps"] = steps

    elif key == "small_mult":
        c["panels"] = [
            {"label": p.get("label") or p.get("title") or "",
             "values": p.get("values") or []}
            for p in chart.get("panels") or []
        ]

    elif key in ("donut", "pie", "treemap", "dot", "lollipop", "pareto"):
        c["items"] = [{"label": i.get("label", ""), "value": i.get("value"),
                       "weight": i.get("weight")} for i in chart.get("items") or []]

    elif key in ("hbar", "vbar"):
        raw = chart.get("bars") or chart.get("vbars") or []
        c["bars"] = [{"label": b.get("label", ""), "value": b.get("value"),
                      "value_label": b.get("value_label"), "weight": b.get("weight")} for b in raw]

    elif key == "pct_stacked":
        c["categories"] = [str(x) for x in chart.get("categories") or []]
        c["segments"] = [{"name": s.get("name", ""), "values": s.get("values") or [],
                          "accent": bool(s.get("accent"))}
                         for s in chart.get("segments") or []]

    elif key == "histogram":
        c["values"] = chart.get("values") or []

    elif key in ("box", "violin", "ridgeline"):
        c["groups"] = [{"label": g.get("label", ""), "sub": g.get("sub", ""),
                        "values": g.get("values") or [], "accent": bool(g.get("accent"))}
                       for g in chart.get("groups") or []]

    elif key in ("scatter", "bubble", "symbol_map"):
        c["points"] = [dict(p) for p in chart.get("points") or []]

    elif key == "parallel":
        c["axes"] = [str(a) for a in chart.get("axes") or []]
        c["items"] = [{"name": it.get("name", ""), "values": it.get("values") or [],
                       "accent": bool(it.get("accent"))}
                      for it in chart.get("items") or []]

    elif key == "error_bar":
        c["items"] = [{"label": it.get("label", ""), "value": it.get("value"),
                       "err": it.get("err"), "accent": bool(it.get("accent"))}
                      for it in chart.get("items") or []]

    elif key == "forest":
        c["items"] = [{"label": it.get("label", ""), "est": it.get("est"),
                       "lo": it.get("lo"), "hi": it.get("hi"),
                       "accent": bool(it.get("accent"))}
                      for it in chart.get("items") or []]

    elif key == "control":
        c["xlabels"] = [str(x) for x in chart.get("xlabels") or []]
        c["series"] = [{"name": s.get("name", ""), "values": s.get("values") or []}
                       for s in chart.get("series") or []]

    elif key == "funnel":
        c["stages"] = [{"label": s.get("label", ""), "value": s.get("value")}
                       for s in chart.get("stages") or []]

    elif key == "bullet":
        c["bands"] = [{"to": b.get("to"), "label": b.get("label", "")}
                      for b in chart.get("bands") or []]

    elif key == "gauge":
        c["min"] = chart.get("min", 0)
        c["max"] = chart.get("max", 100)

    elif key == "target_band":
        c["xlabels"] = [str(x) for x in chart.get("xlabels") or []]
        c["series"] = [{"name": s.get("name", ""), "values": s.get("values") or []}
                       for s in chart.get("series") or []]

    elif key == "dual_axis":
        c["xlabels"] = [str(x) for x in chart.get("xlabels") or []]

    elif key == "radar":
        c["axes"] = [str(a) for a in chart.get("axes") or []]
        c["series"] = [{"name": s.get("name", ""), "values": s.get("values") or [],
                        "accent": bool(s.get("accent"))}
                       for s in chart.get("series") or []]

    elif key == "cal_heatmap":
        c["days"] = [dict(d) for d in chart.get("days") or []]

    elif key == "gantt":
        c["tasks"] = [dict(t) for t in chart.get("tasks") or []]

    elif key == "candlestick":
        c["candles"] = [dict(x) for x in chart.get("candles") or []]

    elif key == "sankey":
        c["nodes"] = [dict(n) for n in chart.get("nodes") or []]
        c["links"] = [dict(lk) for lk in chart.get("links") or []]

    elif key == "streamgraph":
        c["xlabels"] = [str(x) for x in chart.get("xlabels") or []]
        c["series"] = [{"name": s.get("name", ""), "values": s.get("values") or [],
                        "accent": bool(s.get("accent"))}
                       for s in chart.get("series") or []]

    elif key == "waffle":
        c["items"] = [{"label": it.get("label", ""), "value": it.get("value"),
                       "accent": bool(it.get("accent"))}
                      for it in chart.get("items") or []]

    elif key == "rose":
        raw = chart.get("sectors") or chart.get("items") or []
        c["sectors"] = [{"label": s.get("label", ""), "value": s.get("value"),
                         "accent": bool(s.get("accent"))} for s in raw]

    elif key == "choropleth":
        c["regions"] = [{"name": r.get("name", ""), "value": r.get("value")}
                        for r in chart.get("regions") or []]

    elif key == "geo_flow":
        c["points"] = [dict(p) for p in chart.get("points") or []]
        c["flows"] = [dict(f) for f in chart.get("flows") or []]

    elif key == "network":
        c["nodes"] = [dict(n) for n in chart.get("nodes") or []]
        c["edges"] = [dict(e) for e in chart.get("edges") or []]

    elif key == "sunburst":
        c["root"] = chart.get("root") or {}

    return c


def _is_valid(key: str, c: Dict[str, Any]) -> bool:
    """数据是不是真的够画——不够就回退，绝不出空白图。"""
    if key in ("hbar", "vbar"):
        vals = [b for b in c.get("bars") or [] if _num(b.get("value")) is not None]
        return len(vals) >= 1
    if key in ("dot", "lollipop", "pareto", "donut", "pie", "treemap"):
        vals = [i for i in c.get("items") or [] if _num(i.get("value")) is not None]
        return len(vals) >= 2
    if key in ("waterfall", "bridge"):
        return len([s for s in c.get("steps") or [] if _num(s.get("value")) is not None]) >= 2
    if key == "dumbbell":
        return len([i for i in c.get("items") or []
                    if _num(i.get("a")) is not None and _num(i.get("b")) is not None]) >= 1
    if key == "slope":
        pairs = [i for i in c.get("items") or []
                 if _num(i.get("a")) is not None and _num(i.get("b")) is not None]
        return len(pairs) >= 1
    if key in ("grouped_bar",):
        return len(c.get("series") or []) >= 1 and len(c.get("categories") or []) >= 1
    if key in ("stacked_bar",):
        return len(c.get("segments") or []) >= 1 and len(c.get("categories") or []) >= 1
    if key in ("line", "area"):
        ss = c.get("series") or []
        xl = c.get("xlabels") or []
        return len(ss) >= 1 and len(xl) >= 2 and all(len(s.get("values") or []) == len(xl) for s in ss)
    elif key == "heatmap":
        pass

    # ---- 分布与关系（b1） ----
    if key == "pct_stacked":
        cats, segs = c.get("categories") or [], c.get("segments") or []
        # 单条 100% 堆叠（如「全部评价」）也要能画，段数才是关键
        return (len(cats) >= 1 and len(segs) >= 2
                and all(len(s.get("values") or []) == len(cats) for s in segs))
    if key == "histogram":
        return len([v for v in c.get("values") or [] if _num(v) is not None]) >= 8
    if key in ("box", "violin", "ridgeline"):
        need = 3 if key == "box" else 4
        gs = c.get("groups") or []
        return len(gs) >= 2 and all(len(g.get("values") or []) >= need for g in gs)
    if key == "scatter":
        return len([p for p in c.get("points") or []
                    if _num(p.get("x")) is not None and _num(p.get("y")) is not None]) >= 3
    if key == "bubble":
        return len([p for p in c.get("points") or []
                    if _num(p.get("x")) is not None and _num(p.get("y")) is not None
                    and (_num(p.get("size")) or 0) > 0]) >= 3
    if key == "parallel":
        axs = c.get("axes") or []
        return len(axs) >= 3 and all(
            len(it.get("values") or []) == len(axs)
            and all(_num(v) is not None for v in it.get("values") or [])
            for it in c.get("items") or [])

    # ---- 不确定性与目标（b2） ----
    if key == "error_bar":
        return (str(c.get("err_type") or "").upper() in ("SD", "SE", "CI")
                and len([i for i in c.get("items") or []
                         if _num(i.get("value")) is not None
                         and _num(i.get("err")) is not None]) >= 2)
    if key == "forest":
        return len([i for i in c.get("items") or []
                    if _num(i.get("est")) is not None and _num(i.get("lo")) is not None
                    and _num(i.get("hi")) is not None]) >= 1
    if key == "control":
        ss, xl = c.get("series") or [], c.get("xlabels") or []
        return (bool(ss) and len(xl) >= 2
                and len(ss[0].get("values") or []) == len(xl)
                and _num(c.get("center")) is not None and _num(c.get("band")) is not None)
    if key == "funnel":
        return len([s for s in c.get("stages") or [] if _num(s.get("value")) is not None]) >= 2
    if key == "bullet":
        return _num(c.get("value")) is not None and _num(c.get("target")) is not None
    if key == "gauge":
        v, lo, hi = _num(c.get("value")), _num(c.get("min")), _num(c.get("max"))
        return v is not None and lo is not None and hi is not None and lo < hi and lo <= v <= hi
    if key == "target_band":
        ss, xl, band = c.get("series") or [], c.get("xlabels") or [], c.get("band") or {}
        return (bool(ss) and len(xl) >= 2 and len(ss[0].get("values") or []) == len(xl)
                and _num(band.get("lo")) is not None and _num(band.get("hi")) is not None)
    if key == "dual_axis":
        xl, bars, line = c.get("xlabels") or [], c.get("bars") or {}, c.get("line") or {}
        return (len(xl) >= 2 and len(bars.get("values") or []) == len(xl)
                and len(line.get("values") or []) == len(xl))
    if key == "radar":
        axs, ss = c.get("axes") or [], c.get("series") or []
        return (3 <= len(axs) <= 8 and 1 <= len(ss) <= 2
                and all(len(s.get("values") or []) == len(axs) for s in ss))

    # ---- 流程、时间与构成（b3） ----
    if key == "cal_heatmap":
        return len([d for d in c.get("days") or [] if _num(d.get("value")) is not None]) >= 14
    if key == "gantt":
        return len([t for t in c.get("tasks") or []
                    if t.get("start") and t.get("end")]) >= 2
    if key == "candlestick":
        cs = c.get("candles") or []
        return len(cs) >= 5 and all(
            _num(x.get("open")) is not None and _num(x.get("high")) is not None
            and _num(x.get("low")) is not None and _num(x.get("close")) is not None
            for x in cs)
    if key == "sankey":
        return len(c.get("nodes") or []) >= 3 and len(c.get("links") or []) >= 2
    if key == "streamgraph":
        xl, ss = c.get("xlabels") or [], c.get("series") or []
        return (len(xl) >= 3 and 2 <= len(ss) <= 6
                and all(len(s.get("values") or []) == len(xl) for s in ss))
    if key == "kpi_break":
        tr = c.get("trend") or {}
        return (_num((c.get("kpi") or {}).get("value")) is not None
                and len(tr.get("values") or []) >= 3
                and len((c.get("breakdown") or {}).get("items") or []) >= 1)
    if key == "waffle":
        return len([i for i in c.get("items") or [] if _num(i.get("value")) is not None]) >= 1
    if key == "rose":
        return 5 <= len([s for s in c.get("sectors") or []
                         if _num(s.get("value")) is not None]) <= 12

    # ---- 地理、关系与层级（b4） ----
    if key == "choropleth":
        return len(c.get("regions") or []) >= 3
    if key == "symbol_map":
        return len([p for p in c.get("points") or []
                    if _num(p.get("lon")) is not None and _num(p.get("lat")) is not None
                    and (_num(p.get("value")) or 0) >= 0]) >= 3
    if key == "geo_flow":
        pts = {str(p.get("id")) for p in c.get("points") or []}
        fl = [f for f in c.get("flows") or []
              if str(f.get("from")) in pts and str(f.get("to")) in pts
              and (_num(f.get("value")) or 0) > 0]
        return len(pts) >= 3 and len(fl) >= 1
    if key == "network":
        ids = {str(n.get("id")) for n in c.get("nodes") or []}
        es = [e for e in c.get("edges") or []
              if str(e.get("a")) in ids and str(e.get("b")) in ids]
        return len(ids) >= 3 and len(es) >= 1
    if key == "sunburst":
        ch = (c.get("root") or {}).get("children") or []
        return 2 <= len(ch) <= 8 and all((_num(x.get("value")) or 0) > 0 for x in ch)

    if key == "small_mult":
        return len([p for p in c.get("panels") or [] if p.get("values")]) >= 2
    return True


def supports(key: str) -> bool:
    return str(key) in RENDERERS


def render(chart: Dict[str, Any], theme: str = "paper") -> Optional[str]:
    """渲染成内联 SVG；不支持的图型/数据不够就返回 None（调用方回退 v1）。

    chart["_embed"]=True 表示嵌在报告图卡里（外框已有标题/单位/来源）。
    """
    key = str(chart.get("type") or "")
    fn = RENDERERS.get(key)
    if fn is None:
        return None
    c = _normalize(key, chart)
    if not _is_valid(key, c):
        return None
    from . import base as _base
    _base.EMBED = bool(chart.get("_embed"))
    try:
        return fn(c, theme)
    except Exception:
        return None
    finally:
        _base.EMBED = False
