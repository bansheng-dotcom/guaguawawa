# -*- coding: utf-8 -*-
"""第 2 段 source：为每个子问题建立源地图。

源类型（一手/二手/三手/数据库）：
- primary：原始数据/官方统计/官网页面/一线访谈；
- secondary：券商、咨询、媒体对原始数据的加工；
- tertiary：概览、榜单、聚合站等三手转述；
- database：付费数据库/终端。
每个候选必须写清载体（官网/报告/新闻/访谈/电商/数据库）与可访问性
（open/paid/restricted/offline），否则下游无法复核。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import ck, gate, nonempty

TYPE_ORDER = ["primary", "secondary", "tertiary", "database"]
ACCESSIBILITY = {"open", "paid", "restricted", "offline"}


def _flat(art: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for entry in art.get("entries") or []:
        rows.extend(entry.get("candidates") or [])
    return rows


def check_source_map(art: Dict[str, Any]) -> Dict[str, Any]:
    """源地图门禁：数量、层级、字段、覆盖、唯一性。"""
    rows = _flat(art)
    types = {str(r.get("type") or "") for r in rows}
    ids = [str(r.get("id") or "") for r in rows]
    sq_ids = [str(e.get("subquestion_id") or "") for e in art.get("entries") or []]
    checks = [
        ck("source:candidate_count", len(rows) >= 10, "候选源=%d，要求 ≥10" % len(rows)),
        ck("source:type_diversity", len(types & set(TYPE_ORDER)) >= 3,
           "源层级=%s，要求 ≥3 类" % ",".join(sorted(t for t in types if t))),
        ck("source:tier_coverage",
           {"primary", "secondary", "tertiary"} <= types,
           "必须同时有一手/二手/三手，不能只靠二手转述"),
        ck("source:candidate_fields",
           all(all(nonempty(r.get(k)) for k in
                   ("id", "title", "type", "carrier", "accessibility", "url", "date"))
               for r in rows), "候选源七要素必须齐全"),
        ck("source:subquestion_coverage",
           all(any(r.get("subquestion_id") == sid for r in rows) for sid in sq_ids),
           "每个子问题至少 1 个候选源"),
        ck("source:unique_ids", len(ids) == len(set(ids)), "源 id 不能重复"),
        ck("source:accessibility_enum",
           all(str(r.get("accessibility")) in ACCESSIBILITY for r in rows),
           "可访问性必须是 open/paid/restricted/offline"),
    ]
    return gate(checks)


def build(plan: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按子问题归集候选源，产出源地图工件。"""
    entries: List[Dict[str, Any]] = []
    flat: List[Dict[str, Any]] = []
    for sq in plan.get("subquestions") or []:
        sid = str(sq.get("id"))
        candidates = []
        for raw in sources:
            if str(raw.get("subquestion_id") or "") != sid:
                continue
            item = {
                "id": str(raw.get("id") or ""),
                "title": str(raw.get("title") or ""),
                "type": str(raw.get("type") or ""),
                "carrier": str(raw.get("carrier") or ""),
                "accessibility": str(raw.get("accessibility") or ""),
                "url": str(raw.get("url") or ""),
                "date": str(raw.get("date") or ""),
                "publisher": str(raw.get("publisher") or ""),
                "subquestion_id": sid,
            }
            candidates.append(item)
            flat.append(item)
        entries.append({"subquestion_id": sid, "candidates": candidates})

    types = sorted({r["type"] for r in flat if r["type"] in TYPE_ORDER},
                   key=TYPE_ORDER.index)
    art: Dict[str, Any] = {
        "artifact": "source_map",
        "entries": entries,
        "summary": {
            "candidate_count": len(flat),
            "type_count": len(types),
            "types": types,
            "carriers": sorted({r["carrier"] for r in flat if r["carrier"]}),
            "accessibility": sorted({r["accessibility"] for r in flat}),
        },
    }
    art["gate"] = check_source_map(art)
    return art
