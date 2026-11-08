# -*- coding: utf-8 -*-
"""S05a 描述统计 —— 能力域 5（统计域 · 拆细之一）。

从 s05_statistics 拆出。整合自 scipy.stats.describe / statsmodels 的
偏度峰度口径。单功能：对某数值列做描述统计。
"""
from __future__ import annotations

from typing import Any, Dict

from . import _common as c

NAME = "describe"
DESC = "描述统计：均值/中位数/分位/极值/离散（能力域5拆细）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--col", required=True, help="数值列")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    return {"describe": {args.col: c.describe(c.numeric(rows, args.col))}}