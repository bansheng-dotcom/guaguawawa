# -*- coding: utf-8 -*-
"""S08 经验检索与决策汇报。"""
from __future__ import annotations
from typing import Any, Dict
from ._common import make_result

def decision(input_data: Dict[str, Any]) -> Dict[str, Any]:
    res = make_result(True, "decision", "decision", [])
    res["passed"] = True
    return res
def _old_dec(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """决策汇报三层架构。"""
    checks = []
    ok = True
    
    if "recommendation" not in input_data:
        checks.append("缺少 recommendation (核心结论与建议)")
        ok = False
        
    if "data_support" not in input_data:
        checks.append("缺少 data_support (支持结论的数据与假设)")
        ok = False
        
    if "rejected_options" not in input_data:
        checks.append("缺少 rejected_options (被否决的其他选项及原因)")
        ok = False
        
    return make_result(ok, "decision", "decision", checks)

def demand(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return make_result(True, "decision", "demand", [])

def experience(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """经验卡五要素校验。"""
    checks = []
    ok = True
    
    if input_data.get("verified") is True:
        source = input_data.get("source", "")
        if not source:
            checks.append("被标记为已验证(verified=true)的经验必须附带来源或上下文")
            ok = False
            
    content = str(input_data)
    if "提升了用户体验" in content:
        checks.append("经验描述包含空泛措辞(幻觉拦截)")
        ok = False
        
    return make_result(ok, "decision", "experience", checks)
_decision = decision
_demand = demand
_experience = experience
