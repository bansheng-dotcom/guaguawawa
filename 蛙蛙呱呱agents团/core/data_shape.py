# -*- coding: utf-8 -*-
"""core.data_shape —— shape → chart 的适配器。

唯一词汇表在 `core/charts/chart_lib.py`（48 型 + recommend(shape,intent)）；
本模块只做“业务 shape 名 → chart_lib shape/intent”的映射，不再维护第二套图型规则。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

_CH = Path(__file__).resolve().parent / "charts"
if str(_CH) not in sys.path:
    sys.path.insert(0, str(_CH))

from core.charts import chart_lib  # noqa: E402

SHAPES = {
    "scalar": "单点标量（一个数/一个百分比）",
    "pair": "成对值（同一单元的前后/两地/两方案）",
    "panel": "面板（单元 × 时点/城市/渠道）",
    "matrix": "矩阵（单元 × 维度）",
    "timeseries": "时间序列（同一口径 ≥3 期）",
    "breakdown": "构成/分项（总额 = 各分项之和）",
    "flow": "流向（产地→销地，带量/额）",
    "distribution": "分布（多观测点的散点/分布）",
    "range": "区间（低值—高值）",
    "xy": "双变量（x/y，可带气泡大小）",
    "geo": "地理（点/面/流向）",
}

# 业务 shape → (chart_lib shape, intent)
ALIASES = {
    "scalar": ("categories", "rank"),
    "pair": ("two_period", "compare"),
    "panel": ("panel", "compare"),
    "matrix": ("matrix", "compare"),
    "timeseries": ("time_series", "trend"),
    "breakdown": ("breakdown", "explain"),
    "flow": ("flow", "convert"),
    "distribution": ("distribution", "compare"),
    "range": ("distribution", "range"),
    "xy": ("xy", "relate"),
    "geo": ("geo", "map"),
}


CHART_ALIASES = {"range": "error_bar", "bar": "vbar", "area": "line"}


def _canon(chart_type: str) -> str:
    return CHART_ALIASES.get(str(chart_type or ""), str(chart_type or ""))


def candidates(shape: str) -> List[str]:
    lib = ALIASES.get(str(shape))
    if not lib:
        return []
    return [c["key"] for c in chart_lib.recommend(lib[0], lib[1])]


def fits(chart_type: str, shape: str) -> bool:
    return _canon(chart_type) in candidates(shape)


def choose(question: str, shape: str) -> Dict[str, Any]:
    allowed = candidates(shape)
    lib = ALIASES.get(shape)
    note = (f"数据形状「{shape}」→ chart_lib {lib or '未知'}；"
            f"可选：{'、'.join(allowed) or '无，退回表格'}。")
    return {"shape": shape, "allowed": allowed, "note": note,
            "question": question, "fallback": "table" if not allowed else ""}


def audit_sections(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues = []
    for s in sections:
        ch = s.get("chart")
        shape = s.get("shape")
        if not ch:
            continue
        if not shape:
            issues.append(f"{s.get('id')}: 有图但未声明 shape")
            continue
        if not fits(ch, shape):
            issues.append(f"{s.get('id')}: 图型 {ch} 不适配 shape={shape}")
    return {"ok": not issues, "issues": issues}
