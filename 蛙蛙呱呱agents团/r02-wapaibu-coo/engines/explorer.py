# -*- coding: utf-8 -*-
"""R02 多向方案探索与对比看板生成器 (轮次 6 落地)。

对标高星标杆: alchaincyf/huashu-design (Stylescapes 多向探索工作流)
支持从单一业务目标自动裂变出三组不同侧重的运营排期/资源分配策略方案。
"""
from __future__ import annotations
from typing import Any, Dict, List

class MultiPlanExplorer:
    """多向策略方案裂变器。"""

    @classmethod
    def explore_three_plans(cls, intent: str, total_workdays: int = 10) -> Dict[str, Any]:
        """裂变出 3 种鲜明对立的运营策略：激进交付型、稳健防守型、成本精简型。"""
        plans = [
            {
                "id": "plan_aggressive",
                "name": "极速突击型 (Aggressive Sprint)",
                "philosophy": "最大化并行度，紧急系数 1.3，关键路径压缩 25%",
                "estimated_duration_days": round(total_workdays * 0.75, 1),
                "resource_load_pct": 95.0,
                "risk_level": "HIGH"
            },
            {
                "id": "plan_balanced",
                "name": "稳健基准型 (Balanced Operations)",
                "philosophy": "严格遵循 WBS 与 50% 饱和度红线，留有 15% 缓冲",
                "estimated_duration_days": float(total_workdays),
                "resource_load_pct": 80.0,
                "risk_level": "LOW"
            },
            {
                "id": "plan_conservative",
                "name": "弹性精益型 (Lean & Resilient)",
                "philosophy": "消除全部潜在浪费，依赖关系串行化，确保零事故",
                "estimated_duration_days": round(total_workdays * 1.25, 1),
                "resource_load_pct": 65.0,
                "risk_level": "MINIMAL"
            }
        ]

        # 拼装对比看板
        dashboard_md = "# 运营排期策略多向对比看板 (Operations Multi-Plan Dashboard)\n\n"
        dashboard_md += "| 方案名称 | 核心理念 | 预计周期 | 资源负载率 | 风险评级 |\n"
        dashboard_md += "|---|---|---|---|---|\n"
        for p in plans:
            dashboard_md += f"| **{p['name']}** | {p['philosophy']} | {p['estimated_duration_days']} 天 | {p['resource_load_pct']}% | `{p['risk_level']}` |\n"

        return {
            "intent": intent,
            "plans": plans,
            "dashboard_markdown": dashboard_md
        }
