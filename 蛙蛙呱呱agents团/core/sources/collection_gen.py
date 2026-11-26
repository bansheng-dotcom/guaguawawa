# -*- coding: utf-8 -*-
"""core.collection_gen —— 生成候选采集规格（DERIVATION-SOP v4.0 · 第 4 步）。

**这是"生成物"，不是"手写物"**：
    generated: true
    generated_from: {grid_hash, source_id, demands}
    hand_edited: false

手改过（`hand_edited: true`）的规格，重新生成时**不覆盖**，只告警。

用法：
    from core import collection_gen as cg
    draft = cg.generate(demand_doc, match_doc, source)
    errs = cg.validate_draft(draft)
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from core import collection_spec as cs

SCHEMA = cs.SCHEMA
SERIES_DIMS = ("year", "month", "quarter", "week", "day")


def _hash(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]


def generate(demand_doc: Dict[str, Any], match_doc: Dict[str, Any],
             source: Dict[str, Any], spec_id: str = "",
             query: Dict[str, Any] = None) -> Dict[str, Any]:
    """从「需求 + 匹配结果」生成候选规格草稿（不含 claims）。"""
    best = (match_doc or {}).get("best") or {}
    rollups: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for measure, m in sorted(best.items()):
        if m.get("status") == "none":
            skipped.append({"measure": measure, "why": "没有源能提供",
                            "notes": m.get("notes")})
            continue
        dims = list((m.get("dims") or {}).keys())
        mp = m.get("measure_plan") or {}
        rid = "%s__%s" % (measure, "_".join(dims) or "all")
        rollups.append({
            "id": rid,
            "grain": dims,
            "series": any(d in SERIES_DIMS for d in dims),
            "derive": dict(m.get("derive") or {}),
            "measures": {measure: {
                "agg": str(mp.get("agg") or "sum"),
                "expr": str(mp.get("expr") or ""),
                "unit": str(mp.get("unit") or ""),
            }},
        })
    draft = {
        "schema": SCHEMA,
        "id": spec_id or ("gen_" + str(source.get("id") or "src")),
        "title": "自动生成（待确认）",
        "source": str(source.get("id") or ""),
        "query": dict(query or {}),
        "rollups": rollups,
        "claims": [],
        # 生成物标记：重新生成时靠它判断能不能覆盖
        "generated": True,
        "hand_edited": False,
        "generated_from": {
            "grid_hash": _hash((demand_doc or {}).get("demands")),
            "source": str(source.get("id") or ""),
            "demands": (demand_doc or {}).get("count"),
        },
        "skipped": skipped,
    }
    return draft


def validate_draft(draft: Dict[str, Any]) -> List[str]:
    """草稿校验：结构 + 至少一个 rollup + 度量 expr 非空。"""
    errs: List[str] = []
    if not draft.get("generated"):
        errs.append("不是生成物（缺 generated 标记）")
    if not draft.get("rollups"):
        errs.append("没有可用的 rollup（源匹配全部失败？）")
    for r in draft.get("rollups") or []:
        if not r.get("grain"):
            errs.append("[%s] 缺 grain" % r.get("id"))
        for name, m in (r.get("measures") or {}).items():
            if not str((m or {}).get("expr") or ""):
                errs.append("[%s] measures[%s] 缺 expr" % (r.get("id"), name))
    return errs


def merge_into_project(draft: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
    """把草稿合进项目已有规格：**手改过的不覆盖**。"""
    if not existing:
        return draft
    if existing.get("hand_edited"):
        return {"ok": False, "why": "已有规格被手改过（hand_edited），不覆盖",
                "existing": existing}
    if existing.get("generated_from") == draft.get("generated_from"):
        return {"ok": False, "why": "输入没变，无需重新生成", "existing": existing}
    return draft
