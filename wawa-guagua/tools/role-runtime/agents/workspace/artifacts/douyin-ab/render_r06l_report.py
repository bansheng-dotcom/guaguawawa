# -*- coding: utf-8 -*-
"""Render the R06L editorial report from an audited result JSON.

All visible numbers come from the JSON. The template supplies structure and
approved prose; this renderer substitutes placeholder tokens with JSON-backed
values and refuses to emit if a JSON value cannot be located in the output.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_RESULT = HERE / "abtest_result.json"
DEFAULT_TEMPLATE = HERE / "douyin_ab_test_report_stitched.html"
DEFAULT_OUTPUT = HERE / "douyin_ab_test_report_r06l.html"

DECISION_TEXT = {
    "ship": "ship（灰度放量）",
    "no_ship": "no_ship（不放量，补充样本或调整假设）",
    "srm_rerun": "srm_rerun（样本失配，需重跑实验）",
}


def build_values(data: dict) -> dict[str, str]:
    m = data["primary_metric"]
    r = data["secondary_metrics"]["revenue_per_user"]
    aov = data["secondary_metrics"]["aov_buyer"]
    gmv = data["secondary_metrics"]["gmv"]
    srm = data["srm"]
    power = data["power"]
    profile = data["experiment_profile"]

    mde_pp = power["mde_absolute"] * 100
    target_rate = (power["baseline"] + power["mde_absolute"]) * 100
    lift = m["lift_pct"]
    decision = data["decision"]
    impact = m["impact_min_pct"]

    return {
        # metric rail
        "LIFT_ABS_TOKEN": f"{lift:+.2f}%",
        "LIFT_REL_TOKEN": f"{lift:.2f}%",
        "METRIC_CONTROL_RATE": f"{m['control']['value_pct']:.2f}%",
        "METRIC_TREATMENT_RATE": f"{m['treatment']['value_pct']:.2f}%",
        "METRIC_P_VALUE": f"{m['test']['p_value']:.4f}",
        "ALPHA_VALUE": f"{power['alpha']:g}",
        "SRM_CRITICAL": f"{srm['critical']:g}",
        "DECISION_KEYWORD": decision,
        "DECISION_VERDICT": ("判据全部通过" if decision == "ship" else "存在未通过判据"),
        "METRIC_REVENUE_LIFT": f"{r['lift_pct']:+.2f}%",
        "METRIC_REVENUE_CONTROL": f"{r['control']:.2f}",
        "METRIC_REVENUE_TREATMENT": f"{r['treatment']:.2f}",
        "METRIC_SRM": f"{srm['chi2']:.3f}",
        # summary
        "SUMMARY_JUDGEMENT": (
            f"{profile['display_name']}实验：对照组 {m['control']['value_pct']:.2f}%、"
            f"处理组 {m['treatment']['value_pct']:.2f}%，相对提升 {lift:.2f}%"
            f"（p={m['test']['p_value']:.4f}），SRM χ²={srm['chi2']:.3f}，"
            f"每组实际样本 {power['actual_n_control']:,} / {power['actual_n_treatment']:,}，"
            f"决策为 {decision}。"
        ),
        "SUMMARY_REVENUE": (
            f"每用户营收由 {r['control']:.2f} 元升至 {r['treatment']:.2f} 元"
            f"（{r['lift_pct']:+.2f}%），GMV {gmv['lift_pct']:+.2f}%，与转化率同向。"
        ),
        "SUMMARY_ATTRIBUTION": (
            f"客单价（买家）{aov['control']:.2f} 元 → {aov['treatment']:.2f} 元"
            f"（{aov['lift_pct']:+.2f}%），基本持平，提升来自下单人数"
            f"{gmv['buyers_control']} → {gmv['buyers_treatment']}，不是单价变化。"
        ),
        "SUMMARY_DECISION": (
            f"判定门槛为「二比例检验显著、相对提升≥{impact:g}%、"
            f"SRM χ²≤{srm['critical']:g}、功效门（每组样本量≥{power['required_n_per_group']:,}"
            f"或观测提升≥预设 MDE {power['mde_relative'] * 100:.0f}%）」，"
            f"本次决策 {decision}（{DECISION_TEXT.get(decision, decision)}）；"
            f"数据为模拟结果，需用店铺后台明细复算后再放量。"
        ),
        # design section
        "DESIGN_METRIC_ROW": (
            f"{m['definition']}（0/1 二值），采用 pooled two-proportion z test；"
            f"Welch t 仅保留为诊断参考。"
        ),
        "DESIGN_N_CONTROL": f"{m['control']['n']:,}",
        "DESIGN_N_TREATMENT": f"{m['treatment']['n']:,}",
        "DESIGN_SRM_ROW": (
            f"SRM χ²={srm['chi2']:.3f} {'<' if srm['balanced'] else '≥'} {srm['critical']:g}，"
            f"两组接近 50/50，分流{'均衡' if srm['balanced'] else '失配'}。"
        ),
        "DESIGN_POWER_ROW": (
            f"基线 {power['baseline'] * 100:.1f}%、MDE {mde_pp:.1f}pp"
            f"（{power['baseline'] * 100:.1f}%→{target_rate:.1f}%，相对 {power['mde_relative'] * 100:.0f}%）、"
            f"α={power['alpha']:g}、功效 {power['target_power'] * 100:.0f}% → 每组 {power['required_n_per_group']:,}"
        ),
        "DESIGN_POWER_VERDICT": (
            f"实际 {power['actual_n_control']:,} / {power['actual_n_treatment']:,}"
            f" {'≥' if power.get('planning_power_met') else '<'} {power['required_n_per_group']:,}，"
            f"{'达到规划样本量' if power.get('planning_power_met') else '低于规划样本量'}"
            f"；观测 lift {lift:.2f}% "
            f"{'≥' if power.get('observed_lift_exceeds_mde') else '<'} 预设 MDE "
            f"{power['mde_relative'] * 100:.0f}%，功效门"
            f"{'通过' if power['met'] else '未通过'}"
        ),
        "DESIGN_THRESHOLD_ROW": (
            f"impact_min={impact:g}%；SRM χ² 临界={srm['critical']:g}；"
            f"参数模板 {profile['name']}"
        ),
        "DESIGN_SOURCE": (
            f"参数来自场景模板 {profile['name']}（{profile['display_name']}），"
            f"基线来源：{power['baseline_source']}；样本量为双比例 z 检验近似规划值。"
        ),
        # chart section
        "CHART_THRESHOLD_LABEL": f"决策阈值 {target_rate:.2f}%（lift {impact:g}%）",
        "CHART_SOURCE": (
            f"来源：模拟订单聚合表（n={data['source']['row_count']:,}）；"
            f"转化率=下单人数/进店人数。虚线为 impact_min={impact:g}% 对应的处理组转化率 {target_rate:.2f}%。"
        ),
        "CHART_NOTE_1": (
            f"处理组 {m['treatment']['value_pct']:.2f}% 高于对照组 {m['control']['value_pct']:.2f}%，"
            f"two-proportion z={m['test']['z']:.2f}，p={m['test']['p_value']:.4f}"
            f"（{'<' if m['test']['significant'] else '≥'} {power['alpha']:g}）。"
        ),
        "CHART_NOTE_2": (
            f"相对提升 {lift:.2f}%，"
            f"{'超过' if lift >= impact else '低于'} impact_min={impact:g}%，"
            f"{'不是可忽略的边际波动' if lift >= impact else '不构成放量依据'}。"
        ),
        "CHART_NOTE_3": (
            f"SRM χ²={srm['chi2']:.3f}（{srm['critical']:g}），"
            f"两组人数接近 50/50，{'无分流污染' if srm['balanced'] else '存在分流异常'}。"
        ),
        "CHART_IMPLICATION": (
            f"主指标判定 {decision}："
            f"{'通过显著性、阈值、SRM 与样本量判据，可进入放量流程' if decision == 'ship' else '存在未通过的判据，先补样本或修复分流再判定'}。"
        ),
        # attribution section
        "ATTR_JUDGEMENT": (
            f"转化率与每用户营收同向提升约 {lift:.0f}%，"
            f"客单价仅 {aov['lift_pct']:+.2f}%，方向一致。"
        ),
        "ATTR_EXPLANATION": (
            f"下单人数从 {gmv['buyers_control']} 增至 {gmv['buyers_treatment']}，"
            f"而每人平均消费额几乎不变。"
        ),
        "ATTR_HANDLING": (
            f"提升{'不是' if abs(aov['lift_pct']) < 3 else '可能是'}降价换量，"
            f"护栏指标{'安全' if abs(aov['lift_pct']) < 3 else '需复核'}，"
            f"后续按 {profile.get('minimum_runtime_days')} 天窗口监控。"
        ),
        "ATTR_BOUNDARY": (
            f"数据为模拟；Cohen's d={m['cohens_d_treatment_minus_control']:.3f} 属 "
            f"{m['effect_grade']}，是低基线二值指标的固有现象，业务决策以相对提升为准。"
            f"本次决策 {decision}。真实结论需替换后台明细重跑。"
        ),
        "ATTR_GMV": f"{gmv['lift_pct']:+.2f}%",
        "ATTR_REVENUE": f"{r['lift_pct']:+.2f}%",
        "ATTR_CONVERSION": f"{lift:+.2f}%",
        "ATTR_AOV": f"{aov['lift_pct']:+.2f}%",
        # decision section
        "DECISION_TITLE": f"建议 {decision}：{'灰度放量并持续监控护栏指标' if decision == 'ship' else '先补齐未通过的判据再判定'}",
        "DECISION_INTRO": (
            f"动作按证据状态排序，只保留能在下一次经营周期检查的事项；"
            f"护栏指标：{'、'.join(profile.get('guardrails', [])) or '未配置'}。"
        ),
        "ACTION_1_CHECK": (
            f"{lift:.2f}% {'≥' if lift >= impact else '<'} {impact:g}%、"
            f"p={m['test']['p_value']:.4f}、SRM {srm['chi2']:.3f}。"
        ),
        "ACTION_1_JUDGMENT": (
            f"本次判定 {decision}，"
            f"{'可进入灰度放量' if decision == 'ship' else '需先处理未通过判据'}。"
        ),
        "ACTION_1_BASIS": (
            f"显著、lift {lift:.2f}%、SRM {srm['chi2']:.3f}、"
            f"每组样本 {power['actual_n_control']:,}/{power['actual_n_treatment']:,}。"
        ),
        "ACTION_2_CHECK": (
            f"客单价 {aov['control']:.2f}→{aov['treatment']:.2f} 元"
            f"（{aov['lift_pct']:+.2f}%）。"
        ),
        "ACTION_3_CHECK": (
            f"每组规划 {power['required_n_per_group']:,}，实际 "
            f"{power['actual_n_control']:,}/{power['actual_n_treatment']:,}；"
            f"观测 lift {lift:.2f}% 与 MDE {power['mde_relative'] * 100:.0f}% 比较后决定是否补量。"
        ),
        # notes
        "NOTES_SCOPE": (
            f"下单转化率 = 下单用户数 / 实验内唯一进店用户数；每用户营收 = GMV / 用户数；"
            f"客单价（买家）= GMV / 下单人数；相对提升 = (处理组 − 对照组) / 对照组。"
        ),
        "NOTES_BOUNDARY": (
            f"数据为确定性模拟（seed={data['experiment']['seed']}），非真实店铺表现；"
            f"p 值为正态近似（df 量级 {data['primary_metric']['control']['n'] + data['primary_metric']['treatment']['n']:,}）；"
            f"Cohen's d={m['cohens_d_treatment_minus_control']:.3f} 属 {m['effect_grade']}，"
            f"不以 d 分级否决；结论仅对 {data['experiment']['period']['days']} 天实验周期有效，"
            f"不跨大促/换季外推；因果成立依赖随机分流无污染。"
        ),
        "NOTES_SOURCE": (
            f"R06 技能 abtest / ttest / power 确定性计算；场景参数模板 {profile['name']}；"
            f"结构化交接文件 abtest_result.json，由 DAAR 编辑式报告模板渲染。"
            f"输入文件 SHA-256 前 12 位 {data['source']['sha256'][:12]}。"
        ),
        "NOTES_SIGNOFF_PROFILE": profile["display_name"],
    }


def render(result_path: Path, template_path: Path, output_path: Path) -> None:
    data = json.loads(result_path.read_text(encoding="utf-8"))
    values = build_values(data)
    html = template_path.read_text(encoding="utf-8")

    missing = [token for token in values if token not in html]
    if missing:
        raise ValueError(f"template is missing required tokens: {missing}")

    for token, value in sorted(values.items(), key=lambda item: len(item[0]), reverse=True):
        html = html.replace(token, value)

    leftovers = [token for token in values if token in html]
    if leftovers:
        raise ValueError(f"unresolved tokens remain in output: {leftovers}")

    # Every JSON-backed core value must be visible in the rendered report.
    m = data["primary_metric"]
    for value in (f"{m['lift_pct']:.2f}%", f"{m['test']['p_value']:.4f}",
                  f"{data['srm']['chi2']:.3f}", data["decision"],
                  f"{data['power']['required_n_per_group']:,}"):
        if value not in html:
            raise ValueError(f"rendered HTML missing JSON-backed value: {value}")
    output_path.write_text(html, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    p.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    render(args.result, args.template, args.output)
    print(json.dumps({"ok": True, "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
