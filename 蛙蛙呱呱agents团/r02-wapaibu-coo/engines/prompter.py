# -*- coding: utf-8 -*-
"""R02 动态业务意图解析与 Prompter 编译器 (轮次 2 落地)。

对标高星标杆: DSPy / Prompt Compiler / Meta-Prompting
将自然语言模糊运营诉求解构并归一化为标准的排期/容量/SOP工单参数。
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

class OperationsPrompter:
    """动态运营业务意图解析器。"""

    @classmethod
    def decompose_intent(cls, prompt: str) -> Dict[str, Any]:
        """将自然语言业务输入解析为结构化运营参数。"""
        # 提取关键日期
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", prompt)
        # 提取工时/人天估算
        mandays = re.findall(r"(\d+(?:\.\d+)?)\s*(?:人天|人日|pd|days?)", prompt, re.I)
        hours = re.findall(r"(\d+(?:\.\d+)?)\s*(?:小时|工时|h|hours?)", prompt, re.I)
        
        # 领域意图推导
        detected_skill = "schedule"
        if any(w in prompt for w in ["容量", "超载", "工时", "负载", "分配", "派工"]):
            detected_skill = "capacity"
        elif any(w in prompt for w in ["交接", "验收", "上线", "交付"]):
            detected_skill = "handoff"
        elif any(w in prompt for w in ["复盘", "事故", "故障", "定责", "p0", "p1"]):
            detected_skill = "retro"
        elif any(w in prompt for w in ["流程", "sop", "浪费", "会议", "优化"]):
            detected_skill = "process"
        elif any(w in prompt for w in ["知识", "文档", "检索", "沉淀", "文章"]):
            detected_skill = "knowledge"
        elif any(w in prompt for w in ["项目群", "编排", "依赖", "看板", "大盘"]):
            detected_skill = "portfolio"

        return {
            "raw_prompt": prompt,
            "detected_skill": detected_skill,
            "extracted_dates": dates,
            "extracted_mandays": [float(m) for m in mandays],
            "extracted_hours": [float(h) for h in hours],
            "normalized_spec": {
                "target_domain": detected_skill,
                "confidence": 0.92,
                "needs_breakdown": True if (mandays or hours) else False
            }
        }
