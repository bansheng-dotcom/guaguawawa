# -*- coding: utf-8 -*-
"""core.ir_adapters —— 三个薄前端：作者写法 → 富 IR（SOP v3.0 S2–S4）。

每个前端做三件事（SOP §6）：
  1. 声明格式能力（本写法能/不能表达什么）；
  2. parse 到 IR（能映射的映射，不能映射的登记 degraded）；
  3. 降级显式（degraded 列表随 IR 返回，静默损失=失败）。

claims_to_ir：claims.json → IR
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core import report_ir
from core.report_ir import IR_SCHEMA


def _derive_dims(data_refs: List[str], nums_idx: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    """从 data_refs 指到的数字里收集 entity/period 维度（S2 join 之后数字带 entity）。"""
    dims, seen = [], set()
    for r in data_refs:
        n = nums_idx.get(str(r)) or {}
        if n.get("entity") and ("entity", "categorical") not in seen:
            seen.add(("entity", "categorical"))
            dims.append({"name": "entity", "type": "categorical"})
        if n.get("period") and ("period", "temporal") not in seen:
            seen.add(("period", "temporal"))
            dims.append({"name": "period", "type": "temporal"})
    return dims


def _load_raw_rows(claims: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """从 claims 的 raw.paths 读 raw.rows，建 number_id → {entity, period, scope} 索引。

    claims 的 numbers 无 entity（entity 在 collect 期的 raw 里），前端 lowering 时补回——
    这正是「数据从哪来」的答案：维度在 raw，前端把它接回 facts。
    """
    import json
    from pathlib import Path
    raw_path = ((claims.get("raw") or {}).get("paths") or {}).get("raw.json")
    if not raw_path:
        return {}
    p = Path(raw_path)
    if not p.exists():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(r.get("number_id")): r for r in (doc.get("rows") or [])
            if r.get("number_id")}


def claims_to_ir(claims: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """claims.json → 富 IR。返回 (ir, degraded)。"""
    degraded: List[Dict[str, str]] = []

    meta = {
        "title": (claims.get("meta") or {}).get("title") or "报告",
        "audience": (claims.get("meta") or {}).get("audience") or "业务负责人",
    }
    for k in ("standfirst", "one_thing"):
        v = (claims.get("meta") or {}).get(k) or claims.get(k)
        if v:
            meta[k] = v

    nums = claims.get("numbers") or []
    nums_idx = {str(n.get("id")): n for n in nums}
    raw_idx = _load_raw_rows(claims)  # number_id → {entity, period, scope}

    facts = []
    for n in nums:
        r = raw_idx.get(str(n.get("id"))) or {}
        facts.append({
            "id": str(n.get("id")),
            "metric": str(n.get("name") or ""),
            "entity": n.get("entity") or r.get("entity"),
            "period": n.get("period") or r.get("period"),
            "value": n.get("value"),
            "unit": str(n.get("unit") or ""),
            "source": str(n.get("source_file") or ""),
        })

    sources = []
    for s in claims.get("sources") or []:
        sources.append({
            "file": str(s.get("file") or s.get("url") or "agent"),
            "kind": str(s.get("kind") or "web"),
            "title": str(s.get("title") or ""),
            "org": str(s.get("org") or ""),
            "url": str(s.get("url") or ""),
            "grade": str(s.get("grade") or ""),
            "quote": str(s.get("quote") or ""),
        })

    facts_idx = {str(f["id"]): f for f in facts}  # 已补 entity/period 的索引

    sections = []
    for i, s in enumerate(claims.get("sections") or []):
        title = str(s.get("title") or "")
        question = str(s.get("question") or "")
        # 降级 1：claims 无独立 outline → 从 title 派生
        outline = str(s.get("outline") or title)
        if not s.get("outline"):
            degraded.append({"field": f"sections[{i}].outline",
                             "reason": "claims 无 outline，从 title 派生"})
        readings = [{"strong": str(r.get("strong") or ""),
                     "text": str(r.get("text") or ""),
                     "refs": list(r.get("refs") or [])}
                    for r in (s.get("reading") or []) if isinstance(r, dict)]
        chart = s.get("chart") or {}
        data_refs = list(chart.get("refs") or s.get("refs") or [])
        # relation：显式声明优先，否则从 question 推断（v3.0 默认）
        rel = str(chart.get("relation") or s.get("relation") or "")
        if not rel:
            rel = report_ir.infer_relation(question, _derive_dims(data_refs, facts_idx))
        sections.append({
            "title": title,
            "question": question,
            "outline": outline,
            "readings": readings,
            "actions": [],                       # claims 无独立 actions（在「所以」块里）
            "boundary": str(s.get("boundary") or ""),
            "falsifier": str(s.get("falsifier") or ""),
            "chart": {
                "relation": rel,
                "chosen": str(chart.get("type") or ""),
                "data_refs": data_refs,
                "dims": _derive_dims(data_refs, facts_idx),
            },
        })

    ir = {"schema": IR_SCHEMA, "meta": meta, "facts": facts,
          "sources": sources, "sections": sections}
    return ir, degraded


def facts_to_ir(facts: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """声明式 facts.yaml → 富 IR（薄前端：校验默认 + 填默认值）。

    声明式 facts 与 IR 几乎同构（facts + sections + chart-intent），
    所以本前端只做三件事：meta 归一、relation/outline 填默认、dims 反推。
    旧 facts.py（Python 代码）不在本函数处理范围——那是待迁移的旧载体。
    """
    degraded: List[Dict[str, str]] = []
    m = facts.get("meta") or {}
    meta = {
        "title": str(m.get("title") or "报告"),
        "audience": str(m.get("audience") or "业务负责人"),
    }
    for k in ("subtitle", "standfirst", "one_thing"):
        if m.get(k):
            meta[k] = str(m[k])

    ir_facts = []
    for f in facts.get("facts") or []:
        ir_facts.append({
            "id": str(f.get("id")),
            "metric": str(f.get("metric") or ""),
            "entity": f.get("entity"),
            "period": f.get("period"),
            "value": f.get("value"),
            "unit": str(f.get("unit") or ""),
            "source": str(f.get("source") or ""),
            "derived_from": list(f.get("derived_from") or []),
        })
    facts_idx = {str(f["id"]): f for f in ir_facts}

    ir_sources = []
    for s in facts.get("sources") or []:
        ir_sources.append({
            "file": str(s.get("file") or s.get("url") or "agent"),
            "kind": str(s.get("kind") or "web"),
            "title": str(s.get("title") or ""),
            "org": str(s.get("org") or ""),
            "url": str(s.get("url") or ""),
            "grade": str(s.get("grade") or ""),
            "quote": str(s.get("quote") or ""),
        })

    sections = []
    for i, s in enumerate(facts.get("sections") or []):
        title = str(s.get("title") or "")
        question = str(s.get("question") or "")
        outline = str(s.get("outline") or title)
        if not s.get("outline"):
            degraded.append({"field": f"sections[{i}].outline",
                             "reason": "facts 无 outline，从 title 派生"})
        chart = s.get("chart") or {}
        data_refs = list(chart.get("data_refs") or [])
        rel = str(chart.get("relation") or "")
        if not rel:
            rel = report_ir.infer_relation(question, _derive_dims(data_refs, facts_idx))
        sections.append({
            "title": title, "question": question, "outline": outline,
            "readings": [dict(r) for r in (s.get("readings") or [])
                         if isinstance(r, dict)],
            "actions": list(s.get("actions") or []),
            "boundary": str(s.get("boundary") or ""),
            "falsifier": str(s.get("falsifier") or ""),
            "chart": {
                "relation": rel,
                "chosen": str(chart.get("chosen") or ""),
                "data_refs": data_refs,
                "dims": _derive_dims(data_refs, facts_idx),
            },
        })

    ir = {"schema": IR_SCHEMA, "meta": meta, "facts": ir_facts,
          "sources": ir_sources, "sections": sections}
    return ir, degraded


def decision_to_ir(draft: Dict[str, Any],
                   evidence_pack: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """A 线的 draft_sections.json + evidence_pack.json → 富 IR。返回 (ir, degraded)。

    与 claims 的差异（格式能力表）：
      - A 线数字用 region 表空间维（claims 用 entity）→ 映射成 entity；
      - A 线派生数字带 inputs → 映射成 derived_from（溯源边，天然有）；
      - A 线无 outline → 从 title 派生（降级）。
    """
    degraded: List[Dict[str, str]] = []

    meta = {
        "title": str(draft.get("title_lines") or [draft.get("intent") or "报告"])[0]
                 if isinstance(draft.get("title_lines"), list) and draft.get("title_lines")
                 else str(draft.get("intent") or "报告"),
        "audience": "业务负责人",
    }
    if draft.get("standfirst"):
        meta["standfirst"] = str(draft["standfirst"])

    nums = evidence_pack.get("numbers") or []
    facts = []
    for n in nums:
        inputs = n.get("inputs") or ""
        derived_from = ([x.strip() for x in str(inputs).split(",") if x.strip()]
                        if inputs else [])
        f = {
            "id": str(n.get("id")),
            "metric": str(n.get("name") or ""),
            "entity": n.get("region") or n.get("entity"),
            "period": n.get("period"),
            "value": n.get("value"),
            "unit": str(n.get("unit") or ""),
            "source": str(n.get("source_file") or ""),
            "derived_from": derived_from,
        }
        if n.get("formula"):
            f["history"] = [{"event": "derive", "formula": str(n["formula"])}]
        facts.append(f)

    sources = []
    for s in evidence_pack.get("sources") or []:
        sources.append({
            "file": str(s.get("file") or s.get("url") or "agent"),
            "kind": str(s.get("kind") or "web"),
            "title": str(s.get("title") or ""),
            "org": str(s.get("org") or ""),
            "url": str(s.get("url") or ""),
            "grade": str(s.get("grade") or ""),
            "quote": str(s.get("quote") or ""),
        })

    facts_idx = {str(f["id"]): f for f in facts}
    sections = []
    for i, s in enumerate(draft.get("sections") or []):
        title = str(s.get("title") or "")
        question = str(s.get("question") or "")
        outline = str(s.get("outline") or title)
        if not s.get("outline"):
            degraded.append({"field": f"sections[{i}].outline",
                             "reason": "A 线无 outline，从 title 派生"})
        readings = [{"strong": str(r.get("strong") or ""),
                     "text": str(r.get("text") or ""),
                     "refs": list(r.get("refs") or [])}
                    for r in (s.get("reading") or []) if isinstance(r, dict)]
        chart = s.get("chart") or {}
        data_refs = list(chart.get("refs") or s.get("refs") or [])
        rel = str(chart.get("relation") or s.get("relation") or "")
        if not rel:
            rel = report_ir.infer_relation(question, _derive_dims(data_refs, facts_idx))
        sections.append({
            "title": title, "question": question, "outline": outline,
            "readings": readings,
            "actions": [],  # A 线 section 有 decision，但无独立 actions
            "boundary": str(s.get("boundary") or ""),
            "falsifier": str(s.get("falsifier") or ""),
            "chart": {
                "relation": rel,
                "chosen": str(chart.get("type") or ""),
                "data_refs": data_refs,
                "dims": _derive_dims(data_refs, facts_idx),
            },
        })

    ir = {"schema": IR_SCHEMA, "meta": meta, "facts": facts,
          "sources": sources, "sections": sections}
    return ir, degraded
