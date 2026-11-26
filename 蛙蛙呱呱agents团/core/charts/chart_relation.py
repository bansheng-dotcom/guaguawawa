# -*- coding: utf-8 -*-
"""关系 → 图型适配器：没有对应 payload 就不硬画。

关系词用 FT Visual Vocabulary 的九类：deviation / correlation / ranking /
distribution / change_over_time / composition / magnitude / spatial / flow。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


_COMPAT = {
    "ranking": ("dot", "hbar", "vbar"),
    "comparison": ("dot", "hbar", "vbar"),
    "magnitude": ("vbar", "hbar", "dot"),
    "composition": ("share_bar", "pct_stacked", "stacked_bar", "treemap"),
    "change_over_time": ("line", "area", "vbar"),
    "distribution": ("histogram", "box", "dot"),
    "deviation": ("dot", "hbar", "waterfall"),
    "spatial": ("choropleth", "symbol_map", "heatmap"),
    "flow": ("funnel", "sankey", "waterfall"),
    "network": ("network", "sankey"),
    "correlation": ("scatter", "heatmap", "bubble"),
}


def relations() -> List[str]:
    return list(_COMPAT)


def _has_period(items: List[Dict[str, Any]]) -> bool:
    return any(str(x.get("period") or "").strip() for x in items)


def _has_geo(items: List[Dict[str, Any]]) -> bool:
    # 2026-11-22 清理：只看通用地理后缀（省/市/区/县/州/盟）+ 项目配置的地名表，
    # 不再内置具体省份/城市名。
    keys = ("省", "市", "区", "县", "州", "盟")
    try:
        from core.data.data_model import CITY_TOKENS  # noqa: PLC0415
        keys = keys + tuple(CITY_TOKENS)
    except Exception:  # noqa: BLE001
        pass
    return any(any(k in str(x.get("label") or "") for k in keys) for x in items)


def adapt(relation: str, items: List[Dict[str, Any]],
          title: str = "", unit: str = "",
          payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """按关系把 items 适配成图型；payload 不够就返回 None。"""
    rel = str(relation or "").strip()
    if rel not in _COMPAT or len(items) < 2:
        return None
    labels = [str(x.get("label") or "") for x in items]
    values = [float(x.get("value") or 0) for x in items]
    base = {"title": title, "unit_meta": unit,
            "relation": rel, "refs": [x.get("ref") for x in items if x.get("ref")]}

    if rel in ("composition",):
        # 份额条：能直接读“占多少”；不是所有构成都能加总，作者需保证
        return {**base, "type": "share_bar", "items": items}
    if rel in ("flow",):
        if payload and payload.get("links") and payload.get("nodes"):
            return {**base, "type": "sankey", "nodes": payload["nodes"],
                    "links": payload["links"]}
        return {**base, "type": "funnel",
                "stages": [{"label": l, "value": v} for l, v in zip(labels, values)]}
    if rel in ("network",):
        if payload and payload.get("nodes") and payload.get("edges"):
            return {**base, "type": "network", "nodes": payload["nodes"],
                    "edges": payload["edges"]}
        return None
    if rel in ("change_over_time",):
        if not _has_period(items):
            # 没有期次就不假装趋势，退化为比较
            return {**base, "type": "dot", "items": items}
        return {**base, "type": "line",
                "points": [{"label": l, "value": v} for l, v in zip(labels, values)]}
    if rel in ("spatial",):
        if not _has_geo(items):
            return None
        return {**base, "type": "choropleth",
                "values": {l: v for l, v in zip(labels, values)}}
    if rel in ("distribution",):
        return {**base, "type": "dot", "items": items}
    if rel in ("correlation",):
        pts = (payload or {}).get("points") or []
        if pts and all(isinstance(p, dict) and "x" in p and "y" in p for p in pts):
            return {**base, "type": "scatter", "points": pts}
        # 只有一组 y 值，没有 x，不画散点
        return None
    # ranking / comparison / magnitude / deviation
    return {**base, "type": "dot", "items": items}
