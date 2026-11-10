# -*- coding: utf-8 -*-
"""L06 横向决策层：三维风险情景矩阵与多方案裁决看板。
对标开源标杆：backstage/backstage (Tech Insights, Stars: 28k+), sonarqube (Quality Gates)

功能：
1. 摆脱“一锤子买卖”非黑即白的粗暴判定；
2. 依据当前审查结果自动生成三种不同容忍度与交付场景的决策方案：
   - 【方案 A：激进突击版 / Hotfix 应急发布】：忽略 WARN，仅阻断 CRITICAL/BLOCKER，最大化交付速度；
   - 【方案 B：稳健基准版 / Standard 生产上线】：阻断所有 CRITICAL，严格限制 WARN 数量 ≤ 2，兼顾安全与进度；
   - 【方案 C：严苛防御版 / Security 核心加固】：零容忍任何 WARN/HEDGE/STUB，必须 100% 具备实质证据与高测试覆盖；
3. 输出多方案对比权衡矩阵与决策 Markdown 看板。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class ScenarioMatrixPlanner:
    """横向决策看板与三维情景规划器"""

    def evaluate_scenarios(self, review_summary: Dict[str, Any]) -> Dict[str, Any]:
        """根据审查指标（blockers, warnings, test_pass_rate, code_score 等）裂变三种场景"""
        blockers = int(review_summary.get("blockers", 0))
        warnings = int(review_summary.get("warnings", 0))
        code_score = float(review_summary.get("code_score", 85.0))
        test_coverage = float(review_summary.get("test_coverage", 80.0))

        # 方案 A: 激进突击版 (Emergency Hotfix)
        allow_a = blockers == 0
        scenario_a = {
            "name": "激进突击型 (Emergency Hotfix)",
            "risk_tier": "HIGH_RISK",
            "verdict": "APPROVED" if allow_a else "BLOCKED",
            "condition": "允许忽略非致命警告，仅拦截阻断性致命错误",
            "tradeoff": "发布速度极快（T+0），但存在技术债务累积与潜在回归风险",
            "required_actions": ["建立 24 小时线上监控", "次日排期偿还债务"] if allow_a else ["必须紧急修复 Blocker"],
        }

        # 方案 B: 稳健基准型 (Standard Release)
        allow_b = blockers == 0 and warnings <= 2 and code_score >= 70.0
        scenario_b = {
            "name": "稳健基准型 (Standard Production)",
            "risk_tier": "BALANCED",
            "verdict": "APPROVED" if allow_b else "CONDITIONAL_APPROVAL" if blockers == 0 else "BLOCKED",
            "condition": "阻断 Blocker，Warning 控制在 ≤ 2 项，代码评分 ≥ 70",
            "tradeoff": "质量与交付周期的最佳平衡点，推荐大多数工业交付场景",
            "required_actions": ["由技术负责人双签 (Tech Lead Sign-off)"] if allow_b else ["修复超标警告"],
        }

        # 方案 C: 严苛防御型 (Zero-Defect Hardening)
        allow_c = blockers == 0 and warnings == 0 and code_score >= 85.0 and test_coverage >= 80.0
        scenario_c = {
            "name": "严苛防御型 (Zero-Defect Security)",
            "risk_tier": "LOWEST_RISK",
            "verdict": "APPROVED" if allow_c else "REJECTED",
            "condition": "零缺陷容忍：0 Blocker, 0 Warning, 评分 ≥ 85, 测试覆盖率 ≥ 80%",
            "tradeoff": "最高系统可靠性与合规性，但研发与验收迭代周期较长",
            "required_actions": ["直接放行进入主干发布"] if allow_c else ["全面补齐测试与证据链，彻底清空警告"],
        }

        scenarios = [scenario_a, scenario_b, scenario_c]

        return {
            "input_metrics": {
                "blockers": blockers,
                "warnings": warnings,
                "code_score": code_score,
                "test_coverage": test_coverage,
            },
            "scenarios": scenarios,
            "recommended_scenario": "稳健基准型 (Standard Production)",
            "markdown_board": self.generate_markdown_board(scenarios),
        }

    def generate_markdown_board(self, scenarios: List[Dict[str, Any]]) -> str:
        """生成 Markdown 对比看板"""
        lines = [
            "### [Board] R04 审查决策三维横向对比看板 (Decision Stylescape)",
            "",
            "| 决策方案 | 风险评级 | 裁决建议 | 准入条件 | 核心权衡 (Trade-off) |",
            "| :--- | :---: | :---: | :--- | :--- |",
        ]
        for s in scenarios:
            badge = "[PASS]" if s["verdict"] == "APPROVED" else ("[CONDITIONAL]" if "CONDITIONAL" in s["verdict"] else "[BLOCK]")
            lines.append(f"| **{s['name']}** | `{s['risk_tier']}` | {badge} | {s['condition']} | {s['tradeoff']} |")
        lines.append("")
        return "\n".join(lines)
