# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 真实决策审校器与反思自愈循环 (Executive Critic & Auto-Heal Loop)。

对标 GitHub 开源标杆:
- Reflexion (noahshinn/reflexion 5.8k+ stars) / Critic-Agent / Self-Refine
- 依据 CEO 三大黄金决策法则（不可逆带回滚、必须有量化杀死标准、责任人唯一且终身留痕）进行硬核审查。
- 部署 `while attempt <= max_retries` 闭环自愈修正。
"""
from __future__ import annotations
import copy
from typing import Any, Dict, List, Tuple

class ExecutiveCritic:
    """CEO 级决策严格审校器。"""

    @classmethod
    def audit_decision_card(cls, card_data: Dict[str, Any]) -> Tuple[bool, float, List[Dict[str, Any]]]:
        """按 3 条黄金法则打分 (0-100分)。"""
        checks = []
        score = 100.0

        # 法则 1：不可逆决策必须具备回滚预案与止损上限
        rev = card_data.get("reversibility", "可逆")
        rollback = card_data.get("rollback_plan") or card_data.get("rollback_cost_months")
        if rev == "不可逆" and not rollback:
            checks.append({
                "rule": "RULE_1_REVERSIBILITY_LOCK",
                "severity": "CRITICAL",
                "msg": "不可逆决策必须明确回滚方案或时间上限，否则严禁放行"
            })
            score -= 40.0

        # 法则 2：必须具备清晰且可验证的杀死标准 (Kill Criteria)
        kill_criteria = card_data.get("kill_criteria", [])
        if not kill_criteria:
            checks.append({
                "rule": "RULE_2_KILL_CRITERIA_REQUIRED",
                "severity": "CRITICAL",
                "msg": "决策必须定义明确的触发即终止杀死标准 (Kill Criteria)"
            })
            score -= 40.0

        # 法则 3：单一责任人归属与量化成功标准
        owner = card_data.get("owner")
        success_criteria = card_data.get("success_criteria", [])
        if not owner or not success_criteria:
            checks.append({
                "rule": "RULE_3_OWNERSHIP_AND_SUCCESS_CRITERIA",
                "severity": "HIGH",
                "msg": "决策必须明确单一 DRI (Owner) 与成功度量指标"
            })
            score -= 20.0

        score = max(0.0, score)
        passed = (len([c for c in checks if c["severity"] == "CRITICAL"]) == 0 and score >= 70.0)
        return passed, score, checks

    @classmethod
    def auto_heal(cls, card_data: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Auto-Heal 自愈修复闭环。"""
        current_data = copy.deepcopy(card_data)
        attempt = 1
        heal_log = []

        while attempt <= max_retries:
            passed, score, checks = cls.audit_decision_card(current_data)
            if passed:
                return {
                    "ok": True,
                    "final_score": score,
                    "attempts": attempt,
                    "card": current_data,
                    "heal_log": heal_log
                }

            # 执行自愈注入修复补丁
            step_patch = []
            for c in checks:
                if c["rule"] == "RULE_1_REVERSIBILITY_LOCK":
                    current_data["rollback_plan"] = "自动注入标准回滚：保留上一版本基线，30天内发现数据崩盘立即无损切回"
                    step_patch.append("注入标准回滚预案")
                elif c["rule"] == "RULE_2_KILL_CRITERIA_REQUIRED":
                    current_data["kill_criteria"] = [
                        "上线14天内核心指标出现 >15% 异常下跌且无法归因于外部周期",
                        "核心客诉/合规红线触发一票否决"
                    ]
                    step_patch.append("注入工业级杀死标准")
                elif c["rule"] == "RULE_3_OWNERSHIP_AND_SUCCESS_CRITERIA":
                    if not current_data.get("owner"):
                        current_data["owner"] = "r01"
                    if not current_data.get("success_criteria"):
                        current_data["success_criteria"] = ["新策略执行30天内达成预期ROI >= 1.5"]
                    step_patch.append("补充 DRI 与量化成功标准")

            heal_log.append({
                "attempt": attempt,
                "score_before": score,
                "patches_applied": step_patch
            })
            attempt += 1

        # 最终验证
        passed, score, checks = cls.audit_decision_card(current_data)
        return {
            "ok": passed,
            "final_score": score,
            "attempts": attempt - 1,
            "card": current_data,
            "heal_log": heal_log
        }
