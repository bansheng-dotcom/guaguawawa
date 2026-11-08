# -*- coding: utf-8 -*-
"""s06 宏观与情景推演（scenario）：pestel / premortem 两动作。

- pestel：PESTEL 宏观分析——6 类因子齐全性、证据覆盖率、影响摘要。
- premortem：事前尸检——probability × impact 风险评分、排序与最高风险。
阈值：thresholds.json → scenario.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "scenario"
DESC = "宏观与情景推演：PESTEL、事前尸检"

ACTIONS = {
    "pestel": "PESTEL 宏观分析",
    "premortem": "事前尸息（pre-mortem）失效推演",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# pestel
# --------------------------------------------------------------------------- #
def pestel(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["scenario"]
    categories = th["pestel_categories"]
    impact_scale = th["impact_scale"]

    factors = data.get("factors") or []
    checks: List[Dict[str, Any]] = []

    if not factors:
        checks.append(c.ck(False, "factors 为空，无 PESTEL 可分析", "scenario:pestel", "CRITICAL"))

    # 按 category 分桶
    by_cat: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in categories}
    unknown_cats: List[str] = []
    for f in factors:
        cat = str(f.get("category") or "")
        if cat not in by_cat:
            unknown_cats.append(cat)
            by_cat[cat] = by_cat.get(cat, [])
        by_cat[cat].append(f)

    for uc in unknown_cats:
        checks.append(c.ck(False, f"未知 PESTEL 类别 {uc!r}（白名单：{categories}）", "scenario:category", "HIGH", **{"category": uc}))

    categories_checked = 0
    for cat in categories:
        bucket = by_cat.get(cat) or []
        if not bucket:
            checks.append(c.ck(False, f"PESTEL 类别 {cat!r} 无任何因子", "scenario:category_coverage", "HIGH", **{"category": cat}))
        else:
            categories_checked += 1
            checks.append(c.ck(True, f"PESTEL 类别 {cat!r} 含 {len(bucket)} 个因子", "scenario:category_coverage", **{"category": cat, "count": len(bucket)}))

    # 证据覆盖与影响分级
    with_evidence = 0
    impact_summary: Dict[str, int] = {}
    for f in factors:
        cat = str(f.get("category") or "")
        factor = str(f.get("factor") or "")
        evidence = str(f.get("evidence") or "")
        impact = str(f.get("impact") or "")

        if evidence.strip():
            with_evidence += 1
        else:
            checks.append(c.ck(False, f"factor {factor!r} 无证据（须标来源或标待核实）", "scenario:factor_evidence", "HIGH", **{"factor": factor}))

        if impact not in impact_scale:
            checks.append(c.ck(False, f"factor {factor!r} impact={impact!r} 不在分级白名单", "scenario:factor_impact", "HIGH", **{"factor": factor}))
        else:
            impact_summary[impact] = impact_summary.get(impact, 0) + 1

    total_factors = len(factors)
    evidence_coverage = (with_evidence / total_factors) if total_factors > 0 else 0.0

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   categories_checked=categories_checked,
                   total_factors=total_factors,
                   evidence_coverage=round(evidence_coverage, 4),
                   impact_summary=impact_summary,
                   verdict=verdict,
                   next="PESTEL 六类齐全、证据全覆盖" if ok else "补齐缺失类别与无证据因子后重新 pestel",
                   )
    return out


# --------------------------------------------------------------------------- #
# premortem
# --------------------------------------------------------------------------- #
def premortem(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["scenario"]
    prob_scale = th["probability_scale"]
    impact_scale = th["impact_scale"]
    risk_thresholds = th["risk_thresholds"]

    scenarios = data.get("scenarios") or []
    checks: List[Dict[str, Any]] = []

    if not scenarios:
        checks.append(c.ck(False, "scenarios 为空，无失效推演可做", "scenario:premortem", "CRITICAL"))

    risk_ranking: List[Dict[str, Any]] = []
    for sc in scenarios:
        name = str(sc.get("name") or "")
        desc = str(sc.get("desc") or "")
        probability = str(sc.get("probability") or "")
        impact = str(sc.get("impact") or "")
        declared_level = str(sc.get("risk_level") or "")
        mitigation = str(sc.get("mitigation") or "")
        early_warning = str(sc.get("early_warning") or "")

        if not desc.strip():
            checks.append(c.ck(False, f"scenario {name!r} 缺 desc（失效叙事）", "scenario:scenario_desc", "HIGH", **{"scenario": name}))
        if probability not in prob_scale:
            checks.append(c.ck(False, f"scenario {name!r} probability={probability!r} 不在分级白名单", "scenario:scenario_probability", "HIGH", **{"scenario": name}))
        if impact not in impact_scale:
            checks.append(c.ck(False, f"scenario {name!r} impact={impact!r} 不在分级白名单", "scenario:scenario_impact", "HIGH", **{"scenario": name}))

        if probability in prob_scale and impact in impact_scale:
            risk_score = prob_scale[probability] * impact_scale[impact]
            if risk_score < risk_thresholds["low"]:
                risk_tier = "low"
            elif risk_score < risk_thresholds["medium"]:
                risk_tier = "medium"
            elif risk_score < risk_thresholds["high"]:
                risk_tier = "high"
            else:
                risk_tier = "critical"

            if declared_level and declared_level != risk_tier:
                checks.append(c.ck(False, f"scenario {name!r} 声明 risk_level={declared_level!r} 与计算 {risk_tier!r}（score={risk_score}）不一致", "scenario:risk_level_consistency", "HIGH", **{"scenario": name, "declared": declared_level, "computed": risk_tier}))

            if risk_tier in ("high", "critical") and not mitigation.strip():
                checks.append(c.ck(False, f"scenario {name!r} 高风险却无缓解措施（mitigation）", "scenario:mitigation_required", "HIGH", **{"scenario": name}))
            if risk_tier in ("high", "critical") and not early_warning.strip():
                checks.append(c.ck(False, f"scenario {name!r} 高风险却无预警信号（early_warning）", "scenario:early_warning_required", "HIGH", **{"scenario": name}))

            risk_ranking.append({"scenario": name, "risk_score": risk_score,
                                 "risk_tier": risk_tier})
            checks.append(c.ck(True, f"scenario {name!r} risk_score={risk_score} tier={risk_tier}", "scenario:risk_score", **{"scenario": name, "risk_score": risk_score}))

    # 排序：risk_score 降序，同分按名称
    risk_ranking = sorted(risk_ranking, key=lambda r: (-r["risk_score"], r["scenario"]))
    highest_risk = risk_ranking[0] if risk_ranking else None

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   scenario_count=len(scenarios),
                   risk_ranking=risk_ranking,
                   highest_risk=highest_risk,
                   verdict=verdict,
                   next="失效推演完成，最高风险已定位" if ok else "修复分级/缓解/预警字段后重新 premortem",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "pestel":
        result = pestel(data)
    elif args.action == "premortem":
        result = premortem(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result
