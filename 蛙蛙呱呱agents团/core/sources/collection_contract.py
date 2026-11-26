# -*- coding: utf-8 -*-
"""core.collection_contract —— 采集契约（dsh.collection/v1）。

拆卡的真正产出：不是"一堆维度名"，而是**一张能采、能画、能验的表**。
结构借鉴 Open Data Contract Standard（ODCS）：schema/semanticType/quality/slaProperties，
另加本仓的 `acquisition`（怎么采、能不能采到、缺了怎么办）。

用法：
    from core import collection_contract as cc
    contract = cc.build(grid, sem, clarify)
    errs = cc.validate(contract)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

SCHEMA = "dsh.collection/v1"
SEMANTIC_TYPES = ("dimension", "measure")
# FEASIBILITY-SOP v5.0：unavailable 是合法状态（降级），不是错误
AVAILABILITY = ("high", "medium", "low", "unavailable")


def _grain_dims(grid: Dict[str, Any]) -> List[str]:
    """从格子的 grain 声明里拆出维度名（G_category_year → category/year）。"""
    out: List[str] = []
    for c in grid.get("cells") or []:
        g = str(c.get("grain") or "")
        for part in g.split("_")[1:]:
            if part and part not in out and part not in ("year", "month", "day"):
                out.append(part)
    return out


def _dimensions(sem: Dict[str, Any]) -> List[Dict[str, Any]]:
    props = []
    for e in ((sem.get("case") or {}).get("entities") or []):
        levels = [str(x) for x in (e.get("levels") or []) if str(x).strip()]
        p = {"name": str(e.get("id") or ""), "semanticType": "dimension",
             "logicalType": "enum" if levels else "string"}
        if levels:
            p["enum"] = levels
        props.append(p)
    return props


def _measures(sem: Dict[str, Any]) -> List[Dict[str, Any]]:
    props = []
    for m in ((sem.get("case") or {}).get("measures") or []):
        p = {"name": str(m.get("id") or ""), "semanticType": "measure",
             "logicalType": "number", "measureType": str(m.get("type") or "simple")}
        if m.get("unit"):
            p["unit"] = str(m["unit"])
        cal = (m.get("caliber") or {}).get("scope")
        if cal:
            p["caliber"] = str(cal)
        if m.get("expr"):
            p["formula"] = str(m["expr"])
        props.append(p)
    return props


def availability_estimate(measures: List[str], sem: Dict[str, Any]) -> str:
    """可获取性粗估：榜单类中等、统计类高、交叉拆分低。宁可保守。"""
    ms = {str(m.get("id")): m for m in ((sem.get("case") or {}).get("measures") or [])}
    units = {str((ms.get(m) or {}).get("unit") or "") for m in measures}
    if "%" in units:
        return "medium"       # 份额/占比多来自平台榜单
    if any(u in ("亿元", "万人") for u in units):
        return "high"         # 规模类多来自统计/行业报告
    return "medium"


def build(grid: Dict[str, Any], sem: Dict[str, Any],
          clarify: Optional[Dict[str, Any]] = None,
          supply: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """从格网 + 语义层生成一份采集契约。

    rows_expected 用**供给方案声明的真实长表行数**，不是格子数——
    84 个格子 ≠ 84 行数据；一行是什么由供给方案（grain）决定。
    """
    cells = grid.get("cells") or []
    if not cells:
        return None
    from core import supply_plan as _sup

    dims = _grain_dims(grid)
    measures = sorted({str(c.get("measure")) for c in cells if c.get("measure")})
    props = _dimensions(sem) + _measures(sem)
    purposes = [str(a.get("text") or "") for a in (clarify or {}).get("asks") or []
                if a.get("must")]
    _rows = _sup.planned_rows(supply) if supply else None
    return {
        "apiVersion": SCHEMA,
        "id": "fact_" + ("_".join(dims) if dims else "analysis"),
        "purpose": (purposes[0][:80] if purposes else "按拆卡格网采集"),
        "grain": dims or ["all"],
        "rows_expected": (_rows if _rows else len(cells)),
        "rows_expected_source": ("supply.yaml" if _rows else "cell_count(fallback)"),
        "min_points_per_cell": 3,
        "properties": props,
        "quality": {"min_coverage": 0.7, "cross_check": "关键结论 ≥2 独立来源"},
        "slaProperties": {"freshness": "近 2 年", "frequency": "annual"},
        "acquisition": {
            "path": "平台榜单 / 行业报告 / 统计局",
            "availability": availability_estimate(measures, sem),
            "degradation": "缺格标 unavailable，不画、不补零",
            # SUPPLY-SOP v7.0：能力级别由供给方案定，收卡时比计划 vs 实际
            "planned_level": _sup.planned_level(supply) if supply else "L1",
            "supply_layers": [str(s.get("layer")) for s in
                              ((supply or {}).get("sources") or [])],
        },
        "measures_covered": measures,
    }


def validate(contract: Dict[str, Any]) -> List[str]:
    """字段级校验；空 = 合法。"""
    errs: List[str] = []
    if not isinstance(contract, dict):
        return ["契约必须是 dict"]
    if contract.get("apiVersion") != SCHEMA:
        errs.append("apiVersion 必须是 %s" % SCHEMA)
    if not contract.get("id"):
        errs.append("缺 id")
    if not contract.get("grain"):
        errs.append("缺 grain（粒度先行）")
    if not isinstance(contract.get("rows_expected"), int) or contract["rows_expected"] <= 0:
        errs.append("rows_expected 必须是正整数")
    props = contract.get("properties") or []
    if not props:
        errs.append("properties 为空")
    for i, p in enumerate(props):
        if p.get("semanticType") not in SEMANTIC_TYPES:
            errs.append("properties[%d].semanticType 非法: %r" % (i, p.get("semanticType")))
        if not p.get("name"):
            errs.append("properties[%d] 缺 name" % i)
    acq = contract.get("acquisition") or {}
    if acq.get("availability") not in AVAILABILITY:
        errs.append("acquisition.availability 必须是 %s" % (AVAILABILITY,))
    if not acq.get("degradation"):
        errs.append("缺 acquisition.degradation（缺格怎么办）")
    return errs
