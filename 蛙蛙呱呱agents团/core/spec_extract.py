# -*- coding: utf-8 -*-
"""core.spec_extract —— EvidenceGraph → prose specs。

每个字段只从 claim/evidence 取，不自由补数字；冲突 claim 进 review_queue。
"""
from __future__ import annotations

from typing import Any, Dict, List


def extract(graph: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for c in graph.get("claims", []):
        sid = c.get("section")
        if not sid:
            continue
        supports = [e for e in c.get("evidence", []) if e.get("stance") == "supports"]
        contradicts = [e for e in c.get("evidence", []) if e.get("stance") == "contradicts"]
        quotes = "；".join(e.get("quote", "") for e in supports)
        out[sid] = {
            "verdict": c.get("text", ""),
            "fact": c.get("text", ""),
            "evidence": quotes,
            "mechanism": c.get("mechanism", ""),
            "alternative": c.get("rival", ""),
            "signal": c.get("discriminator", ""),
            "action": c.get("action", ""),
            "boundary": c.get("boundary", ""),
            "review": "contradicts:" + contradicts[0].get("quote", "") if contradicts else "",
        }
    return out


def review_queue(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    q = []
    for c in graph.get("claims", []):
        bad = [e for e in c.get("evidence", []) if e.get("stance") == "contradicts"]
        if bad:
            q.append({"claim": c.get("id"), "section": c.get("section"),
                      "contradicts": [e.get("quote") for e in bad]})
    return q
