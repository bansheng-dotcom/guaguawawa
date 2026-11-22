# -*- coding: utf-8 -*-
"""core.semantic_pipeline —— 一条语义管道（SOP v3.0 S5a）。

把 IR 解析成「已解析报告模型」：纯函数，不碰渲染器。
两个薄发射器（report_renderer / kit）将来只消费这个模型的输出，不重算语义。

本管道只做语义（schema 校验 + 图表意图解析），不做排版：
  - schema 校验：report_ir.validate（parse-time 字段级）
  - 图表意图：relation（缺则从 question 推断）→ chosen（缺则取候选第一个）→
               chart_candidates.validate（合法/可行 + suggest）
  - 文案生成、payload（bars/rows/points）解析留给后续步骤（S5b/c）
"""
from __future__ import annotations

from typing import Any, Dict, List

from core import chart_candidates, report_ir
from core.report_ir import IR_SCHEMA


def _resolve_chart(chart: Dict[str, Any], question: str) -> Dict[str, Any]:
    relation = str(chart.get("relation") or "")
    if not relation:
        relation = report_ir.infer_relation(question, chart.get("dims"))
    chosen = str(chart.get("chosen") or "")
    contract: Dict[str, Any] = {
        "relation": relation,
        "chosen": chosen,
        "dims": list(chart.get("dims") or []),
        "data_refs": list(chart.get("data_refs") or []),
    }
    if not chosen:
        cands = chart_candidates.candidates(contract)
        chosen = cands[0]["type"] if cands else "hbar"
        contract["chosen"] = chosen
    validation = chart_candidates.validate(contract)
    return {**chart, "relation": relation, "chosen": chosen,
            "chart_validation": validation}


def resolve(ir: Dict[str, Any], overrides: Dict[str, Dict[str, str]] | None = None) -> Dict[str, Any]:
    """IR → 已解析模型。schema 错误 + 每节图表意图（relation/chosen/validation）。

    overrides: 作者在候选面板上的确认/覆盖，形如 {section_index: {"relation": .., "chosen": ..}}
               这是 SOP §5「候选确认，作者覆盖」的接口（编译器的 escape hatch）。
    """
    schema_errs = report_ir.validate(ir)
    overrides = overrides or {}
    sections: List[Dict[str, Any]] = []
    for idx, s in enumerate(ir.get("sections") or []):
        chart = dict(s.get("chart") or {})
        for k in ("relation", "chosen"):
            v = overrides.get(str(idx), {}).get(k)
            if v:
                chart[k] = v
        sections.append({
            **s,
            "chart": _resolve_chart(chart, str(s.get("question") or "")),
        })
    return {
        "schema": IR_SCHEMA,
        "ok": not schema_errs,
        "schema_errors": schema_errs,
        "meta": ir.get("meta"),
        "facts": ir.get("facts"),
        "sources": ir.get("sources"),
        "sections": sections,
    }


def panel(model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """候选面板：只列出需要作者决策的节（chart_validation.ok=False）。

    每项给：当前 chosen、为什么不行（reason）、合法候选（candidates）。
    作者据此确认/覆盖，再调 apply_decisions 重解析。这是 SOP §5「候选确认」的接口。
    """
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(model.get("sections") or []):
        ch = s.get("chart") or {}
        cv = ch.get("chart_validation") or {}
        if cv.get("ok"):
            continue
        out.append({
            "index": i,
            "title": s.get("title"),
            "question": s.get("question"),
            "relation": ch.get("relation"),
            "chosen": ch.get("chosen"),
            "reason": cv.get("reason"),
            "candidates": cv.get("suggest") or cv.get("allowed") or [],
        })
    return out


def apply_decisions(ir: Dict[str, Any],
                    decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """把作者在候选面板上的决定应用到 IR 并重解析。

    decisions: [{index, relation?, chosen?}]——只填作者要改的节；缺省走推断/候选默认。
    """
    overrides: Dict[str, Dict[str, str]] = {}
    for d in decisions:
        i = str(d.get("index"))
        o: Dict[str, str] = {}
        if d.get("relation"):
            o["relation"] = str(d["relation"])
        if d.get("chosen"):
            o["chosen"] = str(d["chosen"])
        if o:
            overrides[i] = o
    return resolve(ir, overrides)
