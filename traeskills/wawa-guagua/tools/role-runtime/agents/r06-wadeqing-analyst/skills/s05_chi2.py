# -*- coding: utf-8 -*-
"""S05d 卡方检验 —— 能力域 5（统计域 · 拆细之四）。

从 s05_statistics 拆出，整合自 scipy.stats.chi2_contingency。
单功能：RxC 列联表独立性检验 + Cramér's V 效应量 + 临界值判读。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from . import _common as c
from . import _stats

NAME = "chi2"
DESC = "卡方独立性检验 + Cramér's V（能力域5拆细）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--row", required=True, help="行变量列")
    p.add_argument("--col", required=True, help="列变量列")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    return {"chi2": _chi2(rows, args.row, args.col)}


def _chi2(rows, row_col, col_col):
    table = Counter((str(r.get(row_col)), str(r.get(col_col))) for r in rows)
    r_labels = sorted({k[0] for k in table})
    c_labels = sorted({k[1] for k in table})
    row_tot = {r: sum(table[(r, cc)] for cc in c_labels) for r in r_labels}
    col_tot = {cc: sum(table[(rr, cc)] for rr in r_labels) for cc in c_labels}
    total = sum(table.values())
    stat = 0.0
    min_exp = None
    for rr in r_labels:
        for cc in c_labels:
            exp = row_tot[rr] * col_tot[cc] / total if total else 0
            obs = table[(rr, cc)]
            if exp:
                stat += (obs - exp) ** 2 / exp
            if exp > 0 and (min_exp is None or exp < min_exp):
                min_exp = exp
    df = (len(r_labels) - 1) * (len(c_labels) - 1)
    crit = _stats.CHI2_CRIT[df] if 1 <= df <= 10 else None
    significant = (stat > crit) if crit is not None else None
    v = _stats.cramers_v(stat, total, len(r_labels), len(c_labels))
    th = _stats.stat_thresholds()
    cv = th.get("cramers_v", {"small": 0.1, "medium": 0.3, "large": 0.5})
    return {"chi2_statistic": round(stat, 4), "df": df,
            "critical_0.05": crit, "significant_at_0.05": significant,
            "cramers_v": round(v, 4),
            "effect_grade": _stats.effect_grade(v, [cv.get("small", 0.1),
                                                    cv.get("medium", 0.3),
                                                    cv.get("large", 0.5)]),
            "min_expected": round(min_exp, 2) if min_exp else None,
            "table": {f"{r}|{cc}": table[(r, cc)]
                      for r in r_labels for cc in c_labels},
            "note": "独立性检验；任何 cell 期望频数<5 时卡方近似不可靠"}