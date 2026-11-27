# -*- coding: utf-8 -*-
"""第 2 段 research：证据台账（sources / claims / quotes / gaps）。

原则：
  - 来源分三档：一手（原始数据/官方文档）、二手（转述/媒体）、三手（二手再转述）；
  - 每条来源必须带 URL、日期、≥12 字原文，才能被正文引用；
  - 每个 claim 必须挂至少一条已登记来源，禁止“结论裸奔”。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (THRESHOLDS, TIER_ENUM, ck, claim_numbers, gate,
                     is_date, is_http_url, now_iso)

TIER_LABEL = {"primary": "一手", "secondary": "二手", "tertiary": "三手"}


def build(topic: Dict[str, Any], brief: Dict[str, Any]) -> Dict[str, Any]:
    brief = brief or {}
    raw_sources = [s for s in (brief.get("sources") or []) if isinstance(s, dict)]
    sources: List[Dict[str, Any]] = []
    for i, s in enumerate(raw_sources, 1):
        tier = str(s.get("tier") or "secondary").strip()
        if tier not in TIER_ENUM:
            tier = "tertiary"
        sources.append({
            "id": str(s.get("id") or "s%02d" % i),
            "title": str(s.get("title") or "").strip(),
            "url": str(s.get("url") or "").strip(),
            "date": str(s.get("date") or "").strip(),
            "quote": str(s.get("quote") or "").strip(),
            "tier": tier,
            "tier_label": TIER_LABEL[tier],
        })
    src_ids = {s["id"] for s in sources}

    claims: List[Dict[str, Any]] = []
    for i, f in enumerate([x for x in (brief.get("facts") or []) if isinstance(x, dict)], 1):
        numbers = [str(n) for n in (f.get("numbers") or []) if str(n).strip()]
        claims.append({
            "claim_id": str(f.get("id") or "c%02d" % i),
            "section": str(f.get("section") or "").strip(),
            "statement": str(f.get("statement") or "").strip(),
            "numbers": numbers,
            "source_ids": [str(x) for x in (f.get("source_ids") or []) if str(x).strip()],
            "example": str(f.get("example") or "").strip(),
        })

    quotes: List[Dict[str, Any]] = []
    for s in sources:
        if s["quote"]:
            quotes.append({"source_id": s["id"], "text": s["quote"],
                           "tier": s["tier"]})
    quotes = quotes[:8]

    used_text = " ".join(c["statement"] for c in claims)
    gaps: List[str] = []
    for q in [str(x).strip() for x in (brief.get("questions") or []) if str(x).strip()]:
        if q not in used_text:
            gaps.append(q)
    for s in sources:
        if not is_date(s["date"]) or not is_http_url(s["url"]):
            gaps.append("来源 %s 的日期或 URL 待补全" % s["id"])

    artifact: Dict[str, Any] = {
        "artifact": "research_pack",
        "version": "1.0",
        "generated_at": now_iso(),
        "topic_id": topic.get("selected", ""),
        "topic_title": topic.get("selected_title", ""),
        "sources": sources,
        "claims": claims,
        "quotes": quotes,
        "gaps": gaps,
        "tier_counts": {
            "primary": sum(1 for s in sources if s["tier"] == "primary"),
            "secondary": sum(1 for s in sources if s["tier"] == "secondary"),
            "tertiary": sum(1 for s in sources if s["tier"] == "tertiary"),
        },
        "gate": {},
    }
    artifact["claim_numbers"] = sorted(claim_numbers(artifact))
    artifact["gate"] = check(artifact)
    return artifact


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    sources = artifact.get("sources") or []
    claims = artifact.get("claims") or []
    need = THRESHOLDS["research"]["min_sources"]
    checks.append(ck(len(sources) >= need,
                     "来源数 %d ≥ %d" % (len(sources), need),
                     "research.sources", "CRITICAL" if len(sources) < need else "OK"))
    bad_fields = []
    for s in sources:
        quote_len = len(str(s.get("quote") or ""))
        if not is_http_url(s.get("url")):
            bad_fields.append(s.get("id", "?") + ":url")
        if not is_date(s.get("date")):
            bad_fields.append(s.get("id", "?") + ":date")
        if quote_len < THRESHOLDS["research"]["min_quote"]:
            bad_fields.append(s.get("id", "?") + ":quote")
    checks.append(ck(not bad_fields,
                     "来源字段齐（URL/日期/≥%d 字原文）" % THRESHOLDS["research"]["min_quote"],
                     "research.source_fields",
                     "CRITICAL" if bad_fields else "OK", offenders=bad_fields))
    ids = {str(s.get("id")) for s in sources}
    dangling = [c.get("claim_id") for c in claims
                if not c.get("source_ids") or any(x not in ids for x in c.get("source_ids", []))]
    checks.append(ck(not dangling, "每个 claim 均挂已登记来源",
                     "research.claim_sources",
                     "CRITICAL" if dangling else "OK", offenders=dangling))
    checks.append(ck(len(claims) >= THRESHOLDS["research"]["min_claims"],
                     "claim 数 %d ≥ %d" % (len(claims), THRESHOLDS["research"]["min_claims"]),
                     "research.claims",
                     "CRITICAL" if len(claims) < THRESHOLDS["research"]["min_claims"] else "OK"))
    tiers_ok = all(s.get("tier") in TIER_ENUM for s in sources) and bool(sources)
    graded = all(t in (artifact.get("tier_counts") or {}) for t in TIER_ENUM)
    checks.append(ck(tiers_ok and graded, "三档来源分级齐", "research.tiers",
                     "CRITICAL" if not tiers_ok else "OK"))
    checks.append(ck(bool(artifact.get("quotes")), "至少一条可引用原文",
                     "research.quotes", "CRITICAL"))
    return gate(checks, "research")
