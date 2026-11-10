# -*- coding: utf-8 -*-
"""engines/pm_slop_guard.py - L05 质感去劣化 (PM Slop Guard & Anti-Hallucination).

对标开源标杆：reviewdog / StyleGuide / Vale / Pragmatic Spec (Stars > 10k)
核心职责：
1. 拦截 PRD、用户故事与需求方案中的假大空词汇与套话：
   - "提升用户体验"
   - "优化性能"
   - "待定" / "TODO"
   - "根据实际情况" / "视情况而定"
   - "大幅增加留存" / "显著提升效率"
2. 物理级替换为可行动、可测量 (Actionable & Measurable) 的具体指标判据与执行基线；
3. 输出审计报告 (Purification Report)，杜绝伪劣需求流入技术研发环节。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class PMSlopGuard:
    """R07 L05 产品需求质感去劣化与套话拦截守卫。"""

    SLOP_DICTIONARY = [
        (
            r"提升(?:了)?用户体验",
            "降低首屏交互耗时至<1.2s，关键流程转化漏斗流失率下降>=15%",
            "用户体验必须定义具体步骤耗时或流失率降幅",
        ),
        (
            r"优化性能",
            "P99接口响应时间控制在200ms以内，弱网环境加载成功率>=99.5%",
            "性能优化必须具备P95/P99分位延迟指标",
        ),
        (
            r"(?:功能)?待定|TODO:?.*|暂未确定",
            "一期采用标准确定性规则兜底，预留标准化配置扩展接口",
            "PRD禁止出现未决TODO，必须给出MVP确定性降级方案",
        ),
        (
            r"根据实际情况(?:而定)?|视情况而定|视业务而定",
            "按预设A/B对照组三档阈值(基准线/上浮20%/下浮20%)梯次自动降级",
            "严禁模棱两可，必须设定定量梯次或条件分支",
        ),
        (
            r"大幅增加留存|显著提升留存",
            "提升新用户次周留存率绝对值+3.5%，30日复购频次提升10%",
            "留存指标必须明确统计周期与目标绝对/相对增量",
        ),
        (
            r"提升(?:研发|协作)?效率",
            "端到端协作审批流转时长缩短50%，单次任务手工配置步骤由7步精简至2步",
            "效率提升必须提供操作步骤缩减或工时节约测量方法",
        ),
        (
            r"界面稍后补充|稍后开发|后续考虑",
            "一期提供单屏极简核心操作交互，完成主流程状态闭环",
            "禁止无边界占位，必须明确当期范围",
        ),
    ]

    def __init__(self):
        self.version = "1.0.0"

    def audit_text(self, text: str) -> Dict[str, Any]:
        """对文本进行套话模式匹配与可行动性审计。"""
        issues: List[Dict[str, Any]] = []
        clean_text = text

        for pattern, replacement, reason in self.SLOP_DICTIONARY:
            matches = list(re.finditer(pattern, clean_text, re.IGNORECASE))
            if matches:
                for m in matches:
                    issues.append({
                        "pattern": pattern,
                        "matched": m.group(0),
                        "suggested_actionable": replacement,
                        "reason": reason,
                        "severity": "BLOCKER",
                    })
                clean_text = re.sub(pattern, replacement, clean_text, flags=re.IGNORECASE)

        return {
            "is_clean": len(issues) == 0,
            "issues_found": len(issues),
            "issues": issues,
            "purified_text": clean_text,
            "actionability_score": 100 if len(issues) == 0 else max(30, 100 - len(issues) * 15),
        }

    def purify_prd_artifact(self, prd_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """递归净化 PRD / 需求 JSON 工件中的所有字符串字段。"""
        purified = {}
        total_replacements = 0

        for k, v in prd_data.items():
            if isinstance(v, str):
                audit = self.audit_text(v)
                purified[k] = audit["purified_text"]
                total_replacements += audit["issues_found"]
            elif isinstance(v, dict):
                sub_p, cnt = self.purify_prd_artifact(v)
                purified[k] = sub_p
                total_replacements += cnt
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, str):
                        audit = self.audit_text(item)
                        new_list.append(audit["purified_text"])
                        total_replacements += audit["issues_found"]
                    elif isinstance(item, dict):
                        sub_p, cnt = self.purify_prd_artifact(item)
                        new_list.append(sub_p)
                        total_replacements += cnt
                    else:
                        new_list.append(item)
                purified[k] = new_list
            else:
                purified[k] = v

        return purified, total_replacements
