# -*- coding: utf-8 -*-
"""S03 用户故事与 PRD。"""
from __future__ import annotations
import json
from typing import Any, Dict
from ._common import make_result

def _validate_prd(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """PRD 八门禁校验。"""
    checks = []
    ok = True
    
    required_sections = [
        "metrics",          # 1. 目标与指标
        "problem",          # 2. 用户问题与场景
        "stories",          # 3. 核心用户故事
        "rules",            # 4. 业务规则与边界
        "out_of_scope",     # 5. 不在范围
        "assumptions",      # 6. 承重假设
        "acceptance",       # 7. 验收标准
        "telemetry"         # 8. 遥测与埋点
    ]
    
    for sec in required_sections:
        if sec not in input_data or not input_data[sec]:
            checks.append(f"PRD 缺少必填板块: {sec}")
            ok = False
            
    # 特别检查：承重假设至少3个
    assumptions = input_data.get("assumptions", [])
    if isinstance(assumptions, list) and len(assumptions) < 3:
        checks.append(f"PRD 承重假设数量不足，要求至少3个，实际 {len(assumptions)} 个")
        ok = False
        
    
    res = make_result(ok, "prd", "prd", checks)
    res["passed_gates"] = len([s for s in required_sections if s in input_data and input_data[s]])
    return res


def _validate_acceptance(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """验收标准 Given/When/Then 校验。"""
    checks = []
    ok = True
    
    ac_list = input_data.get("criteria", [])
    if not ac_list:
        checks.append("未提供验收标准")
        ok = False
        
    for i, ac in enumerate(ac_list):
        text = ac.get("text", "")
        if "Given " not in text or "When " not in text or "Then " not in text:
            checks.append(f"验收标准 {i} 不符合 Gherkin 语法 (Given/When/Then): {text}")
            ok = False
            
    return make_result(ok, "prd", "acceptance", checks)
def _validate_story(input_data: Dict[str, Any], kind="user") -> Dict[str, Any]:
    checks = []
    ok = True
    if "acceptance_criteria" not in input_data or len(input_data.get("acceptance_criteria", [])) < 4:
        checks.append("缺少至少 4 个验收标准")
        ok = False
    return make_result(ok, "prd", "story", checks)

def prd(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_prd(input_data)
def story(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_story(input_data)
def acceptance(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_acceptance(input_data)
