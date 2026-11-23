# -*- coding: utf-8 -*-
"""core.drill —— 拆卡 v2 的纵向钻取段（DATA-LAYER-SOP v2.0 · S2）。

第一段（横向 MECE）回答「从哪些角度看」；这一段回答
「选定一个品类后，要采哪几张表、能得出哪几个判断」。

**关键：产出的是数据集需求 + 判断，不是 360 个格子。**

用法：
    from core import drill
    plan = drill.plan("脚垫", sem)          # → {datasets, claims, grid_cells: []}
    errs = drill.validate(plan)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core import cell_claim
from core import dataset as _ds

# 平台/行业数据常见的品牌分辨率：TOP5 + 长尾
DEFAULT_BRANDS = ["品牌A", "品牌B", "品牌C", "品牌D", "品牌E", "长尾合计"]
PRICE_BANDS = ["低价带", "中价带", "高价带"]

# 时间粒度 → 一个周期内的点数（用于算 rows_expected / min_rows）
PERIODS = {"year": 3, "quarter": 12, "month": 36, "week": 104, "day": 365}


def _ds_id(category: str, kind: str, tg: str) -> str:
    return "DS-%s-%s%s" % (category, kind, tg)


def plan(category: str, sem: Optional[Dict[str, Any]] = None, *,
         brands: Optional[List[str]] = None, time_grain: str = "month",
         price_bands: Optional[List[str]] = None) -> Dict[str, Any]:
    """对一个品类做钻取：2 张表的声明 + 3 个判断。"""
    tg = time_grain if time_grain in _ds.TIME_GRAINS else "month"
    n = PERIODS.get(tg, 36)
    bs = list(brands or DEFAULT_BRANDS)
    pbs = list(price_bands or PRICE_BANDS)

    ds_brand = _ds.build(
        _ds_id(category, "品牌", tg),
        title="%s 品牌×%s（规模/价格/份额）" % (category, tg),
        source={"kind": "平台榜单", "url": ""},
        grain="brand × %s" % tg, time_grain=tg,
        columns=[
            {"name": "brand", "type": "string", "semantic": "dimension"},
            {"name": tg, "type": "date", "semantic": "dimension"},
            {"name": "price_band", "type": "string", "semantic": "dimension"},
            {"name": "gmv", "type": "number", "semantic": "measure", "unit": "元", "agg": "sum"},
            {"name": "asp", "type": "number", "semantic": "measure", "unit": "元", "agg": "mean"},
            {"name": "share", "type": "number", "semantic": "measure", "unit": "%", "agg": "mean"},
        ],
        rows_expected=len(bs) * n,
        quality={"completeness": "90%", "source_grade": "B"},
        sla={"freshness": "近 %d 个%s" % (n, tg)},
    )
    ds_price = _ds.build(
        _ds_id(category, "价格带", tg),
        title="%s 价格带×%s（结构/均价）" % (category, tg),
        source={"kind": "平台榜单", "url": ""},
        grain="price_band × %s" % tg, time_grain=tg,
        columns=[
            {"name": "price_band", "type": "string", "semantic": "dimension"},
            {"name": tg, "type": "date", "semantic": "dimension"},
            {"name": "gmv_share", "type": "number", "semantic": "measure", "unit": "%", "agg": "mean"},
            {"name": "asp", "type": "number", "semantic": "measure", "unit": "元", "agg": "mean"},
        ],
        rows_expected=len(pbs) * n,
        quality={"completeness": "90%", "source_grade": "B"},
        sla={"freshness": "近 %d 个%s" % (n, tg)},
    )

    claims = [
        cell_claim.build(
            "C-%s-品牌价差" % category,
            "%s 各品牌价差：头部与长尾的均价差是否超过 2 倍" % category,
            dataset=ds_brand["id"],
            query={"filters": {}, "group_by": ["brand"], "metrics": ["asp", "gmv"]},
            min_rows=len(bs),
            chart={"type": "hbar", "x": "brand", "metric": "asp"},
            causal_level="A",
            falsifier="若头部与长尾均价差 < 1.5 倍，本条作废",
        ),
        cell_claim.build(
            "C-%s-价格带上移" % category,
            "%s 主流价格带是否在上移（低价带份额两年内变化）" % category,
            dataset=ds_price["id"],
            query={"filters": {}, "group_by": [tg, "price_band"], "metrics": ["gmv_share"]},
            min_rows=len(pbs) * 2,
            chart={"type": "stacked", "x": tg, "series": "price_band", "metric": "gmv_share"},
            causal_level="A",
            falsifier="若低价带份额回升到两年前水平，本条作废",
        ),
        cell_claim.build(
            "C-%s-价格战时点" % category,
            "%s 的均价在哪些月份出现明显下探（价格战）" % category,
            dataset=ds_brand["id"],
            query={"filters": {}, "group_by": [tg], "metrics": ["asp"]},
            min_rows=max(12, n // 3),
            chart={"type": "line", "x": tg, "metric": "asp"},
            causal_level="A",
            falsifier="若下探幅度 < 5% 或不可跨期复现，本条作废",
        ),
    ]

    return {
        "schema": "dsh.drill_plan/v1",
        "category": category,
        "time_grain": tg,
        "brands": bs,
        "price_bands": pbs,
        "datasets": [ds_brand, ds_price],
        "claims": claims,
        # v1 会在这里产出几百个格子；v2 明确不产
        "grid_cells": [],
        "note": "纵向钻取产出数据集+判断；细粒度数据进表，不进格子",
    }


def validate(dr: Dict[str, Any]) -> List[str]:
    """钻取计划自校验：数据集合法 + 每个判断都能在它引用的表上执行。"""
    errs: List[str] = []
    if not isinstance(dr, dict):
        return ["钻取计划必须是 dict"]
    if not dr.get("category"):
        errs.append("缺 category")
    dss = {d.get("id"): d for d in dr.get("datasets") or []}
    if not dss:
        errs.append("没有数据集声明")
    for did, d in dss.items():
        for e in _ds.validate(d):
            errs.append("[%s] %s" % (did, e))
    claims = dr.get("claims") or []
    if not claims:
        errs.append("没有判断")
    for c in claims:
        for e in cell_claim.validate(c, dss):
            errs.append("[%s] %s" % (c.get("claim_id"), e))
    return errs


def merge_into(plan_doc: Dict[str, Any], dr: Dict[str, Any]) -> Dict[str, Any]:
    """把钻取结果并进拆卡计划（供 prepare 写 plan/drill.json）。"""
    out = dict(plan_doc or {})
    out.setdefault("drills", []).append(dr)
    return out
