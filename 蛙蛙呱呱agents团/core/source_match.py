# -*- coding: utf-8 -*-
"""core.source_match —— 需求 × 源 匹配（DERIVATION-SOP v4.0 · 第 3 步）。

这是经典的数据集成问题「view matching」：给定一个查询需求
（度量 + 粒度 + 维度），判断哪个源能回答它。

两个目录（都是**业务无关**的通用规则）：

    DERIVE_CATALOG   维度怎么从源字段派生（brand←title / month←snapshot_date）
    MEASURE_CATALOG  度量怎么用源字段算（asp=mean(price) / gmv=sum(price*sales)）

匹配结果三态：
    full     所有维度都能拿到（直取或派生），且有历史
    partial  缺维度、或源只能采当下（needs_series 时不满足）
    none     关键维度都拿不到
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core import source_profile as sp

SCHEMA = "dsh.source_match/v1"

# 维度派生目录：dim → {from: [候选源字段], rule: derive DSL, confidence}
DERIVE_CATALOG: Dict[str, Dict[str, Any]] = {
    "brand": {"from": ["title"], "rule": "token:title:0", "confidence": "low"},
    "category": {"from": ["title"], "rule": "token:title:1", "confidence": "low"},
    "month": {"from": ["snapshot_date", "date"],
              "rule": "substr:snapshot_date:0:7", "confidence": "high"},
    "year": {"from": ["snapshot_date", "date"],
             "rule": "substr:snapshot_date:0:4", "confidence": "high"},
    "price_band": {"from": ["price"],
                   "rule": "bucket:price:39,99:低价带,中价带,高价带",
                   "confidence": "medium"},
    "city": {"from": ["city"], "rule": "field:city", "confidence": "high"},
}

# 度量计算目录：measure → {agg, expr, unit, requires}
MEASURE_CATALOG: Dict[str, Dict[str, Any]] = {
    "asp": {"agg": "mean", "expr": "price", "unit": "元",
            "requires": ["price"]},
    "gmv": {"agg": "sum", "expr": "price * sales_30d", "unit": "元",
            "requires": ["price", "sales_30d"]},
    "sales_volume": {"agg": "sum", "expr": "sales_30d", "unit": "件",
                     "requires": ["sales_30d"]},
    "discount_rate": {"agg": "mean", "expr": "1 - price / list_price", "unit": "%",
                      "requires": ["price", "list_price"]},
    "price": {"agg": "mean", "expr": "price", "unit": "元",
              "requires": ["price"]},
}

SERIES_DIMS = ("year", "month", "quarter", "week", "day")


def _dim_plan(dim: str, source: Dict[str, Any],
              catalog: Dict[str, Dict[str, Any]]
              ) -> Dict[str, Any]:
    have = set(sp.field_names(source))
    if dim in have:
        return {"dim": dim, "how": "field", "rule": "field:" + dim}
    spec = catalog.get(dim)
    if not spec:
        return {"dim": dim, "how": "missing", "rule": "", "why": "目录里没有派生规则"}
    src_cols = [c for c in (spec.get("from") or []) if c in have]
    if not src_cols:
        return {"dim": dim, "how": "missing",
                "why": "源没有 %s 这些字段" % (spec.get("from") or [])}
    rule = str(spec.get("rule") or "")
    # rule 里写死的列名可能不是第一个候选列，替换成实际存在的那个
    for c in spec.get("from") or []:
        rule = rule.replace(":" + c + ":", ":" + src_cols[0] + ":")
    if rule.startswith("field:") or rule.startswith("substr:") \
            or rule.startswith("token:") or rule.startswith("bucket:") \
            or rule.startswith("calc:"):
        return {"dim": dim, "how": "derive", "rule": rule,
                "confidence": str(spec.get("confidence") or "medium")}
    return {"dim": dim, "how": "missing", "why": "派生规则非法"}


def _measure_plan(measure: str, source: Dict[str, Any],
                  catalog: Dict[str, Dict[str, Any]]
                  ) -> Dict[str, Any]:
    spec = catalog.get(measure)
    if not spec:
        return {"measure": measure, "how": "missing",
                "why": "目录里没有这个度量的算法，需要人工给 expr"}
    have = set(sp.field_names(source))
    lack = [c for c in (spec.get("requires") or []) if c not in have]
    if lack:
        return {"measure": measure, "how": "missing",
                "why": "源缺列: %s" % lack}
    return {"measure": measure, "how": "compute",
            "agg": str(spec.get("agg") or "sum"),
            "expr": str(spec.get("expr") or ""),
            "unit": str(spec.get("unit") or "")}


def match(demand: Dict[str, Any], source: Dict[str, Any],
          derive_catalog: Optional[Dict[str, Dict[str, Any]]] = None,
          measure_catalog: Optional[Dict[str, Dict[str, Any]]] = None
          ) -> Dict[str, Any]:
    """一个需求 vs 一个源。"""
    dc = dict(derive_catalog or DERIVE_CATALOG)
    mc = dict(measure_catalog or MEASURE_CATALOG)
    dims = [_dim_plan(d, source, dc) for d in demand.get("grain") or []]
    meas = _measure_plan(str(demand.get("measure") or ""), source, mc)

    missing = [d["dim"] for d in dims if d["how"] == "missing"]
    derived = [d["dim"] for d in dims if d["how"] == "derive"]
    direct = [d["dim"] for d in dims if d["how"] == "field"]
    low_conf = [d["dim"] for d in dims if d.get("confidence") == "low"]

    needs_series = bool(demand.get("needs_series")) or any(
        d in SERIES_DIMS for d in (demand.get("grain") or []))
    history_ok = (not needs_series) or (
        str(source.get("history") or "") == "historical")

    if meas["how"] == "missing" and not dims:
        status = "none"
    elif missing or meas["how"] == "missing" or not history_ok:
        status = "partial"
    else:
        status = "full"

    notes: List[str] = []
    if not history_ok:
        notes.append("源 history=%s，只能采当下，做不了趋势"
                     % source.get("history"))
    if low_conf:
        notes.append("低置信派生: %s（必须用样本验证）" % low_conf)
    if meas["how"] == "missing":
        notes.append("度量算不出来: %s" % meas.get("why"))

    return {
        "source": str(source.get("id") or ""),
        "measure": str(demand.get("measure") or ""),
        "status": status,
        "dims": {d["dim"]: d for d in dims},
        "direct": direct,
        "derived": derived,
        "missing": missing,
        "low_confidence": low_conf,
        "history_ok": history_ok,
        "measure_plan": meas,
        "derive": {d["dim"]: d["rule"] for d in dims if d["how"] == "derive"},
        "notes": notes,
    }


def match_all(demands: List[Dict[str, Any]],
              sources: List[Dict[str, Any]],
              **kw) -> Dict[str, Any]:
    """需求 × 源 矩阵。"""
    rows = []
    for d in demands or []:
        for s in sources or []:
            rows.append(match(d, s, **kw))
    best: Dict[str, Dict[str, Any]] = {}
    rank = {"full": 3, "partial": 2, "none": 1}
    for r in rows:
        k = r["measure"]
        if k not in best or rank[r["status"]] > rank[best[k]["status"]]:
            best[k] = r
    return {
        "schema": SCHEMA,
        "matrix": rows,
        "best": best,
        "counts": {s: sum(1 for r in rows if r["status"] == s)
                   for s in ("full", "partial", "none")},
    }
