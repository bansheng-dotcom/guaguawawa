# -*- coding: utf-8 -*-
"""L03 自愈反思层：研究工件 Critic 审校与反思自愈循环。

对标标杆:
- noahshinn/reflexion (5.8k⭐) / all-hands-ai/OpenHands (40k⭐)
能够对研究产出与输入进行缺陷诊断（无源断言、份额未归一、方差过宽、越权拍板），
并自动触发反思、补全与自愈补丁（Auto-Heal）。
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple


class ResearchCritic:
    """战略研究 Critic 审校与自愈器。"""

    DECISION_WORDS = ["必须进入", "绝对可行", "听我的", "立刻投", "直接拍板", "毫无疑问"]

    def audit_findings(self, artifact: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """审校研究产出物的合规度与严谨性。"""
        issues = []
        # 1. 检查是否存在未挂来源的 claims
        claims = artifact.get("claims", [])
        for c in claims:
            sources = c.get("evidence_refs", []) or c.get("sources", [])
            if not sources:
                issues.append(f"Claim [{c.get('id', 'unknown')}] 缺乏引用来源")

        # 2. 检查集中度份额是否归一
        shares = artifact.get("shares", [])
        if shares and abs(sum(shares) - 100.0) > 0.01:
            issues.append(f"市场份额总和不等于 100% (当前为 {sum(shares)}%)")

        # 3. 检查越权决策词
        text_dump = str(artifact)
        for w in self.DECISION_WORDS:
            if w in text_dump:
                issues.append(f"触犯边界红线：出现越权决策拍板词 '{w}'")

        # 4. 检查双口径规模方差
        if "tam_top" in artifact and "tam_bottom" in artifact:
            top = float(artifact["tam_top"])
            bottom = float(artifact["tam_bottom"])
            if top > 0:
                var = abs(top - bottom) / top
                if var >= 0.30:
                    issues.append(f"双口径测算相对方差过宽 ({var:.1%} >= 30%)，需提示置信度收敛")

        return len(issues) == 0, issues

    def heal_payload(self, payload: Dict[str, Any], issues: List[str]) -> Dict[str, Any]:
        """根据审查病灶执行反思并注入自愈补丁。"""
        healed = dict(payload)
        reflections = []

        # 修复份额未归一
        if "shares" in healed:
            shares = healed["shares"]
            total = sum(shares)
            if total > 0 and abs(total - 100.0) > 0.01:
                scale = 100.0 / total
                healed["shares"] = [round(s * scale, 2) for s in shares]
                # 调平微小余数
                diff = 100.0 - sum(healed["shares"])
                if healed["shares"]:
                    healed["shares"][-1] = round(healed["shares"][-1] + diff, 2)
                reflections.append("自愈修复：自动按比例归一化市场份额至 100.0%")

        # 修复越权词汇替换为客观选项词
        for key, val in list(healed.items()):
            if isinstance(val, str):
                orig = val
                for dw in self.DECISION_WORDS:
                    if dw in val:
                        val = val.replace(dw, "建议权衡评估")
                if val != orig:
                    healed[key] = val
                    reflections.append(f"自愈修复：将字段 {key} 中的拍板越权词替换为客观权衡词")

        # 补全缺失 sources
        if "claims" in healed and isinstance(healed["claims"], list):
            for c in healed["claims"]:
                if isinstance(c, dict) and not c.get("evidence_refs") and not c.get("sources"):
                    c["evidence_refs"] = ["default_ref:待核实"]
                    reflections.append(f"自愈修复：为孤立 Claim [{c.get('id', '')}] 自动补充待核实标记")

        healed["_critic_reflections"] = reflections
        return healed
