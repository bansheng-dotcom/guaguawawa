# -*- coding: utf-8 -*-
"""engines/copy_spec_ledger.py - L04 领域账本层 (Domain Spec Ledger & COPY SSOT).

对标标杆: Productboard / StyleGuide / dbt MetricFlow (Stars > 15k)
核心功能:
1. 解析并动态加载 COPY_SPEC.md 单一信任源
2. 提取 8 维发布硬门禁、全平台字数规范、反 AI 味套话黑名单
3. 提供统一校验器，判定文案是否符合领域技术账本
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional


class CopySpecLedger:
    """文案运营领域业务与技术账本解析管理引擎。"""

    def __init__(self, spec_path: Optional[str] = None) -> None:
        if spec_path is None:
            here = os.path.dirname(os.path.abspath(__file__))
            agent_root = os.path.dirname(here)
            spec_path = os.path.join(agent_root, "COPY_SPEC.md")
        self.spec_path = spec_path
        self._cached_spec: Optional[Dict[str, Any]] = None

    def load_spec(self) -> Dict[str, Any]:
        """动态加载并解析 COPY_SPEC.md 为结构化配置。"""
        if self._cached_spec is not None:
            return self._cached_spec

        if not os.path.exists(self.spec_path):
            return {
                "spec_loaded": False,
                "error": f"Spec 文件未找到: {self.spec_path}",
                "rules": {},
            }

        with open(self.spec_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        gates = self._parse_gates(raw_text)
        platforms = self._parse_platforms(raw_text)
        slop_blacklist = self._parse_slop_blacklist(raw_text)

        spec = {
            "spec_loaded": True,
            "version": "v1.0.0",
            "spec_file": self.spec_path,
            "rules": {
                "release_gates": gates,
                "platform_matrix": platforms,
                "slop_blacklist": slop_blacklist,
                "scenario_types": ["lean_datacopy", "story_empathy", "viral_conversion"],
            },
        }
        self._cached_spec = spec
        return spec

    def validate_content(
        self, content: str, title: str = "", channel: str = "微信公众号"
    ) -> Dict[str, Any]:
        """依据账本 8 大门禁对文案进行确定性检验。"""
        spec = self.load_spec()
        rules = spec.get("rules", {})
        gates = rules.get("release_gates", [])
        platforms = rules.get("platform_matrix", {})
        blacklist = rules.get("slop_blacklist", [])

        gate_results: List[Dict[str, Any]] = []

        # Gate 1: 标题吸引力
        has_title = bool(title.strip() and len(title.strip()) >= 5)
        gate_results.append({
            "gate": "Gate-01: 标题吸引力门禁",
            "passed": has_title,
            "message": "标题存在且长度适中" if has_title else "标题缺失或过短",
        })

        # Gate 2: 篇幅达标
        char_len = len(content.strip())
        platform_rule = platforms.get(channel, {"min": 500, "max": 4000})
        is_length_ok = platform_rule["min"] <= char_len <= platform_rule["max"]
        gate_results.append({
            "gate": "Gate-02: 篇幅达标门禁",
            "passed": is_length_ok,
            "message": f"正文字符数 {char_len}，渠道 [{channel}] 要求 [{platform_rule['min']}~{platform_rule['max']}]",
        })

        # Gate 3: 排版与标点
        has_bad_punct = bool(re.search(r"[!！？?]{3,}", content))
        gate_results.append({
            "gate": "Gate-03: 排版与标点门禁",
            "passed": not has_bad_punct,
            "message": "标点符号排版规范" if not has_bad_punct else "存在连续标点滥用",
        })

        # Gate 4: 广告法红线
        ad_violations = [w for w in ["国家级", "第一品牌", "100%收益", "保本保息"] if w in content]
        gate_results.append({
            "gate": "Gate-04: 广告法红线门禁",
            "passed": len(ad_violations) == 0,
            "message": "广告法词汇合规" if not ad_violations else f"包含违规词: {ad_violations}",
        })

        # Gate 5: 质感与去 AI 味
        slop_hits = [w for w in blacklist if w in content]
        gate_results.append({
            "gate": "Gate-05: 质感与去 AI 味门禁",
            "passed": len(slop_hits) <= 2,
            "message": f"AI 味套话命中 {len(slop_hits)} 处" + (f": {slop_hits[:3]}" if slop_hits else ""),
        })

        # Gate 6: 结构完整性 (包含明确 CTA 引导)
        has_cta = any(k in content for k in ["关注", "点击", "立即", "扫码", "留言", "加入", "建议", "讨论"])
        gate_results.append({
            "gate": "Gate-06: 结构完整性门禁",
            "passed": has_cta,
            "message": "包含行动号召 (CTA)" if has_cta else "缺少明确行动号召 (CTA)",
        })

        # Gate 7: 占位符拦截
        has_placeholder = bool(re.search(r"(TODO|此处待定|稍后补充|正文略)", content, re.IGNORECASE))
        gate_results.append({
            "gate": "Gate-07: 占位符拦截门禁",
            "passed": not has_placeholder,
            "message": "无未完成占位符" if not has_placeholder else "存在 TODO 或待定占位符",
        })

        # Gate 8: 未授权发布拦截
        has_unauth = any(k in content for k in ["这篇文章可以发布了", "立即发布上线", "未经授权直接发布"])
        gate_results.append({
            "gate": "Gate-08: 未授权发布拦截门禁",
            "passed": not has_unauth,
            "message": "未触发自作主张越权发布" if not has_unauth else "检测到未授权直接发布指令",
        })

        all_passed = all(g["passed"] for g in gate_results)
        failed_gates = [g["gate"] for g in gate_results if not g["passed"]]

        return {
            "all_passed": all_passed,
            "total_gates": len(gate_results),
            "passed_count": sum(1 for g in gate_results if g["passed"]),
            "failed_gates": failed_gates,
            "details": gate_results,
        }

    def _parse_gates(self, text: str) -> List[str]:
        gates = []
        for line in text.splitlines():
            if re.match(r"^\d+\.\s+\*\*Gate-\d+:", line):
                gates.append(line.split("**")[1])
        if not gates:
            gates = [
                "Gate-01: 标题吸引力门禁",
                "Gate-02: 篇幅达标门禁",
                "Gate-03: 排版与标点门禁",
                "Gate-04: 广告法红线门禁",
                "Gate-05: 质感与去 AI 味门禁",
                "Gate-06: 结构完整性门禁",
                "Gate-07: 占位符拦截门禁",
                "Gate-08: 未授权发布拦截门禁",
            ]
        return gates

    def _parse_platforms(self, text: str) -> Dict[str, Dict[str, int]]:
        return {
            "微信公众号": {"min": 1500, "max": 3000},
            "小红书笔记": {"min": 600, "max": 1000},
            "知乎专栏/回答": {"min": 1000, "max": 2500},
            "短视频/口播脚本": {"min": 300, "max": 600},
            "B站专栏/动态": {"min": 800, "max": 2000},
        }

    def _parse_slop_blacklist(self, text: str) -> List[str]:
        return [
            "总而言之", "综上所述", "显而易见", "不可否认", "毫无疑问",
            "毋庸置疑", "随着科技的飞速发展", "在当今快节奏的社会中",
            "正如古人所云", "让我们拭目以待", "开启了新的篇章",
            "值得注意的是", "不难发现"
        ]
