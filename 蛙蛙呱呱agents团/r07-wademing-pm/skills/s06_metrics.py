# -*- coding: utf-8 -*-
"""S06 产品愿景与指标：northstar / metrics / okr / vision / canvas 五条真实门禁。

北极星指标七判据（PM_SPEC.md §5）：可衡量 / 先导性 / 可行动 / 团队可控 /
非虚荣 / 有基线与目标 / 有数据源。虚荣指标（注册量、下载量、曝光量…）直接拦截。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._common import check, is_blank, load_thresholds, make_result

NAME = "metrics"
DESC = "产品愿景与指标"
ACTIONS = {"northstar": "北极星指标七判据", "metrics": "指标分层门禁",
           "okr": "OKR 3×3 门禁", "vision": "产品愿景门禁",
           "canvas": "商业模式画布门禁"}

_VANITY = ("注册量", "下载量", "用户总数", "总用户数", "浏览量", "曝光量",
           "粉丝数", "点击量", "提升用户体验", "功能数量", "上线数量")

_LAYERS_REQUIRED = ("north_star", "input", "guardrail")

_CANVAS_SECTIONS = ("problem", "solution", "uvp", "unfair_advantage", "segments",
                    "channels", "revenue", "cost", "key_metrics")


def _northstar(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """北极星七判据：每条判据显式命名，禁止用 zip 位置对齐（会张冠李戴）。"""
    metric = str(input_data.get("north_star") or "")
    inputs = input_data.get("input_metrics")
    inputs = [str(m) for m in (inputs if isinstance(inputs, list) else [])
              if not is_blank(m)]
    guardrail = input_data.get("guardrail")
    guardrail = [g for g in (guardrail if isinstance(guardrail, list) else [])
                 if not is_blank(g)]
    spec = load_thresholds().get("metrics", {})
    imin = int(spec.get("input_metrics_min", 3))
    imax = int(spec.get("input_metrics_max", 5))

    criteria = [
        ("is_metric_not_activity", not is_blank(metric)
         and not any(w in metric for w in ("上线", "发布", "完成功能")),
         "北极星指标为空或写成交付动作"),
        ("non_vanity", not any(v in metric for v in _VANITY),
         "北极星指标是虚荣指标（注册/下载/曝光类）"),
        ("leading", bool(metric) and metric not in inputs,
         "北极星与输入指标同层，缺乏先导性"),
        ("input_metrics_band", imin <= len(inputs) <= imax,
         f"输入指标 {len(inputs)} 个不在 {imin}~{imax} 区间"),
        ("guardrail_present", bool(guardrail), "缺少护栏指标（guardrail）"),
        ("baseline_target_defined", not is_blank(input_data.get("baseline"))
         and not is_blank(input_data.get("target")),
         "缺少基线或目标口径（baseline / target）"),
        ("data_source_declared", not is_blank(input_data.get("data_source")),
         "缺少数据源（data_source）"),
    ]
    checks = [check(cond, msg, name) for name, cond, msg in criteria]
    required = int(spec.get("nsm_criteria", len(criteria)))
    checks.append(check(len(criteria) >= required,
                        f"北极星判据 {len(criteria)} 条 < 账本要求的 {required} 条",
                        "criteria_count"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "metrics", "northstar", checks,
                       nsm_criteria=[name for name, cond, _ in criteria if cond],
                       nsm_criteria_required=required,
                       input_metric_count=len(inputs))


def _metrics(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    rows = input_data.get("metrics")
    rows = [r for r in (rows if isinstance(rows, list) else []) if isinstance(r, dict)]
    checks.append(check(bool(rows), "指标清单为空（metrics）", "input"))
    layers: Dict[str, int] = {}
    for idx, row in enumerate(rows):
        layer = str(row.get("layer") or "")
        layers[layer] = layers.get(layer, 0) + 1
        checks.append(check(not is_blank(row.get("definition")),
                            f"指标 {idx} 缺少口径定义（definition）", "definition"))
        checks.append(check(not is_blank(row.get("data_source")),
                            f"指标 {idx} 缺少数据源（data_source）", "data_source"))
    for layer in _LAYERS_REQUIRED:
        checks.append(check(layers.get(layer, 0) > 0,
                            f"指标体系缺少 {layer} 层", "layer"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "metrics", "metrics", checks,
                       layers=layers, metric_count=len(rows))


def _okr(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    spec = load_thresholds().get("metrics", {})
    expect_sets = int(spec.get("okr_sets", 3))
    expect_kr = int(spec.get("okr_kr_per_set", 3))
    cmin = int(spec.get("okr_confidence_min", 60))
    cmax = int(spec.get("okr_confidence_max", 70))
    confidence = input_data.get("confidence", 0)
    try:
        confidence_i = int(confidence)
    except (TypeError, ValueError):
        confidence_i = 0
        checks.append(check(False, "OKR confidence 不是整数", "confidence"))

    sets = input_data.get("okr_sets")
    sets = [s for s in (sets if isinstance(sets, list) else []) if isinstance(s, dict)]
    checks.append(check(len(sets) == expect_sets,
                        f"OKR 目标数 {len(sets)} != {expect_sets}", "okr_sets"))
    for idx, okr_set in enumerate(sets):
        checks.append(check(not is_blank(okr_set.get("objective")),
                            f"第 {idx} 个 O 缺 objective", "objective"))
        krs = okr_set.get("key_results")
        krs = [k for k in (krs if isinstance(krs, list) else []) if isinstance(k, dict)]
        checks.append(check(len(krs) == expect_kr,
                            f"第 {idx} 个 O 的 KR 数 {len(krs)} != {expect_kr}", "key_result"))
        for k_idx, kr in enumerate(krs):
            checks.append(check(not is_blank(kr.get("metric")),
                                f"第 {idx}.{k_idx} 个 KR 缺 metric", "key_result"))
    checks.append(check(cmin <= confidence_i <= cmax,
                        f"OKR 信心指数 {confidence_i} 不在 {cmin}~{cmax}", "confidence"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "metrics", "okr", checks,
                       okr_sets=len(sets), confidence=confidence_i,
                       kr_per_set=expect_kr)


def _vision(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    checks.append(check(not is_blank(input_data.get("vision")), "缺少愿景陈述（vision）",
                        "vision"))
    for field in ("inspiring", "achievable", "emotional"):
        checks.append(check(not is_blank(input_data.get(field)),
                            f"愿景缺少 {field} 维度自检", field))
    variants = input_data.get("variants")
    variants = [v for v in (variants if isinstance(variants, list) else []) if not is_blank(v)]
    checks.append(check(len(variants) >= 3, f"愿景备选 {len(variants)} 条 < 3 条", "variant"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "metrics", "vision", checks, variant_count=len(variants))


def _canvas(input_data: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    sections = input_data.get("sections")
    sections = sections if isinstance(sections, dict) else {}
    checks.append(check(bool(sections), "商业模式画布为空（sections）", "input"))
    filled = []
    for name in _CANVAS_SECTIONS:
        value = sections.get(name)
        if not is_blank(value):
            filled.append(name)
        else:
            checks.append(check(False, f"画布缺少 {name} 区块", "section"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "metrics", "canvas", checks, canvas_sections=filled)


# 历史名称兼容（harness / run_tests 使用 _northstar / _metrics / _okr）
def northstar(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _northstar(input_data)


def metrics(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _metrics(input_data)


def okr(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _okr(input_data)


def vision(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _vision(input_data)


def canvas(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _canvas(input_data)
