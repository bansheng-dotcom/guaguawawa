# -*- coding: utf-8 -*-
"""core/question_derive —— 由数据画像推导问题，而不是从题库里挑题。

规则（每条都是「数据形状 → 能问什么」，不是写死的问题文本）：
  T1 时间轴 + 度量（≥5 点）        → 趋势/斜率（regression time~measure）
  T2 两个度量（同一批观测）         → 关系（correlate）
  T3 维度恰 2 组 + 度量            → 组间差异（ttest）
  T4 维度 ≥3 组 + 度量             → 结构/贡献（rootcause drilldown）
  T5 只有度量、无时间无维度         → 分布（describe）

问题措辞、图型、数据点全部来自画像里的列名与数值；阈值只做方向性设定
（斜率 0、相关 0.5、头部占比 20%），不引用任何具体业务数字。
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any, Dict, List

from core.data_profile import profile_dir


def _read(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _vals(rows: List[Dict[str, str]], col: str) -> List[float]:
    out = []
    for r in rows:
        try:
            out.append(float(r[col]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _distinct(rows: List[Dict[str, str]], col: str) -> List[str]:
    seen: List[str] = []
    for r in rows:
        v = str(r.get(col, ""))
        if v and v not in seen:
            seen.append(v)
    return seen


def derive_questions(role: str, intent: str, data_dir: str) -> List[Dict[str, Any]]:
    prof = profile_dir(data_dir)
    qs: List[Dict[str, Any]] = []

    for t in prof["tables"]:
        f = t["file"]
        stem = Path(f).stem
        times, measures, dims = t["time"], [m for m in t["measures"]
                                            if not re.search(r"share|pct|ratio|占比", m, re.I)], t["dimensions"]
        rows = _read(f)

        # T1 趋势
        if times and measures and len(rows) >= 5:
            tm, me = times[0], measures[0]
            ys = _vals(rows, me)
            xl = [str(r[tm]) for r in rows]
            if len(ys) == len(xl):
                qs.append({
                    "id": f"trend_{stem}_{me}",
                    "question": f"「{me}」在 {tm} 上每年变化多少？",
                    "hypothesis": f"{me} 与 {tm} 同向，斜率大于 0。",
                    "skill": "regression",
                    "command": ["regression", "--input", f, "--x", tm, "--y", me],
                    "numbers": {f"{me} 斜率": "regression.slope",
                                "R²": "regression.r_squared", "p": "regression.p_exact"},
                    "judge": {"kind": "threshold", "field": f"{me} 斜率", "value": 0},
                    "falsify": f"换一段 {tm} 重跑，若斜率转负，趋势判断作废。",
                    "chart": {"shape": "time_series", "data": {
                        "title": f"{me} 随 {tm} 的变化", "unit": "—", "source": Path(f).name,
                        "subtitle": f"{len(xl)} 期 · 单序列 · 时间轴按源表顺序",
                        "note": "斜率为最小二乘拟合，不解释季节性",
                        "x": xl, "y": ys, "name": me}},
                })

        # T2 关系
        if len(measures) >= 2 and len(rows) >= 6:
            a, b = measures[0], measures[1]
            pts = []
            for i, r in enumerate(rows[:30]):
                try:
                    pts.append({"x": float(r[a]), "y": float(r[b]), "label": str(i + 1)})
                except (KeyError, TypeError, ValueError):
                    continue
            qs.append({
                "id": f"rel_{stem}_{a}_{b}",
                "question": f"「{a}」与「{b}」是否同向？",
                "hypothesis": f"{a} 与 {b} 正相关（r ≥ 0.5）。",
                "skill": "correlate",
                "command": ["correlate", "--input", f, "--col-a", a, "--col-b", b],
                "numbers": {"相关系数 r": "correlation.pearson_r"},
                "judge": {"kind": "threshold", "field": "相关系数 r", "value": 0.5},
                "falsify": "加一组样本重算，若 r 掉到 0.5 以下，同向不成立。",
                "chart": {"shape": "relationship", "data": {
                    "title": f"{a} vs {b}", "unit": "—", "source": Path(f).name,
                    "subtitle": f"{len(pts)} 个样本 · 两列原始值 · 未剔除离群点",
                    "note": "同向不等于因果，相关系数需配合业务解释",
                    "xlabel": a, "ylabel": b, "points": pts}},
            })

        # T3 / T4 维度
        for dm in dims:
            groups = _distinct(rows, dm)
            me = next((m for m in measures if m.lower() not in ("share", "pct")), None)
            if not me:
                continue
            if len(groups) == 2 and len(rows) >= 6:
                qs.append({
                    "id": f"diff_{stem}_{dm}",
                    "question": f"「{dm}」的两组之间，「{me}」有没有显著差异？",
                    "hypothesis": f"两组 {me} 差异显著（p < 0.05）。",
                    "skill": "ttest",
                    "command": ["ttest", "--input", f, "--value", me, "--group", dm,
                                "--group-a", groups[0], "--group-b", groups[1]],
                    "numbers": {"均值差": "welch_t.diff", "p": "welch_t.p_exact"},
                    "judge": {"kind": "p_value", "field": "p", "alpha": 0.05},
                    "falsify": "换非参数检验重跑，若 p 仍大于 0.05，差异不成立。",
                })
            elif len(groups) >= 3 and len(rows) <= 40:
                items = [{"label": r[dm], "value": float(r[me])} for r in rows
                         if r.get(me) not in (None, "")]
                qs.append({
                    "id": f"struct_{stem}_{dm}",
                    "question": f"「{me}」的差异主要由哪个 {dm} 贡献？",
                    "hypothesis": f"{dm} 的头部一组占比超过 20%，结构集中。",
                    "skill": "rootcause.drilldown",
                    "command": ["rootcause", "drilldown", "--input", f, "--dim", dm, "--value", me],
                    "numbers": {"合计": "total", "头部占比": "items.0.share_pct"},
                    "judge": {"kind": "threshold", "field": "头部占比", "value": 20},
                    "falsify": "若头部三组累计不到 50%，集中判断不成立。",
                    "chart": {"shape": "cross_section", "data": {
                        "title": f"分 {dm} 的 {me}", "unit": "—", "source": Path(f).name,
                        "subtitle": f"{len(items)} 个 {dm} 分组 · {me} · 降序",
                        "note": "按量级排序，长尾组不代表无价值",
                        "items": items}},
                })

        # T5 分布
        if not times and not dims and measures and len(rows) >= 5:
            me = measures[0]
            qs.append({
                "id": f"dist_{stem}_{me}",
                "question": f"「{me}」的分布有多分散？",
                "hypothesis": f"{me} 的离散度较大，平均值不足以代表。",
                "skill": "describe",
                "command": ["describe", "--input", f, "--col", me],
                "numbers": {"均值": f"describe.{me}.mean", "标准差": f"describe.{me}.std"},
                "judge": {"kind": "threshold", "field": "标准差", "value": 0.01},
                "falsify": "剔除极值后重算，若标准差掉一个量级，判断作废。",
            })

    return qs
