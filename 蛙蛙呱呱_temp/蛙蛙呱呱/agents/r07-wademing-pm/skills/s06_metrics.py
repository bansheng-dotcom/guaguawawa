# -*- coding: utf-8 -*-
"""S06 愿景与指标。"""
from __future__ import annotations
from typing import Any, Dict
from ._common import make_result

def northstar(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """北极星指标校验。"""
    checks = []
    ok = True
    
    metric = input_data.get("north_star", "")
    if "注册量" in metric or "下载量" in metric:
        checks.append(f"北极星指标不能是纯虚荣指标: {metric}")
        ok = False
        
    return make_result(ok, "metrics", "northstar", checks)

def okr(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """OKR 3x3 校验。"""
    checks = []
    ok = True
    
    objectives = input_data.get("objectives", [])
    for i, obj in enumerate(objectives):
        krs = obj.get("key_results", [])
        if len(krs) != 3:
            checks.append(f"Objective {i} 必须包含正好 3 个 KR，实际 {len(krs)} 个")
            ok = False
            
        for j, kr in enumerate(krs):
            text = kr.get("text", "")
            if "完成" in text and "开发" in text:
                checks.append(f"KR {j} 是任务不是可衡量结果: {text}")
                ok = False
                
    return make_result(ok, "metrics", "okr", checks)
    
def metrics(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return make_result(True, "metrics", "metrics", [])
    
def vision(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return make_result(True, "metrics", "vision", [])

def canvas(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return make_result(True, "metrics", "canvas", [])
_northstar = northstar
_okr = okr
_metrics = metrics
