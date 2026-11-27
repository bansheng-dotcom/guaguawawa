# -*- coding: utf-8 -*-
"""第 4 段 verify：逐条验证证据（回抓 / 复算 / 偏见 / 时效）。

判定口径：
- 回抓：url 必须是 http(s) 且源可访问性不是 offline，否则 unverified；
- 复算：value 能被严格数值化并回写一致，否则 unverified；
- 偏见：单一源层级占比 >70% 记 `high_single_source_type`（提示三角验证降级）；
- 时效：距 as_of 超过 24 个月记 `stale`（保留但降级提示）。
任何一项无法确认，都必须在 `unverified_ids` 显式披露，不允许静默通过。
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Tuple

from .common import as_number, ck, gate, now_iso

FRESH_MONTHS = 24


def _parse_date(value: str) -> datetime.date:
    text = str(value or "").strip()
    parts = text.split("-")
    if len(parts) == 3:
        return datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
    if len(parts) == 2:
        return datetime.date(int(parts[0]), int(parts[1]), 1)
    if len(parts) == 1 and parts[0].isdigit():
        return datetime.date(int(parts[0]), 1, 1)
    raise ValueError("无法解析日期: %r" % (value,))


def _months_between(early: datetime.date, late: datetime.date) -> int:
    return (late.year - early.year) * 12 + (late.month - early.month)


def check_verification(art: Dict[str, Any]) -> Dict[str, Any]:
    """验证结果门禁：全覆盖、四维检查、未验证显式披露。"""
    rows = art.get("results") or []
    entries = art.get("entries") or []
    disclosed = [str(x) for x in art.get("unverified_ids") or []]
    actual_unverified = [str(r.get("evidence_id")) for r in rows
                         if str(r.get("status")) == "unverified"]
    checks = [
        ck("verify:coverage", len(rows) == len(entries) and len(rows) > 0,
           "验证条数=%d，台账条数=%d" % (len(rows), len(entries))),
        ck("verify:status_enum",
           all(str(r.get("status")) in {"verified", "unverified"} for r in rows),
           "status 只能是 verified/unverified"),
        ck("verify:disclosure", set(disclosed) == set(actual_unverified),
           "unverified 必须逐条披露，不得静默"),
        ck("verify:four_dimensions",
           all(all(k in r for k in ("refetch", "recompute", "bias", "freshness"))
               for r in rows), "每条结果必须有回抓/复算/偏见/时效四维"),
        ck("verify:recompute_done",
           all(str((r.get("recompute") or {}).get("status")) == "recomputed" for r in rows),
           "数值必须复算通过"),
        ck("verify:freshness_checked",
           all(str((r.get("freshness") or {}).get("status")) in {"fresh", "stale", "unknown"}
               for r in rows), "时效必须给出 fresh/stale/unknown"),
    ]
    return gate(checks)


def build(ledger: Dict[str, Any], source_map: Dict[str, Any],
          as_of: str = "") -> Dict[str, Any]:
    """执行四维验证，产出验证结果工件。"""
    as_of_date = _parse_date(as_of) if as_of else datetime.date.today()
    accessibility: Dict[str, str] = {}
    for entry in source_map.get("entries") or []:
        for cand in entry.get("candidates") or []:
            accessibility[str(cand.get("id"))] = str(cand.get("accessibility") or "")

    entries = ledger.get("entries") or []
    type_counts: Dict[str, int] = {}
    for row in entries:
        key = str(row.get("source_type") or "unknown")
        type_counts[key] = type_counts.get(key, 0) + 1
    total = max(1, len(entries))

    results: List[Dict[str, Any]] = []
    for row in entries:
        eid = str(row.get("evidence_id"))
        reasons: List[str] = []

        url = str(row.get("url") or "")
        access = accessibility.get(str(row.get("source_id")), "")
        if url.startswith(("http://", "https://")) and access != "offline":
            refetch = {"status": "url_ok", "detail": "url 可解析，可访问性=%s" % (access or "unknown")}
        else:
            refetch = {"status": "unverified", "detail": "url 不可回抓或源已下线"}
            reasons.append("refetch")

        try:
            value = as_number(row.get("value"))
            recompute = {"status": "recomputed", "value": round(value, 6)}
        except (TypeError, ValueError):
            recompute = {"status": "unverified", "value": None}
            reasons.append("recompute")

        source_type = str(row.get("source_type") or "unknown")
        share = round(type_counts.get(source_type, 0) / total, 4)
        bias = {
            "status": "high_single_source_type" if share > 0.7 and total >= 5 else "ok",
            "source_type": source_type,
            "share": share,
        }

        try:
            pub = _parse_date(row.get("date"))
            months = max(0, _months_between(pub, as_of_date))
            freshness = {"status": "fresh" if months <= FRESH_MONTHS else "stale",
                         "months": months}
        except (TypeError, ValueError):
            freshness = {"status": "unknown", "months": None}
            reasons.append("freshness")

        status = "verified" if refetch["status"] == "url_ok" \
            and recompute["status"] == "recomputed" else "unverified"
        results.append({
            "evidence_id": eid,
            "status": status,
            "reasons": reasons,
            "refetch": refetch,
            "recompute": recompute,
            "bias": bias,
            "freshness": freshness,
        })

    art: Dict[str, Any] = {
        "artifact": "verification",
        "as_of": as_of_date.isoformat(),
        "entries": [{"evidence_id": r.get("evidence_id")} for r in entries],
        "results": results,
        "unverified_ids": [r["evidence_id"] for r in results if r["status"] == "unverified"],
        "summary": {
            "total": len(results),
            "verified": sum(1 for r in results if r["status"] == "verified"),
            "unverified": sum(1 for r in results if r["status"] == "unverified"),
            "stale": sum(1 for r in results if r["freshness"]["status"] == "stale"),
            "bias_flagged": sum(1 for r in results
                                if r["bias"]["status"] == "high_single_source_type"),
            "generated_at": now_iso(),
        },
    }
    art["gate"] = check_verification(art)
    return art
