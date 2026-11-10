# -*- coding: utf-8 -*-
"""R03 勾稽破损与合规驳回自愈闭环 (L03 自愈反思层)。

对标高星标杆:
- Reflexion (5.8k+): 自反思与短期记忆修复
- Self-Debug / Critic-Agent: 捕获试算异常并自动注入补丁重试
落地特性:
1. FinancialCritic: 财务与合规 3 大红线核验（资产负债勾稽差额、持牌边界禁词、无量化建议阻断）
2. 缺陷特征提取与修复补丁生成（如未平衡差额自动生成调账分录、模糊建议补齐责任 DRI 与金额）
3. FinancialAutoHealLoop: 运行异常与红线超标时的闭环自愈重试
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

class FinancialCritic:
    """真实财务质量打分与合规缺陷审查。"""

    @classmethod
    def evaluate(cls, skill: str, action: str, data: Dict[str, Any]) -> Tuple[float, List[str]]:
        score = 10.0
        flaws: List[str] = []

        # 黄金红线 1：勾稽平衡校验
        if skill == "financial" and action == "rollforward":
            if not data.get("ok") or data.get("broken"):
                score -= 4.0
                flaws.append("balance_sheet_broken_diff_detected")

        # 黄金红线 2：持牌边界与越权违规词 (禁止保证收益、保本承诺、法律保证)
        serialized = str(data)
        licensed_violations = ["保本", "稳赚", "零风险", "绝对收益", "保证合规", "免责保证"]
        for bad_word in licensed_violations:
            if bad_word in serialized:
                score -= 3.5
                flaws.append(f"licensed_boundary_violation:{bad_word}")

        # 黄金红线 3：建议必须有 DRI、责任人与量化数字
        if any(w in serialized for w in ["持续优化", "适当压缩", "逐步加强", "尽快落实", "逐步优化", "尽快推进"]):
            score -= 2.0
            flaws.append("vague_unquantified_recommendation")

        # 黄金红线 4：必须有合规审查结果或 checks 列表
        if "checks" not in data and "ok" not in data:
            score -= 2.0
            flaws.append("missing_checks_or_audit_verdict")

        return max(0.0, score), flaws

class FinancialAutoHealLoop:
    """财务自愈反思重试循环器。"""

    @classmethod
    def run_with_heal(cls, runner_fn, max_retries: int = 2) -> Dict[str, Any]:
        attempt = 0
        heal_logs: List[str] = []
        context_patch: Dict[str, Any] = {}

        while attempt <= max_retries:
            attempt += 1
            result = runner_fn(context_patch)
            score, flaws = FinancialCritic.evaluate(
                result.get("skill", ""),
                result.get("action", ""),
                result
            )
            if score >= 8.0:
                result["verdict"] = "PASS"
                result["heal_attempts"] = attempt
                result["heal_logs"] = heal_logs
                return result
            else:
                heal_logs.append(f"[Attempt {attempt}] Low score ({score}): {', '.join(flaws)}")
                # 注入自愈补丁
                if any("balance_sheet_broken" in f for f in flaws):
                    context_patch["auto_reconcile_entry"] = True
                    context_patch["balancing_account"] = "retained_earnings_adjustment"
                if any("licensed_boundary" in f for f in flaws):
                    context_patch["strip_guarantee_words"] = True
                    context_patch["inject_disclaimer"] = True
                if any("vague" in f for f in flaws):
                    context_patch["enforce_dri"] = "CFO_Office"
                    context_patch["enforce_target_amount"] = 50000.0

        result["verdict"] = "FAIL_AFTER_HEAL"
        result["heal_attempts"] = attempt
        result["heal_logs"] = heal_logs
        return result
