# -*- coding: utf-8 -*-
"""engines/copy_slop_guard.py - L05 质感去劣化 (Copy Slop Guard & Anti-AI-Fluff).

对标标杆: reviewdog / Vale / StyleGuide (Stars > 10k)
核心功能:
1. 物理级拦截与清洗 AI 塑料感与假大空套话（喉舌式套话、无源抒情、伪学术废话）
2. 计算 Slop 劣化指数与 Actionability 行动力得分
3. 物理替换为“数据支撑 + 具象事实 + 动词行动”专业质感文本
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class CopySlopGuard:
    """文案质感去劣化与去 AI 塑料感引擎。"""

    SLOP_PATTERNS = {
        r"总而言之": "核心结论是：",
        r"综上所述": "归结为三点：",
        r"毫无疑问": "数据显示",
        r"毋庸置疑": "事实证明",
        r"显而易见": "业务指标表明",
        r"不可否认(?:的是)?": "实践印证",
        r"随着科技的飞速发展": "在工程实践中",
        r"在当今快节奏的社会中": "在当前业务场景下",
        r"正如古人所云": "行业基准表明",
        r"开启了新的篇章": "进入落地交付阶段",
        r"值得注意的是": "关键指标显示",
        r"不难发现": "数据分析表明",
        r"让我们拭目以待": "建议立即启动灰度验证",
    }

    ACTION_KEYWORDS = [
        "提升", "下降", "增加", "完成", "构建", "落地", "上线", "优化", "验证", "对比",
        "ROI", "CTR", "留存", "转化率", "GMV", "P99", "耗时", "成本", "%", "倍", "秒"
    ]

    def audit_text(self, text: str) -> Dict[str, Any]:
        """全面审计文本质感，输出 Slop 劣化指标与行动力分值。"""
        slop_hits: List[Dict[str, Any]] = []

        for pat in self.SLOP_PATTERNS:
            matches = list(re.finditer(pat, text))
            for m in matches:
                slop_hits.append({
                    "phrase": m.group(0),
                    "start": m.start(),
                    "end": m.end(),
                })

        total_words = max(1, len(text))
        slop_count = len(slop_hits)

        # Slop 扣分：每个套话扣 15 分
        slop_score = max(0.0, 100.0 - (slop_count * 15.0))
        is_clean = slop_count == 0

        # 行动力得分计算 (Actionability Score)：统计动词、数字、量化指标密度
        action_hits = sum(1 for kw in self.ACTION_KEYWORDS if kw in text)
        digits_hits = len(re.findall(r"\d+", text))
        actionability_score = min(100.0, round((action_hits * 6.0) + (digits_hits * 3.0) + (20.0 if is_clean else 0.0), 1))

        return {
            "is_clean": is_clean,
            "slop_count": slop_count,
            "slop_score": slop_score,
            "actionability_score": actionability_score,
            "slop_phrases": [h["phrase"] for h in slop_hits],
            "recommendation": "文本质感优良" if is_clean else f"检测到 {slop_count} 处 AI 塑料感套话，建议一键执行物理精修",
        }

    def polish(self, text: str) -> Tuple[str, int]:
        """一键物理级清洗，将 AI 废话置换为数据与行动导向专业质感文本。"""
        polished = text
        count = 0

        for pat, replacement in self.SLOP_PATTERNS.items():
            matches = len(re.findall(pat, polished))
            if matches > 0:
                polished = re.sub(pat, replacement, polished)
                count += matches

        return polished, count
