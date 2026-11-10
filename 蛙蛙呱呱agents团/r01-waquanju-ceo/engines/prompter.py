# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 动态意图编译器与战略解构大脑 (Executive Prompter)。

对标 GitHub 开源标杆:
- DSPy (stanfordnlp/dspy 23k+ stars) / Meta-Prompting / LangChain Planner
- 将非结构化战略诉求动态编译为跨部门战略简报、组织责任人分工及红线约束。
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

class ExecutivePrompter:
    """CEO 动态战略意图编译器。"""
    
    INTENT_KEYWORDS = {
        "pricing": ["定价", "提价", "降价", "价格", "收费", "price", "pricing"],
        "budget": ["预算", "再平衡", "削减", "追加", "财务", "资金", "budget"],
        "boardroom": ["董事会", "股东", "季报", "年度汇报", "汇报包", "board"],
        "layoffs": ["裁员", "优化", "重组", "组织变动", "人员调整"],
        "pivot": ["转型", "掉头", "新赛道", "pivot", "战略调整"],
        "growth": ["增长", "获客", "扩张", "大促", "营销战役", "growth"]
    }

    @classmethod
    def decompose_strategic_intent(cls, user_intent: str) -> Dict[str, Any]:
        """动态解析自然语言，生成结构化战略规格。"""
        text = user_intent.strip()
        matched_category = "general_strategy"
        for cat, kws in cls.INTENT_KEYWORDS.items():
            if any(k.lower() in text.lower() for k in kws):
                matched_category = cat
                break
        
        # 提取关键量化数值（天数、金额、比例）
        days_match = re.search(r"(\d+)\s*(?:天|day)", text, re.IGNORECASE)
        timebox_days = int(days_match.group(1)) if days_match else 30
        
        amount_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|k|m|元|美元)", text, re.IGNORECASE)
        amount = amount_match.group(0) if amount_match else "未指定"

        # 推导核心影响角色
        impacted_roles = ["r01"]
        if matched_category in ("pricing", "budget"):
            impacted_roles.extend(["r02", "r06", "r14"])
        elif matched_category == "boardroom":
            impacted_roles.extend(["r02", "r06", "r07", "r13"])
        elif matched_category in ("layoffs", "pivot"):
            impacted_roles.extend(["r02", "r03", "r16"])
        else:
            impacted_roles.extend(["r02", "r07"])

        return {
            "raw_intent": text,
            "strategic_category": matched_category,
            "timebox_days": timebox_days,
            "amount_scale": amount,
            "stakeholders": list(dict.fromkeys(impacted_roles)),
            "reversibility_hypothesis": "不可逆" if matched_category in ("pricing", "layoffs", "pivot") else "可逆",
            "must_have_kill_criteria": True,
            "recommended_next_action": "card" if matched_category in ("pricing", "layoffs", "pivot") else "brief"
        }
