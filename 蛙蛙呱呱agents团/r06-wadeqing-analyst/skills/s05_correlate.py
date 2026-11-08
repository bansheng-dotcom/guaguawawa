# -*- coding: utf-8 -*-
"""S05b 相关分析 —— 能力域 5（统计域 · 拆细之二）。

从 s05_statistics 拆出。整合自 scipy.stats.pearsonr。单功能：Pearson 相关。
主张：相关 ≠ 因果；|r| 分级由 thresholds.json 的 correlation 段驱动。
"""
from __future__ import annotations

from typing import Any, Dict

from . import _common as c

NAME = "correlate"
DESC = "Pearson 相关：两数值列线性相关强度（能力域5拆细）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--col-a", required=True)
    p.add_argument("--col-b", required=True)


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    return {"correlation": _correlate(rows, args.col_a, args.col_b)}


def _correlate(rows, a, b):
    va = c.numeric(rows, a)
    vb = c.numeric(rows, b)
    r = c.pearson(va, vb)
    t = c.load_thresholds().get("statistics", {}).get(
        "correlation", {"strong": 0.8, "medium": 0.5})
    strength = "强" if abs(r) >= t.get("strong", 0.8) else (
        "中" if abs(r) >= t.get("medium", 0.5) else "弱")
    return {"col_a": a, "col_b": b, "pearson_r": round(r, 4),
            "strength": strength,
            "note": "相关≠因果；|r| 高提示可能共线，需回归/混杂控制"}