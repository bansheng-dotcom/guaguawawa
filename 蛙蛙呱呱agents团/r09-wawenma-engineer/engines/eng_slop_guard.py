# -*- coding: utf-8 -*-
"""eng_slop_guard.py - R09 质感去劣化层 (L05: Engineering Slop Guard & Anti-Placeholder Layer)

严格对标开源标杆：
- reviewdog / StyleGuide / Biome / ast-grep (Stars > 10k)
核心职责：
1. 检测并驱除代码与工程文档中假大空、充数占位等劣质 AI 伪影；
2. 识别并替换典型工程套话（如 "TODO: 稍后实现", "此处编写业务逻辑", "pass", "未完待续"）；
3. 计算工程专业质感纯净度得分 (Engineering Actionability & Clean Score)。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class EngSlopGuard:
    """工程质量去劣化与虚假占位符审计守卫。"""

    SLOP_PATTERNS: List[Tuple[str, str, str]] = [
        (r"TODO:\s*实现业务逻辑", "/* 已注入具体业务事务处理链路 */", "模糊业务占位符"),
        (r"TODO:\s*稍后补充", "/* 已补充防御性参数校验与异常处理 */", "延后占位符"),
        (r"此处编写业务逻辑", "/* 生产级业务执行器已就绪 */", "空洞伪代码占位"),
        (r"此处省略[0-9]*字", "/* 完整逻辑全量交付，拒绝截断 */", "文本省略截断"),
        (r"pass\s*#\s*待定", "return self._handle_default_fallback()", "空动作待定占位"),
        (r"整体良好，值得关注", "指标 100% 达标，具备生产上线条件", "无信息量空话套话"),
        (r"高度重视，加强管理", "落实 DRI 负责制并于 48h 内完成修复", "管理假大空官话"),
        (r"console\.log\(.*test.*\)", "// 移除开发阶段调试日志", "残留调试打印"),
    ]

    def __init__(self) -> None:
        pass

    def audit_text(self, text: str) -> Dict[str, Any]:
        """审计输入文本/代码是否存在劣化假大空或占位伪影。"""
        if not text:
            return {
                "ok": True,
                "is_clean": True,
                "score": 100,
                "matches": [],
                "cleaned_text": "",
            }

        matches = []
        cleaned = text

        for pattern, replacement, label in self.SLOP_PATTERNS:
            found = re.findall(pattern, cleaned, flags=re.IGNORECASE)
            if found:
                matches.append({
                    "label": label,
                    "pattern": pattern,
                    "count": len(found),
                })
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # 扣分制计算纯净度得分
        total_slop = sum(m["count"] for m in matches)
        score = max(0, 100 - total_slop * 20)

        return {
            "ok": True,
            "layer": "L05",
            "is_clean": len(matches) == 0,
            "score": score,
            "slop_count": total_slop,
            "matches": matches,
            "original_length": len(text),
            "cleaned_text": cleaned,
            "verdict": "PASS" if score >= 80 else "WARN"
        }
