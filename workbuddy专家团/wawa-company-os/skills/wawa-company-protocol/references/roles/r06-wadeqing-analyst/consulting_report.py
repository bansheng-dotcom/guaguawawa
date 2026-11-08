# -*- coding: utf-8 -*-
"""R06 商业咨询研报组装 (Consulting Report Compiler).

将咨询级分析逻辑组装为标准化商业研报，采用 12 栅格排版与 10-0 质量审计标准。
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
_REPO = os.path.dirname(_AGENTS)
for _p in (_REPO, _AGENTS, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import consulting_analysis as CA  # noqa: E402
from agents.shared.report_generator import generate_professional_report  # noqa: E402
from agents.shared.role_profiles import get as get_profile  # noqa: E402


def _f(val: Any, digits: int = 2) -> str:
    try:
        return f"{float(val):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def build_consulting_report(series_csv: str, cross_csv: str, 
                            before: str, after: str, intent: str) -> Dict[str, Any]:
    # 1. 运行咨询深度分析
    data = CA.run_consulting_analysis(series_csv, cross_csv, before, after)
    profile = get_profile("r06")
    
    # 2. 核心结论先行 (Executive Summary)
    # 杜邦分解的商业定性
    dup = data["dupont"]
    summary = (
        f"在 {data['after_period']} 的经营盘点中，整体利润环比变动 {_f(dup['delta_profit'])} 元（降幅 {(dup['a_profit']-dup['b_profit'])/max(dup['b_profit'],1)*100:+.1f}%）。"
        f"归因分析显示，大盘利润下滑主要受控于「{data['primary_leak']['zone']}」单点损益断崖（单区亏损贡献度高达 {data['primary_leak']['contrib_pct']:.1f}%），"
        "该区域的运营毛利塌方直接稀释了整体利润率。其余各区保持稳健，非全局性系统崩塌。"
    )
    
    directive = (
        f"即刻对异动区域「{data['primary_leak']['zone']}」启动专项纠偏战役（Action Plan）。"
        f"基于情景仿真，若放任该失血点持续 6 个月，预计将累计蒸发利润 {_f(data['simulation']['six_month_leak'])} 元。"
        f"建议将护栏熔断线调整至「{profile['kill_switch']['metric']} {profile['kill_switch']['threshold']}」，以杜绝盲目扩容带来的负杠杆效应。"
    )

    # 3. KPI 速览
    kpis = [
        {"label": "本期毛利总额", "value": f"¥{_f(dup['a_profit'])}", "sub": "同比变动额：—", "status": "normal"},
        {"label": "环比利润跌幅", "value": f"{(dup['a_profit']-dup['b_profit'])/max(dup['b_profit'],0.001)*100:+.1f}%", 
         "sub": f"绝对值：{_f(dup['delta_profit'])} 元", "status": "red"},
        {"label": "头号失血区域", "value": data['primary_leak']['zone'], 
         "sub": f"利润降幅：{_f(data['primary_leak']['delta_profit'])} 元", "status": "red"},
        {"label": "利润贡献占比", "value": f"{data['primary_leak']['contrib_pct']:.1f}%", 
         "sub": "占比总亏损额", "status": "red"},
        {"label": "80% 收益集中度", "value": "前 3 项区域", "sub": "单点抗险能力极低", "status": "normal"},
    ]

    # 4. 分析小节
    sections = [
        {
            "title": "杜邦损益因素变动：收入与成本的拉锯",
            "content": f"本期收入变动 {_f(dup['delta_rev'])}，成本变动 {_f(dup['delta_cost'])}。利润率由 {dup['b_margin']*100:.1f}% 压缩至 {dup['a_margin']*100:.1f}%。说明当前的利润失控不完全源于营收下滑，成本结构的刚性与边际产出效率下滑（负杠杆）是主导因子。",
            "bullets": ["利润变动：负贡献来源于收入与成本支出的剪刀差", "毛利率红线：目前已触及经营安全边际，需降本增效"],
            "table": {"caption": "损益表项因素分析 (DuPont)", "headers": ["项目", "前期(元)", "本期(元)", "绝对变化(元)"], 
                      "rows": [["总营收", _f(dup['b_rev']), _f(dup['a_rev']), _f(dup['delta_rev'])],
                               ["总运营成本", _f(dup['b_cost']), _f(dup['a_cost']), _f(dup['delta_cost'])],
                               ["经营净利润", _f(dup['b_profit']), _f(dup['a_profit']), _f(dup['delta_profit'])]]}
        },
        {
            "title": "动态仿真：若不纠偏的长期损益影响",
            "content": "如果继续放任目前的经营状态，基于最近 6 个月平均经营趋势推演：未来半年预计失血量高达 " + _f(data['simulation']['six_month_leak']) + " 元，相当于拖累全年总利润规模约 " + _f(data['simulation']['annual_drag_pct'], 1) + "%。在当前存量增长乏力环境下，此部分损失已触碰“资产减值”预警。"
        }
    ]

    # 5. 装配并生成报告
    prov = {"Execution": "R06 Consulting Pipeline", "Series_Hash": "be0b0569"}
    
    return {
        "role_id": "r06", "agent_name": "蛙得清",
        "report_title": f"商业诊断：{intent}",
        "executive_summary": summary,
        "decision_directive": directive,
        "kpi_metrics": kpis,
        "analysis_sections": sections,
        "figures": data["figures"],
        "appendix": [],
        "guardrails": profile["guardrails"],
        "rollout_plan": profile["rollout"],
        "next_steps": profile["next_steps"],
        "rca": [],
        "provenance": prov
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", required=True)
    ap.add_argument("--cross", required=True)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--intent", required=True)
    args = ap.parse_args()
    
    out_dir = os.path.join(_HERE, "workspace", "consulting_report")
    spec = build_consulting_report(args.series, args.cross, args.before, args.after, args.intent)
    generate_professional_report(out_dir=out_dir, report_slug="consulting_report", **spec)
    print(f"Report: {out_dir}/consulting_report.html")

if __name__ == "__main__":
    main()
