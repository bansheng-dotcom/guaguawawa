# -*- coding: utf-8 -*-
"""core.sources.coverage_plan —— CoveragePlan 与出稿前门禁。"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from core.data.data_shape import SHAPES, fits

SCHEMA = "dsh.coverage_plan/v1"
STATUSES = {"verified", "estimated", "missing"}


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def plan_hash(plan: Dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canon(plan).encode("utf-8")).hexdigest()


def build(frame: Dict[str, Any], cells: List[Dict[str, Any]],
          page_estimate: int, maps: List[str],
          charts: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "task_id": frame.get("task_id"),
        "frame_hash": "sha256:" + hashlib.sha256(canon(frame).encode("utf-8")).hexdigest(),
        "cells": cells,
        "core_units": list((frame.get("depth") or {}).get("core_units") or []),
        "long_tail_units": [u["id"] for u in (frame.get("units") or [])
                            if u["id"] not in ((frame.get("depth") or {}).get("core_units") or [])],
        "depth": {u["id"]: ("deep" if u["id"] in ((frame.get("depth") or {}).get("core_units") or [])
                            else "context") for u in (frame.get("units") or [])},
        "page_estimate": page_estimate,
        "maps": maps,
        "charts": charts or [],
    }


def validate(plan: Dict[str, Any], frame: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if plan.get("schema") != SCHEMA:
        errs.append(f"schema 应为 {SCHEMA}")
    if plan.get("frame_hash") != "sha256:" + hashlib.sha256(canon(frame).encode("utf-8")).hexdigest():
        errs.append("frame_hash 与当前 TaskFrame 不一致")
    unit_ids = {u["id"] for u in (frame.get("units") or [])}
    dim_ids = {d["id"] for d in (frame.get("dimensions") or [])}
    seen = set()
    for c in plan.get("cells") or []:
        key = (c.get("unit"), c.get("dimension"))
        if key in seen:
            errs.append(f"cell 重复: {key}")
        seen.add(key)
        if key[0] not in unit_ids:
            errs.append(f"cell 单元不存在: {key[0]}")
        if key[1] not in dim_ids:
            errs.append(f"cell 维度不存在: {key[1]}")
        if c.get("status") not in STATUSES:
            errs.append(f"cell 状态非法: {c.get('status')}")
        if c.get("shape") and c.get("shape") not in SHAPES:
            errs.append(f"cell shape 非法: {c.get('shape')}")
    return errs


def _cells_by(plan: Dict[str, Any]) -> Dict[tuple, Dict[str, Any]]:
    return {(c.get("unit"), c.get("dimension")): c for c in (plan.get("cells") or [])}


def pre_gate(frame: Dict[str, Any], plan: Dict[str, Any],
             sources: Dict[str, Any], confirmation: Dict[str, Any] | None,
             policy: Dict[str, Any]) -> Dict[str, Any]:
    pol = policy.get("coverage", {})
    checks: List[Dict[str, Any]] = []
    hard_fail: List[str] = []
    soft: List[str] = []

    def add(cid, ok, msg, hard=True):
        checks.append({"id": cid, "ok": bool(ok), "msg": msg, "hard": hard})
        if not ok:
            (hard_fail if hard else soft).append(cid)

    st = sources or {}
    add("G1_sources", int(st.get("cited", 0)) >= int(pol.get("cited_sources_min", 50)),
        f"引用源 {st.get('cited', 0)} / {pol.get('cited_sources_min', 50)}")
    add("G2_saturation", bool(st.get("reached")),
        f"饱和 streak {st.get('no_new_streak', 0)} / {pol.get('saturation_no_new', 15)}")
    add("G3_confirmed", bool(confirmation and confirmation.get("plan_hash") == plan_hash(plan)),
        "确认哈希与 plan 不一致" if not confirmation else "已确认")
    by = _cells_by(plan)
    core = plan.get("core_units") or []
    dims = [d["id"] for d in (frame.get("dimensions") or []) if d.get("required", True)]
    missing = [f"{u}×{d}" for u in core for d in dims
               if by.get((u, d), {}).get("status") == "missing"]
    add("G4_core_missing", not missing,
        "核心缺: " + ", ".join(missing) if missing else "核心无 missing")
    deep_bad = [u for u in core if plan.get("depth", {}).get(u) != "deep"]
    add("G5_core_deep", not deep_bad, f"核心未深链: {deep_bad}" if deep_bad else "核心全深链")
    need_maps = set(pol.get("maps_required", ["national", "regional"]))
    have_maps = set(plan.get("maps") or [])
    add("G6_maps", need_maps.issubset(have_maps),
        f"缺地图: {sorted(need_maps - have_maps)}" if not need_maps.issubset(have_maps) else "双地图齐")
    add("G7_pages", int(plan.get("page_estimate", 0)) >= int(pol.get("page_floor", 21)),
        f"预计页数 {plan.get('page_estimate', 0)} / {pol.get('page_floor', 21)}")
    long_tail = [u for u in plan.get("long_tail_units") or []]
    tail_missing = [u for u in long_tail if any(
        by.get((u, d), {}).get("status") == "missing" for d in dims)]
    add("G8_long_tail", True,
        f"长尾缺数据 {len(tail_missing)} 个，需标红" if tail_missing else "长尾无缺", hard=False)
    est = [c for u in core for d in dims
           if (c := by.get((u, d), {})).get("status") == "estimated"]
    total = max(len(core) * len(dims), 1)
    ratio = len(est) / total
    add("G9_core_estimated", ratio <= float(pol.get("core_estimated_ratio_max", .3)),
        f"核心估算占比 {ratio:.0%}", hard=False)
    charts = plan.get("charts") or []
    bad_charts = [f"{c.get('id', '?')}:{c.get('chart')}≠{c.get('shape')}"
                  for c in charts if not fits(c.get("chart"), c.get("shape"))]
    add("G10_chart_fit", not bad_charts,
        "图型不适配 shape: " + ", ".join(bad_charts) if bad_charts else "图型与 shape 全适配")
    return {"ok": not hard_fail, "checks": checks, "hard_fail": hard_fail, "soft": soft,
            "plan_hash": plan_hash(plan), "source_status": st}
