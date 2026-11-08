# -*- coding: utf-8 -*-
"""s03 公司与竞品情报（competitor）：matrix / battlecard 两动作。

- matrix：竞品特征矩阵——competitors × features 对照与缺口分析。
- battlecard：竞品 Battlecard——威胁等级与定位重叠度。
阈值：thresholds.json → competitor.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "competitor"
DESC = "公司与竞品情报：矩阵、Battlecard"

ACTIONS = {
    "matrix": "竞品特征矩阵",
    "battlecard": "竞品Battlecard",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# matrix
# --------------------------------------------------------------------------- #
def matrix(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["competitor"]
    value_types = th["matrix_value_types"]

    competitors = data.get("competitors") or []
    features = data.get("features") or []
    our_product = data.get("our_product") or {}
    checks: List[Dict[str, Any]] = []

    if not competitors:
        checks.append(c.ck(False, "competitors 为空，无矩阵可构建", "competitor:matrix", "CRITICAL"))
    if not features:
        checks.append(c.ck(False, "features 为空，无特征可对照", "competitor:matrix", "CRITICAL"))

    all_have_features = True
    all_values_valid = True

    for comp in competitors:
        name = str(comp.get("name") or "")
        comp_features = comp.get("features") or {}
        for feat in features:
            if feat not in comp_features:
                all_have_features = False
                checks.append(c.ck(False, f"competitor {name!r} 缺少 feature {feat!r}", "competitor:missing_feature", "HIGH", **{"competitor": name, "feature": feat}))
            else:
                val = str(comp_features[feat]).lower().strip()
                if val not in value_types:
                    all_values_valid = False
                    checks.append(c.ck(False, f"competitor {name!r} feature {feat!r} value={val!r} 不在白名单", "competitor:value_type", "HIGH", **{"competitor": name, "feature": feat, "value": val}))

    if all_have_features and competitors and features:
        checks.append(c.ck(True, f"所有 {len(competitors)} 个竞品均含全部 {len(features)} 个特征", "competitor:feature_coverage"))
    if all_values_valid and competitors and features:
        checks.append(c.ck(True, "所有矩阵取值均在白名单内", "competitor:value_type"))

    # gaps：our_product 中为 no 或 unknown 的特征
    our_features = our_product.get("features") or {}
    gaps: List[str] = []
    for feat in features:
        val = str(our_features.get(feat, "unknown")).lower().strip()
        if val in ("no", "unknown"):
            gaps.append(feat)

    our_covered = len(features) - len(gaps)
    our_coverage = (our_covered / len(features)) if features else 0.0

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   competitor_count=len(competitors),
                   feature_count=len(features),
                   gaps=gaps,
                   our_coverage=round(our_coverage, 4),
                   verdict=verdict,
                   next="竞品矩阵完整" if ok else "补齐缺失特征与无效取值后重新 matrix",
                   )
    return out


# --------------------------------------------------------------------------- #
# battlecard
# --------------------------------------------------------------------------- #
def battlecard(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["competitor"]
    required_sections = th["battlecard_sections"]
    threat_levels = th["threat_levels"]

    competitor = data.get("competitor") or {}
    our_positioning = str(data.get("our_positioning") or "")
    key_differentiators = data.get("key_differentiators") or []
    checks: List[Dict[str, Any]] = []

    all_sections_ok = True
    for sec in required_sections:
        val = competitor.get(sec)
        if val is None or (isinstance(val, (str, list)) and len(val) == 0):
            all_sections_ok = False
            checks.append(c.ck(False, f"battlecard 缺少或为空 section: {sec!r}", "competitor:battlecard_section", "HIGH", **{"section": sec}))
        else:
            checks.append(c.ck(True, f"battlecard section {sec!r} 就绪", "competitor:battlecard_section", **{"section": sec}))

    if not competitor:
        checks.append(c.ck(False, "competitor 为空，无 Battlecard 可生成", "competitor:battlecard", "CRITICAL"))

    # threat_level：基于 strengths vs weaknesses 比率
    strengths = competitor.get("strengths") or []
    weaknesses = competitor.get("weaknesses") or []
    strengths_count = len(strengths) if isinstance(strengths, list) else 0
    weaknesses_count = len(weaknesses) if isinstance(weaknesses, list) else 0

    if strengths_count + weaknesses_count > 0:
        ratio = strengths_count / (strengths_count + weaknesses_count)
    else:
        ratio = 0.0

    if ratio >= 0.75:
        threat_level = "critical"
    elif ratio >= 0.5:
        threat_level = "high"
    elif ratio >= 0.25:
        threat_level = "medium"
    else:
        threat_level = "low"

    if threat_level not in threat_levels:
        threat_level = "medium"

    checks.append(c.ck(True, f"threat_level={threat_level}（strengths={strengths_count} weaknesses={weaknesses_count}）", "competitor:threat_level", **{"threat_level": threat_level}))

    # positioning_overlap：文本相似度（基于词集 Jaccard）
    comp_positioning = str(competitor.get("positioning") or "")
    our_words = set(our_positioning.lower().split())
    comp_words = set(comp_positioning.lower().split())
    if our_words or comp_words:
        intersection = our_words & comp_words
        union = our_words | comp_words
        positioning_overlap = len(intersection) / len(union) if union else 0.0
    else:
        positioning_overlap = 0.0
    positioning_overlap = round(positioning_overlap, 4)

    checks.append(c.ck(True, f"positioning_overlap={positioning_overlap}", "competitor:positioning_overlap", **{"positioning_overlap": positioning_overlap}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   threat_level=threat_level,
                   battlecard_sections=required_sections,
                   positioning_overlap=positioning_overlap,
                   verdict=verdict,
                   next="Battlecard 就绪" if ok else "补齐缺失 section 后重新 battlecard",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "matrix":
        result = matrix(data)
    elif args.action == "battlecard":
        result = battlecard(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result
