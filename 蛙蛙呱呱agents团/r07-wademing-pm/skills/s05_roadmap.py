# -*- coding: utf-8 -*-
"""S05 路线图与发布：roadmap / releasenotes / premortem 三条真实门禁。

- roadmap：结果导向（segment → outcome → business_impact），禁止「功能交付清单」；
- releasenotes：五类变更（New/Improvements/Bug Fixes/Breaking Changes/Deprecations）必须齐备；
- premortem：老虎（失败原因）+ 行动计划（风险/缓解/责任人/截止）双向可追溯。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._common import check, is_blank, load_thresholds, make_result

NAME = "roadmap"
DESC = "路线图与发布"
ACTIONS = {"roadmap": "结果导向路线图门禁", "releasenotes": "发布说明五分类门禁",
           "premortem": "事前验尸门禁"}

_FEATURE_WORDS = ("功能", "页面", "接口", "需求")  # 仅作为提示维度，不单独判失败


def _validate_roadmap(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    items = input_data.get("items")
    items = items if isinstance(items, list) else []
    checks.append(check(bool(items), "路线图为空（items）", "input"))
    for idx, item in enumerate(items):
        item = item if isinstance(item, dict) else {}
        for field, label in (("segment", "人群"), ("outcome", "结果"),
                             ("business_impact", "业务影响")):
            checks.append(check(not is_blank(item.get(field)),
                                f"路线图第 {idx} 条缺少{label}（{field}）", field))
        outcome = str(item.get("outcome") or "")
        checks.append(check(len(outcome.strip()) >= 4,
                            f"路线图第 {idx} 条结果描述过短，无法验收", "outcome"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "roadmap", "roadmap", checks, item_count=len(items))


def _validate_releasenotes(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    categories_required = list(load_thresholds().get("roadmap", {}).get(
        "release_categories") or [])
    checks.append(check(not is_blank(input_data.get("title")), "发布说明缺少版本标题",
                        "title"))
    sections = input_data.get("sections")
    sections = sections if isinstance(sections, dict) else {}
    for name in categories_required:
        entries = sections.get(name)
        entries = entries if isinstance(entries, list) else []
        checks.append(check(bool(entries), f"发布说明缺少 {name} 分类内容", "category"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "roadmap", "releasenotes", checks,
                       categories=categories_required)


def _validate_premortem(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    tigers = input_data.get("tigers")
    tigers = tigers if isinstance(tigers, list) else []
    checks.append(check(bool(tigers), "事前验尸缺少失败原因（tigers）", "tiger"))
    for idx, tiger in enumerate(tigers):
        checks.append(check(not is_blank(tiger), f"失败原因 {idx} 为空", "tiger"))

    plans = input_data.get("action_plans")
    plans = plans if isinstance(plans, list) else []
    checks.append(check(bool(plans), "事前验尸缺少行动计划（action_plans）", "action"))
    for idx, plan in enumerate(plans):
        plan = plan if isinstance(plan, dict) else {}
        for field, label in (("risk", "风险"), ("mitigation", "缓解措施"),
                             ("owner", "责任人"), ("due_date", "截止时间")):
            checks.append(check(not is_blank(plan.get(field)),
                                f"行动计划 {idx} 缺少{label}（{field}）", "action"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "roadmap", "premortem", checks,
                       tiger_count=len(tigers), action_count=len(plans))


# 历史名称兼容（run_tests 使用 _roadmap / _releasenotes / _premortem）
_roadmap = _validate_roadmap
_releasenotes = _validate_releasenotes
_premortem = _validate_premortem


def roadmap(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_roadmap(input_data)


def releasenotes(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_releasenotes(input_data)


def premortem(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_premortem(input_data)
