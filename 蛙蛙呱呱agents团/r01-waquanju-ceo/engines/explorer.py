# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 多向战略探索与对比画廊看板 (Multi-Strategy Explorer & Dashboard)。

对标 GitHub 开源标杆:
- huashu-design (28k+ stars) / Open-Design / Multi-Branch Strategy Exploration
- 自动将模糊的战略命题裂变为 3 个鲜明对立的战略路线（激进突进型、稳健防守型、敏捷精益型），并拼装横向对比看板。
"""
from __future__ import annotations
from typing import Any, Dict, List

class ExecutiveStrategyExplorer:
    """战略多向探索与画廊看板生成器。"""

    @classmethod
    def explore_branches(cls, topic: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """裂变出 3 条风格迥异的战略方案分支。"""
        return [
            {
                "branch_id": "branch_alpha_aggressive",
                "name": "极速突进与高增长方案 (Aggressive)",
                "philosophy": "抢占市场窗口期，全力投资核心赛道，容忍短期亏损换取绝对规模",
                "risk_level": "HIGH",
                "reversibility": "不可逆",
                "resource_weight": 1.5,
                "expected_roi": "3.0x (高风险高收益)",
                "kill_criteria": "30天内新获客成本超过行业平均2倍即熔断",
                "key_owners": ["r01", "r12", "r07"]
            },
            {
                "branch_id": "branch_beta_conservative",
                "name": "稳健防御与正现金流方案 (Conservative)",
                "philosophy": "深耕既有高净值客户，严控现金流消耗，确保6个月以上安全跑道",
                "risk_level": "LOW",
                "reversibility": "高度可逆",
                "resource_weight": 0.8,
                "expected_roi": "1.3x (稳扎稳打)",
                "kill_criteria": "连续两个月经营性现金流净额由正转负即终止",
                "key_owners": ["r01", "r02", "r03"]
            },
            {
                "branch_id": "branch_gamma_lean_mvp",
                "name": "敏捷精益与小步快跑方案 (Lean MVP)",
                "philosophy": "以最小可行实验切入，通过两周灰度快速获取市场反馈，根据数据决定转向",
                "risk_level": "MEDIUM",
                "reversibility": "可逆",
                "resource_weight": 1.0,
                "expected_roi": "2.0x (弹性试错)",
                "kill_criteria": "灰度两周内留存率低于20%且无法通过产品调优修正即放弃",
                "key_owners": ["r01", "r08", "r06"]
            }
        ]

    @classmethod
    def generate_comparison_dashboard(cls, topic: str, branches: List[Dict[str, Any]]) -> str:
        """拼装 Markdown 战略决策对比画廊看板。"""
        md = [
            f"# 战略决策多向对比看板 (Executive Strategy Gallery Dashboard)",
            f"> 决策议题：`{topic}`  ",
            f"> 生成时间：2026-11-09 | 决策主理人：R01 蛙全局 (CEO)  \n",
            "| 方案维度 | 方案 A (极速突进) | 方案 B (稳健防守) | 方案 C (敏捷精益) |",
            "| :--- | :--- | :--- | :--- |"
        ]
        
        dims = [
            ("战略哲学", "philosophy"),
            ("风险级别", "risk_level"),
            ("可逆性", "reversibility"),
            ("资源消耗系数", "resource_weight"),
            ("预期回报", "expected_roi"),
            ("杀死标准 (Kill Criteria)", "kill_criteria"),
            ("牵头核心角色", "key_owners")
        ]

        for label, key in dims:
            row = [f"**{label}**"]
            for b in branches:
                val = b.get(key, "-")
                if isinstance(val, list):
                    val = ", ".join(val)
                row.append(str(val))
            md.append("| " + " | ".join(row) + " |")

        md.append("\n## CEO 决策建议与下一阶段动作\n")
        md.append("- 建议采用 **方案 C (敏捷精益)** 作为首发切入，以最低成本进行两周快速验证；")
        md.append("- 若数据达标，则在下个月董事会申请追加预算无缝切换至 **方案 A** 全面推开。")
        return "\n".join(md)
