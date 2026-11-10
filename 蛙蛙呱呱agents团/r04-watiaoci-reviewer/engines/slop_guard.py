# -*- coding: utf-8 -*-
"""L05 质感去劣化：评审废话假大空清洗与可行动性审计器 (SlopGuard)。
对标开源标杆：reviewdog/reviewdog (Stars: 6.8k+), google/styleguide (Stars: 37k+)

功能：
1. 识别并清洗 AI 评审常见的假大空套话（如：“代码结构良好”、“整体感觉尚可”、“建议后续加强优化”等无实质内容废话）；
2. 强制核查可行动性 (Actionability Audit)：每个 finding 必须包含：
   - target (确切文件行号或对象)
   - issue_type (问题明确归类)
   - expected (预期目标要求)
   - actionable_suggestion (精准且可执行的修改建议，拒绝“进一步加强”)；
3. 输出质感去劣化报告与干净的 Findings 清单。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class SlopGuard:
    """评审质感审计与废话清洗器"""

    # 常见废话/假大空套话词库 (Slop Words)
    SLOP_PATTERNS: List[str] = [
        r"整体(?:表现|结构)?(?:良好|不错|可以|尚可)",
        r"建议(?:后续|在未来)?(?:加强|提升|优化|注意)",
        r"代码写得挺好的",
        r"基本上没有太大问题",
        r"需要高度重视",
        r"逐步落实",
        r"在适当的时候",
        r"进一步健全",
        r"overall looks good to me",
        r"pretty clean code",
        r"minor nitpicks only",
        r"looks promising",
    ]

    def audit_text(self, text: str) -> Dict[str, Any]:
        """审计一段评审意见文本的废话密度"""
        hits: List[str] = []
        for pat in self.SLOP_PATTERNS:
            found = re.findall(pat, text, flags=re.IGNORECASE)
            if found:
                hits.extend(found)

        # 检查是否包含实质细节 (行号、代码标识符、数字)
        has_file_line = bool(re.search(r"(:?\d+[:：]\d+|\.py|\.ts|\.js|line\s*\d+|第\s*\d+\s*行)", text, re.IGNORECASE))
        has_concrete_code = bool(re.search(r"(`[^`]+`|\b[a-zA-Z_][a-zA-Z0-9_]*\(\)|\b[a-zA-Z_][a-zA-Z0-9_]*\b)", text))

        actionability_score = 100.0
        if hits:
            actionability_score -= len(hits) * 25.0
        if not has_file_line:
            actionability_score -= 20.0
        if not has_concrete_code:
            actionability_score -= 20.0

        actionability_score = max(0.0, min(100.0, actionability_score))

        return {
            "slop_hits": hits,
            "has_file_line": has_file_line,
            "has_concrete_code": has_concrete_code,
            "actionability_score": round(actionability_score, 1),
            "is_actionable": actionability_score >= 60.0 and len(hits) == 0,
        }

    def sanitize_findings(self, raw_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对 findings 集合做可行动性精修，过滤或修正无价值套话"""
        clean_findings: List[Dict[str, Any]] = []
        rejected_findings: List[Dict[str, Any]] = []

        for f in raw_findings:
            desc = str(f.get("message") or f.get("description") or f.get("comment") or "")
            audit = self.audit_text(desc)

            if not audit["is_actionable"]:
                rejected_findings.append({
                    "original": f,
                    "reason": "废话套话超标或缺乏具体行号代码指引",
                    "slop_hits": audit["slop_hits"],
                })
            else:
                # 规范化强化
                item = dict(f)
                item["actionable_score"] = audit["actionability_score"]
                clean_findings.append(item)

        return {
            "total_raw": len(raw_findings),
            "clean_count": len(clean_findings),
            "rejected_count": len(rejected_findings),
            "clean_findings": clean_findings,
            "rejected_findings": rejected_findings,
        }
