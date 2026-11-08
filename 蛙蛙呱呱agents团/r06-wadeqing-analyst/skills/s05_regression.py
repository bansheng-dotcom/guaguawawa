# -*- coding: utf-8 -*-
"""S05f 一元线性回归 —— 能力域 5（统计域 · 拆细之六 · 新增）。

整合自 scipy.stats.linregress + statsmodels OLS。单功能：一元 OLS 回归。
纯标准库：斜率/截距/R²/标准化 beta/斜率标准误/t/p/残差，全部直接算。
主张：斜率显著 ≠ 因果；R² 分级由 threshold 驱动。
"""
from __future__ import annotations

from typing import Any, Dict

from . import _common as c
from . import _stats

NAME = "regression"
DESC = "一元 OLS 线性回归 + R² + 标准化 beta（能力域5拆细·新增）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--x", required=True, help="自变量（连续）")
    p.add_argument("--y", required=True, help="因变量（连续）")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    xs = c.numeric(rows, args.x)
    ys = c.numeric(rows, args.y)
    n = min(len(xs), len(ys))
    return {"regression": _stats.linear_regression(xs[:n], ys[:n]),
            "x": args.x, "y": args.y}