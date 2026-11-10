# -*- coding: utf-8 -*-
"""engines/scenario_matrix.py - [L06] 横向决策层：客户成功多维挽留方案看板裂变引擎。

对标开源标杆：
- Scenario Planning 场景规划方法论
- MCDA (Multi-Criteria Decision Analysis) 多准则决策权衡矩阵 (Stars > 5k)

核心职责：
1. 拒绝一锤子买卖挽留策略，自动裂变【极简防御型 / 稳健运营型 / 深度战略型】三维方案看板；
2. 计算各方案的人天投入、留存概率、资源成本与 ROI 权衡矩阵；
3. 输出面向管理决策层的高清对比看板。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class ScenarioMatrix:
    """客户成功多维挽留方案看板裂变引擎。"""

    def __init__(self):
        pass

    def generate(self, client_name: str = "重点客户", arr_value: float = 200000.0) -> List[Dict[str, Any]]:
        """为目标客户生成三维挽留决策矩阵。"""
        scenarios = [
            {
                "id": "minimal_defensive",
                "name": "极简防御型 (紧急止血快速安抚)",
                "person_days": 0.5,
                "estimated_hours": 4.0,
                "resource_cost_rmb": 2000.0,
                "projected_retention_rate": 0.65,
                "expected_retained_arr": round(arr_value * 0.65, 2),
                "roi_multiple": round((arr_value * 0.65) / 2000.0, 1),
                "tactics": [
                    "紧急排查并热修未闭环的 P1/P2 客服工单",
                    "CSM 负责人电话深度安抚关键联系人",
                    "输出 72 小时承诺兑现进度简报",
                ],
                "trade_off": "成本极低、响应极快；但对深层组织关系破损的根治能力有限。",
                "recommended_for": "预算紧缺、仅因单一临时 Bug 引发不满的中小微客户。",
            },
            {
                "id": "steady_standard",
                "name": "稳健运营型 (高管拜访与标准护航)",
                "person_days": 2.0,
                "estimated_hours": 16.0,
                "resource_cost_rmb": 8000.0,
                "projected_retention_rate": 0.85,
                "expected_retained_arr": round(arr_value * 0.85, 2),
                "roi_multiple": round((arr_value * 0.85) / 8000.0, 1),
                "tactics": [
                    "CSM 负责人协同产品线高管开展现场 QBR 深度复盘",
                    "升级专属服务群，客服首响提速至 ≤30 分钟",
                    "赠送 1 次产品核心管理团队深度使用培训",
                    "针对性设计续约 2 年期折扣及增值权益方案",
                ],
                "trade_off": "性价比最高、留存成功率稳固；需协调跨部门高管时间。",
                "recommended_for": "核心腰部客户 (ARR 10~50万)，客情良好但使用度略有下滑的常规续约。(推荐)",
            },
            {
                "id": "strategic_enterprise",
                "name": "深度战略型 (专属驻场与联合标杆共创)",
                "person_days": 5.0,
                "estimated_hours": 40.0,
                "resource_cost_rmb": 25000.0,
                "projected_retention_rate": 0.96,
                "expected_retained_arr": round(arr_value * 0.96, 2),
                "roi_multiple": round((arr_value * 0.96) / 25000.0, 1),
                "tactics": [
                    "高级 CSM 与解决方案架构师联合驻场 3 天",
                    "打通客户私有系统集成断点，定制专属工作流",
                    "将客户重点需求列入产品核心季度 Roadmap 优先交付",
                    "联合打造行业标杆案例，给予年度战略客户公关权益",
                ],
                "trade_off": "留存率最高、深度绑定；但占用研发与专家较多工时。",
                "recommended_for": "头部 KA 战略客户 (ARR > 50万)，面临友商激烈争夺的生死防守场景。",
            },
        ]
        return scenarios

    def render_markdown_matrix(self, scenarios: List[Dict[str, Any]]) -> str:
        """渲染决策看板 Markdown 表格。"""
        lines = [
            "### 客户续约挽留多维横向决策看板",
            "",
            "| 方案维度 | 极简防御型 | 稳健运营型 (推荐) | 深度战略型 |",
            "| :--- | :--- | :--- | :--- |",
        ]
        fields = [
            ("方案名称", lambda s: s["name"]),
            ("投入人天", lambda s: f"{s['person_days']} 人天 ({s['estimated_hours']}h)"),
            ("预估成本", lambda s: f"¥{s['resource_cost_rmb']:,.0f}"),
            ("预期留存率", lambda s: f"{int(s['projected_retention_rate']*100)}%"),
            ("留存预期收益", lambda s: f"¥{s['expected_retained_arr']:,.0f}"),
            ("预估 ROI", lambda s: f"{s['roi_multiple']}x"),
            ("核心战术", lambda s: "<br>".join(s["tactics"][:2])),
            ("适用场景", lambda s: s["recommended_for"]),
        ]
        for label, getter in fields:
            row = [label] + [getter(s) for s in scenarios]
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)
