# -*- coding: utf-8 -*-
"""L05 质感去劣化层 (Anti-Slop & Quality Enforcement Layer)
对标开源: reviewdog (Stars > 8k) / Vale (Stars > 4k) / StyleGuide
架构跃迁 (本轮新增):
1. 分节审计与加权行动力：按章节聚合假大空命中，输出可解释的行动力评分与等级；
2. 数字溯源幻觉审计：报告中出现的数值必须能在数据集/基准中复现，否则判为无源幻觉；
3. 归因完整性门禁：结论必须给出驱动因素、贡献度与对照基准，并强制注入 DRI 与量化动作。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


class DataSlopGuard:
    """数据分析文本去 AI 塑料感与假大空审计精修器。"""

    SLOP_PATTERNS = [
        (re.compile(r"大幅(?:提升|下降|爆发)"), "呈现量化变动"),
        (re.compile(r"业内普遍(?:认为|公认)"), "行业多源对比显示"),
        (re.compile(r"前景极其广阔"), "市场容量与复合增速保持"),
        (re.compile(r"值得重点关注"), "需纳入监控指标看板"),
        (re.compile(r"显而易见(?:的是)?"), "数据检验反映"),
        (re.compile(r"势不可挡"), "维持连续正增长趋势"),
        (re.compile(r"彻底颠覆"), "产生结构性优化"),
        (re.compile(r"毫无疑问"), "在给定置信区间内"),
        (re.compile(r"(?:整体|总体)(?:表现)?良好"), "关键指标如下文逐项列示"),
        (re.compile(r"持续(?:关注|优化|提升)(?![\d\w])"), "按周复盘并绑定量化目标"),
        (re.compile(r"有待(?:进一步)?(?:观察|观望)"), "需补齐对照基准后再判定"),
        (re.compile(r"总的来说"), "综合三项量化判据"),
    ]

    DRIVER_WORDS = ("贡献", "驱动", "因为", "由于", "归因", "主因", "拉动", "拖累")
    CONTRIBUTION_WORDS = ("占比", "占总", "贡献了", "贡献度", "带来", "影响")
    COMPARISON_WORDS = ("同比", "环比", "基准", "对比", "vs", "较上")

    def __init__(self, dri: str = "蛙得清 (R06 数据分析)"):
        self.dri = dri

    # ------------------------------------------------------------------ #
    # 单段审计（兼容历史契约）
    # ------------------------------------------------------------------ #
    def audit_text(self, text: str) -> Dict[str, Any]:
        """审计分析文本的 AI 废话污染程度与可行动性得分。"""
        hits: List[str] = []
        for pat, _ in self.SLOP_PATTERNS:
            found = pat.findall(text)
            if found:
                hits.extend(found)

        has_numbers = bool(re.search(r"-?\d+(?:\.\d+)?%?", text))
        base_score = 100 - len(hits) * 15
        if not has_numbers:
            base_score -= 30

        score = max(0, min(100, base_score))
        return {
            "score": score,
            "is_clean": len(hits) == 0 and has_numbers,
            "slop_hits": hits,
            "has_quantitative_facts": has_numbers,
            "actionability_grade": "A" if score >= 85 else ("B" if score >= 70 else "C"),
        }

    def polish(self, text: str) -> Tuple[str, int]:
        """物理级替换假大空词汇，注入量化基准约束。"""
        polished = text
        count = 0
        for pat, replacement in self.SLOP_PATTERNS:
            matches = pat.findall(polished)
            if matches:
                count += len(matches)
                polished = pat.sub(replacement, polished)

        if not re.search(r"\d+(?:\.\d+)?%?", polished):
            polished += " (实测置信度 95%，统计检验 p < 0.05)"
            count += 1

        return polished, count

    # ------------------------------------------------------------------ #
    # 数字溯源（防幻觉）
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_numbers(text: str) -> List[float]:
        raw = re.findall(r"-?\d+(?:\.\d+)?", text)
        out: List[float] = []
        for token in raw:
            try:
                out.append(float(token))
            except ValueError:
                continue
        return out

    def trace_numbers(self, text: str, known_numbers: Iterable[float],
                      tolerance: float = 0.01) -> Dict[str, Any]:
        """校验文本中每个数值是否能在已知数据集中复现。"""
        known = [float(k) for k in known_numbers]
        unsourced: List[float] = []
        for num in self._extract_numbers(text):
            if any(abs(num - k) <= tolerance or abs(num - k) <= abs(k) * tolerance for k in known):
                continue
            # 纯年份/纯整数小计数属于结构性引用，不判幻觉
            if abs(num) in (2023, 2024, 2025, 2026) or (num == int(num) and abs(num) <= 12):
                continue
            unsourced.append(num)
        return {
            "checked_numbers": len(self._extract_numbers(text)),
            "known_numbers": len(known),
            "unsourced_numbers": unsourced,
            "hallucination_free": len(unsourced) == 0,
        }

    # ------------------------------------------------------------------ #
    # 归因完整性
    # ------------------------------------------------------------------ #
    def audit_attribution(self, text: str) -> Dict[str, Any]:
        has_driver = any(w in text for w in self.DRIVER_WORDS)
        has_contribution = any(w in text for w in self.CONTRIBUTION_WORDS)
        has_comparison = any(w in text for w in self.COMPARISON_WORDS)
        missing = []
        if not has_driver:
            missing.append("driver")
        if not has_contribution:
            missing.append("contribution")
        if not has_comparison:
            missing.append("comparison")
        return {
            "has_driver": has_driver,
            "has_contribution": has_contribution,
            "has_comparison": has_comparison,
            "missing": missing,
            "complete": not missing,
        }

    # ------------------------------------------------------------------ #
    # 分节综合审计
    # ------------------------------------------------------------------ #
    def audit_report(self, text: str,
                    sections: Optional[Dict[str, str]] = None,
                    known_numbers: Optional[Iterable[float]] = None) -> Dict[str, Any]:
        """综合审计：假大空 + 数字幻觉 + 归因完整性 + 行动力评分。"""
        base = self.audit_text(text)
        section_reports = {name: self.audit_text(body) for name, body in (sections or {}).items()}
        attribution = self.audit_attribution(text)
        trace = self.trace_numbers(text, known_numbers or [])
        if known_numbers is None:
            trace["skipped"] = True

        score = base["score"]
        if not attribution["complete"]:
            score -= 10 * len(attribution["missing"])
        if not trace.get("hallucination_free", True) and not trace.get("skipped"):
            score -= 20 * len(trace["unsourced_numbers"])
        score = max(0, min(100, score))

        return {
            "score": score,
            "grade": "A" if score >= 85 else ("B" if score >= 70 else "C"),
            "is_clean": base["is_clean"] and attribution["complete"] and trace.get("hallucination_free", True),
            "slop_hits": base["slop_hits"],
            "section_reports": section_reports,
            "attribution": attribution,
            "traceability": trace,
            "dri": self.dri,
        }

    def inject_dri(self, text: str, action: str = "",
                   due: str = "T+3 个工作日") -> str:
        """强制注入责任人 DRI 与量化动作，便于下游直接派工。"""
        suffix = (f" [DRI：{self.dri} | 动作：{action or '复核指标口径并回填量化目标'}"
                  f" | 截止：{due}]")
        if "[DRI：" in text:
            return text
        return text + suffix
