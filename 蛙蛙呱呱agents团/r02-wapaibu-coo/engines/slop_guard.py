# -*- coding: utf-8 -*-
"""R02 逻辑去劣审计与空话精修过滤器 (轮次 5 落地)。

对标高星标杆: pbakaus/impeccable (Anti-Slop vocabulary & polish filter)
审查运营文本中的假大空假口号、逻辑反模式并进行确定性精修。
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

class SlopGuard:
    """去廉价感与反逻辑伪影审计器。"""

    SLOP_PATTERNS = [
        (r"尽快推进", "明确排期节点 (24h内)"),
        (r"持续跟进", "设定每日对齐追踪负责人"),
        (r"相关人员", "指派具体责任人(DRI)"),
        (r"高度重视", "升级并纳入 P0/P1 风险看板"),
        (r"逐步落实", "拆解为 WBS 最小可交付项")
    ]

    @classmethod
    def audit_text(cls, text: str) -> Dict[str, Any]:
        detected = []
        for pat, repl in cls.SLOP_PATTERNS:
            if re.search(pat, text):
                detected.append({"pattern": pat, "suggestion": repl})
        
        slop_score = len(detected) * 20.0
        return {
            "slop_score": min(100.0, slop_score),
            "is_clean": len(detected) == 0,
            "detected_issues": detected
        }

    @classmethod
    def polish(cls, text: str) -> str:
        """物理级精修：将空话替换为行动指引。"""
        polished = text
        for pat, repl in cls.SLOP_PATTERNS:
            polished = re.sub(pat, repl, polished)
        return polished
