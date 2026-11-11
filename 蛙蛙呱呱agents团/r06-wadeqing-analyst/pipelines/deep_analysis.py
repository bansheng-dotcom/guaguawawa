# -*- coding: utf-8 -*-
"""R06 蛙得清 · 深度分析流水线（Deep Analysis Pipeline）。

解决「报告全面但厚度/深度不足」的 R06 落地方案（其余角色按同一范式复制）：

    薄报告（改造前）   = 跑一个技能 → 三段文字 + 一张小表
    厚报告（改造后）   = 一次出具串起七步分析链，每步都留下可复算数字与图：

        ① 质量体检 quality.audit         → L1 真实性门禁（缺失/重复/离群）
        ② 时间趋势 explore.trend         → 折线图 + 首末变化
        ③ 时序诊断 explore.time_series   → 斜率/季节强度/异常点
        ④ 结构拆解 rootcause.decompose   → 瀑布图 + 贡献度表（谁在拉动总变化）
        ⑤ 帕累托下钻 rootcause.drilldown → 帕累托图 + 80/20 结论
        ⑥ 分布形态 describe              → 直方图 + 偏度/分位
        ⑦ 显著性检验 ttest / anova       → 组间差异是否真实（不是噪声）

纪律（对齐 REP-001）：
    - 每一步都调**角色自己的技能模块**，不复制计算逻辑；
    - 任一步失败只降级该节（写入 note），不伪造数字；
    - 图表全部走 `agents/shared/report_depth.py` → core/charts 48 型 SVG。
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))   # pipelines/
_ROLE = os.path.dirname(_HERE)                       # 角色根
_AGENTS = os.path.dirname(_ROLE)                     # 蛙蛙呱呱agents团/
_REPO = os.path.dirname(_AGENTS)                     # 蛙蛙呱呱/
for _p in (_HERE, _ROLE, _AGENTS, _REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents.shared import report_depth as D  # noqa: E402


# --------------------------------------------------------------------------- #
# 技能调用：统一适配 run(args) 与 action 函数两种风格
# --------------------------------------------------------------------------- #
def _skill(name: str):
    from skills import SKILLS
    return next((m for m in SKILLS if m.NAME == name), None)


def _run(name: str, action: str, **kwargs) -> Dict[str, Any]:
    mod = _skill(name)
    if mod is None:
        return {"ok": False, "error": f"未知技能 {name}"}
    ns = argparse.Namespace(action=action, **kwargs)
    try:
        out = mod.run(ns)
    except Exception as exc:  # noqa: BLE001  单步失败降级，不伪造
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}",
                "skill": name, "action": action}
    return out if isinstance(out, dict) else {"ok": True, "value": out}


def _pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.2f}%"
    except (TypeError, ValueError):
        return "—"


def _f(x: Any, digits: int = 2) -> str:
    try:
        return f"{float(x):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


# --------------------------------------------------------------------------- #
# 主流水线
# --------------------------------------------------------------------------- #
def analyze(csv_path: str, value_col: str, date_col: str = "date",
            dim_col: Optional[str] = None, period_col: Optional[str] = None,
            before: Optional[str] = None, after: Optional[str] = None,
            pk: Optional[str] = None,
            decompose_input: Optional[str] = None) -> Dict[str, Any]:
    """跑通七步分析链，返回 {steps, figures, sections, appendix, signals}。

    :param csv_path: 时间序列输入（趋势/时序/分布/集中度用它）
    :param decompose_input: 前后期横截面输入（结构拆解用它）。
        缺省与 csv_path 相同；当时间序列跨很多期时，务必单独给一份
        「只有 before/after 两期」的横截面，否则 decompose 会把其余所有期
        都算进 after 侧，导致贡献度失真（本模块在 notes 里显式声明这一点）。
    """
    dec_path = decompose_input or csv_path
    steps: Dict[str, Any] = {}
    figures: List[Dict[str, Any]] = []
    sections: List[Dict[str, Any]] = []
    appendix: List[Dict[str, Any]] = []
    signals: List[Dict[str, Any]] = []

    # ① 质量体检 ---------------------------------------------------------
    # 注意：quality.audit 的参数名是 `date`（不是 date_col），传错会 AttributeError。
    q = _run("quality", "audit", input=csv_path, pk=pk, date=date_col)
    steps["quality"] = q
    q_score = q.get("overall_score")
    q_grade = q.get("grade")
    findings = q.get("findings") or []
    critical = [f for f in findings if str(f.get("sev", "")).upper() == "CRITICAL"]
    if critical:
        signals.append({"level": "L1", "severity": "BLOCKER",
                        "text": f"数据质量硬伤 {len(critical)} 项，结论可信度受限："
                                + "；".join(str(f.get("note", "")) for f in critical[:3])})
    if findings:
        appendix.append({
            "title": "数据质量六维明细（quality.audit）",
            "table": D.table(
                ["维度", "严重级", "说明", "读数"],
                [[f.get("dim", ""), f.get("sev", ""), f.get("note", ""),
                  _f(f.get("pct"), 2)] for f in findings],
                "quality.audit findings"),
            "note": f"总体得分 {_f(q_score, 1)} · 评级「{q_grade}」",
        })

    # ② 时间趋势 ---------------------------------------------------------
    tr = _run("explore", "trend", input=csv_path, date=date_col, value=value_col)
    steps["trend"] = tr
    series = tr.get("series") or []
    total = tr.get("total")
    if series:
        first_v, last_v = float(series[0].get("value", 0)), float(series[-1].get("value", 0))
        delta = last_v - first_v
        delta_pct = (delta / first_v * 100) if first_v else 0.0
        fig = D.line_from_series(series, name=value_col,
                                 title=f"{value_col} 逐期走势（{series[0]['date']} → "
                                       f"{series[-1]['date']}）",
                                 note=f"共 {len(series)} 期 · 首值 {_f(first_v)} · "
                                      f"末值 {_f(last_v)} · 首末变化 {delta_pct:+.2f}%")
        if fig:
            fig["fallback_table"] = D.table(
                ["期次", value_col],
                [[s.get("date"), _f(s.get("value"))] for s in series],
                "原始序列")
            figures.append(fig)
        sections.append({
            "title": "时间趋势：整体在扩张还是收缩",
            "content": (f"区间合计 {_f(total)}，{len(series)} 期均值 {_f((total or 0) / max(len(series), 1))}。"
                        f"首末变化 {delta_pct:+.2f}%（{_f(first_v)} → {_f(last_v)}），"
                        f"绝对变动 {delta:+,.2f}。判断趋势方向必须结合时序诊断的斜率，"
                        "单看首末两点会被中间波动误导。"),
            "bullets": [f"最高期：{max(series, key=lambda s: s.get('value', 0))['date']} "
                        f"({_f(max(s.get('value', 0) for s in series))})",
                        f"最低期：{min(series, key=lambda s: s.get('value', 0))['date']} "
                        f"({_f(min(s.get('value', 0) for s in series))})"],
        })
    else:
        sections.append({"title": "时间趋势：整体在扩张还是收缩",
                         "content": f"趋势计算未产出（{tr.get('error') or '输入缺少可用日期列'}）。"
                                    "结论不得在缺趋势的情况下给出。"})

    # ③ 时序诊断 ---------------------------------------------------------
    ts = _run("explore", "time_series", input=csv_path, date=date_col,
              value=value_col, window=3)
    steps["time_series"] = ts
    trend_info = ts.get("trend") or {}
    anomalies = (ts.get("anomalies") or {}).get("top") or []
    anom_count = (ts.get("anomalies") or {}).get("count", 0)
    season_strength = ts.get("seasonality_strength")
    if ts.get("series"):
        sections.append({
            "title": "时序诊断：斜率、季节强度与异常点",
            "content": (f"斜率 {_f(trend_info.get('slope_per_step'), 4)}/期，"
                        f"方向「{trend_info.get('direction', '—')}」，"
                        f"季节强度 {_f(season_strength, 3)}"
                        f"（{'强季节，同比口径必须对齐' if ts.get('seasonality_strong') else '弱季节'}）。"
                        f"滚动中位数带检测到 {anom_count} 个异常点——"
                        "这些点在做归因前必须先单独解释，否则会把噪声写成根因。"),
            "bullets": ([f"异常点：第 {a.get('index', 0) + 1} 期（{series[a['index']]['date']}）"
                         f" 值 {_f(a.get('value'))}，滚动中位 {_f(a.get('rolling_median'))}，"
                         f"偏离 {_f(a.get('deviation'))}"
                         for a in anomalies[:5] if isinstance(a, dict)]
                        or ["未检测到显著异常点，序列可直接进入结构拆解。"]),
            "table": D.table(
                ["日期", value_col, "滚动均值", "异常"],
                [[s.get("date"), _f(s.get("value")), _f(s.get("moving_avg")),
                  "⚠️" if s.get("anomaly") else ""] for s in ts["series"]],
                "time_series 原始输出（移动均值窗口 3）"),
        })
        if anomalies:
            _dates = []
            for a in anomalies[:4]:
                if isinstance(a, dict) and isinstance(a.get("index"), int) \
                        and 0 <= a["index"] < len(series):
                    _dates.append(str(series[a["index"]]["date"]))
            signals.append({"level": "L1", "severity": "WARN",
                            "text": f"{anom_count} 个异常点需单独解释"
                                    + (f"：{'、'.join(_dates)}" if _dates else "")})

    # ④ 结构拆解（瀑布） ---------------------------------------------------
    if dim_col and period_col and before and after:
        dec = _run("rootcause", "decompose", input=dec_path, dim=dim_col,
                   value=value_col, period=period_col, before=before, after=after)
        steps["decompose"] = dec
        segs = dec.get("segments") or []
        total_change = dec.get("total_change", 0)
        if segs:
            wf = D.waterfall_from_segments(segs, total_change,
                                           title=f"{before} → {after} 的 "
                                                 f"{value_col} 变化拆解（按 {dim_col}）")
            if wf:
                wf["fallback_table"] = D.table(
                    [dim_col, "前期", "后期", "变化", "贡献占比"],
                    [[s.get("segment"), _f(s.get("before")), _f(s.get("after")),
                      _f(s.get("delta")), f"{s.get('contribution_pct', 0):.2f}%"]
                     for s in segs], "贡献明细")
                figures.append(wf)
            top = max(segs, key=lambda s: abs(s.get("contribution_pct", 0)))
            sections.append({
                "title": f"结构拆解：{before} → {after} 的 {value_col} 变化由谁拉动",
                "content": (f"总变化 {_f(total_change)}。按「{dim_col}」拆解后，"
                            f"贡献度最大的是「{top.get('segment')}」"
                            f"（{top.get('contribution_pct', 0):.2f}%，"
                            f"变化 {_f(top.get('delta'))}）。"
                            f"其余分段贡献度 < {dec.get('impact_min_pct', 3)}% 的判定为 minor，"
                            "可停止下钻——这是控制报告膨胀的硬规则，不是遗漏。"),
                "table": D.table(
                    [dim_col, "前期", "后期", "变化", "贡献占比", "是否 minor"],
                    [[s.get("segment"), _f(s.get("before")), _f(s.get("after")),
                      _f(s.get("delta")), f"{s.get('contribution_pct', 0):.2f}%",
                      "是" if s.get("below_impact_min") else "否"] for s in segs],
                    "贡献分解（contribution_pct = delta / 总变化）"),
            })

    # ⑤ 帕累托下钻 -------------------------------------------------------
    if dim_col:
        dd = _run("rootcause", "drilldown", input=dec_path, dim=dim_col,
                  value=value_col)
        steps["drilldown"] = dd
        items = dd.get("items") or []
        if items:
            pf = D.pareto_from_items(items, dd.get("pareto_threshold_pct", 80),
                                     title=f"{dim_col} 的帕累托集中度")
            if pf:
                pf["fallback_table"] = D.table(
                    [dim_col, "值", "占比", "累计占比", "排名"],
                    [[i.get("segment"), _f(i.get("value")),
                      f"{i.get('share_pct', 0):.2f}%",
                      f"{i.get('cum_share_pct', 0):.2f}%", i.get("rank")]
                     for i in items], "帕累托明细")
                figures.append(pf)
            n80 = dd.get("pareto_top_n_for_80pct")
            sections.append({
                "title": f"集中度：{dim_col} 是否被少数项撑起",
                "content": (f"合计 {_f(dd.get('total'))}。按 80/20 口径，"
                            f"前 {n80} 项即覆盖 80% 的量——"
                            + ("结构高度集中，任何一项波动都会放大成整体波动，"
                               "必须在护栏里为它单设阈值。"
                               if n80 and n80 <= 2 else
                               "结构相对分散，单点故障风险可控，但仍需盯前两名。")),
                "bullets": [f"{i.get('rank')}. {i.get('segment')}："
                            f"{_f(i.get('value'))}（占 {i.get('share_pct', 0):.2f}%）"
                            for i in items[:4]],
            })

    # ⑥ 分布形态 ---------------------------------------------------------
    ds = _run("describe", "describe", input=csv_path, col=value_col) \
        if _skill("describe") else {}
    steps["describe"] = ds
    stats = (ds.get("describe") or {}).get(value_col) or {}
    if stats:
        sections.append({
            "title": "分布形态：均值能不能代表这个指标",
            "content": (f"样本 {stats.get('count')} 个，均值 {_f(stats.get('mean'))}、"
                        f"中位 {_f(stats.get('median'))}，标准差 {_f(stats.get('std'))}，"
                        f"偏度 {_f(stats.get('skew'), 4)}。"
                        + ("偏度接近 0，均值可作代表值。"
                           if abs(float(stats.get("skew") or 0)) < 0.5 else
                           "偏度偏离 0 较明显，均值会被尾部拖拽，"
                           "对外口径应改用中位数并同时披露分位。")
                        + f" p5={_f(stats.get('p5'))} / p95={_f(stats.get('p95'))}，"
                          "这是设定“正常波动带”的原始依据。"),
            "table": D.table(
                ["统计量", "取值"],
                [["样本数", stats.get("count")], ["均值", _f(stats.get("mean"))],
                 ["中位数", _f(stats.get("median"))], ["标准差", _f(stats.get("std"))],
                 ["最小值", _f(stats.get("min"))], ["最大值", _f(stats.get("max"))],
                 ["p5", _f(stats.get("p5"))], ["p95", _f(stats.get("p95"))],
                 ["偏度", _f(stats.get("skew"), 4)]],
                "describe 输出（单列分布）"),
        })

    # ⑦ 显著性检验 -------------------------------------------------------
    if dim_col:
        tt = _run("ttest", "ttest", input=csv_path, value=value_col,
                  group=dim_col, group_a=None, group_b=None) \
            if _skill("ttest") else {}
        an = _run("anova", "anova", input=csv_path, value=value_col,
                  group=dim_col) if _skill("anova") else {}
        steps["anova"] = an
        av = an.get("anova") or {}
        if av:
            sections.append({
                "title": f"显著性：{dim_col} 之间的差异是真实差异还是噪声",
                "content": (f"单因素方差分析：F={_f(av.get('f_statistic'), 3)}，"
                            f"df=({av.get('df_between')}, {av.get('df_within')})，"
                            f"η²={_f(av.get('eta_squared'), 4)}，"
                            f"效应量评级「{av.get('effect_grade', '—')}」。"
                            + ("组间差异不是噪声，可以据此分配资源。"
                               if float(av.get("f_statistic") or 0) > 3.0 else
                               "组间差异不足以支撑差异化策略，先扩样本再决策。")
                            + " 注意：显著 ≠ 重要，η² 才是“差异有多大”的口径。"),
                "table": D.table(
                    ["组", "均值", "n"],
                    [[g.get("group") if isinstance(g, dict) else g,
                      _f(g.get("mean")) if isinstance(g, dict) else "—",
                      g.get("n") if isinstance(g, dict) else "—"]
                     for g in (av.get("groups") or [])],
                    "分组均值（anova 输入口径）"),
            })

    return {"steps": steps, "figures": figures, "sections": sections,
            "appendix": appendix, "signals": signals,
            "quality": {"score": q_score, "grade": q_grade,
                        "critical": len(critical)}}


__all__ = ["analyze"]
