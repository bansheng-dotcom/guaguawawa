# -*- coding: utf-8 -*-
"""core.chart_contract —— 图表契约 v2：三条线归一成同一形状（S3）。

三条线的现状：
  - 拆卡线：section 只有 chart{type,title,refs,...}，relation 全空，没有 comparison；
  - A 线：    question 有 comparison{kind} → 可映射 relation；
  - flow 线：section 只有显式 chart_spec.type（作者已选定）。

本模块把三者归一成同一形状（纯函数、不改任何产物、不进渲染路径）：
    {relation, intent, chosen, data_refs, dims, why}

  - relation：comparison.kind 优先 → section.relation → 由 chart.type 反查；
  - intent： 由 relation 映射成一句话；
  - chosen： chart.type；
  - dims：   由 data_refs 指到的数字里的 entity/period 推导（S2 已接）。

这是 S4（统一选型）与 S5（统一门禁）的输入，不是新渲染层。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent

INTENT_LABEL = {
    "deviation": "偏离对比", "correlation": "相关", "ranking": "排序",
    "distribution": "分布", "change_over_time": "趋势", "composition": "构成",
    "magnitude": "量级", "spatial": "空间", "flow": "流向",
}


def load_policy() -> tuple:
    """读 chart_by_relation.yaml，返回 (kind→relation, type→relation)。"""
    p = ROOT / "configs" / "chart_by_relation.yaml"
    if not p.exists():
        return {}, {}
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    kind_to_rel = d.get("comparison_to_relation") or {}
    type_to_rel: Dict[str, str] = {}
    for rel, spec in (d.get("relations") or {}).items():
        for t in (spec.get("allowed") or []):
            type_to_rel.setdefault(str(t), str(rel))
    return kind_to_rel, type_to_rel


def _relation(chart: Dict, section: Dict, type_to_rel: Dict, kind_to_rel: Dict) -> str:
    cmp = section.get("comparison") or {}
    kind = str(cmp.get("kind") or "")
    if kind in kind_to_rel:
        return str(kind_to_rel[kind])
    rel = str(chart.get("relation") or section.get("relation") or "").strip()
    if rel:
        return rel
    return type_to_rel.get(str(chart.get("type") or ""), "magnitude")


def normalize(chart: Optional[Dict[str, Any]],
              section: Optional[Dict[str, Any]] = None,
              nums: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """把一张图归一成契约 v2。nums: {number_id: {entity, period, ...}}。"""
    ch = chart or {}
    sec = section or {}
    kind_to_rel, type_to_rel = load_policy()
    chosen = str(ch.get("type") or "")
    rel = _relation(ch, sec, type_to_rel, kind_to_rel)
    # dims：从 refs 指到的数字里收集 entity / period
    idx = nums or {}
    dims, seen = [], set()
    for r in (ch.get("refs") or []):
        n = idx.get(str(r)) or {}
        if n.get("entity") and ("entity", "categorical") not in seen:
            seen.add(("entity", "categorical"))
            dims.append({"name": "entity", "type": "categorical"})
        if n.get("period") and ("period", "temporal") not in seen:
            seen.add(("period", "temporal"))
            dims.append({"name": "period", "type": "temporal"})
    return {
        "relation": rel,
        "intent": INTENT_LABEL.get(rel, "比较"),
        "chosen": chosen,
        "data_refs": list(ch.get("refs") or []),
        "dims": dims,
        "why": str(ch.get("why_this_chart") or sec.get("why_this_chart") or ""),
    }
