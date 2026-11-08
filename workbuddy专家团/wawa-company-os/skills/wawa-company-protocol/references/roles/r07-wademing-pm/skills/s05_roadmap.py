# -*- coding: utf-8 -*-
"""S05 路线图与发布。"""
from __future__ import annotations
from typing import Any, Dict
from ._common import make_result

def roadmap(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """结果导向路线图校验。"""
    checks = []
    ok = True
    
    milestones = input_data.get("milestones", [])
    for i, ms in enumerate(milestones):
        text = ms.get("description", "")
        # By [Time], we will achieve [Metric Target] to enable [Business Value]
        if "we will achieve" not in text or "to enable" not in text:
            checks.append(f"里程碑 {i} 句式不符 Outcome 契约: {text}")
            ok = False
            
    return make_result(ok, "roadmap", "roadmap", checks)
    
def releasenotes(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return make_result(True, "roadmap", "releasenotes", [])

def premortem(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """事前尸检校验。"""
    checks = []
    ok = True
    
    risks = input_data.get("failure_reasons", [])
    if len(risks) < 3:
        checks.append(f"事前尸检失败原因不足 3 个，实际 {len(risks)} 个")
        ok = False
        
    for i, risk in enumerate(risks):
        if "mitigation" not in risk or not risk["mitigation"]:
            checks.append(f"尸检原因 {i} 缺少缓解计划")
            ok = False
            
    return make_result(ok, "roadmap", "premortem", checks)
_roadmap = roadmap
_releasenotes = releasenotes
_premortem = premortem
