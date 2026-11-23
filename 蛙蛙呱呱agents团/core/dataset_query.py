# -*- coding: utf-8 -*-
"""core.dataset_query —— 在数据集上执行查询、并转成图（DATA-LAYER-SOP v2.0 · S5）。

**图从数据集画，不经过格子的 value。**

    rows → run(ds, query, rows) → 分组聚合
         → to_chart(ds, query, rows, spec) → chart payload

聚合方式由数据集列上的 `agg` 决定（sum / mean / count），不从字段名猜。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from core import dataset as _ds


def _agg_map(ds: Dict[str, Any]) -> Dict[str, str]:
    return {str(c.get("name")): str(c.get("agg") or "sum")
            for c in ds.get("columns") or []}


def _unit(ds: Dict[str, Any], col: str) -> str:
    for c in ds.get("columns") or []:
        if str(c.get("name")) == col:
            return str(c.get("unit") or "")
    return ""


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:  # noqa: BLE001
        return None


def run(ds: Dict[str, Any], query: Dict[str, Any],
        rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """执行 filters → group_by → metrics 聚合。"""
    q = query or {}
    filters = dict(q.get("filters") or {})
    gb = list(q.get("group_by") or [])
    metrics = list(q.get("metrics") or [])
    aggs = _agg_map(ds)

    kept: List[Dict[str, Any]] = []
    for r in rows or []:
        ok = True
        for k, want in filters.items():
            got = r.get(k)
            if isinstance(want, (list, tuple, set)):
                if got not in want:
                    ok = False
                    break
            elif got != want:
                ok = False
                break
        if ok:
            kept.append(r)

    buckets: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for r in kept:
        buckets[tuple(r.get(c) for c in gb)].append(r)

    out: List[Dict[str, Any]] = []
    for key, rs in sorted(buckets.items(), key=lambda kv: str(kv[0])):
        vals: Dict[str, float] = {}
        for col in metrics:
            nums = [x for x in (_num(r.get(col)) for r in rs) if x is not None]
            if not nums:
                continue
            how = aggs.get(col, "sum")
            if how == "mean":
                vals[col] = round(sum(nums) / len(nums), 4)
            elif how == "count":
                vals[col] = float(len(nums))
            else:
                vals[col] = round(sum(nums), 4)
        out.append({"group": dict(zip(gb, key)), "metrics": vals, "n": len(rs)})
    return out


def _num_fmt(v: float, unit: str) -> str:
    s = ("%.1f" % v) if abs(v) >= 10 else ("%.2f" % v)
    return s + (unit or "")


def to_chart(ds: Dict[str, Any], query: Dict[str, Any],
             rows: List[Dict[str, Any]], spec: Dict[str, Any]) -> Dict[str, Any]:
    """把查询结果转成图型 payload；画不出就返回 {}（上层走 chart_skip_reason）。

    报告级图要求：标题即结论（带数字）、有基线、有标注、点数够。
    """
    spec = spec or {}
    typ = str(spec.get("type") or "")
    x = str(spec.get("x") or "")
    metric = str(spec.get("metric") or (query or {}).get("metrics", [""])[0])
    if not typ or not x or not metric:
        return {}
    res = run(ds, query, rows)
    if len(res) < 2:
        return {}
    unit = _unit(ds, metric)
    cat = (str(ds.get("id") or "").split("-")[1]
           if "-" in str(ds.get("id") or "") else "")
    src = str((ds.get("source") or {}).get("kind") or "数据集")

    if typ in ("hbar", "vbar"):
        items = [{"label": str(r["group"].get(x)), "value": r["metrics"].get(metric)}
                 for r in res if r["metrics"].get(metric) is not None]
        if len(items) < 3:
            return {}
        top = max(items, key=lambda i: i["value"])
        low = min(items, key=lambda i: i["value"])
        vals = [i["value"] for i in items]
        base = sum(vals) / len(vals)
        return {"type": typ,
                "title": "%s %s：%s %s 最高，最低 %s（差 %.1f 倍）"
                         % (cat, metric, top["label"], _num_fmt(top["value"], unit),
                            _num_fmt(low["value"], unit),
                            (top["value"] / low["value"]) if low["value"] else 0),
                "unit_meta": unit, "source": src, "items": items,
                "baseline": "均值 %s" % _num_fmt(base, unit),
                "annotate": "%s %s" % (top["label"], _num_fmt(top["value"], unit))}

    if typ == "line":
        # 合同要求 line 的 points 是 {label, value}（不是 {x, y}）
        points = [{"label": str(r["group"].get(x)), "value": r["metrics"].get(metric)}
                  for r in res if r["metrics"].get(metric) is not None]
        if len(points) < 3:
            return {}
        hi = max(points, key=lambda p: p["value"])
        lo = min(points, key=lambda p: p["value"])
        return {"type": "line",
                "title": "%s %s：最高 %s（%s），最低 %s（%s）"
                         % (cat, metric, _num_fmt(hi["value"], unit), hi["label"],
                            _num_fmt(lo["value"], unit), lo["label"]),
                "unit_meta": unit, "source": src, "points": points,
                "baseline": "首期 %s" % _num_fmt(points[0]["value"], unit),
                "annotate": "%s %s" % (hi["label"], _num_fmt(hi["value"], unit))}

    if typ in ("stacked", "stacked_bar"):
        series_key = str(spec.get("series") or "")
        if not series_key:
            return {}
        xs: List[str] = []
        series: Dict[str, List[float]] = {}
        for r in res:
            xv = str(r["group"].get(x))
            sv = str(r["group"].get(series_key))
            if xv not in xs:
                xs.append(xv)
            series.setdefault(sv, [0.0] * len(xs))
            while len(series[sv]) < len(xs):
                series[sv].append(0.0)
            v = r["metrics"].get(metric)
            if v is not None:
                series[sv][xs.index(xv)] += float(v)
        if len(xs) < 3 or len(series) < 2:
            return {}
        first, last = xs[0], xs[-1]
        names = list(series)
        top_name = max(names, key=lambda k: series[k][-1])
        delta = series[top_name][-1] - series[top_name][0]
        return {"type": "stacked_bar",
                "title": "%s %s：%s 份额 %s→%s（%.1f 个点）"
                         % (cat, metric, top_name,
                            _num_fmt(series[top_name][0], unit),
                            _num_fmt(series[top_name][-1], unit), delta),
                "unit_meta": unit, "source": src, "xlabels": xs,
                "series": [{"name": k, "values": [round(v, 4) for v in vs]}
                           for k, vs in series.items()],
                "baseline": "首期 %s" % first,
                "annotate": "末期 %s" % last}

    return {}


def feasible(ds: Dict[str, Any], query: Dict[str, Any],
             rows: List[Dict[str, Any]], spec: Dict[str, Any]) -> Dict[str, Any]:
    """试画一次，返回 {ok, chart, rows_used, why}。"""
    res = run(ds, query, rows)
    ch = to_chart(ds, query, rows, spec)
    return {"ok": bool(ch), "chart": ch, "rows_used": len(res),
            "why": "" if ch else "分组后不足 3 个可比点（画不出关系）"}
