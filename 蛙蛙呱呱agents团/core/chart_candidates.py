# -*- coding: utf-8 -*-
"""core.chart_candidates —— 候选面板：relation → 合法候选 + 校验作者选择（S4）。

与 chart_grammar/chooser 的区别：这里**不决定**图型，只给「合法下限」：
  - candidates(contract) 从 relation 的 allowed 里筛出可行候选（≤3），供作者选；
  - validate(contract)   校验作者选定的 chosen 是否合法、可行；不行就返回建议。

可行性只用两个维度判断（来自 S2 接桥的 dims）：
  - 时序类图需要 period 维；二维类图需要 entity 维。
这是 S5 统一门禁里「图拟合度」的底层依据。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent

try:  # 别名以渲染器注册表为单一出处（grouped_bar→grouped 等）
    from core.report_theme.charts_pro.spec import ALIASES
except Exception:  # noqa: BLE001
    ALIASES = {}


def canonical(typ: str) -> str:
    """别名 → 渲染器规范名；不是别名就原样返回。"""
    t = str(typ or "")
    return str(ALIASES.get(t, t))


# 需要时间维才能画
TIME_TYPES = {"line", "area", "step", "slope", "stream", "stack_area",
              "cal_heatmap", "candle", "small_mult", "gantt", "timeline",
              "spiral", "multi_line", "fan", "connected"}
# 需要第二个主体维（entity）才能画
DIM2_TYPES = {"heatmap", "scatter", "bubble", "network", "sankey", "chord",
              "choropleth", "symbol", "geo_flow", "hexbin_map", "marimekko",
              "dot_matrix", "correlogram", "parallel", "dendrogram", "pca",
              "sunburst", "treemap"}

READABILITY = ["hbar", "vbar", "line", "dot", "lollipop", "dumbbell",
               "slope", "waterfall", "scatter", "heatmap", "share_bar",
               "treemap", "sankey", "funnel", "pareto", "bullet"]


def _load_relations() -> Dict[str, List[str]]:
    p = ROOT / "configs" / "chart_by_relation.yaml"
    if not p.exists():
        return {}
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {str(k): [str(t) for t in (v.get("allowed") or [])]
            for k, v in (d.get("relations") or {}).items()}


def _dims(contract: Dict[str, Any]) -> set:
    return {str(d.get("name")) for d in (contract.get("dims") or [])}


def feasible(contract: Dict[str, Any], typ: str) -> bool:
    dims = _dims(contract)
    if typ in TIME_TYPES and "period" not in dims:
        return False
    if typ in DIM2_TYPES and "entity" not in dims:
        return False
    return True


def candidates(contract: Dict[str, Any], n: int = 3) -> List[Dict[str, Any]]:
    rel = contract.get("relation") or "magnitude"
    allowed = _load_relations().get(rel, ["hbar"])
    out = []
    for t in allowed:
        t = canonical(t)
        if not feasible(contract, t):
            continue
        out.append(t)
    out.sort(key=lambda t: READABILITY.index(t) if t in READABILITY else 99)
    return [{"type": t} for t in dict.fromkeys(out)][:max(1, n)]


def validate(contract: Dict[str, Any]) -> Dict[str, Any]:
    rel = contract.get("relation") or "magnitude"
    allowed_raw = _load_relations().get(rel, [])
    allowed = {canonical(t) for t in allowed_raw}
    chosen = canonical(str(contract.get("chosen") or ""))
    if not chosen:
        return {"ok": False, "chosen": "", "allowed": sorted(allowed),
                "reason": "缺 chosen"}
    if chosen not in allowed:
        return {"ok": False, "chosen": chosen, "allowed": sorted(allowed),
                "reason": f"{chosen} 不能表达 {rel}",
                "suggest": [c["type"] for c in candidates(contract)]}
    if not feasible(contract, chosen):
        return {"ok": False, "chosen": chosen,
                "reason": f"{chosen} 需要缺失的维度",
                "suggest": [c["type"] for c in candidates(contract)]}
    return {"ok": True, "chosen": chosen, "relation": rel}
