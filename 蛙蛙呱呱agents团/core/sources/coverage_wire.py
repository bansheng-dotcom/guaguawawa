# -*- coding: utf-8 -*-
"""core.sources.coverage_wire —— 把「覆盖矩阵 / 饱和」接进主链路（SOP A 项）。

问题：`coverage_plan`（G1–G10 覆盖矩阵）和 `task_research`（来源饱和）写好了、
有单测，但 `report_flow.run` 的 `coverage_plan_data / task_frame_data /
source_ledger_data` 三个参数**没有任何调用方传**，主链路永远不跑。

本模块从项目已产出的工件派生这三份数据：
    plan/grid.json           → 格子（unit × dimension × status）
    out_v3/cells_filled.json → 哪些格已填（verified / missing）
    out/claims_merged.json   → 来源账本（cited / streak）

然后由 `decision_report` / `report_line` 传给 `report_flow.run`。
**默认软门禁**（只记录不拦），`GUAGUA_COVERAGE_HARD=1` 才升级为硬门禁。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.sources import coverage_plan as _cp

# 六维（与 card_upgrade.DIMS 一致）
DIMS = ("对象", "空间", "时间", "结构", "机制", "边界")


def _load(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def _filled_cell_ids(project: Path) -> set:
    for rel in ("out_v3/cells_filled.json", "out/cells_filled.json"):
        d = _load(project / rel)
        if d.get("cells"):
            return {str(c.get("cell_id")) for c in d["cells"]
                    if c.get("status") == "filled"}
    return set()


def derive(project_dir: str) -> Dict[str, Any]:
    """从项目工件派生 (frame, plan, sources)。缺关键工件时 ok=False。"""
    project = Path(project_dir)
    grid = _load(project / "plan" / "grid.json")
    cells_in = grid.get("cells") or []
    if not cells_in:
        return {"ok": False, "why": "缺 plan/grid.json（未拆卡）"}

    filled = _filled_cell_ids(project)

    # ---- coverage_plan.cells：unit × dimension × status ----
    cells: List[Dict[str, Any]] = []
    seen = set()
    for c in cells_in:
        unit = str(c.get("entity") or "")
        dim = str(c.get("dim") or "")
        if not unit or dim not in DIMS:
            continue
        key = (unit, dim)
        if key in seen:
            continue
        seen.add(key)
        status = "verified" if str(c.get("cell_id")) in filled else "missing"
        cells.append({"unit": unit, "dimension": dim, "status": status,
                      "shape": c.get("shape") or None})

    # ---- task_frame：核心单元 = 对象维的实体 ----
    core_units = sorted({str(c.get("entity")) for c in cells_in
                         if c.get("dim") == "对象" and c.get("entity")}) or \
                 sorted({str(c.get("entity")) for c in cells_in if c.get("entity")})[:3]
    units = sorted({str(c.get("entity")) for c in cells_in if c.get("entity")})
    depth = {u: ("deep" if any(
        (c.get("dim") == "机制" and str(c.get("entity")) == u
         and (c.get("depth_target") or 1) >= 3) for c in cells_in) else "context")
        for u in units}
    frame = {
        "task_id": "T-" + str(grid.get("schema") or "grid"),
        "units": [{"id": u} for u in units],
        "dimensions": [{"id": d, "required": True} for d in DIMS],
        "depth": {"core_units": core_units, "deep": [u for u, v in depth.items()
                                                     if v == "deep"]},
    }

    # ---- 来源账本：从 claims merged 的 sources 数 ----
    merged = _load(project / "out" / "claims_merged.json") or \
        _load(project / "out_v3" / "claims_merged.json")
    srcs = merged.get("sources") or []
    cited = len({str(s.get("file") or s.get("title") or i)
                 for i, s in enumerate(srcs)})
    # 没有 new_dimensions 时不能伪造 streak：reached 为 False，如实报告
    sources = {"cited": cited, "no_new_streak": 0,
               "reached": False, "dimensions": []}

    plan = _cp.build(frame, cells,
                     page_estimate=int(grid.get("count") or len(cells_in)),
                     maps=[],
                     charts=[{"id": c.get("cell_id"), "chart": "auto",
                              "shape": c.get("shape")} for c in cells_in
                             if c.get("shape")])
    return {"ok": True, "frame": frame, "plan": plan, "sources": sources,
            "cells": len(cells), "filled": len(filled)}


def gate(project_dir: str) -> Dict[str, Any]:
    """派生并跑覆盖门禁。返回 pre_gate 结果 + 派生信息；缺工件时 skipped。"""
    d = derive(project_dir)
    if not d.get("ok"):
        return {"ok": True, "skipped": True, "why": d.get("why")}
    from core.sources import coverage_policy
    res = _cp.pre_gate(d["frame"], d["plan"], d["sources"],
                       {"plan_hash": _cp.plan_hash(d["plan"])},
                       coverage_policy.load())
    res["derived"] = {"cells": d["cells"], "filled": d["filled"]}
    return res
