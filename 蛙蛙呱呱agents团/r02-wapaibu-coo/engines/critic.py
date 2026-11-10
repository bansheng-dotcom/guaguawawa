# -*- coding: utf-8 -*-
"""R02 真实审校与 Auto-Heal 反思自愈闭环 (轮次 3 落地)。

对标高星标杆: Reflexion / Critic-Agent (Self-Reflection Loops)
1. 审校运营工件规范（合理性、无主之责、口径完整性、量化指标）
2. 提取缺陷特征
3. Auto-Heal 自动重试补全机制
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

class CriticEvaluator:
    """真实运营质量打分与缺陷审查。"""

    @classmethod
    def evaluate(cls, skill: str, action: str, data: Dict[str, Any]) -> Tuple[float, List[str]]:
        score = 10.0
        flaws: List[str] = []

        # 黄金准则 1：结果必须标明明确的执行状态与闭环下一步
        if "ok" not in data and "status" not in data:
            score -= 3.0
            flaws.append("missing_status_or_ok")

        # 黄金准则 2：禁止空话与缺乏量化指标
        serialized = str(data)
        if any(w in serialized for w in ["尽快推进", "持续跟进", "相关人员", "逐步优化"]):
            score -= 2.5
            flaws.append("vague_expression_detected")

        # 黄金准则 3：结构化完备性审查
        if skill == "capacity" and action == "delegate":
            packages = data.get("packages", [])
            for pkg in packages:
                if not pkg.get("owner"):
                    score -= 4.0
                    flaws.append("missing_task_owner")

        return max(0.0, score), flaws

class AutoHealLoop:
    """自愈反思重试循环器。"""

    @classmethod
    def run_with_heal(cls, runner_fn, max_retries: int = 2) -> Dict[str, Any]:
        attempt = 0
        heal_logs: List[str] = []
        context_patch: Dict[str, Any] = {}

        while attempt <= max_retries:
            attempt += 1
            result = runner_fn(context_patch)
            score, flaws = CriticEvaluator.evaluate(
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
                # 注入修复补丁
                context_patch["force_owner"] = "r02_auto_assign"
                context_patch["enforce_quant"] = True

        result["verdict"] = "FAIL_AFTER_HEAL"
        result["heal_attempts"] = attempt
        result["heal_logs"] = heal_logs
        return result
