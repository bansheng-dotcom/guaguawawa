# -*- coding: utf-8 -*-
"""R03 质感去劣化与 Anti-Slop 审计精修器 (L05 质感去劣化)。

对标高星标杆: pbakaus/impeccable (106k+) / Anti-Slop
审计并过滤财务与合规分析中的“假大空伪影”，如：
- “高度重视现金流”、“逐步落实降本增效”、“持续跟进税务风险”、“加强合规管理”等无责任主体、无具体金额、无时间窗口的空话套话。
落地特性:
1. audit_text(): 计算伪影与套话扣分并输出诊断清单
2. polish(): 物理精修，自动将模糊空话替换为具备 DRI、量化控制指标及法定截止期限的高质感表述
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

class FinancialSlopGuard:
    """财务合规防水军与去伪影卫士。"""

    SLOP_PATTERNS = [
        r"高度重视", r"逐步落实", r"尽快推进", r"持续跟进", r"加强沟通",
        r"优化流程", r"多措并举", r"抓紧落实", r"深入分析", r"稳妥推进",
        r"积极应对", r"全面排查", r"规范管理", r"加强合规"
    ]

    REPLACEMENTS = {
        "高度重视": "设立专项目标并锁定预警阈值",
        "逐步落实": "拆解为具体责任周计划并追踪达成率",
        "尽快推进": "在 5 个工作日内完成审批并闭环",
        "持续跟进": "指定专人每日核对并在周会前提交台账",
        "多措并举": "实施量化控费三项清单",
        "加强合规": "严格对照法定红线落实审计取证",
        "优化流程": "精简审批节点并将处理时效压缩至法定 SLA 内"
    }

    @classmethod
    def audit_text(cls, text: str) -> Tuple[float, List[str]]:
        """审查文本中包含的空话套话并计算反模式违规度。"""
        detected: List[str] = []
        for pat in cls.SLOP_PATTERNS:
            matches = re.findall(pat, text)
            if matches:
                detected.extend(matches)

        penalty = len(detected) * 1.5
        score = max(0.0, 10.0 - penalty)
        return score, detected

    @classmethod
    def polish(cls, text: str, default_dri: str = "CFO_Office", default_amount: float = 10000.0) -> str:
        """物理去劣化精修：将空话套话强制替换为明确 DRI、金额与时间盒的具体陈述。"""
        polished = text
        for bad_word, replacement in cls.REPLACEMENTS.items():
            if bad_word in polished:
                polished = polished.replace(bad_word, replacement)

        # 若缺乏量化标识，补充治理闭环标注
        if not re.search(r"(\$|¥|[0-9]+%|[0-9]+元|[0-9]+天|[0-9]+月)", polished):
            polished += f" [闭环指引: 由 {default_dri} 于 10 个工作日内落实管控指标 ¥{default_amount:.2f}]"

        return polished
