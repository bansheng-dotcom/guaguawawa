# -*- coding: utf-8 -*-
"""把六维网格接进发卡：每张 TASK.md 末尾追加「你负责的格子」。

系统级改动，不依赖具体项目：卡片生成后调用 attach_cards(项目目录)，
按 clarify + 证据包生成 grid.json，再按能力匹配把格子分给各角色。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core import card_upgrade as cu
from core import roster


def _load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def attach_cards(project: Path) -> Dict[str, Any]:
    project = Path(project)
    clarify = _load(project / "clarify.json") or _load(project / "out" / "clarify.json")
    if not clarify:
        return {"ok": False, "why": "无 clarify.json"}
    pack = {}
    for c in (project / "out" / "_compiled" / "evidence_pack.json",
              project / "out_v2" / "_compiled" / "evidence_pack.json"):
        got = _load(c)
        if got:
            pack = got
            break
    sem = cu.load_semantics(project, pack)
    # 跨项目污染护栏：pack 里的品牌必须在本项目 clarify/语义层出现过，
    # 否则不进入网格（历史事故：成人用品卡里出现「泡泡玛特份额」）。
    clarify_text = json.dumps(clarify, ensure_ascii=False)
    sem_text = json.dumps(sem, ensure_ascii=False)
    brands = [b for b in cu._brands(pack)
              if b and (b in clarify_text or b in sem_text)]
    # 必须用本项目模板；没有模板才退回通用兜底（兜底不再猜业务线）
    grid_tpl = _load(project / "plan" / "grid.template.json") or {}
    grid = cu.build_grid(clarify, sem, brands or None, template=grid_tpl or None)
    cards = cu.agent_cards(roster.build())
    rows, gaps = cu.assign(grid["cells"], cards)
    # plan 既可能在项目根（report brief 写的），也可能在 plan/ 下
    plan_json = (_load(project / "plan.json")
                 or _load(project / "plan" / "plan.json") or {})
    qmap = {str(m.get("qid")): m for m in (plan_json.get("mapping") or [])}
    by_id = {str(c.get("cell_id")): c for c in grid["cells"]}

    # 2026-11-21 问句优先分配：网格再干净，分错人也白搭。
    # 原来只按能力关键词分，r03/r14 各拿 9 格却横跨 9 个问句，按 plan 裁剪后只剩 1 格。
    # 现在：主格给该问主答角色；边界给 r07、结构给 r13（视角卡）。
    PERSP = {"边界": "r07", "结构": "r13"}
    fixed: List[Dict[str, Any]] = []
    for r in rows:
        cell = by_id.get(str(r.get("cell_id"))) or {}
        m = qmap.get(str(cell.get("qid")))
        if not m:
            fixed.append(r)
            continue
        dim = str(cell.get("dim") or "")
        if dim in PERSP:
            r = {**r, "owner": PERSP[dim], "match": "plan",
                 "why": "视角卡：口径/结构校核"}
        elif m.get("primary"):
            r = {**r, "owner": m["primary"], "match": "plan", "why": "plan 主答"}
        fixed.append(r)

    owned = {str(r.get("cell_id")) for r in fixed}
    for cid, cell in by_id.items():
        if cid in owned:
            continue
        m = qmap.get(str(cell.get("qid")))
        if not m or not m.get("primary"):
            continue
        owner = PERSP.get(str(cell.get("dim")), m["primary"])
        fixed.append({"cell_id": cid, "owner": owner, "why": "plan 主答",
                      "match": "plan", "qid": cell.get("qid")})
    rows = fixed

    # 只保留 plan 里该角色负责的问句；没有 plan 卡的角色（视角卡）保留全部
    allowed = {c.get("role"): set(c.get("questions") or [])
               for c in (plan_json.get("cards") or [])}
    rows = [r for r in rows
            if not allowed.get(r.get("owner"))
            or str(r.get("qid") or by_id.get(str(r.get("cell_id")), {}).get("qid") or "")
            in allowed[r["owner"]]]
    # gaps 按最终归属重算：问句优先分配后，原来「无角色命中」的格已经有主了
    owned_ids = {str(r.get("cell_id")) for r in rows}
    gaps = [{"cell_id": cid, "why": "无 plan 映射且能力未命中"}
            for cid in by_id if cid not in owned_ids]
    by_role: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_role.setdefault(r["owner"], []).append(r)
    # 上限按「问」算，不按「卡」算：SOP 是每 must 问 8–24 格，
    # 一张卡领 3 个问句就该有 3×24 的容量；按卡 24 会把 r05 的 18 格挤进排队。
    BASE_CAP = 24

    def _cap(role: str) -> int:
        qs = allowed.get(role)
        return BASE_CAP * max(1, len(qs)) if qs else BASE_CAP

    kept = {k: v[:_cap(k)] for k, v in by_role.items()}
    queued = {k: v[_cap(k):] for k, v in by_role.items() if len(v) > _cap(k)}
    plan = project / "plan"
    plan.mkdir(parents=True, exist_ok=True)
    cu._w(plan / "grid.json", grid)
    cu._w(plan / "grid_assignment.json", {
        "by_role": {k: [x["cell_id"] for x in v] for k, v in kept.items()},
        "queued": {k: [x["cell_id"] for x in v] for k, v in queued.items()},
        "gaps": gaps, "counts": {k: len(v) for k, v in kept.items()}})

    touched = 0
    for rid, cells in kept.items():
        task = project / "cards" / rid / "TASK.md"
        if not task.is_file():
            continue
        table = "\n".join(
            f"| {c['cell_id']} | {c['dim']} | {c['entity']} | {c['measure']} "
            f"| L{c['depth_target']} | {c['match']} |" for c in cells)
        block = (f"\n\n## 维度网格（你负责的 {len(cells)} 个格子）\n\n"
                 f"| 格子 | 维度 | 对象 | 度量 | 深度 | 匹配 |\n|---|---|---|---|---|---|\n{table}\n\n"
                 f"> 填不了的格写 `unavailable` + 已试来源；**不许跳格、不许合并格**。\n")
        text = task.read_text(encoding="utf-8")
        marker = "## 维度网格（"
        if marker in text:
            text = text.split(marker)[0]
        task.write_text(text.rstrip() + block, encoding="utf-8")
        touched += 1
    return {"ok": True, "grid": grid["count"], "roles": len(by_role),
            "cards": touched, "gaps": len(gaps)}
