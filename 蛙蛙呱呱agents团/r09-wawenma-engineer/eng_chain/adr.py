# -*- coding: utf-8 -*-
"""第 1 段 ADR：需求与约束 → 架构决策记录 + 模块边界 + 取舍。

只回答三件事：为什么做这个决定、决定之后谁负责什么、代价是什么。
不做技术选型之外的实现细节；实现交给 api/feature 段。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_list, nonempty_str,
                     render_stage)


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    req = brief.get("requirements") or {}
    options = req.get("options") or []
    chosen = req.get("decision") or (options[0].get("name") if options else "")
    picked = next((o for o in options if o.get("name") == chosen), {})
    tradeoffs = brief.get("tradeoffs") or []
    art: Dict[str, Any] = {
        "artifact": "adr",
        "stage": "adr",
        "project": brief.get("project", ""),
        "number": (brief.get("adr") or {}).get("number", "ADR-001"),
        "title": f"{brief.get('project', '项目')} 架构决策记录",
        "status": (brief.get("adr") or {}).get("status", "accepted"),
        "context": {
            "problem": req.get("problem", ""),
            "constraints": req.get("constraints") or [],
        },
        "options": [
            {"name": o.get("name", ""), "pros": o.get("pros") or [],
             "cons": o.get("cons") or []}
            for o in options
        ],
        "decision": {
            "chosen": chosen,
            "rationale": req.get("rationale") or "；".join(req.get("constraints") or []),
        },
        "consequences": {
            "positive": picked.get("pros") or [],
            "negative": picked.get("cons") or [],
            "risks": [t.get("cost", "") for t in tradeoffs if t.get("cost")],
        },
        "boundaries": [
            {"module": m.get("name", ""), "owns": m.get("owns", ""),
             "does_not_own": m.get("does_not_own", "")}
            for m in (brief.get("modules") or [])
        ],
        "tradeoffs": [
            {"choice": t.get("choice", ""), "gain": t.get("gain", ""),
             "cost": t.get("cost", ""), "mitigation": t.get("mitigation", "")}
            for t in tradeoffs
        ],
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """ADR 门禁：背景、选项、决定、边界、取舍五项缺一不可。"""
    ctx = art.get("context") or {}
    options = art.get("options") or []
    decision = art.get("decision") or {}
    boundaries = art.get("boundaries") or []
    tradeoffs = art.get("tradeoffs") or []
    names = [o.get("name") for o in options]
    checks = [
        ck(nonempty_str(ctx.get("problem")) and len(ctx.get("constraints") or []) >= 2,
           "背景问题与至少 2 条约束", "adr:context", "CRITICAL"),
        ck(len(options) >= 2 and all(nonempty_str(o.get("name")) and
                                     o.get("pros") and o.get("cons") for o in options),
           "至少 2 个候选方案且各有利弊", "adr:options", "CRITICAL"),
        ck(decision.get("chosen") in names and nonempty_str(decision.get("rationale")),
           "决定必须来自候选项并有理由", "adr:decision", "CRITICAL"),
        ck(len(boundaries) >= 2 and all(nonempty_str(b.get("module")) and
                                        nonempty_str(b.get("owns")) and
                                        nonempty_str(b.get("does_not_own"))
                                        for b in boundaries),
           "模块边界必须写清 owns / does_not_own", "adr:boundaries", "CRITICAL"),
        ck(len(tradeoffs) >= 2 and all(nonempty_str(t.get("gain")) and
                                       nonempty_str(t.get("cost")) for t in tradeoffs),
           "至少 2 条取舍（收益 vs 代价）", "adr:tradeoffs", "CRITICAL"),
    ]
    return gate(checks, "adr")


def render(art: Dict[str, Any]) -> str:
    d = art.get("decision") or {}
    c = art.get("consequences") or {}
    opt_rows = [[o.get("name"), "；".join(o.get("pros") or []),
                 "；".join(o.get("cons") or [])] for o in art.get("options") or []]
    bnd_rows = [[b.get("module"), b.get("owns"), b.get("does_not_own")]
                for b in art.get("boundaries") or []]
    tr_rows = [[t.get("choice"), t.get("gain"), t.get("cost"), t.get("mitigation")]
               for t in art.get("tradeoffs") or []]
    summary = (f"**背景**：{art.get('context', {}).get('problem', '')}\n\n"
               f"**决定**：{d.get('chosen', '')} —— {d.get('rationale', '')}\n\n"
               f"**后果**：正向 {'；'.join(c.get('positive') or [])}；"
               f"负向 {'；'.join(c.get('negative') or [])}")
    tables = [
        "## 候选方案", "", md_table(["方案", "优点", "代价"], opt_rows),
        "", "## 模块边界", "", md_table(["模块", "负责", "不负责"], bnd_rows),
        "", "## 取舍台账", "", md_table(["选择", "收益", "代价", "缓解"], tr_rows),
    ]
    return render_stage(art, summary, tables)
