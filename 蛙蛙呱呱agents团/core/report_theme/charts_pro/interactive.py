# -*- coding: utf-8 -*-
"""charts_pro.interactive —— ECharts 交互后端（P5-4，可选）。

定位：**不是替换** SVG 产线，而是给 HTML 报告多一个可交互后端。
    GUAGUA_CHART_BACKEND=echarts   → 优先输出 ECharts；不支持的类型回退 SVG
    默认                           → 仍走静态 SVG（零破坏）

零依赖边界：JSON 与 HTML 都由标准库生成；`echarts.min.js` 走 CDN，
且每张图都带**静态 SVG 兜底**——JS 未执行（PDF/断网/打印）时读者看到的就是原图。

交互能力：tooltip、图例开关（多序列）、dataZoom（类别多时）、热力图 visualMap。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .. import tokens
from . import layout, spec as pro_spec

ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"

_ITEMS = {"hbar", "vbar", "lollipop", "pareto", "share_bar", "diverging",
          "treemap", "waffle", "sunburst", "rose", "dot"}
_PIE = {"pie", "donut"}


def supported(chart_type: str) -> bool:
    t = pro_spec.ALIASES.get(str(chart_type), str(chart_type))
    return t in (_ITEMS | _PIE | {"line", "area", "multi_line", "scatter",
                                 "heatmap", "funnel", "grouped", "stacked"})


def _color(i: int) -> str:
    c = tokens.DEFAULT_TOKENS["color"]
    palette = [c["ink"], c["accent"], c["blue"], c["muted"], c["faint"], c["line2"]]
    return palette[i % len(palette)]


def _items(s: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for it in s.get("items") or s.get("points") or []:
        if isinstance(it, dict) and it.get("value") is not None:
            out.append({"label": str(it.get("label") or it.get("name") or ""),
                        "value": float(it.get("value") or 0)})
    return out


def to_option(prepared: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Layout 预处理后的 spec → ECharts option；不支持的类型返回 None。"""
    s = prepared
    t = str(s.get("type") or "")
    dec = int((s.get(layout.LAYOUT_KEY) or {}).get("decimals") or 1)
    unit = str(s.get("unit") or s.get("unit_meta") or "")
    fmt = "{value} " + unit if unit else "{value}"

    if t in _ITEMS:
        items = _items(s)
        if not items:
            return None
        labels = [x["label"] for x in items]
        vals = [x["value"] for x in items]
        horizontal = t in ("hbar", "lollipop", "pareto", "share_bar", "diverging")
        cat = {"type": "category", "data": labels,
               "axisLabel": {"fontSize": 11, "interval": 0}}
        val = {"type": "value", "axisLabel": {"fontSize": 10}}
        opt: Dict[str, Any] = {
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"},
                        "valueFormatter": None},
            "grid": {"left": 100, "right": 30, "top": 20, "bottom": 40},
            "series": [{"type": "bar",
                        "data": [{"value": v,
                                  "itemStyle": {"color": _color(i)}}
                                 for i, v in enumerate(vals)],
                        "barMaxWidth": 26}],
            "animation": False,
        }
        if t == "treemap":
            opt["series"] = [{"type": "treemap", "data": [
                {"name": x["label"], "value": abs(x["value"])} for x in items]}]
            opt.pop("grid", None)
            opt["tooltip"] = {"trigger": "item"}
        elif t == "sunburst":
            opt["series"] = [{"type": "sunburst", "data": [
                {"name": x["label"], "value": abs(x["value"])} for x in items]}]
            opt.pop("grid", None)
            opt["tooltip"] = {"trigger": "item"}
        elif horizontal:
            opt["yAxis"] = cat
            opt["xAxis"] = {**val, "axisLabel": {"fontSize": 10, "formatter": fmt}}
            if t in ("pareto", "diverging"):
                opt["xAxis"] = val
            else:
                opt["xAxis"] = val
        else:
            opt["xAxis"] = cat
            opt["yAxis"] = val
        # tooltip 里带单位；多类别给缩放
        opt["tooltip"]["valueFormatter"] = ("function(v){return v+' " + unit + "'}"
                                            if unit else "function(v){return v}")
        if len(items) > 12:
            opt["dataZoom"] = [{"type": "inside"}, {"type": "slider", "height": 14}]
        # 横向条的目标线
        if s.get("ref") is not None and horizontal:
            opt["series"].append({"type": "line", "data": [],
                                  "markLine": {"silent": True, "data": [
                                      {"xAxis": float(s["ref"]),
                                       "label": {"formatter": str(s.get("ref_label") or "参照")}}]}})
        return opt

    if t in _PIE:
        items = _items(s)
        if not items:
            return None
        radius = ["45%", "68%"] if t == "donut" else "68%"
        return {
            "tooltip": {"trigger": "item",
                        "valueFormatter": ("function(v){return v+' " + unit + "'}"
                                           if unit else None)},
            "legend": {"bottom": 0, "textStyle": {"fontSize": 10}},
            "series": [{"type": "pie", "radius": radius, "center": ["50%", "45%"],
                        "data": [{"name": x["label"], "value": x["value"],
                                  "itemStyle": {"color": _color(i)}}
                                 for i, x in enumerate(items)],
                        "label": {"fontSize": 10}}],
            "animation": False,
        }

    if t in ("line", "area", "multi_line"):
        ser = s.get("series") or []
        if ser:
            xs = [str(x) for x in (s.get("stages") or s.get("categories")
                                   or (ser[0].get("labels") if ser else []) or [])]
            series = []
            for i, one in enumerate(ser):
                series.append({"type": "line", "name": str(one.get("name") or ""),
                               "data": [float(v) for v in one.get("values") or []],
                               "smooth": False, "symbolSize": 5,
                               "lineStyle": {"color": _color(i)},
                               "itemStyle": {"color": _color(i)}})
            if not xs:
                xs = [str(i + 1) for i in range(len(series[0]["data"]))]
            return {"tooltip": {"trigger": "axis"}, "legend": {"top": 0},
                    "grid": {"left": 40, "right": 20, "top": 30, "bottom": 30},
                    "xAxis": {"type": "category", "data": xs},
                    "yAxis": {"type": "value"},
                    "series": series, "animation": False}
        pts = s.get("points") or []
        if not pts:
            return None
        xs = [str(p.get("label") or i) for i, p in enumerate(pts)]
        ys = [float(p.get("value") or 0) for p in pts]
        area = {"areaStyle": {}} if t == "area" else {}
        return {"tooltip": {"trigger": "axis"},
                "grid": {"left": 48, "right": 20, "top": 20, "bottom": 34},
                "xAxis": {"type": "category", "data": xs},
                "yAxis": {"type": "value",
                          "axisLabel": {"formatter": fmt} if unit else {}},
                "series": [{"type": "line", "data": ys, "smooth": False,
                            "lineStyle": {"color": _color(0)},
                            "itemStyle": {"color": _color(0)}, **area}],
                "animation": False}

    if t == "scatter":
        pts = s.get("points") or []
        if not pts:
            return None
        data = [[float(p.get("x", 0)), float(p.get("y", 0)),
                 str(p.get("label") or "")] for p in pts]
        return {"tooltip": {"trigger": "item"},
                "grid": {"left": 48, "right": 20, "top": 20, "bottom": 34},
                "xAxis": {"type": "value"}, "yAxis": {"type": "value"},
                "series": [{"type": "scatter", "data": data,
                            "itemStyle": {"color": _color(1)}}],
                "animation": False}

    if t == "heatmap":
        rows, cols, mat = s.get("rows") or [], s.get("cols") or [], s.get("matrix") or []
        if not (rows and cols and mat):
            return None
        data = []
        for i, r in enumerate(mat):
            for j, v in enumerate(r):
                data.append([j, i, float(v)])
        vals = [x[2] for x in data]
        return {"tooltip": {"trigger": "item"},
                "grid": {"left": 70, "right": 30, "top": 20, "bottom": 50},
                "xAxis": {"type": "category", "data": [str(c) for c in cols]},
                "yAxis": {"type": "category", "data": [str(r) for r in rows]},
                "visualMap": {"min": min(vals), "max": max(vals), "calculable": True,
                              "orient": "horizontal", "left": "center", "bottom": 0},
                "series": [{"type": "heatmap", "data": data}],
                "animation": False}

    if t == "funnel":
        items = s.get("stages") or []
        if not items:
            return None
        return {"tooltip": {"trigger": "item"},
                "series": [{"type": "funnel", "data": [
                    {"name": str(x.get("label", "")), "value": float(x.get("value", 0))}
                    for x in items]}], "animation": False}

    return None


