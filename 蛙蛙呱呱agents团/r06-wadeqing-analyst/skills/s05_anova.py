# -*- coding: utf-8 -*-
"""S05e 单因素 ANOVA —— 能力域 5（统计域 · 拆细之五）。

从 s05_statistics 拆出，整合自 scipy.stats.f_oneway。
单功能：多组均值差异的单因素方差分析 + η² 效应量 + F 值 + 组描述。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c
from . import _stats

NAME = "anova"
DESC = "单因素 ANOVA + η² 效应量（能力域5拆细）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--value", required=True, help="指标数值列")
    p.add_argument("--group", required=True, help="分组列")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    return {"anova": _anova(rows, args.value, args.group)}


def _anova(rows, value, group):
    groups: Dict[str, List[float]] = {}
    for r in rows:
        if c.isnum(r.get(value)):
            groups.setdefault(str(r.get(group)), []).append(float(r[value]))
    grand = [v for vs in groups.values() for v in vs]
    gm = sum(grand) / len(grand) if grand else 0.0
    ssb = sum(len(vs) * (sum(vs) / len(vs) - gm) ** 2 for vs in groups.values())
    ssw = sum(sum((v - sum(vs) / len(vs)) ** 2 for v in vs)
              for vs in groups.values() if len(vs) > 1)
    sst = ssb + ssw
    k = len(groups)
    n = len(grand)
    dfb, dfw = k - 1, n - k
    f = (ssb / dfb) / (ssw / dfw) if dfb and dfw and ssw else 0.0
    eta2 = _stats.eta_squared(ssb, sst)
    th = _stats.stat_thresholds()
    e2 = th.get("eta2", {"small": 0.01, "medium": 0.06, "large": 0.14})
    return {"k_groups": k, "n": n,
            "ss_between": round(ssb, 4), "ss_within": round(ssw, 4),
            "df_between": dfb, "df_within": dfw,
            "f_statistic": round(f, 4),
            "eta_squared": round(eta2, 4),
            "effect_grade": _stats.effect_grade(eta2, [e2.get("small", 0.01),
                                                       e2.get("medium", 0.06),
                                                       e2.get("large", 0.14)]),
            "groups": {g: c.describe(vs) for g, vs in groups.items()},
            "note": "F 精确 p 值需 scipy.stats.f；η²=SSb/SSt 衡量方差解释比例"}