# -*- coding: utf-8 -*-
"""core.cards.pipeline —— 发卡 / 验卡 / 收卡的唯一对外入口。

本模块已并入三件拆卡实现（2026-11-27，card 收敛）：
    分卡        cluster / assign / apply_to_cells（原 card_plan）
    卡信封      issue_bundle（原 card_bundle）
    探源        probe / degraded_cells（原 card_probe）

仍需转发的实现：
    report_dispatch  发卡（write_plan / issue）、验卡（load_issued / verify_claims）
    card_issue       拆卡五轴（prepare）、老路径入口（bootstrap）、探源卡
    dispatch         收卡合并（collect）

删除条件：report_dispatch + card_issue + dispatch.collect 的实现搬入本模块后，
这三个模块退场；在此之前只许新增转发，不许另建第二个外部入口。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.base import project as _project
from core.cards import card_issue as _card_issue
from core.cards import dispatch as _dispatch
from core.cards import report_dispatch as _report_dispatch
from core.data import dataset_gates as dg
from core import demand as dm
from core.sources import collection_gen as cg
from core.sources import collection_spec as cs
from core.sources import source_match as sm
from core.sources import source_profile as sp
from shared.knowledge import brief as _brief


# --------------------------------------------------------------------------- #
# 分卡（原 card_plan）
# --------------------------------------------------------------------------- #
DEFAULT_CAP = 24
DEFAULT_LOAD = 3


def cluster(cells: List[Dict[str, Any]], cap: int = DEFAULT_CAP) -> List[Dict[str, Any]]:
    by_q: Dict[str, List[Dict[str, Any]]] = {}
    for c in cells or []:
        by_q.setdefault(str(c.get("qid") or "Q?"), []).append(c)
    out: List[Dict[str, Any]] = []
    for qid, cs_ in by_q.items():
        if len(cs_) <= cap:
            out.append({"card_id": qid, "qid": qid, "cells": cs_, "split": False})
            continue
        by_dim: Dict[str, List[Dict[str, Any]]] = {}
        for c in cs_:
            by_dim.setdefault(str(c.get("dim") or "其他"), []).append(c)
        k = 1
        for dim, ds in by_dim.items():
            for i in range(0, len(ds), cap):
                out.append({"card_id": f"{qid}-{k}", "qid": qid,
                            "dim": dim, "cells": ds[i:i + cap], "split": True})
                k += 1
    return out


def _score(cluster_cells: List[Dict[str, Any]], card: Dict[str, Any]) -> int:
    try:
        from core.cards import card_upgrade as cu
        return sum(cu._score_role(c, card) for c in cluster_cells)
    except Exception:  # noqa: BLE001
        return 0


def assign(clusters: List[Dict[str, Any]], cards: Dict[str, Dict[str, Any]],
           load_cap: int = DEFAULT_LOAD) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    load: Dict[str, int] = {rid: 0 for rid in cards}
    gaps: List[Dict[str, Any]] = []
    for cl in clusters:
        scored = sorted(((_score(cl["cells"], c), rid) for rid, c in cards.items()),
                        key=lambda x: (-x[0], load[x[1]]))
        pick: Optional[Tuple[int, str]] = None
        for sc, rid in scored:
            if load[rid] < load_cap and (sc > 0 or rid in ("r05", "r06")):
                pick = (sc, rid)
                break
        if pick is None:
            cl["owner"], cl["match"] = "", "gap"
            gaps.append({"card_id": cl["card_id"], "type": "capability",
                         "why": "无角色能力匹配或全部满载", "route": "r02"})
            continue
        sc, rid = pick
        load[rid] += 1
        cl["owner"] = rid
        cl["match"] = "strong" if sc > 0 else "weak"
        cl["score"] = sc
    return clusters, gaps


def apply_to_cells(clusters: List[Dict[str, Any]],
                   cells: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    owner = {}
    for cl in clusters:
        for c in cl["cells"]:
            owner[str(c.get("cell_id"))] = cl.get("owner") or ""
    out = []
    for c in cells:
        cc = dict(c)
        cc["owner"] = owner.get(str(c.get("cell_id")), "")
        cc["match"] = "strong" if cc["owner"] else "gap"
        out.append(cc)
    return out


# --------------------------------------------------------------------------- #
# 卡信封（原 card_bundle）
# --------------------------------------------------------------------------- #
def issue_bundle(card_dir: Path | str, role: str, task_id: str, question: str,
                 root: Path | str | None = None,
                 task_type: Optional[str] = None,
                 skills: Optional[List[str]] = None,
                 non_goals: Optional[List[str]] = None) -> Dict[str, Any]:
    """在 card_dir 生成 CardBundle；root 指向项目根时 brief 另落 project/briefs。"""
    proj = _project.load(root) if root is not None else None
    return _brief.issue_bundle(
        card_dir, role, task_id, question, project=proj,
        task_type=task_type, skills=skills, non_goals=non_goals)


# --------------------------------------------------------------------------- #
# 探源（原 card_probe）
# --------------------------------------------------------------------------- #
PROBE_SCHEMA = "dsh.probe/v1"
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
    try:
        for s in sp.load_catalog(project):
            if s and not sp.validate(s):
                out.append(s)
    except Exception:  # noqa: BLE001
        pass
    spec = cs.load(str(project / "collection.yaml"))
    if spec:
        s = sp.load(str(spec.get("source") or ""))
        if s and not out:
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

    _supply: Dict[str, Any] = {}
    try:
        from core.sources import supply_plan as _sup
        _supply = _sup.load_or_generate(project)
        _planned = _sup.planned_level(_supply) if _supply else None
        _planned_rows = _sup.planned_rows(_supply)
        _supply_issues: List[str] = []
    except Exception as exc:  # noqa: BLE001
        _planned, _planned_rows, _supply_issues = None, None, [str(exc)]

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
        "schema": PROBE_SCHEMA,
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
    try:
        from core.sources import supply_plan as _sp2
        _gen = _sp2.from_probe(out, project)
        _sp2.save(_gen, project)
        out["supply_path"] = str(project / "plan" / "supply.json")
        out["supply_summary"] = (_gen or {}).get("summary") or {}
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


# --------------------------------------------------------------------------- #
# 发卡
# --------------------------------------------------------------------------- #
def write_plan(base: str, confirm: bool = False,
               roster_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """把意图映射成问题→角色计划（不落卡）。"""
    return _report_dispatch.write_plan(base, confirm=confirm,
                                       roster_data=roster_data)


def prepare(project, intent: str = "") -> Dict[str, Any]:
    """拆卡五轴 + 发卡前门禁（S1–S12）。"""
    return _card_issue.prepare(Path(project), intent=intent)


def bootstrap(project, intent: str,
              only: Optional[List[str]] = None) -> Dict[str, Any]:
    """老路径 / 并行调研的统一入口：澄清 → 语义层 → 五轴门禁 → 发卡。"""
    return _card_issue.bootstrap(Path(project), intent, only)


def prepare_probe_cards(project) -> Dict[str, Any]:
    """两段发卡的第一段：给探测层发探源卡。"""
    return _card_issue.prepare_probe_cards(Path(project))


def issue(base: str, only: Optional[List[str]] = None) -> Dict[str, Any]:
    """按已确认的映射表发卡（nonce + 签名）。"""
    return _report_dispatch.issue(base, only=only)


# --------------------------------------------------------------------------- #
# 验卡
# --------------------------------------------------------------------------- #
def load_issued(base: str) -> Optional[Dict[str, Any]]:
    return _report_dispatch.load_issued(base)


def verify_claims(claims: Dict[str, Any], role: str,
                  issued: Dict[str, Any]):
    """一张 claims 是不是这张卡被别人执行出来的。"""
    return _report_dispatch.verify_claims(claims, role, issued)


# --------------------------------------------------------------------------- #
# 收卡
# --------------------------------------------------------------------------- #
def collect(out_dir: str, *args, **kwargs):
    """收卡：归一/去重/冲突/覆盖 + 能力级别，合并成 claims_merged。"""
    return _dispatch.collect(out_dir, *args, **kwargs)
