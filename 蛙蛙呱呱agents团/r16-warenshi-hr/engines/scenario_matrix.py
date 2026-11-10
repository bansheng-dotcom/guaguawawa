# -*- coding: utf-8 -*-
"""engines/scenario_matrix.py - [L06] 横向决策层：HR 招聘与用工三维方案裂变看板。

对标开源标杆：
- Scenario Planning / Multi-Criteria Decision Analysis (MCDA, Stars > 5k)
- 拒绝单一拍脑袋招聘方案，为决策者提供交付周期、用工成本、组织沉淀与流动风险的多维精算

核心职责：
1. 自动裂变三维横向用工决策看板：
   - 方案 A: 极速敏捷外包版 (Contingent/Contractor Rush) —— 极速到岗(3~5天)、灵活用工、无长期社保负担、综合用工费率略高；
   - 方案 B: 稳健全职自研版 (FTE Balanced，推荐) —— 标准招聘流程(14~21天)、注重文化匹配与核心留存、综合 ROI 最佳；
   - 方案 C: 菁英校园管培版 (Graduate/Pipeline Buffer) —— 提前储备、培养周期长(30~45天)、单人成本低、长期组织梯队健康。
2. 5 维量化权衡精算 (交付周期, 综合人月成本, 稳定性/流动风险, 组织沉淀价值, 综合 ROI 评分)；
3. 输出结构化 JSON 与 Markdown 决策看板。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class HRScenarioMatrix:
    """HR 招聘与用工决策看板三维裂变引擎。"""

    def __init__(self):
        pass

    def generate(
        self,
        role_title: str = "资深工程师",
        headcount: int = 1,
        base_monthly_salary: float = 25000.0,
    ) -> List[Dict[str, Any]]:
        """依据招聘岗位、编制人数与基准月薪裂变三维横向用工决策看板。"""
        hc = max(1, int(headcount))
        base_salary = max(1000.0, float(base_monthly_salary))

        # -------------------------------------------------------------
        # 方案 A: 极速敏捷外包版 (Contingent/Contractor Rush)
        # -------------------------------------------------------------
        cost_a_unit = round(base_salary * 1.35, 2)  # 含供应商综合费率溢价
        cost_a_total = round(cost_a_unit * hc, 2)
        scenario_a = {
            "id": "SCN_A_CONTINGENT",
            "name": "极速敏捷外包版 (Contingent/Contractor Rush)",
            "role_title": role_title,
            "headcount": hc,
            "is_recommended": False,
            "lead_time_days": 4,  # 3~5 天
            "monthly_cost_per_person": cost_a_unit,
            "total_monthly_cost": cost_a_total,
            "turnover_risk": "高风险 (合约期短，人员流动频繁，项目结束即解散)",
            "retention_value": "较低 (核心架构与业务认知难以在组织内部长期沉淀)",
            "roi_score": 7.9,
            "pros": ["极速3~5天到岗", "无长期解除补偿与年终金包袱", "按月灵活核减编制"],
            "cons": ["单人月度服务费率溢价35%", "核心资产外溢风险高", "归属感弱"],
            "summary": f"适合应急保交付或短期突击项目。{hc}人月成本约 ¥{cost_a_total}，到岗仅需 4 天。",
        }

        # -------------------------------------------------------------
        # 方案 B: 稳健全职自研版 (FTE Balanced，推荐)
        # -------------------------------------------------------------
        cost_b_unit = round(base_salary * 1.40, 2)  # 含五险一金单位统筹、公积金及法定福利
        cost_b_total = round(cost_b_unit * hc, 2)
        scenario_b = {
            "id": "SCN_B_FTE",
            "name": "稳健全职自研版 (FTE Balanced)",
            "role_title": role_title,
            "headcount": hc,
            "is_recommended": True,
            "lead_time_days": 18,  # 14~21 天
            "monthly_cost_per_person": cost_b_unit,
            "total_monthly_cost": cost_b_total,
            "turnover_risk": "极低风险 (标准劳动合同，团队认同感强，年流动率预期 < 8%)",
            "retention_value": "极高 (自研核心资产，技术经验与业务认知完全沉淀在内部)",
            "roi_score": 9.5,
            "pros": ["自研核心技术全面沉淀", "团队凝聚力强与文化认同高", "长期投入产出比最佳"],
            "cons": ["招聘筛选周期 14~21 天", "需足额缴纳五险一金单位统筹"],
            "summary": f"战略推荐方案。兼顾招聘质量、合规社保统筹与组织知识沉淀，综合 ROI 达到 9.5 分。",
        }

        # -------------------------------------------------------------
        # 方案 C: 菁英校园管培版 (Graduate/Pipeline Buffer)
        # -------------------------------------------------------------
        cost_c_unit = round(base_salary * 0.55, 2)  # 应届/管培生基准薪资折算
        cost_c_total = round(cost_c_unit * hc, 2)
        scenario_c = {
            "id": "SCN_C_GRADUATE",
            "name": "菁英校园管培版 (Graduate/Pipeline Buffer)",
            "role_title": role_title,
            "headcount": hc,
            "is_recommended": False,
            "lead_time_days": 35,  # 30~45 天
            "monthly_cost_per_person": cost_c_unit,
            "total_monthly_cost": cost_c_total,
            "turnover_risk": "中等 (成长期前 6 个月需专属导师带教，产出爬坡期略长)",
            "retention_value": "高 (形成健康组织梯队储备，企业文化塑造度与可塑性极高)",
            "roi_score": 8.5,
            "pros": ["单人月度用工成本仅为成熟全职的 39%", "组织梯队健康", "企业文化忠诚度高"],
            "cons": ["交付周期长需 30~45 天提前储备", "需投入骨干导师带教成本"],
            "summary": f"适合组织梯队战略储备。单人月成本 ¥{cost_c_unit} 具备显著成本优势，需配套导师机制。",
        }

        return [scenario_a, scenario_b, scenario_c]

    def render_markdown(self, scenarios: List[Dict[str, Any]]) -> str:
        """渲染 Markdown 5 维对比决策看板。"""
        lines = [
            "### 📊 R16 蛙人事 · 用工决策三维裂变权衡看板 (Scenario Matrix)",
            "",
            "| 方案代号 | 策略方案 | 推荐 | 到岗周期 | 单人人月成本 | 编制总月成本 | 稳定性/流动风险 | 组织沉淀价值 | 综合评分 |",
            "| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :---: |",
        ]
        for sc in scenarios:
            rec = "⭐ 推荐" if sc.get("is_recommended") else "-"
            lines.append(
                f"| {sc['id']} | {sc['name']} | {rec} | {sc['lead_time_days']}天 | ¥{sc['monthly_cost_per_person']} | ¥{sc['total_monthly_cost']} | {sc['turnover_risk'][:8]}... | {sc['retention_value'][:8]}... | {sc['roi_score']} |"
            )

        lines.append("")
        lines.append("**决策专家建议**:")
        for sc in scenarios:
            mark = "【推荐选择】" if sc.get("is_recommended") else "【备选方案】"
            lines.append(f"- **{sc['name']}** {mark}: {sc['summary']}")

        return "\n".join(lines)


# 别名兼容
ScenarioMatrix = HRScenarioMatrix