def _fallback_svg(s: Dict[str, Any]) -> str:
    try:
        return pro_spec.render(s)
    except Exception:  # noqa: BLE001 兜底失败就空着，不阻断报告
        return ""


def render_spec(spec_in: Dict[str, Any], cdn: str = ECHARTS_CDN) -> Optional[str]:
    """canonical spec（type + items/points/...）→ ECharts HTML；不支持返回 None。"""
    s = layout.prepare(dict(spec_in or {}))
    opt = to_option(s)
    if not opt:
        return None
    key = hashlib.sha1(json.dumps(opt, ensure_ascii=False, sort_keys=True)
                       .encode("utf-8")).hexdigest()[:8]
    eid, fid = "ec-" + key, "ecf-" + key
    fb = _fallback_svg(s)
    payload = json.dumps(opt, ensure_ascii=False).replace("</", "<\\/")
    return f"""
<div class="echart-wrap" data-engine="echarts">
  <div class="echart" id="{eid}" style="width:100%;height:280px"></div>
  <div class="echart-fallback" id="{fid}">{fb}</div>
</div>
<script src="{cdn}"></script>
<script>(function(){{var el=document.getElementById('{eid}');if(!window.echarts||!el)return;
var f=document.getElementById('{fid}');if(f)f.style.display='none';
var c=window.echarts.init(el);c.setOption({payload});
window.addEventListener('resize',function(){{c.resize()}});}})();</script>"""


def render_chart(chart: Dict[str, Any], theme: str = "paper",
                 cdn: str = ECHARTS_CDN) -> Optional[str]:
    """旧 chart dict → ECharts HTML；映射不了返回 None（调用方回退 SVG）。"""
    from . import compat
    s = compat.to_spec(chart)
    if not s:
        return None
    s = dict(s)
    if not s.get("unit") and (chart.get("unit_meta") or chart.get("unit")):
        s["unit"] = str(chart.get("unit_meta") or chart.get("unit"))
    return render_spec(s, cdn)
