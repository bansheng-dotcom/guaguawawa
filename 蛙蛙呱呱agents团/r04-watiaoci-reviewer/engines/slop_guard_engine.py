# -*- coding: utf-8 -*-
"""L05 质感去劣化：SlopGuard 可行动性审计与精准行号绑定引擎。
对标开源项目：reviewdog (Stars > 6.5k), Google StyleGuide (Stars > 37k)。
解决病灶：审查意见充斥“整体良好”、“建议进一步加强”、“注意代码规范”等假大空废话 (AI Slop)，缺乏具体行号、代码锚点与可检验的重构建议。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


class SlopGuardEngine:
    """去套话 (Anti-Slop) 审计与行号约束精修引擎。"""

    # 典型废话套话模式库
    SLOP_PATTERNS = [
        r"整体(?:表现|来看)?(?:良好|不错|尚可)",
        r"建议(?:进一步)?(?:加强|优化|提升|完善)",
        r"注意(?:代码)?(?:规范|风格)",
        r"后续(?:持续)?(?:跟进|关注)",
        r"原则上(?:可以|同意|予以)",
        r"需在未来版本中解决",
        r"总体架构设计合理",
    ]

    @classmethod
    def audit_critique(cls, text: str, line_number: int | None = None, file_anchor: str | None = None) -> Dict[str, Any]:
        """审计单条评审意见是否含有废话套话，并检查是否绑定了行号与可执行修复动作。"""
        slop_hits = []
        for pat in cls.SLOP_PATTERNS:
            if re.search(pat, text):
                slop_hits.append(pat)

        has_line = line_number is not None and line_number > 0
        has_anchor = bool(file_anchor and file_anchor.strip())
        is_slop = len(slop_hits) > 0

        # 行动性审计 (Actionability): 必须包含具体动作指示动词与量化/确切目标
        actionable_verbs = ["替换", "删除", "重命名", "封装", "提取", "修复", "引入", "捕获", "校验"]
        has_action = any(v in text for v in actionable_verbs)

        score = 100
        if is_slop:
            score -= 40
        if not has_line:
            score -= 30
        if not has_anchor:
            score -= 15
        if not has_action:
            score -= 15

        actionable = (score >= 70) and not is_slop and has_line

        return {
            "text": text,
            "is_slop": is_slop,
            "slop_hits": slop_hits,
            "has_line": has_line,
            "line_number": line_number,
            "file_anchor": file_anchor,
            "has_action": has_action,
            "actionability_score": max(0, score),
            "actionable": actionable,
        }

    @classmethod
    def polish_critique(cls, raw_critique: str, file_path: str, line: int, concrete_fix: str) -> Dict[str, Any]:
        """将模糊的套话评审意见物理重构为符合工业级准则的高质感明确指令。"""
        cleaned = raw_critique
        for pat in cls.SLOP_PATTERNS:
            cleaned = re.sub(pat, "", cleaned).strip("，。； ")

        polished_message = f"[{file_path}:{line}] 缺陷发现：{cleaned or '存在结构性反模式'}。处置动作：{concrete_fix}"
        return {
            "raw": raw_critique,
            "file_path": file_path,
            "line": line,
            "concrete_fix": concrete_fix,
            "polished_message": polished_message,
        }
