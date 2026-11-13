# -*- coding: utf-8 -*-
"""L06 横向决策层：三维横向决策看板裂变引擎。
对标开源项目：SonarQube / Backstage (Stars > 28k), Scenario Planning。
解决病灶：审查结论一锤子买卖（只有单一的放行或驳回），无法根据业务场景为人类决策者提供【激进突击版 / 稳健基准版 / 严苛防御版】三维横向选择矩阵。
"""
from __future__ import annotations

from typing import Any, Dict, List


class ScenarioDashboardEngine:
    """三维审查决策看板生成与裂变引擎。"""

    SCENARIO_PROFILES = {
        "aggressive": {
            "name": "激进突击版 (Aggressive / Hotfix)",
            "description": "适用于紧急故障止血、内部实验原型。仅拦截 P-THEATRE 假门禁与运行时崩溃错误，其余缺陷暂缓。",
            "min_score": 60,
            "blocking_severities": ["CRITICAL"],
            "allow_stubs": True,
            "required_evidence_level": "L1",
        },
        "balanced": {
            "name": "稳健基准版 (Balanced / Standard Production)",
            "description": "适用于常规迭代发版、标准商业交付。严格拦截所有 CRITICAL 与 HIGH 缺陷，要求三级证据链达到 L2+。",
            "min_score": 80,
            "blocking_severities": ["CRITICAL", "HIGH"],
            "allow_stubs": False,
            "required_evidence_level": "L2",
        },
        "strict": {
            "name": "严苛防御版 (Strict / High Reliability)",
            "description": "适用于金融支付、核心底层基建。零容忍任何 MEDIUM 及以上缺陷，强制 L3 通路完整性与 0 代码异味。",
            "min_score": 95,
            "blocking_severities": ["CRITICAL", "HIGH", "MEDIUM"],
            "allow_stubs": False,
            "required_evidence_level": "L3",
        },
    }

    @classmethod
    def generate_three_tier_dashboard(cls, findings: List[Dict[str, Any]], base_score: int = 100) -> Dict[str, Any]:
        """为一组审查发现裂变生成三套平行决策方案。"""
        scenarios: Dict[str, Any] = {}

        for key, profile in cls.SCENARIO_PROFILES.items():
            blocked_findings = [
                f for f in findings
                if f.get("severity", "MEDIUM").upper() in profile["blocking_severities"]
            ]
            penalty = sum(f.get("penalty", 10) for f in blocked_findings)
            effective_score = max(0, base_score - penalty)
            verdict = "PASS" if effective_score >= profile["min_score"] and not blocked_findings else "REJECT"

            scenarios[key] = {
                "profile": profile["name"],
                "description": profile["description"],
                "verdict": verdict,
                "effective_score": effective_score,
                "blocked_issues_count": len(blocked_findings),
                "unresolved_risks_accepted": len(findings) - len(blocked_findings),
                "tradeoff": (
                    "极速交付，承担一定技术债风险" if key == "aggressive"
                    else "平衡速度与质量，符合生产常规标准" if key == "balanced"
                    else "极高可靠性，拒绝任何潜在隐患，发版周期延长"
                ),
            }

        # 生成 Markdown 决策看板表格
        md_table = [
            "### R04 挑刺独立评审官 · 三维横向决策矩阵 (Decision Dashboard)",
            "",
            "| 决策方案 | 裁决结果 | 适用准入分 | 拦截缺陷数 | 放行技术债 | 权衡代价 (Trade-off) |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |",
        ]
        for key, sc in scenarios.items():
            md_table.append(
                f"| **{sc['profile']}** | `{sc['verdict']}` | >={cls.SCENARIO_PROFILES[key]['min_score']}分 | {sc['blocked_issues_count']} 项 | {sc['unresolved_risks_accepted']} 项 | {sc['tradeoff']} |"
            )

        return {
            "scenarios": scenarios,
            "markdown_dashboard": "\n".join(md_table),
        }
