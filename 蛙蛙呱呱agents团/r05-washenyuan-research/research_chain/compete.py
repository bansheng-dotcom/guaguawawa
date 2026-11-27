# -*- coding: utf-8 -*-
"""第 7 段 compete：5 家 × 8 维竞品矩阵 + battlecard + 五力 + 份额。

硬约束：
- 矩阵固定 8 个维度、5 家竞品，每格必须有 value 与可追的 source_id；
- 每家必须有 battlecard（定位/威胁/打法）；
- 五力各一条，评分只能是 low/medium/high，并挂来源；
- 份额合计不得超过 100%，且与 size 段的 p50 口径一致（runner 跨段校验）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import as_number, ck, gate, nonempty

RATINGS = {"low", "medium", "high"}


def check_competition(art: Dict[str, Any]) -> Dict[str, Any]:
    """竞争格局门禁：矩阵完整、逐格有源、五力与份额可追。"""
    dims = [str(d) for d in art.get("dimensions") or []]
    players = art.get("competitors") or []
    known = set(art.get("known_source_ids") or [])
    shares = art.get("shares") or []
    forces = art.get("five_forces") or []

    def _cells_ok() -> bool:
        for p in players:
            cells = p.get("cells") or {}
            for d in dims:
                cell = cells.get(d) or {}
                if not nonempty(cell.get("value")):
                    return False
                if str(cell.get("source_id")) not in known:
                    return False
        return True

    share_values = []
    share_ok = True
    for item in shares:
        try:
            value = as_number(item.get("share"))
        except (TypeError, ValueError):
            share_ok = False
            break
        share_values.append(value)
        if str(item.get("source_id")) not in known:
            share_ok = False
            break

    checks = [
        ck("compete:dimensions_8", len(dims) == 8 and len(set(dims)) == 8,
           "维度数=%d，要求恰好 8 个且不重复" % len(dims)),
        ck("compete:competitors_5", len(players) == 5, "竞品数=%d，要求 5 家" % len(players)),
        ck("compete:unique_players",
           len({str(p.get("name") or "") for p in players}) == len(players),
           "竞品名不能重复"),
        ck("compete:matrix_complete",
           all(all(d in (p.get("cells") or {}) for d in dims) for p in players),
           "每家竞品必须覆盖全部维度"),
        ck("compete:cell_source", _cells_ok(), "每格必须有值且 source_id 可追"),
        ck("compete:battlecard",
           all(all(nonempty((p.get("battlecard") or {}).get(k))
                   for k in ("positioning", "threat", "attack")) for p in players),
           "每家必须有定位/威胁/打法三段 battlecard"),
        ck("compete:five_forces",
           len(forces) == 5 and all(
               nonempty(f.get("force")) and str(f.get("rating")) in RATINGS
               and nonempty(f.get("rationale"))
               and str(f.get("source_id")) in known for f in forces),
           "五力必须各一条、评分合规、理由与来源齐全"),
        ck("compete:shares",
           len(shares) == 5 and share_ok and len(share_values) == 5
           and all(0 < v <= 100 for v in share_values)
           and sum(share_values) <= 100.5,
           "5 家份额必须为正且合计 ≤100%"),
        ck("compete:market_size",
           float(art.get("market_size") or 0) > 0,
           "必须写市场口径规模，供跨段一致性校验"),
    ]
    return gate(checks)


def build(competition: Dict[str, Any], source_map: Dict[str, Any],
          ledger: Dict[str, Any]) -> Dict[str, Any]:
    """归集竞品情报，产出 competition 工件。"""
    known_sources: List[str] = []
    for entry in source_map.get("entries") or []:
        for cand in entry.get("candidates") or []:
            known_sources.append(str(cand.get("id") or ""))
    known_sources = sorted(set(known_sources))

    dims = [str(d) for d in competition.get("dimensions") or []]
    players: List[Dict[str, Any]] = []
    for raw in competition.get("competitors") or []:
        cells: Dict[str, Dict[str, Any]] = {}
        for dim in dims:
            cell = (raw.get("cells") or {}).get(dim) or {}
            cells[dim] = {"value": str(cell.get("value") or ""),
                          "source_id": str(cell.get("source_id") or "")}
        card = raw.get("battlecard") or {}
        players.append({
            "name": str(raw.get("name") or ""),
            "cells": cells,
            "battlecard": {
                "positioning": str(card.get("positioning") or ""),
                "threat": str(card.get("threat") or ""),
                "attack": str(card.get("attack") or ""),
            },
        })
    forces = [{
        "force": str(f.get("force") or ""),
        "rating": str(f.get("rating") or ""),
        "rationale": str(f.get("rationale") or ""),
        "source_id": str(f.get("source_id") or ""),
    } for f in competition.get("five_forces") or []]
    shares = [{
        "player": str(s.get("player") or ""),
        "share": s.get("share"),
        "source_id": str(s.get("source_id") or ""),
    } for s in competition.get("shares") or []]

    art: Dict[str, Any] = {
        "artifact": "competition",
        "dimensions": dims,
        "competitors": players,
        "five_forces": forces,
        "shares": shares,
        "market_size": competition.get("market_size"),
        "market_size_source": str(competition.get("market_size_source") or ""),
        "known_source_ids": known_sources,
        "summary": {
            "competitor_count": len(players),
            "dimension_count": len(dims),
            "share_sum": round(sum(as_number(s.get("share")) for s in shares
                                   if s.get("share") is not None), 2),
            "five_forces_high": sum(1 for f in forces if f["rating"] == "high"),
            "ledger_evidence_used": len({cell["source_id"] for p in players
                                         for cell in p["cells"].values()}),
        },
    }
    art["gate"] = check_competition(art)
    return art
