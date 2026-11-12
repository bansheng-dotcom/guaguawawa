# -*- coding: utf-8 -*-
"""R07 技能契约（T6）：每技能机器可读的「输入 + 输出」JSON Schema。

把「产品经理技能能吃什么、吐什么」升级为可校验的 JSON Schema。
`agent.py contract validate` 用它做确定性校验：技能实际输出不符契约即 FAIL。

schema 是 JSON Schema 的子集（对齐 skills._common.validate_schema）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

_s = {"type": "string"}
_b = {"type": "boolean"}
_n = {"type": "number"}
_i = {"type": "integer"}
_arr = {"type": "array"}
_obj = {"type": "object"}

# 输入统一宽松对象（每个动作 --input 一个 JSON 对象，语义门禁由 harness/技能承担）。
_IN = {"type": "object"}


def _o(required: List[str], props: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "object", "required": required, "properties": props}


def _ok(required: List[str], **props: Any) -> Dict[str, Any]:
    base = {"ok": _b, "checks": _arr}
    base.update(props)
    return _o(["ok", "checks"] + required, base)


CONTRACTS: Dict[str, Any] = {
"rice": {
    "desc": "RICE 排序：score/敏感性",
    "input": {"args": {"input": _s}},
    "output": {"rice": _ok(["rice"], rice=_obj)},
},
"discover": {
    "desc": "产品发现与JTBD：jobstory/discover/interview",
    "input": {"jobstory": _IN, "discover": _IN, "interview": _IN},
    "output": {
        "jobstory": _ok([], mode=_s),
        "discover": _ok(["assumption_count"], risk_types=_arr,
                        assumption_count=_i, validation_count=_i),
        "interview": _ok([], sections_band=_obj),
    },
},
"ost": {
    "desc": "机会树与用户研究：ost/poc/assumption/research",
    "input": {"ost": _IN, "poc": _IN, "assumption": _IN, "research": _IN},
    "output": {
        "ost": _ok(["opportunity_count"], opportunity_count=_i, focus_count=_i),
        "poc": _ok(["recommended_poc"], recommended_poc=_arr, solutions=_arr,
                   recommend_threshold=_n),
        "assumption": _ok(["quadrants"], quadrants=_obj, assumptions=_arr),
        "research": _ok(["feature_request_count"], note_fields=_arr,
                        feature_request_count=_i),
    },
},
"prd": {
    "desc": "用户故事与PRD：prd/story/acceptance",
    "input": {"prd": _IN, "story": _IN, "acceptance": _IN},
    "output": {
        "prd": _ok(["passed_gates"], gates=_arr, gate_ok=_obj, passed_gates=_i),
        "story": _ok(["ac_count"], kind=_s, ac_count=_i, ac_band=_arr),
        "acceptance": _ok(["ac_count"], ac_count=_i),
    },
},
"priority": {
    "desc": "优先级与Backlog：opportunity/ice/rice/backlog",
    "input": {"opportunity": _IN, "ice": _IN, "rice": _IN, "backlog": _IN},
    "output": {
        "opportunity": _ok(["ranked"], formula=_s, ranked=_arr),
        "ice": _ok(["ranked"], formula=_s, ranked=_arr),
        "rice": _ok(["ranked"], formula=_s, ranked=_arr),
        "backlog": _ok(["ordered"], item_count=_i, ordered=_arr),
    },
},
"roadmap": {
    "desc": "路线图与发布：roadmap/releasenotes/premortem",
    "input": {"roadmap": _IN, "releasenotes": _IN, "premortem": _IN},
    "output": {
        "roadmap": _ok(["item_count"], item_count=_i),
        "releasenotes": _ok(["categories"], categories=_arr),
        "premortem": _ok(["tiger_count"], tiger_count=_i, action_count=_i),
    },
},
"metrics": {
    "desc": "产品愿景与指标：northstar/metrics/okr/vision/canvas",
    "input": {"northstar": _IN, "metrics": _IN, "okr": _IN, "vision": _IN,
              "canvas": _IN},
    "output": {
        "northstar": _ok(["input_metric_count"], nsm_criteria=_arr,
                         input_metric_count=_i),
        "metrics": _ok(["layers"], layers=_obj, metric_count=_i),
        "okr": _ok(["okr_sets"], okr_sets=_i, confidence=_i),
        "vision": _ok(["variant_count"], variant_count=_i),
        "canvas": _ok(["canvas_sections"], canvas_sections=_arr),
    },
},
"techbrief": {
    "desc": "技术翻译与代码反推需求：techbrief/uibrief/codetoprd/releasegate",
    "input": {"techbrief": _IN, "uibrief": _IN, "codetoprd": _IN, "releasegate": _IN},
    "output": {
        "techbrief": _ok(["modules"], modules=_arr),
        "uibrief": _ok(["ui_modules"], ui_modules=_arr, states_required=_arr),
        "codetoprd": _ok(["page_count"], page_count=_i, api_count=_i),
        "releasegate": _ok(["decision"], blocker_count=_i, check_count=_i, decision=_s),
    },
},
"decision": {
    "desc": "经验检索与决策汇报：decision/demand/experience",
    "input": {"decision": _IN, "demand": _IN, "experience": _IN},
    "output": {
        "decision": _ok(["layers"], layers=_arr),
        "demand": _ok(["demand_required_fields"], demand_required_fields=_arr),
        "experience": _ok(["card_fields"], card_fields=_arr),
    },
},
"prdguard": {
    "desc": "PRD 结构门禁：check/render",
    "input": {"check": _IN, "render": _IN},
    "output": {
        "check": _ok(["p0_count"], p0_count=_i),
        "render": _ok(["out"], out=_s),
    },
},
}


def skill_names() -> List[str]:
    return list(CONTRACTS)


def get(skill: str) -> Dict[str, Any]:
    return CONTRACTS.get(skill, {})


def actions(skill: str) -> List[str]:
    return list(get(skill).get("output", {}).keys())


def input_schema(skill: str, action: str) -> Dict[str, Any]:
    """输入契约：每个动作的输入是一个 --input JSON 对象（宽松 object）。"""
    return get(skill).get("input", {}).get(action, {"type": "object"})


def output_schema(skill: str, action: str) -> Dict[str, Any]:
    return get(skill).get("output", {}).get(action)


def validate_input(skill: str, action: str, data: Any) -> Dict[str, Any]:
    """输入侧契约校验（T6 双向校验的输入端）。输入 schema 逐动作登记，缺登记即 fail。"""
    entry = get(skill)
    if not entry or action not in entry.get("input", {}):
        return {"ok": False, "skill": skill, "action": action,
                "errors": [f"契约未登记输入动作 {skill}/{action}"]}
    errs = c.validate_schema(data, input_schema(skill, action))
    return {"ok": not errs, "skill": skill, "action": action, "errors": errs,
            "schema": input_schema(skill, action)}


def validate_output(skill: str, action: str, result: Any) -> Dict[str, Any]:
    schema = output_schema(skill, action)
    if schema is None:
        return {"ok": False, "skill": skill, "action": action,
                "errors": [f"契约未定义动作 {action}（可用 {actions(skill)}）"]}
    errs = c.validate_schema(result, schema)
    return {"ok": not errs, "skill": skill, "action": action, "errors": errs,
            "schema": schema}