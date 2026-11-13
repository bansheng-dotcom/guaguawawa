# -*- coding: utf-8 -*-
"""L04 领域账本层：REVIEW_SPEC.md 规范解析与确定性评分引擎。
对标开源项目：awesome-design-md (Stars > 2k)。
解决病灶：审查门禁与扣分逻辑散落硬编码，缺乏统一规范约束与确定性打分判定。
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List


class ReviewSpecEngine:
    """领域规范解析与打分引擎。"""

    DEFAULT_PENALTIES = {
        "P-THEATRE": 40,
        "P-CIRCULAR": 25,
        "P-SLOP": 10,
        "P-UNSOURCED": 20,
        "P-UNBOUND": 15,
        "P-REGRESS": 35,
        "P-STUB": 20,
    }

    @classmethod
    def load_spec(cls, spec_path: str | None = None) -> Dict[str, Any]:
        """读取并结构化解析 REVIEW_SPEC.md。"""
        if spec_path is None:
            spec_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "REVIEW_SPEC.md")

        if not os.path.exists(spec_path):
            return {"ok": False, "error": "Spec file not found"}

        with open(spec_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        penalties = dict(cls.DEFAULT_PENALTIES)
        # 正则提取反模式扣分表格
        pattern = r"\|\s*\*\*(P-[A-Z]+)\*\*\s*\|\s*[^|]+\|\s*([A-Z]+)\s*\|\s*-(\d+)\s*分\s*\|"
        matches = re.findall(pattern, content)
        for p_id, sev, score in matches:
            penalties[p_id] = int(score)

        return {
            "ok": True,
            "spec_path": spec_path,
            "version": "1.0",
            "penalties": penalties,
            "evidence_levels": ["L1", "L2", "L3"],
        }

    @classmethod
    def evaluate_verdict(cls, initial_score: int, detected_penalties: List[str]) -> Dict[str, Any]:
        """根据规范确定性扣分并计算最终裁决。"""
        spec = cls.load_spec()
        penalties_map = spec.get("penalties", cls.DEFAULT_PENALTIES)

        total_penalty = 0
        details = []
        has_critical = False

        for p_id in detected_penalties:
            score = penalties_map.get(p_id, 10)
            total_penalty += score
            is_crit = p_id in ("P-THEATRE", "P-REGRESS")
            if is_crit:
                has_critical = True
            details.append({"pattern": p_id, "penalty": score, "critical": is_crit})

        final_score = max(0, initial_score - total_penalty)

        if has_critical or final_score < 70:
            verdict = "REJECT"
        elif final_score >= 85:
            verdict = "PASS"
        else:
            verdict = "CONDITIONAL"

        return {
            "initial_score": initial_score,
            "penalty_score": total_penalty,
            "final_score": final_score,
            "verdict": verdict,
            "details": details,
        }
