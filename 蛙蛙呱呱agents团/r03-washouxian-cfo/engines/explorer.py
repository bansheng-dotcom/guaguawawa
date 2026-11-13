# -*- coding: utf-8 -*-
"""R03 多向财务情景探索与决策看板裂变器 (L06 横向决策层)。

对标高星标杆: huashu-design (28k+) / Scenario Planning & Stylescapes
面对复杂的财务跑道预测、预算编制与合规投入诉求，拒绝单一结果一锤子买卖，
自动裂变出三组平行情景与权衡对比看板：
1. 【保守紧缩型 (Conservative)】：严格冷冻非核心HC与营销开支，延长现金跑道至最大值；
2. 【基准稳健型 (Baseline)】：按预算常态化支出，维持平衡健康的资本结构；
3. 【进取扩张型 (Aggressive)】：扩大获客与市场投放，短期承受现金收窄，追求 ARR 极限增长。
"""
from __future__ import annotations
from typing import Any, Dict, List

class MultiScenarioExplorer:
    """财务与预算多情景裂变与决策对比生成器。"""

    @classmethod
    def explore_scenarios(cls, base_runway_months: float, base_burn_rate: float, cash_balance: float) -> Dict[str, Any]:
        """裂变出三组平行情景模型。"""
        # 1. 保守紧缩型 (缩减 35% 烧钱速度)
        con_burn = base_burn_rate * 0.65
        con_runway = round(cash_balance / max(1.0, con_burn), 1)

        # 2. 基准稳健型
        base_runway = round(cash_balance / max(1.0, base_burn_rate), 1)

        # 3. 进取扩张型 (增加 40% 投放)
        agg_burn = base_burn_rate * 1.4
        agg_runway = round(cash_balance / max(1.0, agg_burn), 1)

        scenarios = {
            "conservative": {
                "name": "保守紧缩型 (防守避险)",
                "monthly_burn": round(con_burn, 2),
                "runway_months": con_runway,
                "risk_profile": "极低风险，现金储备充裕，但可能错失市场窗口",
                "recommended_for": "宏观融资收紧、行业下行或面临合规罚款风险期"
            },
            "baseline": {
                "name": "基准稳健型 (平衡可持续)",
                "monthly_burn": round(base_burn_rate, 2),
                "runway_months": base_runway,
                "risk_profile": "中等风险，收支节奏受控，跑道处于健康预警线内",
                "recommended_for": "常态化运营与阶段性业务爬坡期"
            },
            "aggressive": {
                "name": "进取扩张型 (规模优先)",
                "monthly_burn": round(agg_burn, 2),
                "runway_months": agg_runway,
                "risk_profile": "高风险，现金消耗极快，极度依赖后续融资注入",
                "recommended_for": "窗口期抢占市场、产品单位经济模型 (LTV/CAC > 3x) 极佳时"
            }
        }

        # 生成横向比选 Markdown 看板
        board_md = cls._render_comparison_board(cash_balance, scenarios)

        return {
            "cash_balance": cash_balance,
            "scenarios": scenarios,
            "comparison_board_md": board_md
        }

    @classmethod
    def _render_comparison_board(cls, cash_balance: float, scenarios: Dict[str, Any]) -> str:
        lines = [
            "# 蛙守线 (CFO) 财务多情景横向比选决策看板",
            "",
            f"**当前可用现金结余基准**: `${cash_balance:,.2f}`",
            "",
            "| 策略情景 | 月度净消耗 (Burn Rate) | 预计现金跑道 (Runway) | 风险偏好等级 | 适用经营周期与战略意图 |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]
        for key, sc in scenarios.items():
            lines.append(
                f"| **{sc['name']}** | `${sc['monthly_burn']:,.2f}` | **{sc['runway_months']} 个月** | {sc['risk_profile'][:12]}... | {sc['recommended_for']} |"
            )

        lines.extend([
            "",
            "> **CFO 决策建议**: 若当前处于安全港合规审验期或融资窗口期，推荐选用 **【基准稳健型】**，并设置 6 个月预警熔断点。"
        ])
        return "\n".join(lines)
