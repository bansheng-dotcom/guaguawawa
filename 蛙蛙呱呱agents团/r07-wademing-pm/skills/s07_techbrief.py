# -*- coding: utf-8 -*-
"""S07 技术翻译与代码反推需求。"""
from __future__ import annotations
from typing import Any, Dict
from ._common import make_result

def techbrief(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """技术翻译五模块。"""
    checks = []
    ok = True
    
    brief = input_data.get("brief", {})
    if not brief:
        checks.append("未提供 technical_brief")
        return make_result(False, "techbrief", "techbrief", checks)
        
    for text in str(brief).values():
        if "实现代码" in str(text) or "class " in str(text) or "def " in str(text):
            checks.append("技术翻译越界，包含具体代码实现细节")
            ok = False
            break
            
    return make_result(ok, "techbrief", "techbrief", checks)

def uibrief(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return make_result(True, "techbrief", "uibrief", [])

def codetoprd(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """代码反推需求。"""
    checks = []
    ok = True
    
    if "business_process" not in input_data:
        checks.append("缺少业务流程定义")
        ok = False
        
    if "core_fields" not in input_data:
        checks.append("缺少核心字段业务状态解释")
        ok = False
        
    return make_result(ok, "techbrief", "codetoprd", checks)

def releasegate(input_data: Dict[str, Any]) -> Dict[str, Any]:
    res = make_result(True, "techbrief", "releasegate", [])
    res["decision"] = "go"
    return res
_techbrief = techbrief
_uibrief = uibrief
_codetoprd = codetoprd
_releasegate = releasegate
