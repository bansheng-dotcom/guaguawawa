# -*- coding: utf-8 -*-
"""第 2 段 plan：先写计划，再看数。

方案 §13.4 的硬要求：
  - 指标 / 粒度 / 窗口 / 维度 / 检验 / 停止条件，缺一项即失败；
  - `preregistered=true` 且 `data_read_before_plan=false`（计划先于看数）；
  - 每个假设恰好对应一轮计划，避免“先看数再补假设”。

计划契约沿用 `experience/plan_schema.json`，不另起一套。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .common import ck, gate, now_iso, read_json

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCHEMA_PATH = os.path.join(_HERE, "experience", "plan_schema.json")
_DATA_EVIDENCE_KEYS = ("rows", "observed", "data_profile", "actual_values", "raw_rows")


def _empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _schema() -> Dict[str, Any]:
    return read_json(_SCHEMA_PATH) if os.path.exists(_SCHEMA_PATH) else {
        "required_fields": ["round", "analytical_step", "question", "query_spec",
                            "expected_output", "acceptance_criteria", "stop_condition"],
        "analytical_step_enum": ["trend_analysis", "decomposition", "attribution",
                                 "risk_mining"],
        "query_spec_required": ["metrics", "group_by", "date_range"],
        "expected_output_required": ["format", "required_fields"],
        "acceptance_criteria_required": ["min_rows", "all_required_fields"],
        "stop_condition_required": ["if_impact_below_pct", "reason"],
    }


def build(frame: Dict[str, Any], before: str, after: str, split: str = "",
          grain: str = "day", window: str = "", tests: Optional[List[str]] = None,
          min_rows: int = 30) -> Dict[str, Any]:
    fg = frame.get("gate") or {}
    if not fg.get("ok"):
        raise ValueError("frame 门禁未通过，不能进入 plan：" + "; ".join(fg.get("errors", [])[:3]))
    metric = frame["metric"]
    dims = list(frame.get("dimensions") or [])
    test_plan = tests or ["welch_t", "bootstrap_ci", "cohen_d", "holm"]
    rounds = []
    for i, h in enumerate(frame["hypotheses"], 1):
        rounds.append({
            "round": i,
            "hypothesis_id": h["id"],
            "analytical_step": h["test"],
            "question": h["statement"],
            "query_spec": {
                "metrics": [metric],
                "group_by": dims,
                "date_range": {"start": before, "end": after, "split": split,
                               "label": window or frame.get("window", "")},
                "filters": [],
                "grain": grain,
            },
            "expected_output": {"format": "table",
                                "required_fields": ["segment", "value", "delta"]},
            "acceptance_criteria": {"min_rows": min_rows, "all_required_fields": True},
            "stop_condition": {
                "if_impact_below_pct": float(h.get("min_impact_pct", 3.0)),
                "reason": "分段贡献低于阈值即停止下钻，避免在噪声上继续归因",
            },
            "tests": test_plan,
            "multiple_testing": "holm",
            "denominator_definition": f"{metric} 的期内同口径总量（全部分段合计）",
        })
    plan = {
        "artifact": "analysis_plan",
        "version": "1.0",
        "generated_at": now_iso(),
        "frame_question": frame.get("question", ""),
        "metric": metric,
        "grain": grain,
        "window": window or frame.get("window", ""),
        "before": before,
        "after": after,
        "split": split,
        "dimensions": dims,
        "preregistered": True,
        "data_read_before_plan": False,
        "rounds": rounds,
    }
    plan["gate"] = check(plan, frame)
    return plan


def check(plan: Dict[str, Any], frame: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    schema = _schema()
    checks = []
    rounds = plan.get("rounds") or []
    checks.append(ck(bool(rounds), f"计划轮数={len(rounds)}", "structure",
                     "CRITICAL" if not rounds else "OK"))
    checks.append(ck(plan.get("preregistered") is True, "preregistered=true",
                     "preregistration", "CRITICAL" if plan.get("preregistered") is not True else "OK"))
    checks.append(ck(plan.get("data_read_before_plan") is False,
                     "data_read_before_plan=false（计划先于看数）", "preregistration",
                     "CRITICAL" if plan.get("data_read_before_plan") is not False else "OK"))
    checks.append(ck(bool(plan.get("split")), "前后期切分点 split 明确", "window",
                     "CRITICAL" if not plan.get("split") else "OK"))
    for key in _DATA_EVIDENCE_KEYS:
        if key in plan:
            checks.append(ck(False, f"计划中出现数据证据字段 {key}（计划先于看数）",
                             "preregistration", "CRITICAL"))
    numbers = [r.get("round") for r in rounds]
    checks.append(ck(numbers == list(range(1, len(rounds) + 1)),
                     f"轮次连续 {numbers}", "structure",
                     "CRITICAL" if numbers != list(range(1, len(rounds) + 1)) else "OK"))
    enum = schema.get("analytical_step_enum", [])
    for r in rounds:
        tag = f"round {r.get('round')}"
        for f in schema.get("required_fields", []):
            val = r.get(f)
            empty = _empty(val)
            checks.append(ck(not empty, f"{tag} 含必填字段 {f}", "structure",
                             "CRITICAL" if empty else "OK"))
        checks.append(ck(r.get("analytical_step") in enum,
                         f"{tag} analytical_step 合法={r.get('analytical_step')}", "structure",
                         "CRITICAL" if r.get("analytical_step") not in enum else "OK"))
        for grp in ("query_spec", "expected_output", "acceptance_criteria", "stop_condition"):
            obj = r.get(grp) or {}
            for k in schema.get(f"{grp}_required", []):
                val = obj.get(k)
                empty = _empty(val)
                checks.append(ck(not empty, f"{tag}.{grp}.{k} 存在", "structure",
                                 "CRITICAL" if empty else "OK"))
        qs = r.get("query_spec") or {}
        checks.append(ck(bool(qs.get("metrics")), f"{tag} 指标非空", "metric",
                         "CRITICAL" if not qs.get("metrics") else "OK"))
        checks.append(ck(bool(qs.get("group_by")), f"{tag} 维度非空", "metric",
                         "CRITICAL" if not qs.get("group_by") else "OK"))
        dr = qs.get("date_range") or {}
        checks.append(ck(bool(dr.get("start")) and bool(dr.get("end")),
                         f"{tag} 窗口 start/end 明确", "window",
                         "CRITICAL" if not (dr.get("start") and dr.get("end")) else "OK"))
        stop = r.get("stop_condition") or {}
        checks.append(ck(isinstance(stop.get("if_impact_below_pct"), (int, float)),
                         f"{tag} 停止条件为数值阈值", "stop_condition",
                         "CRITICAL" if not isinstance(stop.get("if_impact_below_pct"), (int, float)) else "OK"))
        if frame:
            fmetric = frame.get("metric")
            checks.append(ck(qs.get("metrics") == [fmetric] or fmetric in qs.get("metrics", []),
                             f"{tag} 指标与 frame 一致（{fmetric}）", "consistency",
                             "CRITICAL" if fmetric not in qs.get("metrics", []) else "OK"))
    if frame:
        fids = [h["id"] for h in frame.get("hypotheses", [])]
        pids = [r.get("hypothesis_id") for r in rounds]
        checks.append(ck(sorted(fids) == sorted(pids),
                         f"假设与计划一一对应 frame={fids} plan={pids}", "consistency",
                         "CRITICAL" if sorted(fids) != sorted(pids) else "OK"))
        fdims = frame.get("dimensions") or []
        for r in rounds:
            gb = (r.get("query_spec") or {}).get("group_by") or []
            checks.append(ck(set(gb) <= set(fdims), f"round {r.get('round')} 维度不越界",
                             "consistency", "HIGH" if not set(gb) <= set(fdims) else "OK"))
    return gate(checks, "plan")
