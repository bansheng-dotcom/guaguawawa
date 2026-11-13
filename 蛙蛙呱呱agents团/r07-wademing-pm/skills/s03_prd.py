# -*- coding: utf-8 -*-
"""S03 用户故事与 PRD：prd / story / acceptance 三条真实门禁。

PRD 八门禁（PM_SPEC.md §4 SSOT）：
problem / user / value / scope / metric / acceptance / risk / read。
八门禁只校验「结构与口径可定义」，不做方案优劣判断（那是 R04 的职责）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._common import check, is_blank, load_thresholds, make_result

NAME = "prd"
DESC = "用户故事与 PRD"
ACTIONS = {"prd": "PRD 八门禁校验", "story": "用户故事与验收条目门禁",
           "acceptance": "验收准则 Given/When/Then 门禁"}

_GATE_ORDER = ("problem", "user", "value", "scope",
               "metric", "acceptance", "risk", "read")

_HEDGE_WORDS = ("待定", "待补充", "视情况", "灵活处理", "TODO", "TBD")


def _gate_spec() -> Dict[str, Any]:
    return load_thresholds().get("prd", {})


def _pick(data: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in data and not is_blank(data.get(k)):
            return data.get(k)
    return None


def _gates(input_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """逐门禁产出结构化判据（每个门禁至少一条判据）。"""
    out: Dict[str, List[Dict[str, Any]]] = {}

    problem = _pick(input_data, "problem_statement", "problem")
    text = str(problem or "")
    out["problem"] = [
        check(not is_blank(problem), "缺少问题与场景（problem_statement）", "problem"),
        check(len(text.strip()) >= 10, f"问题描述过短（{len(text.strip())} < 10 字符）",
              "problem"),
        check(not any(w in text for w in _HEDGE_WORDS), "问题描述含模糊措辞", "problem"),
    ]

    users = _pick(input_data, "users", "target_users") or []
    users = users if isinstance(users, list) else []
    out["user"] = [
        check(bool(users), "缺少目标用户（users）", "user"),
        check(all(isinstance(u, dict) and not is_blank(u.get("segment")) for u in users),
              "用户缺少 segment 分层", "user"),
        check(all(isinstance(u, dict) and not is_blank(u.get("scenario")) for u in users),
              "用户缺少 scenario 使用场景", "user"),
    ]

    value = _pick(input_data, "value_proposition", "value") or {}
    value = value if isinstance(value, dict) else {}
    out["value"] = [
        check(all(not is_blank(value.get(k)) for k in ("before", "how", "after")),
              "价值主张缺 before/how/after 三段对比", "value"),
    ]

    scope = _pick(input_data, "scope", "mvp_scope") or {}
    scope = scope if isinstance(scope, dict) else {}
    p0 = scope.get("p0") or []
    non_goals = scope.get("non_goals") or []
    out["scope"] = [
        check(bool(p0), "P0 范围为空（scope.p0）", "scope"),
        check(bool(non_goals), "缺少不做清单（scope.non_goals）", "scope"),
    ]

    metrics = _pick(input_data, "metrics", "success_metrics") or {}
    metrics = metrics if isinstance(metrics, dict) else {}
    out["metric"] = [
        check(not is_blank(metrics.get("north_star")), "缺少北极星指标（metrics.north_star）",
              "metric"),
        check(not is_blank(metrics.get("target")) and not is_blank(metrics.get("baseline")),
              "缺少基线与目标口径（baseline / target）", "metric"),
        check(not is_blank(metrics.get("guardrail")), "缺少护栏指标（metrics.guardrail）",
              "metric"),
    ]

    ac = _pick(input_data, "acceptance_criteria", "acceptance") or []
    ac = ac if isinstance(ac, list) else []
    ac_ok = bool(ac) and all(
        isinstance(a, dict) and all(not is_blank(a.get(k)) for k in ("given", "when", "then"))
        for a in ac)
    out["acceptance"] = [
        check(bool(ac), "缺少验收标准（acceptance_criteria）", "acceptance"),
        check(ac_ok, "验收标准未按 Given/When/Then 结构化", "acceptance"),
    ]

    risk_min = int(_gate_spec().get("risk_hypotheses_min", 3))
    risks = _pick(input_data, "risks", "assumptions") or []
    risks = risks if isinstance(risks, list) else []
    out["risk"] = [
        check(len(risks) >= risk_min,
              f"承重假设 {len(risks)} 条 < {risk_min} 条硬底线", "risk"),
        check(all(isinstance(r, dict) and not is_blank(r.get("hypothesis")) for r in risks),
              "假设缺少 hypothesis", "risk"),
        check(all(isinstance(r, dict) and not is_blank(r.get("validation")) for r in risks),
              "假设缺少 validation 验证方式", "risk"),
    ]

    summary = _pick(input_data, "executive_summary", "read")
    out["read"] = [
        check(not is_blank(summary), "缺少结论摘要（executive_summary）", "read"),
        check(len(str(summary or "").strip()) >= 10, "结论摘要过短，不具可读性", "read"),
    ]
    return out


def _validate_prd(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """PRD 八门禁：任一 BLOCKER 未过即整体 FAIL（不用加权平均稀释红线）。"""
    input_data = input_data if isinstance(input_data, dict) else {}
    gates = _gates(input_data)
    checks: List[Dict[str, Any]] = []
    gate_ok: Dict[str, bool] = {}
    for gate in _GATE_ORDER:
        items = gates.get(gate, [])
        gate_ok[gate] = bool(items) and all(c["ok"] for c in items)
        checks.extend(items)
    passed = sum(1 for g in _GATE_ORDER if gate_ok[g])
    checks.append(check(passed == len(_GATE_ORDER),
                        f"PRD 八门禁通过 {passed}/{len(_GATE_ORDER)}，未达全通过",
                        "summary"))
    ok = passed == len(_GATE_ORDER)
    return make_result(ok, "prd", "prd", checks,
                       gates=list(_GATE_ORDER), gate_ok=gate_ok,
                       passed_gates=passed)


def _validate_story(input_data: Dict[str, Any], kind: str = "user") -> Dict[str, Any]:
    """用户故事门禁：As a / I want / so that 三段 + 验收条目数区间。"""
    spec = _gate_spec()
    if kind == "job":
        ac_min, ac_max = int(spec.get("jobstory_ac_min", 6)), int(spec.get("jobstory_ac_max", 8))
    else:
        ac_min, ac_max = int(spec.get("story_ac_min", 4)), int(spec.get("story_ac_max", 6))

    checks = []
    story = str(input_data.get("story") or "")
    low = story.lower()
    checks.append(check(all(t in low for t in ("as a", "i want", "so that")),
                        "用户故事未按 As a / I want / so that 三段式书写", "story"))
    items = input_data.get("acceptance_criteria")
    items = items if isinstance(items, list) else []
    n = len(items)
    checks.append(check(ac_min <= n <= ac_max,
                        f"验收条目 {n} 条不在 {ac_min}~{ac_max} 区间", "acceptance"))
    checks.append(check(all(not is_blank(a) for a in items),
                        "存在空白验收条目", "acceptance"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "prd", "story", checks,
                       ac_count=n, kind=kind, ac_band=[ac_min, ac_max])


def _validate_acceptance(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """验收准则门禁：支持 {given,when,then} 结构体与 Gherkin 文本两种载体。"""
    checks = []
    items = input_data.get("acceptance_criteria")
    if items is None:
        items = input_data.get("criteria")
    items = items if isinstance(items, list) else []
    checks.append(check(bool(items), "未提供验收标准", "acceptance"))
    bad = 0
    for idx, ac in enumerate(items):
        if isinstance(ac, dict):
            ok_this = all(not is_blank(ac.get(k)) for k in ("given", "when", "then"))
        else:
            low = str(ac).lower()
            ok_this = all(t in low for t in ("given", "when", "then"))
        if not ok_this:
            bad += 1
            checks.append(check(False, f"验收标准 {idx} 缺 Given/When/Then 要素",
                                "acceptance"))
    checks.append(check(bad == 0 and bool(items), "验收标准未全部满足 Gherkin 语法",
                        "acceptance"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "prd", "acceptance", checks, ac_count=len(items))


def prd(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_prd(input_data)


def story(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_story(input_data, input_data.get("kind", "user"))


def acceptance(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_acceptance(input_data)
