# -*- coding: utf-8 -*-
"""S05g A/B 实验 —— 能力域 5（统计域 · 拆细之七）。

从 s05_statistics 拆出，整合自 data-analytics-skills 的 ab-test-analysis +
DoWhy 随机化检验。单功能：lift + 显著性 + SRM 样本比例失配检测。
"""
from __future__ import annotations

from typing import Any, Dict

from . import _common as c
from . import _stats

NAME = "abtest"
DESC = "A/B 实验：lift + 显著性 + SRM 失配检测（能力域5拆细）"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--group", required=True, help="分组列")
    p.add_argument("--control", required=True, help="对照组取值")
    p.add_argument("--treatment", required=True, help="处理组取值")
    p.add_argument("--metric", required=True, help="指标列（二进制=转化率，连续=均值）")


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    return {"abtest": _abtest(rows, args.group, args.control,
                              args.treatment, args.metric)}


def _abtest(rows, group, control, treatment, metric):
    gc = [r for r in rows if str(r.get(group)) == control]
    gt = [r for r in rows if str(r.get(group)) == treatment]
    val_c = [float(r[metric]) for r in gc if c.isnum(r.get(metric))]
    val_t = [float(r[metric]) for r in gt if c.isnum(r.get(metric))]
    mc = sum(val_c) / len(val_c) if val_c else 0.0
    mt = sum(val_t) / len(val_t) if val_t else 0.0
    lift = (mt - mc) / mc if mc else 0.0

    res = _stats.welch_t(val_c, val_t, control, treatment)

    # SRM：样本比例失配卡方（预期 50/50）
    nc, nt = len(val_c), len(val_t)
    n = nc + nt
    exp = n / 2
    srm = (nc - exp) ** 2 / exp + (nt - exp) ** 2 / exp if n else 0.0

    th = _stats.stat_thresholds()
    srm_crit = th.get("srm_critical_chi2", 3.841)
    impact_min = c.load_thresholds().get("abtest", {}).get("impact_min_pct", 3.0)

    srm_flag = srm > srm_crit
    significant = res.get("significant", False)
    lift_pct = round(lift * 100, 2)
    decision = "srm_rerun" if srm_flag else (
        "ship" if (significant and lift_pct >= impact_min) else "no_ship")
    return {"control_mean": round(mc, 4), "treatment_mean": round(mt, 4),
            "lift_pct": lift_pct, "impact_min_pct": impact_min,
            "t": res.get("t"), "p_value_approx": res.get("p_value_approx"),
            "significant": significant,
            "srm_chi2": round(srm, 4), "srm_critical_chi2": srm_crit,
            "srm_flag": srm_flag, "decision": decision,
            "note": "决策表：显著正且 lift≥impact_min 且无SRM=ship；"
                    "否则 no_ship；SRM 异常=重跑"}