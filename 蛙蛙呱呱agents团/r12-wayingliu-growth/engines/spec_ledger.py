# -*- coding: utf-8 -*-
"""[L04] 领域账本层 (Domain Spec Ledger & Growth SSOT).

对标标杆: PostHog / dbt Semantic Layer / GrowthBook
核心功能:
1. 规范并动态加载 GROWTH_SPEC.md 单一信任源 (Single Source of Truth)；
2. 提取北极星指标、8 维增长门禁、统计显著性准则、全渠道标准及反劣化黑名单；
3. 提供动态校验与规则导出 (JSON / Markdown / Dict)。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional


class SpecLedger:
    """增长运营领域业务与技术账本解析管理引擎。"""

    def __init__(self, spec_path: Optional[str] = None) -> None:
        if spec_path is None:
            here = os.path.dirname(os.path.abspath(__file__))
            agent_root = os.path.dirname(here)
            spec_path = os.path.join(agent_root, "GROWTH_SPEC.md")
        self.spec_path = spec_path
        self._cached_spec: Optional[Dict[str, Any]] = None

    def load_spec(self) -> Dict[str, Any]:
        """动态加载并解析 GROWTH_SPEC.md 为结构化配置字典。"""
        if self._cached_spec is not None:
            return self._cached_spec

        if not os.path.exists(self.spec_path):
            spec = self._fallback_spec()
            self._cached_spec = spec
            return spec

        with open(self.spec_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        north_star = self._parse_north_star(raw_text)
        stat_criteria = self._parse_statistical_criteria(raw_text)
        gates = self._parse_release_gates(raw_text)
        channels = self._parse_channel_standards(raw_text)
        blacklist = self._parse_slop_blacklist(raw_text)

        spec = {
            "spec_loaded": True,
            "version": "1.0.0",
            "spec_file": self.spec_path,
            "north_star": north_star.get("primary", "WAU"),
            "north_star_details": north_star,
            "confidence_threshold": stat_criteria.get("confidence_threshold", 0.95),
            "p_value_threshold": stat_criteria.get("p_value_threshold", 0.05),
            "statistical_criteria": stat_criteria,
            "release_gates": gates,
            "omnichannel_standards": channels,
            "slop_blacklist": blacklist,
            "scenario_types": [
                "minimal_rapid",
                "steady_lean",
                "omnichannel_roi_balanced",
            ],
        }
        self._cached_spec = spec
        return spec

    def _parse_north_star(self, text: str) -> Dict[str, Any]:
        primary = "WAU"
        m = re.search(r"Primary Metric:\s*([A-Za-z0-9_]+)", text)
        if m:
            primary = m.group(1).strip()
        sec_m = re.search(r"Secondary Metric:\s*([^\n]+)", text)
        secondary = sec_m.group(1).strip() if sec_m else "Paid Retention Rate (D30 >= 20%)"
        return {"primary": primary, "secondary": secondary}

    def _parse_statistical_criteria(self, text: str) -> Dict[str, Any]:
        p_val = 0.05
        m_p = re.search(r"P-Value Threshold:\s*p\s*<\s*([0-9\.]+)", text)
        if m_p:
            p_val = float(m_p.group(1))

        conf = 0.95
        m_c = re.search(r"Confidence Level:\s*>=\s*([0-9\.]+)%", text)
        if m_c:
            conf = float(m_c.group(1)) / 100.0

        min_sample = 1000
        m_s = re.search(r"Minimum Sample Size:\s*([0-9]+)", text)
        if m_s:
            min_sample = int(m_s.group(1))

        return {
            "p_value_threshold": p_val,
            "confidence_threshold": conf,
            "min_sample_size": min_sample,
            "min_mde": 0.05,
            "min_power": 0.80,
        }

    def _parse_release_gates(self, text: str) -> List[Dict[str, Any]]:
        default_gates = [
            {"id": "Gate-01", "name": "Metric-Goal Alignment", "desc": "北极星对齐门禁"},
            {"id": "Gate-02", "name": "Statistical Significance", "desc": "显著性准则门禁"},
            {"id": "Gate-03", "name": "Unit Economics Health", "desc": "单位经济学门禁"},
            {"id": "Gate-04", "name": "Virality & Referral Loop", "desc": "病毒裂变门禁"},
            {"id": "Gate-05", "name": "Omnichannel Compliance", "desc": "全渠道合规门禁"},
            {"id": "Gate-06", "name": "Anti-Slop & Quantitative Evidence", "desc": "去劣化量化门禁"},
            {"id": "Gate-07", "name": "Scenario Matrix Coverage", "desc": "三维方案决策门禁"},
            {"id": "Gate-08", "name": "Redline & Anti-Fraud Safety", "desc": "红线安全门禁"},
        ]
        gate_matches = re.findall(r"\*\*Gate-(\d+):\s*([^(\n]+)\(([^)\n]+)\)\*\*", text)
        if len(gate_matches) >= 8:
            return [
                {"id": f"Gate-{idx}", "name": name.strip(), "desc": desc.strip()}
                for idx, name, desc in gate_matches
            ]
        return default_gates

    def _parse_channel_standards(self, text: str) -> Dict[str, Any]:
        return {
            "微信生态": {"min_chars": 800, "max_chars": 5000, "ctr_baseline": 0.015},
            "小红书": {"min_chars": 200, "max_chars": 1000, "engagement_baseline": 0.05},
            "付费投放": {"target_roas": 1.5, "max_cac": 200.0},
            "冷邮件外联": {"reply_rate_baseline": 0.08, "require_compliance": True},
            "应用商店": {"rating_baseline": 4.5, "keyword_density_range": [0.02, 0.05]},
        }

    def _parse_slop_blacklist(self, text: str) -> List[str]:
        defaults = [
            "显著提升",
            "大幅增长",
            "视情况而定",
            "待定",
            "毋庸置疑",
            "毫无疑问",
            "综上所述",
            "开启了新的篇章",
            "让我们拭目以待",
            "持续向好",
        ]
        m = re.search(r"## 5\. Slop Blacklist.*?\n((?:- .*\n?)+)", text)
        if m:
            items = [line.strip("- ").strip() for line in m.group(1).splitlines() if line.strip("- ").strip()]
            if items:
                return items
        return defaults

    def validate_growth_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """依据账本 8 大门禁对增长方案进行确定性动态检验。"""
        spec = self.load_spec()
        gate_results: List[Dict[str, Any]] = []

        # Gate 01: 北极星对齐门禁
        goal_text = str(plan.get("goal", plan.get("north_star", ""))).upper()
        ns_primary = str(spec.get("north_star", "WAU")).upper()
        ns_passed = ns_primary in goal_text or "WAU" in goal_text or "DAU" in goal_text or "RETENTION" in goal_text or "留存" in goal_text
        gate_results.append({
            "gate": "Gate-01: Metric-Goal Alignment (北极星对齐门禁)",
            "passed": ns_passed,
            "message": f"目标对齐北极星指标 [{ns_primary}]" if ns_passed else f"目标缺失或未对齐北极星指标 [{ns_primary}]",
        })

        # Gate 02: 显著性门禁 (若涉及 A/B 实验)
        p_val = plan.get("p_value")
        conf = plan.get("confidence", plan.get("confidence_level"))
        stat_required = "ab_test" in plan or p_val is not None
        if stat_required:
            stat_passed = (p_val is not None and float(p_val) < spec["p_value_threshold"]) and (
                conf is None or float(conf) >= spec["confidence_threshold"] or float(conf) >= 95.0
            )
            msg = f"统计显著性达标 (p={p_val}, conf={conf})" if stat_passed else f"统计显著性不达标 (要求 p < {spec['p_value_threshold']})"
        else:
            stat_passed = True
            msg = "非 A/B 测试实验，显著性检查免试通过"
        gate_results.append({
            "gate": "Gate-02: Statistical Significance (显著性准则门禁)",
            "passed": stat_passed,
            "message": msg,
        })

        # Gate 03: 单位经济学门禁
        ltv_cac = plan.get("ltv_cac")
        payback = plan.get("payback_months")
        if ltv_cac is not None:
            ue_passed = float(ltv_cac) >= 3.0 and (payback is None or float(payback) <= 12.0)
            msg = f"LTV/CAC 为 {ltv_cac} (>= 3.0), 回收期 {payback}m (<= 12m)" if ue_passed else f"LTV/CAC={ltv_cac} 低于健康阈值 3.0"
        else:
            ue_passed = True
            msg = "未提供单位经济学预算，默认通过"
        gate_results.append({
            "gate": "Gate-03: Unit Economics Health (单位经济学门禁)",
            "passed": ue_passed,
            "message": msg,
        })

        # Gate 04: 病毒裂变门禁
        k_factor = plan.get("k_factor")
        if k_factor is not None:
            k_passed = float(k_factor) >= 0.0
            msg = f"K-Factor 测算完成 (K={k_factor})"
        else:
            k_passed = True
            msg = "无裂变指标需求"
        gate_results.append({
            "gate": "Gate-04: Virality & Referral Loop (病毒裂变门禁)",
            "passed": k_passed,
            "message": msg,
        })

        # Gate 05: 全渠道合规门禁
        channel = plan.get("channel")
        channels = spec.get("omnichannel_standards", {})
        if channel:
            channel_passed = any(c in channel or channel in c for c in channels)
            msg = f"渠道 [{channel}] 符合全渠道矩阵规范" if channel_passed else f"渠道 [{channel}] 属于非标渠道"
        else:
            channel_passed = True
            msg = "未指定特定渠道"
        gate_results.append({
            "gate": "Gate-05: Omnichannel Compliance (全渠道合规门禁)",
            "passed": channel_passed,
            "message": msg,
        })

        # Gate 06: 去劣化量化门禁
        all_text = " ".join([str(v) for v in plan.values() if isinstance(v, (str, list, dict))])
        found_slop = [w for w in spec.get("slop_blacklist", []) if w in all_text]
        slop_passed = len(found_slop) == 0
        gate_results.append({
            "gate": "Gate-06: Anti-Slop & Quantitative Evidence (去劣化量化门禁)",
            "passed": slop_passed,
            "message": "文案客观量化无套话" if slop_passed else f"命中假大空违禁词: {found_slop}",
        })

        # Gate 07: 三维方案决策门禁
        scenarios = plan.get("scenarios")
        if scenarios is not None:
            sc_passed = isinstance(scenarios, list) and len(scenarios) >= 3
            msg = f"已裂变 {len(scenarios)} 维决策方案" if sc_passed else "决策方案不足 3 维"
        else:
            sc_passed = True
            msg = "方案情景矩阵检查通过"
        gate_results.append({
            "gate": "Gate-07: Scenario Matrix Coverage (三维方案决策门禁)",
            "passed": sc_passed,
            "message": msg,
        })

        # Gate 08: 红线安全门禁
        redlines_violated = []
        if "cash_subsidy" in all_text.lower() and (ltv_cac is None or float(ltv_cac) < 3.0):
            redlines_violated.append("无 ROI 约束的纯现金补贴")
        if "刷量" in all_text or "买量伪造" in all_text:
            redlines_violated.append("虚假流量与伪造增长")
        if "未经授权采集" in all_text or "爬取个人信息" in all_text:
            redlines_violated.append("侵犯隐私未授权采集")

        redline_passed = len(redlines_violated) == 0
        gate_results.append({
            "gate": "Gate-08: Redline & Anti-Fraud Safety (红线安全门禁)",
            "passed": redline_passed,
            "message": "合规安全，无触碰红线" if redline_passed else f"触碰安全红线: {redlines_violated}",
        })

        all_passed = all(g["passed"] for g in gate_results)
        failed_gates = [g["gate"] for g in gate_results if not g["passed"]]

        return {
            "all_passed": all_passed,
            "total_gates": len(gate_results),
            "passed_gates": sum(1 for g in gate_results if g["passed"]),
            "failed_gates": failed_gates,
            "gate_details": gate_results,
        }

    def export_rules(self, format_type: str = "json") -> Any:
        """导出当前生效的规则字典或 JSON 字符串。"""
        spec = self.load_spec()
        if format_type.lower() == "json":
            return json.dumps(spec, ensure_ascii=False, indent=2)
        return spec

    def export_markdown(self) -> str:
        """导出规格账本为标准 Markdown 格式。"""
        spec = self.load_spec()
        lines = [
            f"# {spec.get('north_star', 'WAU')} Growth Specification Rules",
            "",
            "## 1. Core Metrics & Significance",
            f"- North Star Metric: {spec.get('north_star')}",
            f"- P-Value Threshold: p < {spec.get('p_value_threshold')}",
            f"- Confidence Threshold: >= {spec.get('confidence_threshold') * 100}%",
            "",
            "## 2. Release Gates",
        ]
        for g in spec.get("release_gates", []):
            lines.append(f"- **{g.get('id')}**: {g.get('name')} ({g.get('desc')})")
        lines.append("")
        lines.append("## 3. Omnichannel Matrix")
        for ch, config in spec.get("omnichannel_standards", {}).items():
            lines.append(f"- **{ch}**: {json.dumps(config, ensure_ascii=False)}")
        return "\n".join(lines)

    def _fallback_spec(self) -> Dict[str, Any]:
        return {
            "spec_loaded": False,
            "version": "1.0.0-fallback",
            "spec_file": self.spec_path,
            "north_star": "WAU",
            "confidence_threshold": 0.95,
            "p_value_threshold": 0.05,
            "release_gates": [
                {"id": "Gate-01", "name": "Metric-Goal Alignment", "desc": "北极星对齐门禁"},
                {"id": "Gate-02", "name": "Statistical Significance", "desc": "显著性准则门禁"},
                {"id": "Gate-03", "name": "Unit Economics Health", "desc": "单位经济学门禁"},
                {"id": "Gate-04", "name": "Virality & Referral Loop", "desc": "病毒裂变门禁"},
                {"id": "Gate-05", "name": "Omnichannel Compliance", "desc": "全渠道合规门禁"},
                {"id": "Gate-06", "name": "Anti-Slop & Quantitative Evidence", "desc": "去劣化量化门禁"},
                {"id": "Gate-07", "name": "Scenario Matrix Coverage", "desc": "三维方案决策门禁"},
                {"id": "Gate-08", "name": "Redline & Anti-Fraud Safety", "desc": "红线安全门禁"},
            ],
            "omnichannel_standards": {},
            "slop_blacklist": ["显著提升", "大幅增长", "待定"],
            "scenario_types": ["minimal_rapid", "steady_lean", "omnichannel_roi_balanced"],
        }


GrowthSpecLedger = SpecLedger
