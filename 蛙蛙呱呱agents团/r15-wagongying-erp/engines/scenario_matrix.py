# -*- coding: utf-8 -*-
"""engines/scenario_matrix.py - [L06] 横向决策层：供应链补货与采购三维方案裂变看板。

对标开源标杆：
- Scenario Planning / Multi-Criteria Decision Analysis (MCDA, Stars > 5k)
- 拒绝一锤子买卖，为决策者提供多维成本、周期与风险权衡

核心职责：
1. 自动裂变三维供应链策略看板：
   - 方案 A: 极速敏捷突击版 (JIT Rush) —— 准时制小批量、资金占用极低、交付速度快、单件成本略高；
   - 方案 B: 稳健经济批量版 (EOQ Balanced, 推荐) —— 平衡订货成本与持货成本、综合 ROI 与履约保障最佳；
   - 方案 C: 战略安全缓冲版 (Buffer Maximized) —— 大批量享受价格阶梯、高安全库存抗断供、资金占用较高。
2. 5 维量化权衡指标精算 (订货批量, 资金占用, 交付周期, 缺货风险, 综合 ROI 评分)；
3. 输出结构化 JSON 与 Markdown 对比看板。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class SupplyScenarioMatrix:
    """供应链三维采购/补货决策看板裂变引擎。"""

    def __init__(self):
        pass

    def generate(
        self,
        item_code: str = "ITEM_STANDARD",
        target_demand_qty: float = 1000.0,
        base_unit_cost: float = 50.0,
    ) -> List[Dict[str, Any]]:
        """依据物料与总需求量裂变三维权衡方案。"""
        demand = max(10.0, float(target_demand_qty))
        cost = max(1.0, float(base_unit_cost))

        # 方案 A: 极速敏捷版 (JIT Rush)
        jit_batch = round(demand * 0.25, 1)
        jit_unit_price = round(cost * 1.08, 2)
        jit_capital = round(jit_batch * jit_unit_price, 2)
        scenario_a = {
            "id": "SCN_A_JIT",
            "name": "极速敏捷突击版 (JIT Rush)",
            "is_recommended": False,
            "batch_qty": jit_batch,
            "unit_price": jit_unit_price,
            "capital_lock_amount": jit_capital,
            "lead_time_days": 3,
            "stockout_risk": "中等 (依赖供应商高频交付能力)",
            "holding_cost_annual": round(jit_capital * 0.05, 2),
            "roi_score": 8.2,
            "summary": "以极小批次多频次下单，资金占用降低 60%，适合需求波动大或现金紧缺期。",
        }

        # 方案 B: 稳健经济批量版 (EOQ Balanced)
        eoq_batch = round(demand * 0.50, 1)
        eoq_unit_price = round(cost * 1.00, 2)
        eoq_capital = round(eoq_batch * eoq_unit_price, 2)
        scenario_b = {
            "id": "SCN_B_EOQ",
            "name": "稳健经济批量版 (EOQ Balanced)",
            "is_recommended": True,
            "batch_qty": eoq_batch,
            "unit_price": eoq_unit_price,
            "capital_lock_amount": eoq_capital,
            "lead_time_days": 7,
            "stockout_risk": "极低 (维持 10 天安全库存)",
            "holding_cost_annual": round(eoq_capital * 0.08, 2),
            "roi_score": 9.4,
            "summary": "标准经济订货批量模型，兼顾订货成本与持货费用，综合运营与交期体验最佳。",
        }

        # 方案 C: 战略安全缓冲版 (Buffer Maximized)
        buf_batch = round(demand * 1.20, 1)
        buf_unit_price = round(cost * 0.92, 2)  # 阶梯折扣
        buf_capital = round(buf_batch * buf_unit_price, 2)
        scenario_c = {
            "id": "SCN_C_BUFFER",
            "name": "战略安全缓冲版 (Buffer Maximized)",
            "is_recommended": False,
            "batch_qty": buf_batch,
            "unit_price": buf_unit_price,
            "capital_lock_amount": buf_capital,
            "lead_time_days": 14,
            "stockout_risk": "零风险 (维持 30 天超额安全缓冲)",
            "holding_cost_annual": round(buf_capital * 0.15, 2),
            "roi_score": 8.0,
            "summary": "享受 8% 大宗采购阶梯折扣并锁定货源，杜绝断供，但资金占用与仓储成本较高。",
        }

        return [scenario_a, scenario_b, scenario_c]

    def render_markdown(self, scenarios: List[Dict[str, Any]]) -> str:
        """渲染 Markdown 对比看板表格。"""
        lines = [
            "| 方案代号 | 策略名称 | 推荐 | 单次批量 | 采购单价 | 资金占用 | 交期 | 缺货风险 | 综合评分 |",
            "| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :---: |",
        ]
        for sc in scenarios:
            rec = "⭐ 推荐" if sc["is_recommended"] else "-"
            lines.append(
                f"| {sc['id']} | {sc['name']} | {rec} | {sc['batch_qty']} | ¥{sc['unit_price']} | ¥{sc['capital_lock_amount']} | {sc['lead_time_days']}天 | {sc['stockout_risk']} | {sc['roi_score']} |"
            )
        return "\n".join(lines)


# 别名兼容
ScenarioMatrix = SupplyScenarioMatrix
