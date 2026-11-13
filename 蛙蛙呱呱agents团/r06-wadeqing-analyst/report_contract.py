# -*- coding: utf-8 -*-
"""R06 蛙得清 · 报告映射（result → report contract 的精细桥）。

给 core/report_bridge.emit 的 specialist 参数：把数据分析技能的真实 result
翻译成带图表、带根因、带统计检验的编辑级 contract。返回 None 时回退通用映射。

这是「数据结论」角色的样板：把 result 的结构化字段（trend/groups/funnel/
segments/abtest）映射成 core/report_renderer.py 认识的 chart 结构。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _chart_meta(title: str, unit: str, source: str) -> Dict[str, Any]:
    return {"title": title, "unit_meta": unit, "source": source}


def r06_contract(result: Dict[str, Any], skill: str, action: str,
                 intent: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    # 证据包优先：有 claims 就走通用写作器（report_specs/writing/r06.yaml 驱动）
    if isinstance(data, dict) and data.get("claims"):
        try:
            from shared import report_writer
            got = report_writer.build("r06", data, result, intent)
            if got:
                return got
        except Exception:  # noqa: BLE001  写作器失败回落原有映射，不静默出错
            pass

    typ = result.get("type", "")

    # ---- explore.trend → 折线图（含异常窗口/参考线，可选）----
    if typ == "trend" and result.get("series"):
        series = result["series"]
        xlabels = [s["date"] for s in series]
        values = [s["value"] for s in series]
        total = result.get("total")
        chart = {
            "type": "line",
            "title": "时间趋势",
            "unit_meta": "按日期 · 值",
            "source": "explore trend（确定性计算）",
            "xlabels": xlabels,
            "series": [{"name": "值", "values": values, "accent": True}],
        }
        sections = [{
            "index": 1, "title": "时间趋势", "question": "数值随时间如何变化？拐点在哪？",
            "chart": chart,
            "reading": [
                {"strong": "区间：", "text": f"{xlabels[0]} → {xlabels[-1]}，共 {len(xlabels)} 期"},
                {"strong": "合计：", "text": f"{total:,.2f}" if total is not None else "—"},
            ],
            "boundary": {"title": "证据边界",
                         "text": "仅基于提供的时间序列；未做季节分解，不推断未来。"},
        }]
        return _base(result, skill, action, intent, "数据结论报告",
                     _trend_metrics(result, total), "时间趋势与总量", sections)

    # ---- explore.groupby → 横向柱图 ----
    if typ == "groupby" and result.get("groups"):
        groups = sorted(result["groups"], key=lambda g: -g.get("sum", 0))
        chart = {
            "type": "hbar",
            "title": "分组合计对比",
            "unit_meta": "按组 · 合计",
            "source": "explore groupby（确定性计算）",
            "bars": [{"label": g["group"], "value": g["sum"],
                      "value_label": f"{g['sum']:,.1f}",
                      "sub": f"均值 {g.get('mean', 0):,.1f} · n={g.get('n', 0)}",
                      "weight": "context"} for g in groups],
        }
        sections = [{
            "index": 1, "title": "分组合计对比",
            "question": "哪一组贡献最大？各组均值与样本量如何？",
            "chart": chart,
            "reading": [{"strong": "组数：", "text": f"{len(groups)} 组"},
                        {"strong": "排序：", "text": "按合计降序"}],
            "boundary": {"title": "证据边界",
                         "text": "仅描述分组统计，不推断组间因果差异（需 t 检验）。"},
        }]
        return _base(result, skill, action, intent, "数据结论报告",
                     _group_metrics(result), "分组合计", sections)

    # ---- explore.funnel → 漏斗图 ----
    if typ == "funnel" and result.get("stages"):
        stages = result["stages"]
        chart = {
            "type": "funnel",
            "title": "转化漏斗",
            "unit_meta": "逐级人数",
            "source": "explore funnel（确定性计算）",
            "stages": [{"label": s["stage"], "value": s["count"]} for s in stages],
        }
        worst = next((s for s in stages if s.get("drop_alert")), None)
        reading = [{"strong": "阶段数：", "text": f"{len(stages)} 级"}]
        if worst:
            reading.append({"strong": "主要流失：",
                            "text": f"{worst['stage']} 骤降 {worst['step_drop_pct']:.1f}%"})
        sections = [{
            "index": 1, "title": "转化漏斗",
            "question": "用户在哪些步骤流失？最大漏损点在哪？",
            "chart": chart, "reading": reading,
            "boundary": {"title": "证据边界",
                         "text": "漏斗只反映顺序计数，不区分流失原因。"},
        }]
        return _base(result, skill, action, intent, "数据结论报告",
                     _funnel_metrics(result), "转化漏斗", sections)

    # ---- rootcause.decompose → 横向贡献图 + 明细表 ----
    if result.get("dimension") and result.get("segments"):
        segs = result["segments"]
        chart = {
            "type": "hbar",
            "title": f"贡献分解（{result['dimension']}）",
            "unit_meta": "贡献 delta",
            "source": "rootcause decompose（确定性计算）",
            "bars": [{"label": s["segment"], "value": s.get("delta", 0),
                      "value_label": f"{s.get('delta', 0):,.1f}",
                      "sub": f"{s.get('contribution_pct', 0):.1f}%",
                      "weight": "critical" if s.get("delta", 0) < 0 else "context"}
                     for s in sorted(segs, key=lambda x: -x.get("delta", 0))],
        }
        rows = [[{"text": s["segment"]},
                 {"text": f"{s.get('before', 0):,.1f}"},
                 {"text": f"{s.get('after', 0):,.1f}"},
                 {"text": f"{s.get('delta', 0):,.1f}"},
                 {"text": f"{s.get('contribution_pct', 0):.1f}%"}]
                for s in segs]
        sections = [{
            "index": 1, "title": "贡献分解",
            "question": f"总变化 {result.get('total_change', 0):,.1f} 由哪些维度贡献？",
            "chart": chart,
            "reading": [{"strong": "总变化：", "text": f"{result.get('total_change', 0):,.1f}"},
                        {"strong": "影响下限：", "text": f"{result.get('impact_min_pct', 0):.1f}%"}],
            "table": {"caption": "贡献明细", "columns": [
                {"text": "维度"}, {"text": "before"}, {"text": "after"},
                {"text": "delta"}, {"text": "贡献占比"}], "rows": rows},
            "boundary": {"title": "证据边界",
                         "text": "贡献分解是算术归因，不等同于因果；未观测混杂未消除。"},
        }]
        return _base(result, skill, action, intent, "数据结论报告",
                     _decompose_metrics(result), "贡献分解", sections)

    # ---- abtest → 结论 + 对比柱 ----
    if result.get("abtest"):
        ab = result["abtest"]
        chart = {
            "type": "vbar",
            "title": "A/B 对比",
            "unit_meta": "组均值",
            "source": "abtest（确定性计算）",
            "vbars": [
                {"label": "对照组", "value": ab.get("control_mean", 0),
                 "weight": "context"},
                {"label": "实验组", "value": ab.get("treatment_mean", 0),
                 "weight": "healthy" if ab.get("significant") else "context"},
            ],
            "annotate": {"x": 0.5, "y": 0.28,
                         "line1": f"lift {ab.get('lift_pct', 0):.1f}%",
                         "line2": f"p={ab.get('p_value_approx', 0):.3f}"},
        }
        verdict = ("显著，可 ship" if ab.get("significant")
                   and ab.get("lift_pct", 0) >= ab.get("impact_min_pct", 0)
                   else "不显著，no_ship")
        sections = [{
            "index": 1, "title": "A/B 检验",
            "question": "实验组相对对照组是否显著更优？",
            "chart": chart,
            "reading": [
                {"strong": "提升：", "text": f"{ab.get('lift_pct', 0):.2f}%"},
                {"strong": "p 值：", "text": f"{ab.get('p_value_approx', 0):.3f}（{verdict}）"},
                {"strong": "SRM：", "text": f"χ²={ab.get('srm_chi2', 0):.2f}（{'失衡' if ab.get('srm_flag') else '正常'}）"},
            ],
            "boundary": {"title": "证据边界",
                         "text": "p 值≠效应量；SRM 失衡时结论不可信。"},
        }]
        return _base(result, skill, action, intent, "数据结论报告",
                     _abtest_metrics(ab), "A/B 检验", sections)

    return None  # 其余动作回退通用映射


# --------------------------------------------------------------------------- #
def _base(result, skill, action, intent, doc_type, metric_strip, summary_title,
          sections) -> Dict[str, Any]:
    ok = bool(result.get("ok", True))
    status = "healthy" if ok else "critical"
    return {
        "doc_type": f"{doc_type} · 蛙得清",
        "title_lines": [f"蛙得清 · {skill}/{action}", intent],
        "standfirst": summary_title,
        "meta": ["角色 r06 蛙得清（数据分析师）", "渲染器 core/report_renderer.py"],
        "metric_strip": metric_strip,
        "summary": [{"label": "结论：", "text": summary_title},
                    {"label": "说明：", "text": "由技能真实运行结果确定性生成，数字可回溯。"}],
        "sections": sections,
        "notes": {"summary": "口径、来源与证据边界",
                  "items": [{"label": "来源：",
                             "text": f"R06 skills 的 {skill}/{action} 动作（确定性计算，无 LLM）。"},
                            {"label": "边界：",
                             "text": "结论仅对本次输入成立；未观测混杂未消除。"}]},
        "footer": ["R06 蛙得清 · 数据分析师", "core/report_renderer.py 确定性渲染"],
    }


def _metric(label, value, note, status="none"):
    return {"label": label, "value": value, "note": note, "status": status}


def _trend_metrics(result, total):
    series = result.get("series", [])
    return [
        _metric("期数", str(len(series)), "数据点", "none"),
        _metric("合计", f"{total:,.1f}" if total is not None else "—", "区间总和", "accent"),
        _metric("首值", f"{series[0]['value']:,.1f}" if series else "—", "起点", "none"),
        _metric("末值", f"{series[-1]['value']:,.1f}" if series else "—", "终点", "none"),
    ]


def _group_metrics(result):
    groups = result.get("groups", [])
    top = max(groups, key=lambda g: g.get("sum", 0)) if groups else {}
    return [
        _metric("组数", str(len(groups)), "分组", "none"),
        _metric("最大组", str(top.get("group", "—")), "按合计", "accent"),
        _metric("最大合计", f"{top.get('sum', 0):,.1f}", "sum", "none"),
        _metric("组均值区间", "—", "见明细", "none"),
    ]


def _funnel_metrics(result):
    stages = result.get("stages", [])
    first = stages[0] if stages else {}
    last = stages[-1] if stages else {}
    return [
        _metric("阶段数", str(len(stages)), "漏斗级数", "none"),
        _metric("入口", f"{first.get('count', 0):,.0f}", "首级", "accent"),
        _metric("出口", f"{last.get('count', 0):,.0f}", "末级", "none"),
        _metric("漏损阈值", f"{result.get('drop_warn_pct', 0):.0f}%", "drop_alert", "watch"),
    ]


def _decompose_metrics(result):
    return [
        _metric("总变化", f"{result.get('total_change', 0):,.1f}", "delta", "accent"),
        _metric("维度", str(result.get('dimension', '—')), "分解轴", "none"),
        _metric("分支数", str(len(result.get('segments', []))), "贡献项", "none"),
        _metric("影响下限", f"{result.get('impact_min_pct', 0):.1f}%", "minor 阈值", "watch"),
    ]


def _abtest_metrics(ab):
    sig = ab.get("significant")
    return [
        _metric("提升", f"{ab.get('lift_pct', 0):.2f}%", "lift", "accent"),
        _metric("p 值", f"{ab.get('p_value_approx', 0):.3f}", "Welch t", "none"),
        _metric("显著性", "显著" if sig else "不显著", "α=0.05", "healthy" if sig else "watch"),
        _metric("SRM", "失衡" if ab.get("srm_flag") else "正常", "χ²", "critical" if ab.get("srm_flag") else "healthy"),
    ]
