# -*- coding: utf-8 -*-
"""L02 意图解构层：战略研究 Prompter 与声明式分析编译器。

对标标杆:
- stanfordnlp/dspy (19k⭐) / ray-project/ray (34k⭐)
能够听懂复杂模糊的战略研究诉求（如：“调研下做 AI 协同工具能不能做，看下巨头集中度和规模”），
自动解构为规范化度量、研究子问题、意图路由与研究步骤拓扑。
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple


class ResearchPrompter:
    """战略研究诉求自然语言解构与编译器。"""

    INTENT_KEYWORDS = {
        "sizing": ["市场规模", "tam", "sam", "som", "空间测算", "能做多大", "天花板"],
        "industry": ["行业集中度", "hhi", "cr4", "产业链", "价值链", "行业格局", "格局"],
        "competitor": ["竞品", "对手", "战斗卡", "battlecard", "矩阵对比", "对标"],
        "business": ["商业画布", "商业模式", "变现", "单位经济", "cac", "ltv"],
        "scenario": ["宏观", "pestel", "事前尸检", "风险", "失效", "死穴"],
        "auto": ["调研计划", "研究追踪", "搜集进度", "路线图"],
        "research": ["证据台账", "来源", "出处", "研报", "引用"]
    }

    def compile_intent(self, text: str) -> Dict[str, Any]:
        """将自然语言战略诉求编译为结构化研究动作拓扑。"""
        low = text.lower()
        matched_domains = []
        for domain, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in low:
                    if domain not in matched_domains:
                        matched_domains.append(domain)
                    break

        if not matched_domains:
            matched_domains = ["research"]

        # 提取关键实体与潜在数值
        money_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:亿|万|kw|w|k|元|美金|刀)", text)
        ratios = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)

        # 构建执行 DAG 节点
        dag_steps = []
        for idx, domain in enumerate(matched_domains, 1):
            if domain == "industry":
                action = "concentration" if any(k in low for k in ["hhi", "cr4", "集中度"]) else "landscape"
            elif domain == "sizing":
                action = "sensitivity" if any(k in low for k in ["敏感性", "关键驱动", "摆动"]) else "size"
            elif domain == "competitor":
                action = "battlecard" if any(k in low for k in ["战斗卡", "对位", "battlecard"]) else "matrix"
            elif domain == "scenario":
                action = "premortem" if any(k in low for k in ["尸检", "失效", "死穴", "premortem"]) else "pestel"
            elif domain == "business":
                action = "monetize" if any(k in low for k in ["变现", "定价", "cac", "ltv"]) else "canvas"
            elif domain == "auto":
                action = "track" if any(k in low for k in ["进度", "追踪", "完成率"]) else "plan"
            else:
                action = "report" if any(k in low for k in ["报告", "汇报", "穿透"]) else "ledger"

            dag_steps.append({
                "step_id": f"S{idx:02d}",
                "skill": domain,
                "action": action,
                "inputs_hint": {
                    "matched_text": text,
                    "extracted_figures": money_matches,
                    "extracted_ratios": ratios
                },
                "depends_on": [f"S{idx-1:02d}"] if idx > 1 else []
            })

        return {
            "query": text,
            "primary_domain": matched_domains[0],
            "matched_domains": matched_domains,
            "dag_steps": dag_steps,
            "step_count": len(dag_steps),
            "estimated_token_cost": len(text) * 2 + len(dag_steps) * 100
        }
