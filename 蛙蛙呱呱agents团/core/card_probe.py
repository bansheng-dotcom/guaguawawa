# -*- coding: utf-8 -*-
"""core.card_probe —— 拆卡后的可行性测试与降级（FEASIBILITY-SOP v5.0）。

**位置：拆卡之后、采集之前。** 它不做门禁、不砍格子，只回答三件事：

    这只格子要采什么？      demand_of(grid, sem)
    有没有源能答？          source_match.match_all(demands, sources)
    采到了质量够不够？      collection_spec.preview / quality

然后给每只格子打三态：
    collectable = full | partial | none
    availability = available | unavailable
    tried / why

mode:
    report   只报告，不改 grid（默认）
    degrade  把 none 的格子标 unavailable
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import collection_gen as cg
from core import collection_spec as cs
from core import dataset_gates as dg
from core import demand as dm
from core import source_match as sm
from core import source_profile as sp

SCHEMA = "dsh.probe/v1"
ROOT = Path(__file__).resolve().parent.parent
MODES = ("report", "degrade", "off")


def _load_json(p: Path, default: Any = None) -> Any:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default if default is not None else {}


def _load_semantic(project: Path) -> Dict[str, Any]:
    p = project / "semantic_layer.yaml"
    if not p.is_file():
        return {}
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def _load_sources(project: Path) -> List[Dict[str, Any]]:
    """项目自带规格的源优先；否则把 configs/sources 全拿上。"""
    out: List[Dict[str, Any]] = []
    spec = cs.load(str(project / "collection.yaml"))
    if spec:
        s = sp.load(str(spec.get("source") or ""))
        if s:
            out.append(s)
    if not out:
        for p in sorted(sp.SOURCES_DIR.glob("*.yaml")):
            s = sp.load(str(p))
            if s and not sp.validate(s):
                out.append(s)
    return out


def _best_for(demand_doc: Dict[str, Any], match_doc: Dict[str, Any]) -> Dict[str, Any]:
    """measure → 最好的匹配（best 已经按 status 排序过）。"""
    best = (match_doc or {}).get("best") or {}
    return best


def _evidence_layer(project: Path) -> Dict[str, Any]:
    """L1 证据层：项目里有没有「数字 + 来源」这种点证据。

    老报告（无长表那种）没有长表，但有几百个数字、每个挂 url+quote。
    判「没数据」之前必须先看这一层——否则会把有证据的报告误判成无数据。
    """
    nums: List[Dict[str, Any]] = []
    srcs: List[Dict[str, Any]] = []
    for p in (project / "claims_merged.json",
              project / "out" / "claims_merged.json"):
        if p.is_file():
            d = _load_json(p, {})
            nums = list(d.get("numbers") or [])
            srcs = list(d.get("sources") or [])
            break
    if not nums:
        # 退到各卡的 claims.json
        for f in sorted(project.glob("*/*/claims.json")):
            d = _load_json(f, {})
            nums.extend(d.get("numbers") or [])
            srcs.extend(d.get("sources") or [])
    with_src = sum(1 for n in nums if str(n.get("source_file") or "").strip())
    return {
        "numbers": len(nums),
        "sources": len(srcs),
        "with_source": with_src,
        "with_source_rate": (round(with_src / len(nums), 3) if nums else 0.0),
        "available": bool(nums),
    }


def _has_dataset_layer(project: Path) -> bool:
    """有没有数据集层（长表）：采集规格 / mart / datasets 任一存在。"""
    if (project / "collection.yaml").is_file():
        return True
    if (project / "plan" / "mart.json").is_file():
        return True
    ds = project / "data" / "datasets"
    if ds.is_dir() and any(ds.glob("*.csv")):
        return True
    return False


def _degrade_level(dataset_rows: int, ev: Dict[str, Any]) -> str:
    """降级只分三层：有长表 / 只有点证据 / 什么都没有。"""
    if dataset_rows > 0:
        return "dataset"
    if ev.get("available"):
        return "evidence"
    return "none"


def probe(project: str, mode: str = "report",
          sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """跑一次可行性测试；返回明细，mode=degrade 时同时更新 grid.json。"""
    project = Path(project)
    if mode not in MODES:
        mode = "report"
    ev = _evidence_layer(project)
    grid = _load_json(project / "plan" / "grid.json", {})
    cells = grid.get("cells") or []
    if not cells:
        # 没有网格（老项目）：不判格子，但要说清有没有证据层数据
        return {"ok": True, "mode": mode, "cells": 0, "demands": 0,
                "evidence_layer": ev,
                "degrade_level": _degrade_level(0, ev),
                "note": ("没有 plan/grid.json（老报告路径）；"
                         "证据层 %d 个数字 / %d 个来源"
                         % (ev["numbers"], ev["sources"]))}

    sem = _load_semantic(project)
    srcs = sources if sources is not None else _load_sources(project)
    dd = dm.demand_of(grid, sem)
    mm = sm.match_all(dd["demands"], srcs) if srcs else {"best": {}, "matrix": [],
                                                        "counts": {}}

    # 有采集规格时，跑样本验证
    spec = cs.load(str(project / "collection.yaml"))
    pv = qt = None
    if spec:
        try:
            pv = cs.preview(spec, n=5, project_dir=str(project))
            qt = cs.quality(spec, project_dir=str(project))
        except Exception:  # noqa: BLE001
            pv = qt = None

    gates = dg.derivation_gates(dd, mm, qt)
    draft = cg.generate(dd, mm, srcs[0], spec_id=spec.get("id") if spec else "",
                        query=(spec or {}).get("query") or {}) if srcs else {}

    # 每个需求 → 三态
    best = _best_for(dd, mm)
    dem_cells: Dict[str, List[str]] = {}
    for d in dd["demands"]:
        dem_cells[str(d["measure"])] = list(d.get("cells") or [])
    cell_state: Dict[str, Dict[str, Any]] = {}
    for measure, m in best.items():
        status = str(m.get("status") or "none")
        # 证据层兜底只对「完全没有数据集层」的老报告生效；
        # 有采集规格的项目，数据集层就是权威——none 就是真没有。
        if status == "none" and ev.get("available") and not _has_dataset_layer(project):
            status = "point"
        for cid in dem_cells.get(measure, []):
            cell_state[cid] = {
                "measure": measure,
                "collectable": status,
                "availability": "unavailable" if status == "none" else "available",
                "tried": [str(m.get("source") or "")],
                "why": ("；".join(m.get("notes") or []) or
                        ("缺列: %s" % m.get("missing") if m.get("missing") else "")),
            }

    # 更新 grid（只在 degrade 模式）
    changed = 0
    if mode == "degrade":
        for c in cells:
            st = cell_state.get(str(c.get("cell_id") or ""))
            if not st:
                continue
            c["collectable"] = st["collectable"]
            c["availability"] = st["availability"]
            c["tried"] = st["tried"]
            c["why"] = st["why"]
            changed += 1
        (project / "plan" / "grid.json").write_text(
            json.dumps(grid, ensure_ascii=False, indent=1), encoding="utf-8")

    # 需求级：判为 none 的，补成「无数据」节（报告里保留，标 unavailable）
    unavailable_demands: List[Dict[str, Any]] = []
    for d in dd["demands"]:
        m = best.get(str(d["measure"])) or {}
        st = str(m.get("status") or "none")
        if st != "none":
            continue
        if not m:
            continue
        # 证据层兜底只对「完全没有数据集层」的老报告生效（见上）
        if ev.get("available") and not _has_dataset_layer(project):
            continue
        unavailable_demands.append({
            "measure": str(d["measure"]),
            "title": "（无数据）%s：%s" % (d["measure"], "×".join(d["grain"])),
            "grain": d["grain"],
            "cells": list(d.get("cells") or []),
            "why": "；".join(m.get("notes") or []) or "没有源能提供",
            "tried": [str(m.get("source") or "")],
        })

    out = {
        "schema": SCHEMA,
        "mode": mode,
        "ok": True,
        "cells": len(cells),
        "demands": dd["count"],
        "sources": [str(s.get("id")) for s in srcs],
        "counts": (mm or {}).get("counts") or {},
        "gates": gates,
        "draft": draft,
        "preview": {"ok": (pv or {}).get("ok"),
                    "staging_rows": (pv or {}).get("staging_rows"),
                    "total_rows": (pv or {}).get("total_rows")},
        "quality": {"ok": (qt or {}).get("ok"),
                    "problems": (qt or {}).get("problems")},
        "cell_state": cell_state,
        "unavailable_demands": unavailable_demands,
        "evidence_layer": ev,
        "degrade_level": _degrade_level(
            int((pv or {}).get("total_rows") or 0), ev),
        "degraded": changed,
        "full": sum(1 for v in cell_state.values() if v["collectable"] == "full"),
        "partial": sum(1 for v in cell_state.values() if v["collectable"] == "partial"),
        "none": sum(1 for v in cell_state.values() if v["collectable"] == "none"),
    }
    (project / "plan").mkdir(parents=True, exist_ok=True)
    (project / "plan" / "derivation.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def degraded_cells(project: str) -> List[Dict[str, Any]]:
    """采集后/报告前读降级结果，供 report_flow 保留空节。"""
    project = Path(project)
    d = _load_json(project / "plan" / "derivation.json", {})
    return [dict(cell_id=k, **v)
            for k, v in (d.get("cell_state") or {}).items()
            if v.get("availability") == "unavailable"]
