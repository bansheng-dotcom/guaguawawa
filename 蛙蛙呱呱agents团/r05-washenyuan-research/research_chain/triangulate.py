# -*- coding: utf-8 -*-
"""第 5 段 triangulate：把证据合成结论，并记录矛盾。

规则：
- 每条结论必须 ≥2 个独立来源；只有 1 个来源时显式 `single_source=true`，
  且置信度只能是 low；
- 置信度：高 = ≥2 源且 ≥2 层源且全部验证；中 = ≥2 源但层级单一/有未验证；
  低 = 单源或全部未验证；
- 同一子问题、同一单位的数值，极差/中位数 >10% 即记矛盾，不得静默取平均。
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Tuple

from .common import as_number, ck, confidence_rank, gate, sort_ids

SPREAD_THRESHOLD = 0.10


def _series_key(row: Dict[str, Any]) -> str:
    """可比序列键：优先用显式 series；缺省时退化为“子问题|指标|单位”。

    不能只按单位分组——同一子问题下“渗透率%”和“购买意愿%”并不可比，
    把不可比数字判成矛盾会制造伪冲突。
    """
    series = str(row.get("series") or "").strip()
    if series:
        return series
    return "%s|%s|%s" % (row.get("subquestion_id"), row.get("metric") or "",
                         row.get("unit") or "")


def _expected_contradictions(evidence_index: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in evidence_index:
        try:
            value = as_number(row.get("value"))
        except (TypeError, ValueError):
            continue
        key = _series_key(row)
        groups.setdefault(key, []).append({**row, "value": value})
    out: Dict[str, Dict[str, Any]] = {}
    for key, rows in groups.items():
        if len(rows) < 2:
            continue
        values = [r["value"] for r in rows]
        median = statistics.median(values)
        if median == 0:
            continue
        spread = (max(values) - min(values)) / abs(median)
        if spread > SPREAD_THRESHOLD:
            out[key] = {
                "spread_pct": round(spread * 100, 2),
                "values": sorted(rows, key=lambda r: str(r.get("evidence_id"))),
            }
    return out


def check_synthesis(art: Dict[str, Any]) -> Dict[str, Any]:
    """合成门禁：结论可追、置信度合规、矛盾不静默。"""
    conclusions = art.get("conclusions") or []
    contradictions = art.get("contradictions") or []
    index = art.get("evidence_index") or []
    expected = _expected_contradictions(index)
    recorded = {str(c.get("series")): c for c in contradictions}
    checks = [
        ck("tri:conclusions_nonempty", len(conclusions) > 0, "结论不能为空"),
        ck("tri:confidence_enum",
           all(str(c.get("confidence")) in {"high", "medium", "low"} for c in conclusions),
           "置信度只能是 high/medium/low"),
        ck("tri:two_sources_or_single",
           all(len(c.get("source_ids") or []) >= 2 or c.get("single_source") is True
               for c in conclusions), "每条结论 ≥2 源，或显式标 single_source"),
        ck("tri:single_source_low_confidence",
           all(not c.get("single_source") or str(c.get("confidence")) == "low"
               for c in conclusions), "单源结论必须降为 low"),
        ck("tri:evidence_known",
           all(str(e) in {str(r.get("evidence_id")) for r in index}
               for c in conclusions for e in (c.get("evidence_ids") or [])),
           "结论引用的证据必须存在于证据索引"),
        ck("tri:contradictions_recorded",
           set(expected) == set(recorded), "预期矛盾 %d 组，已记录 %d 组"
           % (len(expected), len(recorded))),
        ck("tri:contradiction_status",
           all(str(c.get("status")) in {"open", "resolved"} and str(c.get("resolution"))
               for c in contradictions), "矛盾必须写状态与处置"),
    ]
    return gate(checks)


def build(plan: Dict[str, Any], ledger: Dict[str, Any],
          verification: Dict[str, Any]) -> Dict[str, Any]:
    """按子问题合成结论，产出 synthesis 工件。"""
    status_by_id = {str(r.get("evidence_id")): str(r.get("status"))
                    for r in verification.get("results") or []}
    questions = {str(sq.get("id")): str(sq.get("question")) for sq in plan.get("subquestions") or []}
    evidence_index: List[Dict[str, Any]] = []
    by_sq: Dict[str, List[Dict[str, Any]]] = {}
    for row in ledger.get("entries") or []:
        item = {
            "evidence_id": str(row.get("evidence_id")),
            "subquestion_id": str(row.get("subquestion_id")),
            "source_id": str(row.get("source_id")),
            "source_type": str(row.get("source_type")),
            "series": str(row.get("series") or ""),
            "metric": str(row.get("metric") or ""),
            "value": row.get("value"),
            "unit": str(row.get("unit") or ""),
        }
        evidence_index.append(item)
        by_sq.setdefault(item["subquestion_id"], []).append(item)

    conclusions: List[Dict[str, Any]] = []
    for idx, sq in enumerate(plan.get("subquestions") or [], start=1):
        sid = str(sq.get("id"))
        rows = by_sq.get(sid) or []
        if not rows:
            continue
        source_ids = sort_ids(r["source_id"] for r in rows)
        source_types = sorted({r["source_type"] for r in rows if r["source_type"]})
        verified = sum(1 for r in rows if status_by_id.get(r["evidence_id"]) == "verified")
        single = len(source_ids) < 2
        if single:
            confidence = "low"
        elif len(source_types) >= 2 and verified == len(rows):
            confidence = "high"
        elif verified > 0:
            confidence = "medium"
        else:
            confidence = "low"
        first = rows[0]
        conclusions.append({
            "id": "C%d" % idx,
            "subquestion_id": sid,
            "text": "%s 现有证据支持的判断：%s（%s%s / %s）"
                    % (questions.get(sid, sid), first.get("claim") or "",
                       first.get("value"), first.get("unit"), first.get("period") or "未标"),
            "confidence": confidence,
            "source_ids": source_ids,
            "source_types": source_types,
            "evidence_ids": sort_ids(r["evidence_id"] for r in rows),
            "verified_count": verified,
            "evidence_count": len(rows),
            "single_source": single,
        })
    conclusions.sort(key=lambda c: (confidence_rank(c["confidence"]), c["id"]))

    contradictions: List[Dict[str, Any]] = []
    for series, info in sorted(_expected_contradictions(evidence_index).items()):
        first = info["values"][0]
        contradictions.append({
            "series": series,
            "subquestion_id": first.get("subquestion_id"),
            "metric": first.get("metric"),
            "unit": first.get("unit"),
            "spread_pct": info["spread_pct"],
            "values": [
                {"evidence_id": r["evidence_id"], "value": r["value"],
                 "source_id": r["source_id"]}
                for r in info["values"]
            ],
            "status": "open",
            "resolution": "保留区间并写入报告边界，不取平均",
        })

    art: Dict[str, Any] = {
        "artifact": "synthesis",
        "conclusions": conclusions,
        "contradictions": contradictions,
        "evidence_index": evidence_index,
        "summary": {
            "conclusion_count": len(conclusions),
            "high": sum(1 for c in conclusions if c["confidence"] == "high"),
            "medium": sum(1 for c in conclusions if c["confidence"] == "medium"),
            "low": sum(1 for c in conclusions if c["confidence"] == "low"),
            "single_source": sum(1 for c in conclusions if c["single_source"]),
            "contradiction_count": len(contradictions),
        },
    }
    art["gate"] = check_synthesis(art)
    return art
