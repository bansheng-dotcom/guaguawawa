# -*- coding: utf-8 -*-
"""S05c 两样本 t 检验 —— 能力域 5（统计域 · 拆细之三）。

从 s05_statistics 拆出，整合自 scipy.stats.ttest_ind(equal_var=False)。
单功能：两独立样本 Welch t 检验 + Cohen's d 效应量 + 显著性判读。
"""
from __future__ import annotations

from typing import Any, Dict

from . import _common as c
from . import _stats

NAME = "ttest"
DESC = "两独立样本 Welch t 检验 + Cohen's d（能力域5拆细）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--value", required=True, help="指标数值列")
    p.add_argument("--group", required=True, help="分组列")
    p.add_argument("--group-a", required=True)
    p.add_argument("--group-b", required=True)


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    ga = args.group_a
    gb = args.group_b
    g1 = [float(r[args.value]) for r in rows
          if str(r.get(args.group)) == ga and c.isnum(r.get(args.value))]
    g2 = [float(r[args.value]) for r in rows
          if str(r.get(args.group)) == gb and c.isnum(r.get(args.value))]
    return {"welch_t": _stats.welch_t(g1, g2, ga, gb)}