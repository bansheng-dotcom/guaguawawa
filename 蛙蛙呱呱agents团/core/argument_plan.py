# -*- coding: utf-8 -*-
"""core.argument_plan —— 每节先定 claim tree 与论证类型，再写正文。

目标：20 节不共用一套三段模板；同类型不能连续超过 2 节。
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

TYPES = ("causal", "tradeoff", "counterintuitive", "path", "risk", "scenario", "comparison")

RULES = (
    ("规模", "causal"), ("增速", "causal"), ("周期", "causal"),
    ("覆盖", "comparison"), ("结构", "comparison"), ("版图", "comparison"),
    ("渠道", "tradeoff"), ("层级", "tradeoff"), ("价格", "tradeoff"), ("成本", "tradeoff"),
    ("竞争", "counterintuitive"),
    ("风险", "risk"),
    ("情景", "scenario"),
    ("路径", "path"), ("前置", "path"), ("健康", "path"),
)


def choose_type(kicker: str, prev: List[str]) -> str:
    for key, typ in RULES:
        if key in (kicker or "") and not (len(prev) >= 2 and prev[-1] == prev[-2] == typ):
            return typ
    for typ in TYPES:
        if not (len(prev) >= 2 and prev[-1] == prev[-2] == typ):
            return typ
    return "comparison"


def plan(sections: Iterable[Dict[str, Any]], graph: Dict[str, Any]) -> Dict[str, Any]:
    claims = {c.get("section"): c for c in graph.get("claims", [])}
    out = []
    prev: List[str] = []
    for s in sections:
        typ = choose_type(s.get("kicker", ""), prev)
        prev.append(typ)
        c = claims.get(s["id"], {})
        out.append({
            "id": s["id"], "type": typ, "kicker": s.get("kicker", ""),
            "main": c.get("id"), "claim": c.get("text"),
            "supports": [e.get("source_id") for e in c.get("evidence", [])
                         if e.get("stance") == "supports"],
            "rival": c.get("rival"), "discriminator": c.get("discriminator"),
            "action": c.get("action"), "boundary": c.get("boundary"),
        })
    return {"schema": "dsh.argument_plan/v1", "sections": out}


def validate(p: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    secs = p.get("sections", [])
    if len({x.get("type") for x in secs}) < 5:
        errs.append("论证类型少于 5 种")
    for i in range(2, len(secs)):
        if secs[i].get("type") == secs[i - 1].get("type") == secs[i - 2].get("type"):
            errs.append(f"{secs[i]['id']}: 同类型连续 3 节")
    for x in secs:
        for k in ("main", "rival", "discriminator", "boundary"):
            if not x.get(k):
                errs.append(f"{x['id']}: 缺 {k}")
    return errs
