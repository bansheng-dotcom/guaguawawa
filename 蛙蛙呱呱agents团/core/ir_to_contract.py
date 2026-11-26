# -*- coding: utf-8 -*-
"""core.ir_to_contract —— 已解析 IR 模型 → 报告 contract（给 report_renderer 用）。

为什么需要它：三前端只做到了「写法 → IR」，还缺「IR → 渲染契约」这一段。
有了它，facts.py 那条路径（flow --project）就能改走 report_renderer，
不必再维护第二套渲染器（kit）。

用法：
    from core import ir_to_contract
    contract = ir_to_contract.build(resolved_model)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.charts.chart_payload import build_payload

# IR 的 relation 词汇 → charts_pro 渲染型名（与 charts_pro/spec.py ALIASES 对齐）
_RENDER_TYPE = {"stacked_bar": "stacked", "grouped_bar": "grouped",
                "ridgeline": "ridge", "candlestick": "candle",
                "symbol_map": "symbol", "streamgraph": "stream"}

DEFAULT_THEME = "sticker"

# chart_spec 允许的 payload 键（透传白名单）：覆盖 charts_pro 的全部载荷形状
_PAYLOAD_KEYS = {
    "items", "bars", "vbars", "points", "rows", "cols", "matrix", "cells",
    "series", "categories", "nodes", "edges", "links", "stages", "steps",
    "groups", "values", "panels", "axes", "tasks", "milestones", "ohlc",
    "columns", "low", "high", "start", "deltas", "value", "target", "band",
    "top", "bottom", "median", "note", "accent_note",
}


def _chart(s: Dict[str, Any], facts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ch = s.get("chart") or {}
    typ = str(ch.get("chosen") or ch.get("type") or "")
    if not typ:
        return None
    typ = _RENDER_TYPE.get(typ, typ)
    refs = list(ch.get("data_refs") or [])
    sub = [f for f in facts if str(f.get("id")) in {str(r) for r in refs}]
    # 优先用 IR 里原样透传的 payload（facts.py 的 chart_spec 自带完整形状），
    # 没有再按 facts 重建——这样 matrix/series/nodes 等形状不会丢。
    payload_in = ch.get("payload") or {}
    payload = {k: v for k, v in payload_in.items()
               if k in _PAYLOAD_KEYS and v not in (None, "", [], {})}
    if not payload:
        payload = build_payload(typ, sub)
    if not payload:
        return None
    units = {str(f.get("unit") or "") for f in sub if f.get("unit")}
    unit = next(iter(units)) if len(units) == 1 else ""
    srcs = {str(f.get("source") or "") for f in sub if f.get("source")}
    out = {
        "type": typ,
        "title": str(s.get("title") or ch.get("intent") or ""),
        "unit_meta": unit or "见正文",
        "source": "、".join(sorted(srcs)) or "本节来源见附录",
        "refs": refs,
    }
    out.update(payload)
    return out


def build(model: Dict[str, Any]) -> Dict[str, Any]:
    """已解析模型 → contract。只有 meta/sections 是硬要求，其余容缺。"""
    meta = model.get("meta") or {}
    facts = model.get("facts") or []
    sources = model.get("sources") or []
    secs_in = model.get("sections") or []

    title = str(meta.get("title") or "报告")
    subtitle = str(meta.get("subtitle") or "")
    title_lines = [title] + ([subtitle] if subtitle else [])

    summary = []
    if meta.get("standfirst"):
        summary.append({"text": str(meta["standfirst"])})

    # 指标条：取前 4 条事实当 headline（label/value/note 三件）
    metric_strip = []
    for f in facts[:4]:
        note = " ".join(x for x in (str(f.get("entity") or ""),
                                    str(f.get("period") or "")) if x)
        metric_strip.append({
            "label": str(f.get("metric") or ""),
            "value": str(f.get("value") if f.get("value") is not None else ""),
            "note": note or "见正文",
            "status": "none",
        })

    sections = []
    for i, s in enumerate(secs_in, 1):
        sec: Dict[str, Any] = {
            "index": i,
            "title": str(s.get("title") or "")[:40],
            "full_title": str(s.get("title") or ""),
            "question": str(s.get("question") or ""),
            "reading": [{"strong": str(r.get("strong") or ""),
                         "text": str(r.get("text") or ""),
                         "refs": list(r.get("refs") or [])}
                        for r in (s.get("readings") or []) if isinstance(r, dict)],
            "boundary": str(s.get("boundary") or ""),
            "falsifier": str(s.get("falsifier") or ""),
        }
        ch = _chart(s, facts)
        if ch:
            sec["chart"] = ch
        sections.append(sec)

    note_items = [{"text": str(x.get("title") or x.get("file") or "")}
                  for x in sources[:20] if (x.get("title") or x.get("file"))]
    return {
        "doc_type": str(meta.get("doc_type") or "R01 报告"),
        "title_lines": title_lines,
        "standfirst": str(meta.get("standfirst") or ""),
        "summary": summary,
        "metric_strip": metric_strip,
        "sections": sections,
        "notes": ({"summary": "证据包与回溯", "items": note_items}
                  if note_items else {"summary": "证据包与回溯", "items": []}),
        "footer": [
            "蛙蛙呱呱专家团",
            "数据、口径与来源见附录",
            "生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M"),
        ],
        "theme": DEFAULT_THEME,
        "layout": "flow",
    }
