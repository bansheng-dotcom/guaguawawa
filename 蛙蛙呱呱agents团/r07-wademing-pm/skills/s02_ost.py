# -*- coding: utf-8 -*-
"""S02 机会树与用户研究：ost / poc / assumption / research 四条真实门禁。

对齐 Teresa Torres 的 Opportunity Solution Tree 与 Ulwick 的 ODI：
- 机会树必须「结果 → 机会 → 解决方案 → 实验」四层可追溯；
- POC 打分是真实乘算（可行性 × 影响 × 市场匹配），低于阈值一律不推荐；
- 假设按 Impact × Confidence 四象限分流，禁止「全靠拍脑袋」。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._common import check, is_blank, load_thresholds, make_result

NAME = "ost"
DESC = "机会树与用户研究"
ACTIONS = {"ost": "校验机会解决方案树", "poc": "POC 方案打分与推荐",
           "assumption": "承重假设四象限分流", "research": "用户研究记录门禁"}

_NOTE_REQUIRED = ("participant", "biggest_pain", "desired_outcome")


def _ost_rules() -> Dict[str, Any]:
    return load_thresholds().get("ost", {})


def _validate_ost(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """OST 四层门禁：期望结果 → 机会 → 解决方案 → 可验证实验。"""
    rules = _ost_rules()
    opp_min = int(rules.get("opportunities_min", 3))
    opp_max = int(rules.get("opportunities_max", 7))
    sol_min = int(rules.get("solutions_min", 3))
    exp_min = int(rules.get("experiments_min", 1))

    checks = []
    desired = input_data.get("desired_outcome") or input_data.get("outcome")
    checks.append(check(not is_blank(desired),
                        "机会树缺少期望结果（desired_outcome）" if is_blank(desired)
                        else "机会树已锚定期望结果", "outcome"))

    opportunities = input_data.get("opportunities")
    opportunities = opportunities if isinstance(opportunities, list) else []
    checks.append(check(opp_min <= len(opportunities) <= opp_max,
                        f"机会点数量 {len(opportunities)} 不在 {opp_min}~{opp_max} 区间",
                        "opportunity"))

    experiments_total = 0
    selected_count = 0
    for idx, opp in enumerate(opportunities):
        opp = opp if isinstance(opp, dict) else {}
        solutions = opp.get("solutions") if isinstance(opp.get("solutions"), list) else []
        if opp.get("selected") is True:
            selected_count += 1
            checks.append(check(len(solutions) >= sol_min,
                                f"选中的机会 {idx} 方案数 {len(solutions)} < {sol_min}",
                                "solution"))
        for s_idx, sol in enumerate(solutions):
            sol = sol if isinstance(sol, dict) else {}
            experiments = sol.get("experiments")
            experiments = experiments if isinstance(experiments, list) else []
            experiments_total += len(experiments)
            for e_idx, exp in enumerate(experiments):
                exp = exp if isinstance(exp, dict) else {}
                checks.append(check(not is_blank(exp.get("hypothesis"))
                                    and not is_blank(exp.get("method")),
                                    f"实验 {idx}.{s_idx}.{e_idx} 缺 hypothesis/method",
                                    "experiment"))
    checks.append(check(experiments_total >= exp_min,
                        f"整棵机会树没有可验证实验（需 >= {exp_min}）", "experiment"))

    focus = [f for f in (input_data.get("focus") or []) if isinstance(f, str) and f.strip()]
    checks.append(check(0 < len(focus) <= int(rules.get("top_focus", 3)),
                        f"聚焦机会数 {len(focus)} 不在 1~{int(rules.get('top_focus', 3))}",
                        "focus"))

    ok = all(c["ok"] for c in checks)
    return make_result(ok, "ost", "ost", checks,
                       opportunity_count=len(opportunities),
                       selected_count=selected_count,
                       experiment_count=experiments_total,
                       focus_count=len(focus))


def _score_poc(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """POC 打分：score = feasibility × impact × market_fit（1~5 分制），阈值推荐。"""
    rules = _ost_rules()
    scale_min = float(rules.get("poc_scale_min", 1))
    scale_max = float(rules.get("poc_scale_max", 5))
    threshold = float(rules.get("poc_recommend_min", 12))

    checks = []
    scored: List[Dict[str, Any]] = []
    recommended: List[str] = []
    solutions = input_data.get("solutions")
    solutions = solutions if isinstance(solutions, list) else []
    checks.append(check(bool(solutions), "未提供 POC 候选方案", "solution"))
    for idx, sol in enumerate(solutions):
        sol = sol if isinstance(sol, dict) else {}
        name = str(sol.get("name") or f"solution_{idx}")
        try:
            f = float(sol.get("feasibility", 0) or 0)
            i = float(sol.get("impact", 0) or 0)
            m = float(sol.get("market_fit", 0) or 0)
        except (TypeError, ValueError):
            checks.append(check(False, f"方案 {name} 打分为非数值", "score"))
            continue
        for label, value in (("feasibility", f), ("impact", i), ("market_fit", m)):
            checks.append(check(scale_min <= value <= scale_max,
                                f"方案 {name} 的 {label}={value} 超出 {scale_min:g}~{scale_max:g} 分制",
                                "score"))
        total = round(f * i * m, 4)
        scored.append({"name": name, "score": total})
        if total >= threshold:
            recommended.append(name)
    scored.sort(key=lambda x: x["score"], reverse=True)
    checks.append(check(bool(recommended),
                        f"没有方案达到推荐阈值 {threshold:g} 分", "recommend"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "ost", "poc", checks,
                       recommended_poc=recommended,
                       solutions=scored,
                       recommend_threshold=threshold)


def _prioritize_assumptions(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """承重假设四象限：Impact × Confidence 决定先实验 / 先验证 / 观察 / 放弃。"""
    checks = []
    quadrants: Dict[str, List[str]] = {"experiment": [], "validate": [],
                                       "monitor": [], "park": []}
    rows: List[Dict[str, Any]] = []
    assumptions = input_data.get("assumptions")
    assumptions = assumptions if isinstance(assumptions, list) else []
    checks.append(check(bool(assumptions), "未提供承重假设，无法排优先级", "assumption"))
    for idx, a in enumerate(assumptions):
        a = a if isinstance(a, dict) else {}
        name = str(a.get("name") or f"assumption_{idx}")
        try:
            impact = float(a.get("impact", 0) or 0)
            confidence = float(a.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            checks.append(check(False, f"假设 {name} 的 impact/confidence 非数值",
                                "assumption"))
            continue
        # impact 兼容 0~1 与 0~10 两种量纲
        impact_norm = impact / 10.0 if impact > 1.0 else impact
        if impact_norm >= 0.7 and confidence <= 0.3:
            quadrant = "experiment"
        elif impact_norm >= 0.7 and confidence > 0.3:
            quadrant = "validate"
        elif impact_norm < 0.7 and confidence <= 0.3:
            quadrant = "monitor"
        else:
            quadrant = "park"
        quadrants[quadrant].append(name)
        rows.append({"name": name, "impact": impact, "confidence": confidence,
                     "quadrant": quadrant})
    checks.append(check(bool(quadrants["experiment"]),
                        "没有任何假设进入 experiment 象限（无高影响低置信假设）",
                        "quadrant"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "ost", "assumption", checks,
                       quadrants=quadrants, assumptions=rows)


def _validate_research(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """用户研究记录门禁：访谈笔记必备字段 + 需求条目来源/频次。"""
    checks = []
    notes = input_data.get("interview_notes")
    notes = notes if isinstance(notes, dict) else {}
    checks.append(check(bool(notes), "缺少访谈笔记（interview_notes）", "note"))
    for field in _NOTE_REQUIRED:
        checks.append(check(not is_blank(notes.get(field)),
                            f"访谈笔记缺少 {field}" if is_blank(notes.get(field))
                            else f"访谈笔记已记录 {field}", "note"))
    fields = sorted(k for k, v in notes.items() if not is_blank(v))

    requests = input_data.get("feature_requests")
    requests = requests if isinstance(requests, list) else []
    checks.append(check(bool(requests), "缺少需求条目（feature_requests）", "requirement"))
    for idx, req in enumerate(requests):
        req = req if isinstance(req, dict) else {}
        checks.append(check(not is_blank(req.get("source")) and not is_blank(req.get("frequency")),
                            f"需求条目 {idx} 缺 source/frequency", "requirement"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "ost", "research", checks,
                       feature_request_count=len(requests),
                       note_fields=fields)


def ost(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_ost(input_data)


def poc(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _score_poc(input_data)


def assumption(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _prioritize_assumptions(input_data)


def research(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _validate_research(input_data)
