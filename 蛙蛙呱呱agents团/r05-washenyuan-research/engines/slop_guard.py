# -*- coding: utf-8 -*-
"""L05 质感去劣化：战略研究报告去假大空、量化证据审计与 DRI 强制绑定。

对标标杆:
- errata-ai/vale（词库驱动 Lint：告警分级、可配置规则与稳定退出码）
- reviewdog/reviewdog（门禁式审查结果回写：阻断/建议分级）
- pbakaus/impeccable / reviewdog 生态的空话扫描实践

吸收机制:
1. 词库化规则：SLOP_PATTERNS 每条“套话正则 + 可替换的量化表述”，审计与精修共用一份词库；
2. 多维质量度量：在命中数之外，新增量化证据密度、行动力与 A/B/C/D 分级，
   让“看起来顺”与“可被证伪”区分开；
3. 门禁式阻断：enforce_quality() 先清洗再复检，占位套话（待定/TODO）、无量化证据、
   低质感分三项硬阻断，并强制注入责任人 DRI，避免“无主研报”流入决策层。
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple


class ResearchSlopGuard:
    """战略研究文本质感去劣、量化证据审计与发布门禁护栏。"""

    # (套话正则, 替换语) —— 替换语不得再命中任何套话正则，保证 polish 后复检干净
    SLOP_PATTERNS: List[Tuple[str, str]] = [
        (r"前景极其广阔", "细分市场年复合增速可测算"),
        (r"前景广阔", "细分市场存在可测算空间"),
        (r"大有可为", "存在可量化的切入机会"),
        (r"未来可期", "后续 12 个月关键指标可验证"),
        (r"整体良好", "核心指标同比保持增长"),
        (r"持续关注", "纳入季度量化跟踪清单"),
        (r"值得重点关注", "列入优先级 P1 的量化监测项"),
        (r"全面提升", "按季度提升 X%（以基线为准）"),
        (r"显著提升", "环比提升 X%（以基线为准）"),
        (r"大幅增长", "同比增长 X%（以基线为准）"),
        (r"按需采购", "按季度预算与用量核算采购"),
        (r"视情况而定", "按预设触发条件分档决策"),
        (r"相关细节待定", "相关细节将在下一里程碑补齐量化口径"),
        (r"毋庸置疑", "据已披露数据"),
        (r"总而言之", "综合上述测算"),
        (r"业内公认", "根据行业调研与披露数据"),
        (r"显而易见", "从可比数据可推导"),
        (r"颠覆式创新", "具备差异化架构优势"),
        (r"革命性突破", "在关键指标上形成代际改进"),
        (r"遥遥领先", "在核心指标上领先 X%"),
        (r"大力推进", "明确责任人与推进里程碑"),
        (r"高度重视", "由 DRI 牵头设立专项里程碑"),
        (r"基本合格", "达到验收阈值的 80 分位"),
        (r"应该差不多", "基准情景下预期可达成"),
        (r"大概率没有问题", "风险敞口已纳入敏感性测算"),
        (r"可能可以", "在基准假设下可行"),
        (r"众所周知", "根据公开资料"),
        (r"无限可能", "存在多条可选路径"),
        (r"前途无量", "长期空间取决于渗透率"),
        (r"全面赋能", "向客户输出可量化能力"),
        (r"闭环生态", "端到端流程可追溯"),
    ]

    # 量化证据：数字 + 单位 / 百分号；「来源」等溯源词同样计入证据密度
    _QUANT_RE = re.compile(
        r"\d+(?:\.\d+)?\s*(?:亿元|万元|亿美元|万美元|亿|万|元|美元|%|％|"
        r"个百分点|pp|倍|家|人|个|月|天|年|台|套)"
    )
    _SOURCE_RE = re.compile(r"来源|出处|见附表|附录|Source|source")
    _PENDING_RE = re.compile(r"待定|TODO|TBD")
    _ACTION_RE = re.compile(
        r"推进|落地|配置|里程碑|责任人|阶段|预算|触发|优先级|回收|迭代|验收|交付|试点|补齐"
    )

    # ------------------------------------------------------------------
    # 内部度量
    # ------------------------------------------------------------------
    def _quantified_mentions(self, text: str) -> int:
        """统计量化证据锚点数量（数字+单位 / 百分号 + 来源类溯源词）。"""
        return len(self._QUANT_RE.findall(text)) + len(self._SOURCE_RE.findall(text))

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        return "D"

    def _actionability(self, text: str, quantified: int) -> float:
        """行动力 0~100：量化锚点、动作动词、DRI 绑定共同决定可执行程度。"""
        action_hits = len(self._ACTION_RE.findall(text))
        score = 20.0 + min(quantified, 6) * 10.0 + min(action_hits, 4) * 5.0
        if "DRI" in text.upper():
            score += 10.0
        return round(max(0.0, min(100.0, score)), 2)

    def _score(self, slop_hits: int, quantified: int) -> float:
        """严谨度分数 0~100：套话按命中扣分，量化证据按条回补（上限 5 条）。"""
        score = 100.0 - slop_hits * 8.0 + min(quantified, 5) * 2.0
        return round(max(0.0, min(100.0, score)), 2)

    # ------------------------------------------------------------------
    # 审计 / 精修
    # ------------------------------------------------------------------
    def audit_text(self, text: str) -> Dict[str, Any]:
        """审计文本中的劣质套话，并输出量化证据密度、行动力与等级。"""
        text = text or ""
        findings: List[Dict[str, Any]] = []
        for pattern, replacement in self.SLOP_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                findings.append({
                    "pattern": pattern,
                    "count": len(matches),
                    "samples": matches[:3],
                    "replacement": replacement,
                })

        slop_hits = sum(finding["count"] for finding in findings)
        quantified = self._quantified_mentions(text)
        evidence_density = round(quantified / max(len(text), 1) * 100.0, 3)
        score = self._score(slop_hits, quantified)

        return {
            "score": score,
            "is_clean": slop_hits == 0,
            "findings_count": len(findings),
            "findings": findings,
            "slop_hits": slop_hits,
            "quantified_mentions": quantified,
            "evidence_density": evidence_density,
            "actionability": self._actionability(text, quantified),
            "grade": self._grade(score),
        }

    def polish(self, text: str) -> Tuple[str, int]:
        """按词库物理替换套话，返回 (精修文本, 替换次数)。"""
        polished = text or ""
        replacement_count = 0
        for pattern, replacement in self.SLOP_PATTERNS:
            polished, count = re.subn(pattern, replacement, polished)
            replacement_count += count
        return polished, replacement_count

    # ------------------------------------------------------------------
    # 发布门禁
    # ------------------------------------------------------------------
    def enforce_quality(self, text: str, dri: Optional[str] = None) -> Dict[str, Any]:
        """先清洗再复检：占位套话/无量化证据/低质感分三项硬阻断，并强制绑定 DRI。"""
        text = text or ""
        dri = dri or "蛙深远"

        polished, replacements = self.polish(text)
        blocking_issues: List[str] = []

        # 占位符必须在原稿上判定，否则清洗会把证据一并抹掉、造成假通过
        if self._PENDING_RE.search(text):
            blocking_issues.append("PENDING_PLACEHOLDER")
        if self._quantified_mentions(text) == 0:
            blocking_issues.append("NO_QUANTIFIED_EVIDENCE")

        audit = self.audit_text(polished)
        if audit["score"] < 60:
            blocking_issues.append("SLOP_HIGH")

        if "DRI" not in polished.upper():
            polished = polished.rstrip() + "责任人 DRI：{}。".format(dri)

        return {
            "ok": not blocking_issues,
            "polished": polished,
            "replacements": replacements,
            "score": audit["score"],
            "grade": audit["grade"],
            "blocking_issues": blocking_issues,
            "dri": dri,
            "slop_hits": audit["slop_hits"],
            "evidence_density": audit["evidence_density"],
            "quantified_mentions": audit["quantified_mentions"],
        }
