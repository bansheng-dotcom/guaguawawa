# -*- coding: utf-8 -*-
"""core.charts.chart_query —— 图表层：面板 → 查询 → 按形状选图。

SOP v5：
    图不是“画”出来的，是查询结果的编码。
    形状决定图型：矩阵→热力、排序→条、趋势→线、构成→占比、分布→直方。

硬规则：
    1. 图的数据点 = 查询返回行数（top-N 要在 note 里写明“仅列前 N”）；
    2. 标题必须含数字（结论式标题）；
    3. 图必须带来源 refs 与一句 note（极值/差距）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

MAX_TOP = 10


def _f(r: Dict[str, Any]) -> float:
    try:
        return float(r.get("value") or 0)
    except (TypeError, ValueError):
        return 0.0


def _rows(rows: List[Dict[str, Any]], metric_id: Optional[str]) -> List[Dict[str, Any]]:
    return [r for r in rows if not metric_id or str(r.get("metric_id")) == metric_id]


def plan(rows: List[Dict[str, Any]],
         metric_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    rs = _rows(rows, metric_id)
    if len(rs) < 2:
        return None
    periods = sorted({str(r.get("period")) for r in rs})
    entities = sorted({str(r.get("entity")) for r in rs if r.get("entity")})
    segments = sorted({str(r.get("segment")) for r in rs if r.get("segment")})
    vals = [_f(r) for r in rs]
    total = sum(vals)
    if len(segments) >= 2 and len(entities) >= 2:
        return {"kind": "matrix", "entities": entities, "segments": segments}
    if len(periods) >= 3 and len(entities) <= 2:
        return {"kind": "trend", "periods": periods}
    if len(vals) >= 4 and 88 <= total <= 112:
        return {"kind": "composition"}
    if len(entities) >= 4:
        return {"kind": "rank"}
    return {"kind": "bar"}


def build(rows: List[Dict[str, Any]], metric_id: Optional[str] = None,
          title: str = "") -> Optional[Dict[str, Any]]:
    rs = _rows(rows, metric_id)
    p = plan(rows, metric_id)
    if not p:
        return None
    unit = str(rs[0].get("unit") or "")
    refs = [r.get("number_id") for r in rs if r.get("number_id")]
    vals = [_f(r) for r in rs]
    hi, lo = max(vals), min(vals)
    ratio = (hi / lo) if lo else 0
    base_title = title or str(rs[0].get("metric_name") or "指标")
    head = f"{base_title}：最高 {hi:g}{unit}，最低 {lo:g}{unit}"
    if ratio:
        head += f"，差 {ratio:.1f} 倍"
    kind = p["kind"]

    if kind == "matrix":
        idx_e = {e: i for i, e in enumerate(p["entities"])}
        idx_s = {s: j for j, s in enumerate(p["segments"])}
        matrix = [[None for _ in p["segments"]] for _ in p["entities"]]
        bucket: Dict[tuple, List[float]] = {}
        for r in rs:
            i, j = idx_e.get(str(r.get("entity"))), idx_s.get(str(r.get("segment")))
            if i is None or j is None:
                continue
            bucket.setdefault((i, j), []).append(_f(r))
        for (i, j), vs in bucket.items():
            matrix[i][j] = round(sum(vs) / len(vs), 4)
        return {"type": "heatmap", "origin": "panel_query", "title": head, "unit_meta": unit,
                "rows": p["entities"], "cols": p["segments"], "matrix": matrix,
                "refs": refs,
                "note": f"矩阵 {len(p['entities'])}×{len(p['segments'])}；空白=该格无数据"}

    if kind == "trend":
        pts: Dict[str, List[float]] = {}
        for r in rs:
            pts.setdefault(str(r.get("period")), []).append(_f(r))
        points = [{"label": k, "value": round(sum(v) / len(v), 4)}
                  for k, v in sorted(pts.items())]
        first, last = points[0]["value"], points[-1]["value"]
        delta = f"，{last - first:+.1f}{unit}" if first else ""
        return {"type": "line", "origin": "panel_query", "title": head + delta, "unit_meta": unit,
                "points": points, "refs": refs,
                "note": f"{len(points)} 个期次；首末变化 {last - first:+.1f}{unit}"}

    if kind == "composition":
        items = [{"label": str(r.get("entity")), "value": _f(r)} for r in rs]
        items.sort(key=lambda x: -x["value"])
        return {"type": "share_bar", "origin": "panel_query", "title": head, "unit_meta": unit,
                "items": items, "refs": refs,
                "note": f"{len(items)} 项，合计 {sum(vals):g}{unit}"}

    items = [{"label": str(r.get("entity")), "value": _f(r)} for r in rs]
    items.sort(key=lambda x: -x["value"])
    top = items[:MAX_TOP]
    typ = "hbar" if len(top) >= 4 else "vbar"
    return {"type": typ, "origin": "panel_query", "title": head, "unit_meta": unit,
            "items": top, "refs": refs,
            "accent_note": f"最高 {hi:g}{unit} / 最低 {lo:g}{unit}" +
                           (f"（仅列前 {len(top)}）" if len(items) > len(top) else ""),
            "note": f"共 {len(items)} 个主体"}
