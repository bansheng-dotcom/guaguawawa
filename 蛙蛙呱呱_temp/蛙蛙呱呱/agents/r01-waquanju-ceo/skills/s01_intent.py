# -*- coding: utf-8 -*-
"""S01 意图识别与任务分级 (Intent Routing)。"""
from __future__ import annotations

import json
from typing import Any, Dict

from ._common import make_result

NAME = "intent"
DESC = "意图识别与任务分级：brief/clarify/triage"


def _validate_brief(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    ok = True

    if "options" in input_data and len(input_data["options"]) == 1:
        ok = False
    if "success_criteria" not in input_data or not input_data["success_criteria"]:
        if input_data.get("decision_made"):
            checks.append({"ok": False, "msg": "决策先行缺标准", "sev": "CRITICAL"})
            ok = False

    res = make_result(ok, "intent", "brief", [])
    if checks:
        res["checks"] = checks
    return res


def _validate_clarify(input_data: Dict[str, Any]) -> Dict[str, Any]:
    res = make_result(True, "intent", "clarify", [])
    has_evidence = all(
        isinstance(v, dict) and v.get("evidence")
        for k, v in input_data.items()
        if isinstance(v, dict)
    )
    res["light"] = "green" if has_evidence else "red"
    if not input_data:
        res["light"] = "red"
    return res


def _validate_triage(input_data: Dict[str, Any]) -> Dict[str, Any]:
    res = make_result(True, "intent", "triage", [])
    # triage 接受自然语言 intent；从关键词推导跨域与 boardroom 信号。
    intent = str(input_data.get("intent", ""))
    domains = input_data.get("domains", [])
    if not domains:
        domain_keys = {
            "data": ("数据", "分析", "趋势", "订单"),
            "ops": ("排期", "SOP", "流程"),
            "product": ("产品", "需求", "PRD"),
        }
        domains = [
            name
            for name, keys in domain_keys.items()
            if any(k.lower() in intent.lower() for k in keys)
        ]
    if len(domains) >= 2:
        res["boardroom"] = True
    res["domains"] = domains
    res["level"] = input_data.get("level", "strategy")
    return res


brief = _validate_brief
clarify = _validate_clarify
triage = _validate_triage


def add_parser(subparsers) -> None:
    p = subparsers.add_parser(NAME, help=DESC)
    sp = p.add_subparsers(dest="action", required=True)

    p_brief = sp.add_parser("brief")
    p_brief.add_argument("--input", required=True)

    p_clarify = sp.add_parser("clarify")
    p_clarify.add_argument("--input", required=True)

    p_triage = sp.add_parser("triage")
    p_triage.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    """统一技能入口：按 action 读取输入并执行对应意图校验。"""
    with open(args.input, "r", encoding="utf-8-sig") as f:
        input_data = json.load(f)
    fn = {
        "brief": _validate_brief,
        "clarify": _validate_clarify,
        "triage": _validate_triage,
    }.get(args.action)
    if fn is None:
        return make_result(
            False, "intent", str(args.action), [{"ok": False, "msg": "未知 action"}]
        )
    return fn(input_data)


# harness 兼容别名：旧门禁名称仍可直接调用。
_clarify = _validate_clarify
_triage = _validate_triage
