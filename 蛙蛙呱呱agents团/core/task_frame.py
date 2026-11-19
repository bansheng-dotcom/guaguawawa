# -*- coding: utf-8 -*-
"""core.task_frame —— TaskFrame：任务类型、分析单元、维度、深度、地图、页数。

不做业务线模板；只校验“每个单元/维度有来源、核心单元 3–5、双地图、页数下限”。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

SCHEMA = "dsh.task_frame/v1"
UNIT_LEVELS = {"category", "sku", "customer", "channel", "region", "competitor", "supplier"}


def _canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def frame_hash(frame: Dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canon(frame).encode("utf-8")).hexdigest()


def validate(frame: Dict[str, Any], policy: Dict[str, Any] | None = None) -> List[str]:
    errs: List[str] = []
    pol = (policy or {}).get("coverage", {})
    if frame.get("schema") != SCHEMA:
        errs.append(f"schema 应为 {SCHEMA}")
    dec = frame.get("decision") or {}
    if not str(dec.get("question") or "").strip():
        errs.append("decision.question 为空")
    units = frame.get("units") or []
    dims = frame.get("dimensions") or []
    if not units:
        errs.append("units 为空")
    if not dims:
        errs.append("dimensions 为空")
    ids = set()
    for u in units:
        uid = u.get("id")
        if not uid:
            errs.append("unit 缺 id")
        if uid in ids:
            errs.append(f"unit id 重复: {uid}")
        ids.add(uid)
        if u.get("level") not in UNIT_LEVELS:
            errs.append(f"unit {uid} level 非法: {u.get('level')}")
        if not u.get("sources"):
            errs.append(f"unit {uid} 缺 sources")
    dim_ids = set()
    for d in dims:
        did = d.get("id")
        if not did:
            errs.append("dimension 缺 id")
        if did in dim_ids:
            errs.append(f"dimension id 重复: {did}")
        dim_ids.add(did)
        if not d.get("sources"):
            errs.append(f"dimension {did} 缺 sources")
    core = (frame.get("depth") or {}).get("core_units") or []
    lo = int(pol.get("core_units_min", 3))
    hi = int(pol.get("core_units_max", 5))
    if not (lo <= len(core) <= hi):
        errs.append(f"core_units 数量 {len(core)} 不在 {lo}–{hi}")
    if len(set(core)) != len(core):
        errs.append("core_units 有重复")
    unknown = [x for x in core if x not in ids]
    if unknown:
        errs.append(f"core_units 不在 units 中: {unknown}")
    maps = [m.get("level") for m in (frame.get("maps") or []) if m.get("required", True)]
    for need in pol.get("maps_required", ["national", "regional"]):
        if need not in maps:
            errs.append(f"缺必填地图: {need}")
    if int(frame.get("page_floor", 0)) < int(pol.get("page_floor", 21)):
        errs.append(f"page_floor 低于 {pol.get('page_floor', 21)}")
    sat = frame.get("saturation") or {}
    if not sat.get("reached"):
        errs.append("saturation.reached 未为 true")
    return errs


def build(brief: Dict[str, Any], decision: Dict[str, Any], units: List[Dict[str, Any]],
          dimensions: List[Dict[str, Any]], depth: Dict[str, Any],
          maps: List[Dict[str, Any]], page_floor: int,
          source_policy: Dict[str, Any], saturation: Dict[str, Any],
          conflicts: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "task_id": brief.get("task_id"),
        "brief": brief.get("brief"),
        "decision": decision,
        "units": units,
        "dimensions": dimensions,
        "depth": depth,
        "maps": maps,
        "page_floor": page_floor,
        "source_policy": source_policy,
        "saturation": saturation,
        "conflicts": conflicts or [],
    }
