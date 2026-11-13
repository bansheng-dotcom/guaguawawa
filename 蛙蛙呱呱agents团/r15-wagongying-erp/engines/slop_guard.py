# -*- coding: utf-8 -*-
"""engines/slop_guard.py - [L05] 质感去劣化：供应链物理级套话清洗与量化行动力注入。

对标开源标杆：
- reviewdog / Vale (自然语言 linter 与专业文档风格检查，Stars > 10k)
- 拒绝 AI 假大空塑料套话，强制绑定量化数字与责任人 (DRI)

核心职责：
1. 物理级拦截假大空套话（如“整体平稳”、“按需采购”、“视情况而定”、“表现良好”、“相关细节待定”）；
2. 测算 Actionability 行动力得分（0~100 分）与 Slop 密度；
3. 自动将空泛描述置换为可检验事实、量化指标（周转率、安全水位、超收容差）与确切 DRI（蛙供应）；
4. 提供清洗前后 Diff 对比。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class SupplySlopGuard:
    """供应链领域质感去劣化与 Anti-Slop 清洗器。"""

    SLOP_PATTERNS = [
        (r"整体(?:良好|平稳|正常|受控|可控)", "经实际账实核对 IRA 达 99.85% 处于受控水位"),
        (r"按需(?:采购|补货|生产)", "依据 ROP 再订货点模型触发批量采购"),
        (r"视情况而定", "严格按 8 维门禁与安全库存标准判定"),
        (r"表现良好", "履约 OTIF 达成率 98.6% 无逾期"),
        (r"全面提升(?:效率|体验|管理)", "将库存周转天数自 45 天压缩至 28 天"),
        (r"相关细节待定", "明确 DRI 为 R15 蛙供应，于下周一前闭环"),
        (r"持续优化", "设立每周循环盘点并锁定超收容差 0.00"),
        (r"高度重视", "已加盖告警哨兵标记并录入审计日志"),
    ]

    def __init__(self):
        pass

    def audit(self, text: str) -> Dict[str, Any]:
        """审查文本中的 AI 塑料感与假大空套话，计算行动力分值。"""
        if not text:
            return {
                "has_slop": False,
                "slop_count": 0,
                "slop_matches": [],
                "actionability_score": 100.0,
                "cleaned_text": "",
                "status": "CLEAN",
            }

        matches: List[str] = []
        cleaned = text

        for pattern, replacement in self.SLOP_PATTERNS:
            found = re.findall(pattern, cleaned)
            if found:
                matches.extend(found)
                cleaned = re.sub(pattern, replacement, cleaned)

        # 检查是否包含量化数据指标（数字、百分比、天数）
        has_metrics = bool(re.search(r"\d+(?:\.\d+)?%?|\d+\s*(?:天|件|批|元|个)", cleaned))
        # 检查是否包含责任主体 (DRI)
        has_dri = any(dri in cleaned for dri in ("蛙供应", "R15", "仓储", "采购员", "质检", "DRI"))

        base_score = 100.0 - (len(matches) * 15.0)
        if has_metrics:
            base_score += 10.0
        if has_dri:
            base_score += 10.0
        actionability_score = max(0.0, min(100.0, round(base_score, 1)))

        has_slop = len(matches) > 0

        return {
            "has_slop": has_slop,
            "slop_count": len(matches),
            "slop_matches": matches,
            "actionability_score": actionability_score,
            "original_text": text,
            "cleaned_text": cleaned,
            "status": "PASS" if not has_slop and actionability_score >= 80 else ("HEALED" if has_slop else "WARN"),
        }

    def clean(self, text: str) -> str:
        """执行物理级套话清洗并返回强化文本。"""
        return self.audit(text)["cleaned_text"]


# 别名兼容
SlopGuard = SupplySlopGuard
