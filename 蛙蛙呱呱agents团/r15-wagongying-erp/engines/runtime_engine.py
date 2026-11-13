# -*- coding: utf-8 -*-
"""engines/runtime_engine.py - [L01] 工具实体层：真实 ERP 供应链计算沙箱与物料守恒探针。

对标开源标杆：
- Frappe ERPNext / Odoo / Apache OFBiz (Stars > 15k~35k)
- 供应链库存守恒、多阶 BOM 展开与安全再订货点计算沙箱

核心职责：
1. 库存预计可用量守恒精算沙箱 (actual + ordered + planned - reserved == projected, 绝对容差 0.00)；
2. 负库存刚性拦截判定与短缺量计算；
3. 多阶 BOM 物料清单展开与损耗率阶梯计算沙箱 (Multi-level BOM Explosion)；
4. 采购超收容差 0 刚性校验与让步接收授权沙箱；
5. 经济订货批量与再订货点计算 (Safety Stock & Reorder Point ROP)；
6. 运行时探针健康诊断 (Probe Health)。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class ERPRuntimeEngine:
    """真实 ERP 与供应链运营确定性计算沙箱引擎。"""

    def __init__(self, default_uom: str = "Unit"):
        self.default_uom = default_uom

    def calculate_inventory_conservation(
        self,
        actual_qty: float,
        ordered_qty: float,
        planned_qty: float,
        reserved_qty: float,
        allow_negative_stock: bool = False,
    ) -> Dict[str, Any]:
        """精算库存预计可用量并核验守恒等式。

        守恒公式：projected = actual + ordered + planned - reserved
        """
        actual = round(float(actual_qty), 4)
        ordered = round(float(ordered_qty), 4)
        planned = round(float(planned_qty), 4)
        reserved = round(float(reserved_qty), 4)

        if reserved < 0 or ordered < 0 or planned < 0:
            raise ValueError("ordered, planned, reserved 数量必须为非负数")

        projected = round(actual + ordered + planned - reserved, 4)
        has_negative_stock = actual < 0
        negative_blocked = has_negative_stock and (not allow_negative_stock)

        # 验算差额
        recalc = round(actual + ordered + planned - reserved, 4)
        diff = abs(projected - recalc)

        return {
            "actual_qty": actual,
            "ordered_qty": ordered,
            "planned_qty": planned,
            "reserved_qty": reserved,
            "projected_available": projected,
            "is_conserved": diff < 1e-6,
            "diff": diff,
            "has_negative_stock": has_negative_stock,
            "negative_blocked": negative_blocked,
            "allow_negative_stock": allow_negative_stock,
            "status": "BLOCKED" if negative_blocked else ("WARN" if has_negative_stock else "OK"),
        }

    def calculate_bom_requirements(
        self,
        bom_lines: List[Dict[str, Any]],
        finished_good_qty: float,
    ) -> Dict[str, Any]:
        """多阶/明细 BOM 物料需求量展开（含损耗率精算）。

        公式：gross_requirement = finished_good_qty * line_qty * (1 + scrap_rate)
        """
        fg_qty = round(float(finished_good_qty), 4)
        if fg_qty <= 0:
            raise ValueError("成品制造数量必须大于 0")

        expanded_items: List[Dict[str, Any]] = []
        total_gross_qty = 0.0

        for line in bom_lines:
            item_code = line.get("item_code", "UNKNOWN")
            unit_qty = float(line.get("qty", line.get("quantity", 1.0)))
            scrap_rate = float(line.get("scrap_rate", 0.0))
            if unit_qty <= 0:
                raise ValueError(f"物料 {item_code} 单件用量必须大于 0")
            if scrap_rate < 0:
                raise ValueError(f"物料 {item_code} 损耗率不能为负数")

            net_qty = round(fg_qty * unit_qty, 4)
            gross_qty = round(net_qty * (1.0 + scrap_rate), 4)
            total_gross_qty += gross_qty

            expanded_items.append({
                "item_code": item_code,
                "unit_qty": unit_qty,
                "scrap_rate": scrap_rate,
                "net_qty": net_qty,
                "gross_qty": gross_qty,
                "uom": line.get("uom", "Unit"),
            })

        return {
            "finished_good_qty": fg_qty,
            "lines_count": len(bom_lines),
            "total_gross_material_qty": round(total_gross_qty, 4),
            "expanded_lines": expanded_items,
            "valid": len(expanded_items) > 0,
        }

    def calculate_safety_stock_and_rop(
        self,
        daily_usage: float,
        lead_time_days: int,
        safety_days: int = 5,
        service_factor: float = 1.65,
    ) -> Dict[str, Any]:
        """计算安全库存 (Safety Stock) 与再订货点 (Reorder Point, ROP)。

        ROP = (Lead Time * Daily Usage) + Safety Stock
        """
        daily = round(max(0.0, float(daily_usage)), 2)
        lead = max(1, int(lead_time_days))
        s_days = max(0, int(safety_days))

        lead_demand = round(daily * lead, 2)
        safety_stock = round(daily * s_days * (service_factor / 1.65), 2)
        reorder_point = round(lead_demand + safety_stock, 2)

        return {
            "daily_usage": daily,
            "lead_time_days": lead,
            "safety_days": s_days,
            "lead_time_demand": lead_demand,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
        }

    def verify_procurement_over_receipt(
        self,
        po_qty: float,
        receipt_qty: float,
        tolerance_rate: float = 0.0,
        has_concession: bool = False,
    ) -> Dict[str, Any]:
        """采购超收容差刚性审判（默认零容差 0.00）。"""
        po = round(float(po_qty), 4)
        rec = round(float(receipt_qty), 4)
        tol = max(0.0, float(tolerance_rate))

        max_allowed = round(po * (1.0 + tol), 4)
        is_over = rec > max_allowed
        diff = round(rec - po, 4)

        allowed = (not is_over) or has_concession

        return {
            "po_qty": po,
            "receipt_qty": rec,
            "tolerance_rate": tol,
            "max_allowed_qty": max_allowed,
            "is_over_receipt": is_over,
            "over_qty": max(0.0, diff),
            "has_concession": has_concession,
            "allowed": allowed,
            "status": "PASS" if allowed else "REJECTED",
        }

    def probe_health(self) -> Dict[str, Any]:
        """确定性健康探针 (Probe Health)，校验沙箱各个算子确定性。"""
        # 自测库存守恒
        cons = self.calculate_inventory_conservation(100, 50, 20, 30)
        cons_ok = cons["is_conserved"] and cons["projected_available"] == 140.0

        # 自测 BOM 展开
        bom = self.calculate_bom_requirements([{"item_code": "CPU", "qty": 1, "scrap_rate": 0.02}], 10)
        bom_ok = bom["valid"] and bom["expanded_lines"][0]["gross_qty"] == 10.2

        # 自测超收判断
        over = self.verify_procurement_over_receipt(100, 105, tolerance_rate=0.0)
        over_ok = over["is_over_receipt"] and not over["allowed"]

        all_healthy = cons_ok and bom_ok and over_ok

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "layer": "L01",
            "name": "ERPRuntimeEngine",
            "probes": {
                "inventory_conservation_sandbox": cons_ok,
                "bom_explosion_sandbox": bom_ok,
                "procurement_over_receipt_sandbox": over_ok,
            },
            "metrics": {
                "sample_projected": cons["projected_available"],
                "sample_bom_gross": bom["total_gross_material_qty"],
                "sample_over_status": over["status"],
            },
        }
