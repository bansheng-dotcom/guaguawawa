# -*- coding: utf-8 -*-
"""core.card_plan —— 自适应分卡（SOP v5：按问题簇，而不是按角色/固定张数）。

规则：
    1. 先按 qid 聚成「问题簇」；
    2. 簇内格子 > 单卡容量（默认 24）→ 按维度再拆；
    3. 每个簇按能力匹配派给角色；一个角色可拿多张，单角色同时最多 load_cap 张；
    4. 没有角色能接 → 缺口（R02 路由）。

卡数是算出来的：Σ ceil(簇格数 / 容量)，不是写死 7 张。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

DEFAULT_CAP = 24
DEFAULT_LOAD = 3


def cluster(cells: List[Dict[str, Any]], cap: int = DEFAULT_CAP) -> List[Dict[str, Any]]:
    by_q: Dict[str, List[Dict[str, Any]]] = {}
    for c in cells or []:
        by_q.setdefault(str(c.get("qid") or "Q?"), []).append(c)
    out: List[Dict[str, Any]] = []
    for qid, cs in by_q.items():
        if len(cs) <= cap:
            out.append({"card_id": qid, "qid": qid, "cells": cs, "split": False})
            continue
        by_dim: Dict[str, List[Dict[str, Any]]] = {}
        for c in cs:
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
        from core import card_upgrade as cu
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
