# -*- coding: utf-8 -*-
"""core.cells_unified —— 三套「格子→数字」的统一读数与对账（P5-5）。

问题：v1 `build()` 读已填格子、v2 `from_drill()` 读数据集/mart、v3 `from_collection()`
从采集 mart 出数——同一格可能得到三个数。

做法（方案要求先双写、再切）：
    1. `observations(project)` 给出**唯一读数**：优先 `out/raw.json`（清洗后观测），
       其次 `plan/mart.json`（采集 mart），都按 (measure, entity, period) 归一；
    2. `compare(project)` 把 v1（cells_filled）与统一读数逐键对账，写
       `out/cells_claims_diff.json`；
    3. `build()` 在 unified 模式下用统一读数覆盖格子标量，并记录 `value_from`；
       对账不为 0 的键标 `needs_human`，不静默改数。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TIME_HINTS = ("date", "month", "year", "week", "quarter", "day", "period",
              "日期", "月份", "年份", "时间", "周", "月", "年")


def _load(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def _load_yaml(p: Path, default=None):
    try:
        import yaml
        return yaml.safe_load(Path(p).read_text(encoding="utf-8")) or default
    except Exception:  # noqa: BLE001
        return default


def _is_time(name: str) -> bool:
    low = str(name).lower()
    return any(h in low for h in TIME_HINTS)


def key_of(measure: Any, entity: Any, period: Any) -> str:
    return "%s|%s|%s" % (str(measure or ""), str(entity or "").strip(),
                         str(period or "").strip())


def obs(measure: str, entity: str, period: str, value: Any, unit: str = "",
        source: str = "", path: str = "") -> Optional[Dict[str, Any]]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return {"key": key_of(measure, entity, period), "measure": measure,
            "entity": entity, "period": period, "value": v, "unit": unit,
            "source": source, "path": path}


def _from_raw(project: Path) -> List[Dict[str, Any]]:
    raw = _load(project / "out" / "raw.json", {}) or {}
    out = []
    for r in raw.get("rows") or []:
        o = obs(str(r.get("metric_id") or ""), str(r.get("entity") or ""),
                str(r.get("period") or ""), r.get("value"),
                str(r.get("unit") or ""), str(r.get("source_id") or ""), "raw")
        if o:
            o["metric_name"] = str(r.get("metric_name") or "")
            out.append(o)
    return out


def _mart_measures(project: Path) -> Tuple[List[str], List[str], Dict[str, str]]:
    """从 collection.yaml 推：measure 列名、维度列名、grain 维度。"""
    spec = _load_yaml(project / "collection.yaml", {}) or {}
    measures: List[str] = []
    dims: List[str] = []
    for r in spec.get("rollups") or []:
        for k in (r.get("measures") or {}):
            if k not in measures:
                measures.append(str(k))
        for d in r.get("grain") or []:
            if str(d) not in dims:
                dims.append(str(d))
    return measures, dims, {str(r.get("id")): str(r.get("id")) for r in []}


def _from_mart(project: Path) -> List[Dict[str, Any]]:
    mart = _load(project / "plan" / "mart.json", {}) or {}
    measures, dims, _ = _mart_measures(project)
    out: List[Dict[str, Any]] = []
    for rid, rows in mart.items():
        if not isinstance(rows, list) or not rows:
            continue
        cols = list(rows[0].keys())
        ms = [m for m in measures if m in cols] or \
            [c for c in cols if c not in dims and not _is_time(c)]
        ds = [d for d in dims if d in cols] or \
            [c for c in cols if c not in ms]
        ent_col = next((d for d in ds if not _is_time(d)), ds[0] if ds else "")
        per_col = next((d for d in ds if _is_time(d)), "")
        for r in rows:
            for m in ms:
                o = obs(m, str(r.get(ent_col) or ""), str(r.get(per_col) or ""),
                        r.get(m), "", str(rid), "mart")
                if o:
                    out.append(o)
    return out


def observations(project: Path | str) -> List[Dict[str, Any]]:
    """唯一读数：raw.json 优先，其次 plan/mart.json。"""
    project = Path(project)
    rows = _from_raw(project)
    if not rows:
        rows = _from_mart(project)
    return rows


def index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        out.setdefault(r["key"], r)      # 同键取第一条（冲突另有 raw.conflicts 记录）
    return out


def from_cells(project: Path | str) -> List[Dict[str, Any]]:
    project = Path(project)
    doc = _load(project / "out_v3" / "cells_filled.json", {}) or {}
    out = []
    for c in doc.get("cells") or []:
        if str(c.get("status") or "filled") != "filled":
            continue
        o = obs(str(c.get("measure_id") or c.get("measure") or ""),
                str(c.get("entity") or ""), str(c.get("period") or ""),
                c.get("value"), str(c.get("unit") or ""),
                str(c.get("source_file") or ""), "cells")
        if o:
            out.append(o)
    return out


def compare(project: Path | str, tol: float = 1e-6,
            write: bool = True) -> Dict[str, Any]:
    """双写对账：cells（v1） vs 统一读数（raw/mart）。"""
    project = Path(project)
    cells = index(from_cells(project))
    uniq = index(observations(project))
    diffs: List[Dict[str, Any]] = []
    matched = 0
    for k, c in cells.items():
        u = uniq.get(k)
        if not u:
            continue
        matched += 1
        if abs(float(u["value"]) - float(c["value"])) > tol:
            diffs.append({"key": c["key"], "measure": c["measure"],
                          "entity": c["entity"], "period": c["period"],
                          "cells_value": c["value"], "unified_value": u["value"],
                          "unified_path": u["path"]})
    res = {"schema": "dsh.cells_diff/v1", "ok": not diffs,
           "cells": len(cells), "unified": len(uniq), "matched": matched,
           "diffs": diffs,
           "missing_in_unified": sorted({k for k in cells if k not in uniq})[:50]}
    if write:
        out = project / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "cells_claims_diff.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def apply_to_cells(project: Path | str, cells: List[Dict[str, Any]],
                   tol: float = 1e-6) -> Dict[str, Any]:
    """把统一读数覆盖到已填格子；返回对账摘要（供 build() 落 value_from）。"""
    uniq = index(observations(project))
    matched = 0
    mismatched: List[Dict[str, Any]] = []
    for c in cells:
        k = key_of(c.get("measure_id") or c.get("measure"),
                   c.get("entity"), c.get("period"))
        u = uniq.get(k)
        if not u:
            c.setdefault("value_from", "cell")
            continue
        matched += 1
        if abs(float(u["value"]) - float(c.get("value") or 0)) > tol:
            mismatched.append({"key": k, "cells_value": c.get("value"),
                               "unified_value": u["value"]})
            c["needs_human"] = True
        c["value"] = u["value"]
        c["value_from"] = "observation"
        c["unified_path"] = u["path"]
        if u.get("unit") and not c.get("unit"):
            c["unit"] = u["unit"]
    return {"matched": matched, "mismatched": mismatched,
            "unified_rows": len(uniq)}
