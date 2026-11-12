# -*- coding: utf-8 -*-
"""S08 经验检索与决策汇报：decision / demand / experience 三条真实门禁。

决策三层（PM_SPEC.md §6）：产品判断 → 执行规格 → 决策闸门（成功/非目标/停止条件）。
需求卡七字段齐备才允许流转；经验卡五要素齐备才允许入库，禁止「已验证但无来源」。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._common import check, is_blank, load_thresholds, make_result

NAME = "decision"
DESC = "经验检索与决策汇报"
ACTIONS = {"decision": "决策三层门禁", "demand": "需求卡七字段门禁",
           "experience": "经验卡五要素门禁"}

_DEMAND_FIELDS = ("demand_id", "problem", "scope", "non_goals",
                  "success_metric", "acceptance", "review_status")
_REVIEW_OK = ("已复核", "approved", "reviewed", "pass")
_GATE_KEYS = ("success", "non_goals", "stop_condition")


def _validate_decision(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    layers_required = list(load_thresholds().get("decision", {}).get("layers")
                           or ["product_judgment", "execution_spec", "decision_gate"])
    present = []
    for layer in layers_required:
        if is_blank(input_data.get(layer)):
            checks.append(check(False, f"决策缺少 {layer} 层", layer))
        else:
            present.append(layer)
    gate = input_data.get("decision_gate")
    gate = gate if isinstance(gate, dict) else {}
    for key in _GATE_KEYS:
        checks.append(check(not is_blank(gate.get(key)),
                            f"决策闸门缺少 {key}", "decision_gate"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "decision", "decision", checks, layers=present)


def _validate_demand(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    present = []
    for field in _DEMAND_FIELDS:
        value = input_data.get(field)
        if is_blank(value):
            checks.append(check(False, f"需求卡缺少 {field}", field))
        else:
            present.append(field)
    status = str(input_data.get("review_status") or "")
    checks.append(check(any(tok in status for tok in _REVIEW_OK),
                        f"需求卡复核状态不可流转：{status!r}", "review_status"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "decision", "demand", checks,
                       demand_required_fields=present,
                       demand_field_count=len(_DEMAND_FIELDS))


def _validate_experience(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    card_fields = list(load_thresholds().get("experience", {}).get("card_fields")
                       or ["trigger", "scope", "rule", "boundary", "source_credibility"])
    present: List[str] = []
    for field in card_fields:
        if is_blank(input_data.get(field)):
            checks.append(check(False, f"经验卡缺少 {field}", field))
        else:
            present.append(field)
    if input_data.get("verified") is True:
        checks.append(check(not is_blank(input_data.get("source")),
                            "标记为已验证的经验缺来源（source），判为幻觉", "provenance"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "decision", "experience", checks, card_fields=present)


# 历史名称兼容（harness / run_tests 使用 _decision / _demand / _experience）
_decision = _validate_decision
_demand = _validate_demand
_experience = _validate_experience


def decision(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_decision(input_data)


def demand(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_demand(input_data)


def experience(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_experience(input_data)
