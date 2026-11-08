# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict
from ._common import make_result

NAME = "discover"
DESC = "产品发现、JTBD 与用户访谈验证"
ACTIONS = {"jobstory": "校验 Job story", "discover": "校验发现计划",
           "interview": "校验访谈脚本"}

def _validate_jobstory(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    ok = True
    if "outcome" not in input_data:
        checks.append("Missing outcome")
        ok = False
    return make_result(ok, "discover", "jobstory", checks)

def _validate_discover(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    ok = True
    if "assumptions" not in input_data or not input_data["assumptions"]:
        checks.append("Missing assumptions")
        ok = False
    if "success_metrics" not in input_data or not input_data["success_metrics"]:
        checks.append("Missing success metrics")
        ok = False
    return make_result(ok, "discover", "discover", checks)

def _validate_interview_script(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    ok = True
    q = str(input_data)
    if "觉得" in q or "好不好" in q or "将来" in q:
        checks.append("Violation of Mom Test")
        ok = False
    return make_result(ok, "discover", "interview", checks)

def discover(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_discover(input_data)

def jobstory(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_jobstory(input_data)
    
def interview(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_interview_script(input_data)