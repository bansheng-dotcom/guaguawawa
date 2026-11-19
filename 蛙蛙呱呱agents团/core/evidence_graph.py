# -*- coding: utf-8 -*-
"""core.evidence_graph —— claim → source → quote → span 的可追溯证据图。

规则（与 docs/REPORT-SYSTEM-UPGRADE-SOP.md 一致）：
- 每个 claim 至少 1 条 supports；
- stance ∈ supports/contradicts/context；
- claim 里的数字必须能在 quote 中找到（estimated 的派生数除外）；
- 缺 rival/discriminator/boundary 的 claim 不能进 argument plan。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

SCHEMA = "dsh.evidence_graph/v1"
STANCES = ("supports", "contradicts", "context")
NUM = re.compile(r"\d+(?:\.\d+)?")


def _nums(text: str) -> List[str]:
    return NUM.findall(text or "")


def build(sources: Iterable[Dict[str, Any]], claims: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {"schema": SCHEMA, "sources": list(sources), "claims": list(claims)}


def validate(graph: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    src = {s.get("id"): s for s in graph.get("sources", [])}
    for c in graph.get("claims", []):
        cid = c.get("id") or "?"
        ev = c.get("evidence") or []
        if not ev:
            errors.append(f"{cid}: 无 evidence")
            continue
        if not any(e.get("stance") == "supports" for e in ev):
            errors.append(f"{cid}: 无 supports")
        for e in ev:
            if e.get("source_id") not in src:
                errors.append(f"{cid}: 来源不存在 {e.get('source_id')}")
            if e.get("stance") not in STANCES:
                errors.append(f"{cid}: stance 非法 {e.get('stance')}")
            if not e.get("quote"):
                errors.append(f"{cid}: 缺 quote")
        for k in ("rival", "discriminator", "boundary"):
            if not c.get(k):
                errors.append(f"{cid}: 缺 {k}")
    return errors


def audit_text(text: str, graph: Dict[str, Any]) -> Dict[str, Any]:
    """正文里的数字必须能在 claim 的 quote 中找到；estimated claim 允许派生。"""
    quotes = " ".join(
        e.get("quote", "") for c in graph.get("claims", []) for e in c.get("evidence", [])
    )
    allowed = set(_nums(quotes))
    for c in graph.get("claims", []):
        if c.get("estimated"):
            allowed.update(_nums(c.get("text", "")))
    missing = [n for n in _nums(text) if n not in allowed]
    return {"ok": not missing, "missing": sorted(set(missing)),
            "numbers": len(_nums(text)), "quoted": len(allowed)}


def traceability(graph: Dict[str, Any]) -> Dict[str, Any]:
    total = supported = 0
    for c in graph.get("claims", []):
        for n in _nums(c.get("text", "")):
            total += 1
            if any(n in e.get("quote", "") for e in c.get("evidence", [])):
                supported += 1
    return {"claims": len(graph.get("claims", [])),
            "numbers": total, "supported": supported,
            "rate": round(supported / total, 3) if total else 1.0}
