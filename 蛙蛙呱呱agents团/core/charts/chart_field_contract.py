# -*- coding: utf-8 -*-
"""core.charts.chart_field_contract —— 图型**数据字段**契约审计（P4-2 · 治 V-1）。

V-1 的根因：`charts_pro.spec.REQUIRED`（只写主键）与 `samples.SAMPLE`（真字段）
是两份，门禁只跑 samples，按 REQUIRED 装配必踩 KeyError。

本模块**不复制第二份表**：REQUIRED 仍以 `charts_pro.spec.REQUIRED` 为准，
`contract_audit(samples)` 把「声明字段」与「样例行」逐型比对；
`scripts/check_charts_pro.py` 调它——两份一旦漂移，CI 直接红。

与 `core/charts/chart_spec.py`（报告交付契约：type/title/source/claim_to_prove）
和 `core/charts/chart_contract.py`（三条线归一）分工不同：这里只管渲染器的数据字段。
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.data import data_standard as ds
from core.report_theme.charts_pro import spec as pro_spec


def required_of(chart_type: str) -> List[str]:
    """某图型必填的数据键（别名解析到真型）。"""
    t = pro_spec.ALIASES.get(str(chart_type), str(chart_type))
    return list(pro_spec.REQUIRED.get(t, ()))


def contract_audit(samples: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """声明 vs 样例：逐型比对必填字段。"""
    mism: List[Dict[str, Any]] = []
    for k in sorted(samples):
        if k not in pro_spec.RENDERERS:
            mism.append({"type": k, "missing_in_sample": [],
                         "problem": "样例没有对应渲染器"})
            continue
        keys = set(samples[k].keys()) - {"type"}
        miss = [f for f in required_of(k) if f not in keys]
        if miss:
            mism.append({"type": k, "missing_in_sample": miss})
    return {"ok": not mism, "types": len(samples), "mismatch": mism}


def _pick(obs: List[ds.Observation], key: str) -> List[str]:
    out: List[str] = []
    for o in obs:
        v = str(getattr(o, key, "") or "").strip()
        if v and v not in out:
            out.append(v)
    return out


def build_spec(dataset: ds.Dataset, chart_type: str,
               group: str = "entity", time: str = "period",
               title: str = "", unit: str = "",
               fallback: str = "") -> ds.ChartSpec:
    """Dataset → ChartSpec（数据引用，不把数字塞进 spec）。"""
    obs = dataset.observations
    t = pro_spec.ALIASES.get(str(chart_type), str(chart_type))
    encode: Dict[str, Any] = {"value": "value", "label": group}
    option: Dict[str, Any] = {"title": title or dataset.name, "unit": unit,
                              "fallback": fallback}
    if t in ("line", "area", "multi_line", "stacked", "pct_stacked"):
        encode = {"x": time, "y": "value", "series": group}
    elif t in ("heatmap", "dot_matrix", "ym_heat"):
        cats = [c for c in ("entity", "metric_id", "scope") if len(_pick(obs, c)) >= 2]
        encode = {"x": cats[0] if cats else group,
                  "y": cats[1] if len(cats) > 1 else "period",
                  "value": "value"}
    elif t in ("pie", "donut", "treemap", "funnel", "waffle", "rose"):
        encode = {"label": group, "value": "value"}
    elif t in ("scatter", "bubble", "quadrant"):
        encode = {"x": time, "y": "value", "label": group}
    return ds.ChartSpec(chart_type=t,
                        data_ref={"dataset": dataset.name,
                                  "metric": _pick(obs, "metric_id")[:1],
                                  "rows": len(obs)},
                        encode=encode, option=option)
