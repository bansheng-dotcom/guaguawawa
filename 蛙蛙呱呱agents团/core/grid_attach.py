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
    grid = cu.build_grid(clarify, sem, cu._brands(pack))
    cards = cu.agent_cards(roster.build())
    rows, gaps = cu.assign(grid["cells"], cards)
    by_role: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_role.setdefault(r["owner"], []).append(r)
    # 一张卡最多 24 格（SOP 上限），其余排队下一批；不能让一张卡变成 80 行的表
    CAP = 24
    kept = {k: v[:CAP] for k, v in by_role.items()}
    queued = {k: v[CAP:] for k, v in by_role.items() if len(v) > CAP}
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
            f"| L{c['depth_target']} | {c['match']} |" for c in cells[:24])
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
