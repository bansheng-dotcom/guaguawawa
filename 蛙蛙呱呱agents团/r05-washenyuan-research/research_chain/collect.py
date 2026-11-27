# -*- coding: utf-8 -*-
"""第 3 段 collect：把候选源落成证据台账。

每条证据必须同时具备三要素：可直接回抓的 `url`、发布/口径 `date`、原文 `quote`；
并补齐 `claim/value/unit/period`，否则不能进入三角验证。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import as_number, ck, gate, nonempty

REQUIRED = ["evidence_id", "subquestion_id", "source_id", "claim",
            "value", "unit", "period", "url", "date", "quote"]


def check_ledger(art: Dict[str, Any]) -> Dict[str, Any]:
    """证据台账门禁：字段完整、三要素齐、来源/子问题可追。"""
    rows = art.get("entries") or []
    known_sources = set(art.get("known_source_ids") or [])
    known_sq = set(art.get("known_subquestion_ids") or [])
    ids = [str(r.get("evidence_id") or "") for r in rows]
    numeric_ok = True
    for r in rows:
        try:
            as_number(r.get("value"))
        except (TypeError, ValueError):
            numeric_ok = False
            break
    checks = [
        ck("collect:ledger_nonempty", len(rows) > 0, "证据台账不能为空"),
        ck("collect:field_complete",
           all(all(nonempty(r.get(k)) for k in REQUIRED) for r in rows),
           "每条证据十字段必须齐全"),
        ck("collect:three_elements",
           all(nonempty(r.get("url")) and nonempty(r.get("date"))
               and nonempty(r.get("quote")) for r in rows),
           "url/date/quote 三要素缺一不可"),
        ck("collect:value_numeric", numeric_ok, "value 必须是数字"),
        ck("collect:source_known",
           all(str(r.get("source_id")) in known_sources for r in rows),
           "证据必须引用源地图里存在的 source id"),
        ck("collect:subquestion_known",
           all(str(r.get("subquestion_id")) in known_sq for r in rows),
           "证据必须挂在已声明的子问题上"),
        ck("collect:unique_ids", len(ids) == len(set(ids)), "证据 id 不能重复"),
    ]
    return gate(checks)


def build(plan: Dict[str, Any], source_map: Dict[str, Any],
          evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按源地图与计划归集证据，产出证据台账。"""
    source_type: Dict[str, str] = {}
    known_sources: List[str] = []
    for entry in source_map.get("entries") or []:
        for cand in entry.get("candidates") or []:
            sid = str(cand.get("id") or "")
            source_type[sid] = str(cand.get("type") or "")
            known_sources.append(sid)
    known_sq = [str(sq.get("id")) for sq in plan.get("subquestions") or []]

    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(evidence, start=1):
        sid = str(raw.get("source_id") or "")
        rows.append({
            "evidence_id": str(raw.get("evidence_id") or raw.get("claim_id") or "E%02d" % idx),
            "subquestion_id": str(raw.get("subquestion_id") or ""),
            "source_id": sid,
            "source_type": source_type.get(sid, ""),
            "claim": str(raw.get("claim") or ""),
            "series": str(raw.get("series") or ""),
            "metric": str(raw.get("metric") or ""),
            "value": raw.get("value"),
            "unit": str(raw.get("unit") or ""),
            "period": str(raw.get("period") or ""),
            "url": str(raw.get("url") or ""),
            "date": str(raw.get("date") or ""),
            "quote": str(raw.get("quote") or ""),
        })

    art: Dict[str, Any] = {
        "artifact": "evidence_ledger",
        "entries": rows,
        "known_source_ids": sorted(set(known_sources)),
        "known_subquestion_ids": known_sq,
        "summary": {
            "count": len(rows),
            "by_subquestion": {sid: sum(1 for r in rows if r["subquestion_id"] == sid)
                               for sid in known_sq},
            "by_source_type": {
                t: sum(1 for r in rows if r["source_type"] == t)
                for t in sorted({r["source_type"] for r in rows if r["source_type"]})
            },
        },
    }
    art["gate"] = check_ledger(art)
    return art
