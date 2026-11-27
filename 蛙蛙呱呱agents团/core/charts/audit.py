# -*- coding: utf-8 -*-
"""core.charts.audit —— 图表六维审计（T10）。

为什么需要它：
    仓库已经能“画”48 型图，但缺“怎么验收”。本模块给每张图 6 项确定性检查，
    任一项不过即扣分；报告链与图谱教学共用同一把尺子：

    1. data_drawable   数据可画：payload 非空且至少有一个数值
    2. chart_fit       图合适：该型的使用纪律（饼图 ≤5 类、分组 ≤3 系列…）
    3. calc_correct    计算正确：占比加总、瀑布算术、漏斗单调、K 线开高低收
    4. labels_clear    标注清楚：有标题/标签，SVG 有文字或 payload 自带标签
    5. visual_professional 视觉专业：viewBox、无渐变、无斜体、配色 ≤8 色
    6. return_contract 返回正确：SVG 起止标签完整、非空

同时提供难度分级：
    - quick  ：基础比较/趋势/构成，教学与快报默认；
    - guided ：统计/空间/流程等复杂型，生产默认 guided。

用法：
    from core.charts.audit import audit, level_of
    r = audit("line", {"points": [...]}, svg)
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Tuple

#: 48 型难度分级（quick = 教学/快报可直接用；其余 guided）
QUICK = {
    "vbar", "hbar", "line", "area", "pie", "donut", "histogram",
    "grouped_bar", "stacked_bar", "pct_stacked", "scatter", "kpi_break",
    "table", "funnel", "waterfall", "share_bar", "dot", "lollipop",
}

#: 各型的“使用纪律”硬约束（chart_fit）
FIT_RULES: Dict[str, Dict[str, Any]] = {
    "pie": {"max_items": 5},
    "donut": {"max_items": 5},
    "share_bar": {"max_items": 8},
    "grouped_bar": {"max_series": 3},
    "stacked_bar": {"max_series": 5},
    "pct_stacked": {"max_series": 5},
    "line": {"min_points": 3},
    "area": {"min_points": 3},
    "streamgraph": {"max_series": 6, "non_negative": True},
    "candlestick": {"ohlc_valid": True},
    "funnel": {"monotonic": True},
    "waterfall": {"waterfall_arithmetic": True},
}


def level_of(key: str) -> str:
    """图型难度分级：quick / guided。"""
    return "quick" if key in QUICK else "guided"


def _numbers(obj: Any) -> List[float]:
    out: List[float] = []
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_numbers(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(_numbers(v))
    return out


def _payload_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    for k in ("items", "points", "stages", "rows", "groups", "candles", "ohlc"):
        v = payload.get(k)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v
    return []


#: 连续色阶图型：颜色数量本身就是数据编码，不做 ≤8 色限制
CONTINUOUS_SCALES = {"cal_heatmap", "heatmap", "ym_heat", "choropleth",
                     "symbol_map", "geo_flow"}


def _check(cid: str, ok: bool, msg: str, severity: str = "CRITICAL") -> Dict[str, Any]:
    return {"id": cid, "ok": bool(ok), "msg": msg,
            "severity": "OK" if ok else severity}


def _fit(key: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    rule = FIT_RULES.get(key)
    if not rule:
        return True, "无该型专属纪律"
    items = _payload_items(payload)
    series = payload.get("series") or []
    if "max_items" in rule and len(items) > rule["max_items"]:
        return False, f"{key} 类别 {len(items)} > {rule['max_items']}，先合并小项"
    if "max_series" in rule and len(series) > rule["max_series"]:
        return False, f"{key} 系列 {len(series)} > {rule['max_series']}"
    pts = payload.get("points") or []
    if "min_points" in rule and len(pts) < rule["min_points"]:
        return False, f"{key} 数据点 {len(pts)} < {rule['min_points']}，趋势不可读"
    if rule.get("non_negative"):
        vals = _numbers(series)
        if any(v < 0 for v in vals):
            return False, f"{key} 出现负值，流图不适用"
    if rule.get("monotonic"):
        vals = [float(x.get("value", 0)) for x in items]
        if any(b > a + 1e-9 for a, b in zip(vals, vals[1:])):
            return False, "漏斗各阶段必须单调不增"
    return True, "符合该型使用纪律"


def _calc(key: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    if key in ("candlestick",):
        for i, c in enumerate(payload.get("ohlc") or []):
            o, h, l, cl = c.get("o"), c.get("h"), c.get("l"), c.get("c")
            if None in (o, h, l, cl) or not (h >= max(o, cl) and l <= min(o, cl)):
                return False, f"第 {i + 1} 根 K 线开高低收关系非法"
        return True, "OHLC 关系成立"
    if key == "waterfall" or ("start" in payload and "deltas" in payload):
        start = float(payload.get("start", 0))
        deltas = [float(d.get("value", 0)) for d in payload.get("deltas") or []]
        end = payload.get("end")
        calc = start + sum(deltas)
        if end is not None and abs(calc - float(end)) > max(0.01, abs(float(end)) * 0.01):
            return False, f"瀑布算术不闭合：{start}+{sum(deltas):.2f}≠{end}"
        return True, "瀑布算术闭合"
    if key == "funnel":
        vals = [float(x.get("value", 0)) for x in payload.get("stages") or []]
        if any(b > a + 1e-9 for a, b in zip(vals, vals[1:])):
            return False, "漏斗阶段出现回升，口径可能不一致"
        return True, "漏斗单调"
    if payload.get("unit_meta") in ("%", "百分比", "占比") or payload.get("expect_total") is not None:
        vals = [float(x.get("value", 0)) for x in _payload_items(payload)]
        if vals:
            total = sum(vals)
            want = float(payload.get("expect_total", 100))
            if abs(total - want) > max(0.5, abs(want) * 0.01):
                return False, f"占比加总 {total:.1f} ≠ {want:g}"
            return True, f"占比加总 {total:.1f}"
    return True, "无求和类计算需要复核"


def _labels(payload: Dict[str, Any], svg: str) -> Tuple[bool, str]:
    items = _payload_items(payload)
    has_payload_label = any(("label" in x or "name" in x) for x in items)
    has_payload_label = has_payload_label or bool(payload.get("xlabels"))
    vals = payload.get("values")
    if isinstance(vals, dict) and vals:
        has_payload_label = True
    has_text = "<text" in (svg or "")
    if not (has_payload_label or has_text):
        return False, "既无数据标签，也没有 SVG 文字"
    return True, "标签可读"


def _visual(key: str, svg: str) -> Tuple[bool, str]:
    if not svg:
        return False, "没有 SVG"
    if "<svg" not in svg or 'viewBox="' not in svg:
        return False, "SVG 缺 viewBox"
    if re.search(r"linear-gradient|radial-gradient", svg, re.I):
        return False, "SVG 使用渐变"
    if re.search(r"font-style\s*:\s*italic|<i[ >]", svg, re.I):
        return False, "SVG 使用斜体"
    colors = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}", svg)}
    if key not in CONTINUOUS_SCALES and len(colors) > 8:
        return False, f"配色 {len(colors)} 种 > 8"
    return True, f"配色 {len(colors)} 种，viewBox 就绪"


def _contract(svg: str) -> Tuple[bool, str]:
    if not svg:
        return False, "返回空 SVG"
    if "<svg" not in svg or "</svg>" not in svg:
        return False, "SVG 起止标签不完整"
    if len(svg) < 80:
        return False, "SVG 过短，疑似空图"
    return True, "返回契约成立"


def audit(key: str, payload: Dict[str, Any], svg: str = "") -> Dict[str, Any]:
    """对单张图做六维审计；返回 checks/score/ok/level。"""
    payload = payload or {}
    nums = _numbers(payload)
    checks = [
        _check("data_drawable", bool(payload) and bool(nums),
               f"数值 {len(nums)} 个" if nums else "payload 无数值"),
        _check("chart_fit", *_fit(key, payload)),
        _check("calc_correct", *_calc(key, payload)),
        _check("labels_clear", *_labels(payload, svg), severity="WARN"),
        _check("visual_professional", *_visual(key, svg) if svg else (True, "未提供 SVG，跳过"),
               severity="WARN"),
        _check("return_contract", *_contract(svg) if svg else (True, "未提供 SVG，跳过")),
    ]
    passed = sum(1 for c in checks if c["ok"])
    score = round(passed / len(checks) * 100, 1)
    return {"chart": key, "level": level_of(key), "checks": checks,
            "score": score, "ok": passed == len(checks)}


def audit_many(cases: Iterable[Tuple[str, Dict[str, Any], str]]) -> Dict[str, Any]:
    rows = [audit(k, p, s) for k, p, s in cases]
    bad = [r for r in rows if not r["ok"]]
    return {"count": len(rows), "ok": not bad,
            "score": round(sum(r["score"] for r in rows) / len(rows), 1) if rows else 0,
            "failed": [{"chart": r["chart"], "score": r["score"],
                        "errors": [c["msg"] for c in r["checks"] if not c["ok"]]}
                       for r in bad],
            "rows": rows}
