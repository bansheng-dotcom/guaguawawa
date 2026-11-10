# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 去劣质感与决策反伪影审查器 (Executive SlopGuard & Polish)。

对标 GitHub 开源标杆:
- pbakaus/impeccable (106k+ stars) / Anti-Slop / Anti-Hallucination
- 检测假大空空话套话、伪决策模式，并将模糊承诺自动精修为具体行动项与明确 DRI。
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

class ExecutiveSlopGuard:
    """CEO 决策反伪影与去假大空守卫。"""

    SLOP_PATTERNS = [
        (r"尽快(?:推进|落实|安排)", "缺少明确 Deadline 与具体行动步骤"),
        (r"逐步(?:优化|完善|推进)", "缺乏阶段性里程碑与验收标准"),
        (r"加强.*(?:协同|沟通|配合)", "空泛表态，未落实责任人与对接机制"),
        (r"高度重视", "情绪化空话，缺乏资源倾斜指标"),
        (r"积极(?:研究|探索)", "拖延借口，无交付物定义"),
        (r"原则上同意", "避重就轻，未完成风险评估")
    ]

    @classmethod
    def audit_text(cls, text: str) -> Tuple[bool, float, List[Dict[str, Any]]]:
        """对战略文本进行空话与反模式审计。"""
        issues = []
        for pattern, explanation in cls.SLOP_PATTERNS:
            matches = list(re.finditer(pattern, text))
            for m in matches:
                issues.append({
                    "matched": m.group(0),
                    "pos": m.span(),
                    "reason": explanation
                })

        slop_score = min(100.0, len(issues) * 25.0)
        passed = (len(issues) == 0)
        return passed, slop_score, issues

    @classmethod
    def polish_text(cls, text: str, default_owner: str = "r02", default_days: int = 7) -> str:
        """物理级精修：将空话替换为明确 DRI 与工时约束。"""
        polished = text
        replacements = [
            (r"尽快推进", f"由 {default_owner} 在 {default_days} 天内完成端到端落地并提交验收"),
            (r"尽快落实", f"由 {default_owner} 在 {default_days} 天内出具实施方案"),
            (r"逐步优化", "分两个Sprint迭代完成，首周产出MVP基准"),
            (r"进一步优化", "设定明确指标阈值并在两周内完成增量调优"),
            (r"加强各部门协同", f"建立由 {default_owner} 牵头的每日15分钟站会与阻碍消除机制"),
            (r"高度重视并积极研究", f"由 {default_owner} 组织专家评审并在48小时内出具专项可行性报告"),
            (r"原则上同意，后续细化", f"有条件通过：要求 {default_owner} 在3天内补齐回滚方案与杀死标准后生效")
        ]
        for pat, repl in replacements:
            polished = re.sub(pat, repl, polished)
        return polished
