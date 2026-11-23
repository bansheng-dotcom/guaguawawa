# -*- coding: utf-8 -*-
"""core.demand —— 从拆卡网格抽「采集需求」（DERIVATION-SOP v4.0 · 第 2 步）。

网格已经把业务拆好了。这里把格子翻译成「要采什么」：

    格子 (measure, grain, dim)  →  需求 {measure, grain, dims, cells}

同一 (度量, 粒度) 的多个实体合并成一条需求——因为采集是按「表」算的，
不是按「实体」算的。

用法：
    from core import demand
    reqs = demand.demand_of(grid, sem)
    errs = demand.validate(reqs)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

SCHEMA = "dsh.demand/v1"


def _grain_of(cell: Dict[str, Any],
              gmap: Optional[Dict[str, List[str]]] = None) -> List[str]:
    """格子 → 粒度维度列表。

    优先用语义层的 `grain_declarations`（那里有权威的 dims），
    因为从 `G_price_band` 按 "_" 硬切会得到 ["price","band"]（错），
    而声明里是 ["channel","category","price_band"]（对）。
    """
    raw = cell.get("grain")
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if str(x).strip()]
    s = str(raw or "")
    if not s:
        return []
    if gmap and s in gmap:
        return list(gmap[s])
    # 兜底：G_brand_channel_year → brand/channel/year
    parts = [p for p in s.split("_")[1:] if p]
    out = []
    for p in parts:
        q = p
        if q.endswith("year"):
            q = "year"
        elif q.endswith("month"):
            q = "month"
        elif q.endswith("quarter"):
            q = "quarter"
        elif q.endswith("week"):
            q = "week"
        out.append(q)
    return out or [s]


def demand_of(grid: Dict[str, Any],
              sem: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """网格 → 需求清单（按 meature × grain 去重）。"""
    cells = (grid or {}).get("cells") or []
    measures = {str(m.get("id")): m
                for m in ((sem or {}).get("case") or {}).get("measures") or []}
    # 语义层是粒度的权威出处：G_price_band → [channel, category, price_band]
    gmap = {str(g.get("id")): [str(x) for x in (g.get("dims") or [])]
            for g in ((sem or {}).get("grain_declarations") or [])}
    buckets: Dict[tuple, Dict[str, Any]] = {}
    for c in cells:
        m = str(c.get("measure") or c.get("measure_id") or "")
        if not m:
            continue
        gr = _grain_of(c, gmap)
        key = (m, tuple(gr))
        b = buckets.setdefault(key, {
            "measure": m,
            "grain": list(gr),
            "dims": set(),
            "entities": set(),
            "cells": [],
            "qids": set(),
            "measure_type": str((measures.get(m) or {}).get("type") or ""),
            "needs_series": any(d in ("year", "month", "quarter", "week", "day")
                                for d in gr),
        })
        b["dims"].add(str(c.get("dim") or ""))
        b["entities"].add(str(c.get("entity") or ""))
        b["cells"].append(str(c.get("cell_id") or ""))
        b["qids"].add(str(c.get("qid") or ""))

    out: List[Dict[str, Any]] = []
    for (m, gr), b in sorted(buckets.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        out.append({
            "measure": b["measure"],
            "grain": b["grain"],
            "dims": sorted(d for d in b["dims"] if d),
            "entities": sorted(e for e in b["entities"] if e),
            "cells": b["cells"],
            "qids": sorted(q for q in b["qids"] if q),
            "cell_count": len(b["cells"]),
            "measure_type": b["measure_type"],
            "needs_series": b["needs_series"],
        })
    return {
        "schema": SCHEMA,
        "demands": out,
        "count": len(out),
        "cells_total": len(cells),
        "covers_cells": sum(x["cell_count"] for x in out),
    }


def validate(reqs: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(reqs, dict):
        return ["需求清单必须是 dict"]
    if reqs.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    ds = reqs.get("demands") or []
    if not ds:
        errs.append("需求为空（网格没有可用格子）")
    for i, d in enumerate(ds):
        if not d.get("measure"):
            errs.append("demands[%d] 缺 measure" % i)
        if not d.get("grain"):
            errs.append("demands[%d] 缺 grain" % i)
        if int(d.get("cell_count") or 0) <= 0:
            errs.append("demands[%d] 没有关联格子" % i)
    # 覆盖性：需求覆盖的格子数应等于网格格子数（不漏格）
    if reqs.get("cells_total") and reqs.get("covers_cells") != reqs.get("cells_total"):
        errs.append("需求覆盖 %s 格，网格有 %s 格（有格子没进需求）"
                    % (reqs.get("covers_cells"), reqs.get("cells_total")))
    return errs
