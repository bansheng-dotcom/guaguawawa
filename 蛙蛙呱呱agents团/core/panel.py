# -*- coding: utf-8 -*-
"""core.panel —— 面板规格（L0）与覆盖校验。

第一性原理：分析 = 面板上的运算。
本模块回答两件事：
    1. 这个领域该建哪几张面板（实体 × 维度 × 期次 × 指标，目标行数）；
    2. 角色交上来的行，把面板填到了什么程度。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

DEFAULT_REGIONS = ["北京", "上海", "广州", "深圳"]
DEFAULT_CATS = ["主粮", "零食", "用品", "医疗", "服务"]
DEFAULT_YEARS = ["2023", "2024", "2025"]


def detect_regions(intent: str, clarify: Dict[str, Any]) -> List[str]:
    text = intent + " " + str(clarify)
    if "北京" in text:
        return ["朝阳", "海淀", "丰台", "通州", "昌平", "大兴", "顺义", "石景山"]
    if "内蒙古" in text:
        return ["呼和浩特", "包头", "鄂尔多斯", "赤峰"]
    if "全国" in text or "中国" in text:
        return ["全国"]
    return list(DEFAULT_REGIONS)


def build(intent: str, clarify: Dict[str, Any]) -> List[Dict[str, Any]]:
    regions = detect_regions(intent, clarify)
    cats = list(DEFAULT_CATS)
    years = list(DEFAULT_YEARS)
    panels = [
        {"id": "P1", "name": "区域×品类零售", "entities": regions, "dimensions": cats,
         "periods": years, "metrics": ["retail.sales", "retail.yoy"],
         "keywords": ["零售", "销售", "规模", "市场"], "source_plan": ["A", "B"]},
        {"id": "P2", "name": "品牌×渠道份额", "entities": ["TOP10 品牌"], "dimensions": ["商超", "便利店", "电商", "即时零售"],
         "periods": years[-2:], "metrics": ["share.brand"],
         "keywords": ["份额", "品牌", "集中度"], "source_plan": ["B"]},
        {"id": "P3", "name": "单店模型", "entities": ["社区自雇", "社区雇人", "前置仓"], "dimensions": ["固定成本", "毛利率", "盈亏平衡"],
         "periods": years[-1:], "metrics": ["breakeven.monthly", "gross_margin"],
         "keywords": ["单店", "毛利", "平衡", "成本"], "source_plan": ["C", "D"]},
    ]
    for p in panels:
        p["target_rows"] = (len(p["entities"]) * len(p["dimensions"])
                            * len(p["periods"]) * len(p["metrics"]))
    return panels


def _hit(row: Dict[str, Any], panel: Dict[str, Any]) -> bool:
    name = str(row.get("metric_name") or "")
    if any(k in name for k in panel.get("keywords") or []):
        return True
    mid = str(row.get("metric_id") or "")
    return any(m.split(".")[0] in mid for m in panel.get("metrics") or [])


def coverage(rows: Iterable[Dict[str, Any]], panels: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(rows or [])
    out = []
    for p in panels:
        hit = [r for r in rows if _hit(r, p)]
        entities = {str(r.get("entity")) for r in hit if r.get("entity")}
        periods = {str(r.get("period")) for r in hit if r.get("period")}
        out.append({
            "panel": p["id"], "name": p["name"],
            "target_rows": p["target_rows"], "filled": len(hit),
            "rate": round(len(hit) / p["target_rows"], 3) if p["target_rows"] else 0,
            "entities": len(entities), "periods": len(periods),
            "ok": len(hit) >= max(3, int(p["target_rows"] * 0.8)),
        })
    total_target = sum(x["target_rows"] for x in out)
    total_filled = sum(x["filled"] for x in out)
    return {"panels": out,
            "target_rows": total_target, "filled": total_filled,
            "rate": round(total_filled / total_target, 3) if total_target else 0,
            "ok": all(x["ok"] for x in out) if out else False}
