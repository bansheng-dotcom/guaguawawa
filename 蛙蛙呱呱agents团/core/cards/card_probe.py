# -*- coding: utf-8 -*-
"""core.cards.card_probe —— 拆卡后的可行性测试与降级（FEASIBILITY-SOP v5.0）。

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

from core.sources import collection_gen as cg
from core.sources import collection_spec as cs
from core.data import dataset_gates as dg
from core import demand as dm
from core.sources import source_match as sm
from core.sources import source_profile as sp

SCHEMA = "dsh.probe/v1"
ROOT = Path(__file__).resolve().parent.parent.parent
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


def _catalog_answers(project: Path) -> Dict[str, Any]:
    """探测层在 data_catalog.json 里申报的 answers（planned_rows / L2_condition）。"""
    p = project / "cards" / "r18" / "data_catalog.json"
    if not p.is_file():
        return {}
    d = _load_json(p, {})
    return dict((d or {}).get("answers") or {})


def _load_sources(project: Path) -> List[Dict[str, Any]]:
    """源优先级：r18 探源目录（最权威）> 项目自带规格的源 > configs/sources 全量。"""
    out: List[Dict[str, Any]] = []
    # ① r18 交回的数据目录：这是探源产物，最贴近真实可得性
    try:
        for s in sp.load_catalog(project):
            if s and not sp.validate(s):
                out.append(s)
    except Exception:  # noqa: BLE001
        pass
    # ② 项目自带采集规格声明的源
    spec = cs.load(str(project / "collection.yaml"))
    if spec:
        s = sp.load(str(spec.get("source") or ""))
        if s and not out:
            out.append(s)
    # ③ 兜底：configs/sources 全量
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


def probe(project: str, mode: str = "report",
          sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """跑一次可行性测试；返回明细，mode=degrade 时同时更新 grid.json。"""
    project = Path(project)
    if mode not in MODES:
        mode = "report"
    grid = _load_json(project / "plan" / "grid.json", {})
    cells = grid.get("cells") or []
    if not cells:
        return {"ok": False, "why": "没有 plan/grid.json 或没有格子"}

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
        if str(m.get("status") or "") != "none" and m:
            continue
        if not m:
            continue
        unavailable_demands.append({
            "measure": str(d["measure"]),
            "title": "（无数据）%s：%s" % (d["measure"], "×".join(d["grain"])),
            "grain": d["grain"],
            "cells": list(d.get("cells") or []),
            "why": "；".join(m.get("notes") or []) or "没有源能提供",
            "tried": [str(m.get("source") or "")],
        })

    # SUPPLY-SOP v7.2：供给方案由**本次探测生成**，不要求预先存在。
    # 上一轮生成的 plan/supply.json 只用来做对比基线。
    _supply: Dict[str, Any] = {}
    try:
        from core.sources import supply_plan as _sup
        _supply = _sup.load_or_generate(project)
        _planned = _sup.planned_level(_supply) if _supply else None
        _planned_rows = _sup.planned_rows(_supply)
        _supply_issues: List[str] = []
    except Exception as exc:  # noqa: BLE001
        _planned, _planned_rows, _supply_issues = None, None, [str(exc)]

    # 供给方案原料（SUPPLY-SOP v7.1）：每个需求 × 命中源 × 级别 × 缺口
    _rank = {"full": "L2", "partial": "L1", "none": "L0"}
    supply_demands: List[Dict[str, Any]] = []
    for d in dd["demands"]:
        m = best.get(str(d["measure"])) or {}
        _st = str(m.get("status") or "none")
        supply_demands.append({
            "measure": str(d["measure"]),
            "grain": list(d.get("grain") or []),
            "cells": list(d.get("cells") or []),
            "cell_count": int(d.get("cell_count") or 0),
            "matched_source": m.get("source") or "",
            "matched_via": dict(m.get("derive") or {}),
            "level": _rank.get(_st, "L0"),
            "missing": list(m.get("missing") or []),
            "why": "；".join(str(x) for x in (m.get("notes") or [])),
        })
    _l0 = [x["measure"] for x in supply_demands if x["level"] == "L0"]
    _cat_ans = _catalog_answers(project)
    _to_l2 = str(_cat_ans.get("L2_condition") or "")
    if not _to_l2 and _l0:
        _to_l2 = ("需补以下源才能做序列：%s（采购第三方数据或按月手工快照）"
                  % "、".join(_l0))
    _rows = _cat_ans.get("planned_rows") or _planned_rows

    out = {
        "schema": SCHEMA,
        "mode": mode,
        "ok": True,
        "cells": len(cells),
        "demands": dd["count"],
        "planned_level": _planned,
        "planned_rows": _rows,
        "supply_issues": _supply_issues,
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
        "supply_demands": supply_demands,
        "business": project.name,
        "to_l2_condition": _to_l2,
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "degraded": changed,
        "full": sum(1 for v in cell_state.values() if v["collectable"] == "full"),
        "partial": sum(1 for v in cell_state.values() if v["collectable"] == "partial"),
        "none": sum(1 for v in cell_state.values() if v["collectable"] == "none"),
    }
    (project / "plan").mkdir(parents=True, exist_ok=True)
    (project / "plan" / "derivation.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    # SUPPLY-SOP v7.1：供给方案是**探测的产物**，不是手写输入。
    # 写 plan/supply.json，后面发采集卡与收卡都读它。
    try:
        from core.sources import supply_plan as _sp2
        _gen = _sp2.from_probe(out, project)
        _sp2.save(_gen, project)
        out["supply_path"] = str(project / "plan" / "supply.json")
        out["supply_summary"] = (_gen or {}).get("summary") or {}
        # 计划级别以本次生成的供给方案为准（不沿用旧文件）
        out["planned_level"] = (out["supply_summary"] or {}).get("planned_level")
    except Exception as exc:  # noqa: BLE001
        out["supply_error"] = str(exc)
    return out


def degraded_cells(project: str) -> List[Dict[str, Any]]:
    """采集后/报告前读降级结果，供 report_flow 保留空节。"""
    project = Path(project)
    d = _load_json(project / "plan" / "derivation.json", {})
    return [dict(cell_id=k, **v)
            for k, v in (d.get("cell_state") or {}).items()
            if v.get("availability") == "unavailable"]
