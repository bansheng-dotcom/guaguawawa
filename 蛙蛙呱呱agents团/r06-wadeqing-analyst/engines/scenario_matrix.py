# -*- coding: utf-8 -*-
"""L06 横向决策层 (Comparative Scenario Matrix Layer)
对标开源: Scenario Planning / MCDA / Stylescapes
架构跃迁 (本轮新增):
1. 四准则加权 MCDA：增长/ROI/风险/成本归一打分，输出排名与推荐理由；
2. 区间预测：每套方案给出置信带与风险调整期望值，拒绝单点拍脑袋；
3. 敏感性分析：对增速与预算做 ±20% 扰动，验证推荐排名是否稳健 (龙卷风)。
"""
from __future__ import annotations

from typing import Any, Dict, List


class ScenarioComparativeMatrix:
    """多维情景推演与横向决策看板生成器。"""

    CRITERIA_WEIGHTS = {
        "growth": 0.25,
        "roi": 0.30,
        "risk": 0.25,
        "cost": 0.20,
    }

    RISK_SCORES = {"conservative": 0.90, "baseline": 0.65, "aggressive": 0.35}

    def generate_scenarios(self, base_metric: float, growth_rate: float = 0.15) -> Dict[str, Any]:
        """基于基准指标，裂变出三种风险偏好下的横向推演情景。"""
        cons_growth = growth_rate * 0.4
        base_growth = growth_rate * 1.0
        aggr_growth = growth_rate * 1.8

        scenarios = [
            {
                "type": "conservative",
                "label": "保守紧缩型",
                "forecast_value": round(base_metric * (1.0 + cons_growth), 2),
                "growth_rate_pct": round(cons_growth * 100.0, 2),
                "budget_required": round(base_metric * 0.05, 2),
                "risk_profile": "极低 (稳守现有客群与渠道)",
                "roi_expected": round((base_metric * cons_growth) / (base_metric * 0.05), 2),
            },
            {
                "type": "baseline",
                "label": "基准稳健型",
                "forecast_value": round(base_metric * (1.0 + base_growth), 2),
                "growth_rate_pct": round(base_growth * 100.0, 2),
                "budget_required": round(base_metric * 0.15, 2),
                "risk_profile": "中等 (按计划推进常规运营迭代)",
                "roi_expected": round((base_metric * base_growth) / (base_metric * 0.15), 2),
            },
            {
                "type": "aggressive",
                "label": "进取扩张型",
                "forecast_value": round(base_metric * (1.0 + aggr_growth), 2),
                "growth_rate_pct": round(aggr_growth * 100.0, 2),
                "budget_required": round(base_metric * 0.35, 2),
                "risk_profile": "较高 (多渠道高频拉新，需严密监控ROI)",
                "roi_expected": round((base_metric * aggr_growth) / (base_metric * 0.35), 2),
            },
        ]

        for sc in scenarios:
            band = abs(sc["forecast_value"] - base_metric) * 0.25
            sc["forecast_low"] = round(sc["forecast_value"] - band, 2)
            sc["forecast_high"] = round(sc["forecast_value"] + band, 2)
            sc["risk_adjusted_value"] = round(
                sc["forecast_value"] * self.RISK_SCORES[sc["type"]], 2)

        self._score_and_rank(scenarios)
        sensitivity = self._sensitivity(base_metric, growth_rate)
        best = next(s for s in scenarios if s["rank"] == 1)

        return {
            "base_metric": base_metric,
            "scenario_count": len(scenarios),
            "criteria_weights": dict(self.CRITERIA_WEIGHTS),
            "scenarios": scenarios,
            "recommended": best["label"],
            "comparison_matrix_md": self._build_markdown_table(scenarios),
            "recommendation_criteria": self._recommendation_reason(best, sensitivity),
            "sensitivity": sensitivity,
        }

    # ------------------------------------------------------------------ #
    # MCDA 打分与排名
    # ------------------------------------------------------------------ #
    def _score_and_rank(self, scenarios: List[Dict[str, Any]]) -> None:
        def _norm(values: List[float], invert: bool = False) -> List[float]:
            lo, hi = min(values), max(values)
            if hi - lo == 0:
                return [1.0 for _ in values]
            return [(1 - (v - lo) / (hi - lo)) if invert else ((v - lo) / (hi - lo))
                    for v in values]

        growth_raw = [s["growth_rate_pct"] for s in scenarios]
        roi_raw = [s["roi_expected"] for s in scenarios]
        cost_raw = [s["budget_required"] for s in scenarios]
        risk_raw = [self.RISK_SCORES[s["type"]] for s in scenarios]

        scores = {
            "growth": _norm(growth_raw),
            "roi": _norm(roi_raw),
            "risk": _norm(risk_raw),
            "cost": _norm(cost_raw, invert=True),
        }
        for i, sc in enumerate(scenarios):
            weighted = sum(scores[k][i] * w for k, w in self.CRITERIA_WEIGHTS.items())
            sc["mcda_scores"] = {k: round(scores[k][i] * 100, 1) for k in scores}
            sc["weighted_score"] = round(weighted * 100, 1)

        ranked = sorted(scenarios, key=lambda s: s["weighted_score"], reverse=True)
        for idx, sc in enumerate(ranked, 1):
            sc["rank"] = idx

    # ------------------------------------------------------------------ #
    # 敏感性分析（±20% 扰动）
    # ------------------------------------------------------------------ #
    def _sensitivity(self, base_metric: float, growth_rate: float) -> Dict[str, Any]:
        def _winner(g: float, budget_scale: float) -> str:
            cands = []
            for typ, mult, budget_ratio in (("conservative", 0.4, 0.05),
                                            ("baseline", 1.0, 0.15),
                                            ("aggressive", 1.8, 0.35)):
                budget = base_metric * budget_ratio * budget_scale
                gain = base_metric * g * mult
                cands.append({
                    "type": typ,
                    "label": typ,
                    "forecast_value": round(base_metric + gain, 2),
                    "growth_rate_pct": round(g * mult * 100.0, 2),
                    "budget_required": round(budget, 2),
                    "roi_expected": round((gain / budget) if budget else 0.0, 2),
                    "risk_profile": typ,
                    "rank": 0,
                })
            self._score_and_rank(cands)
            return next(c["type"] for c in cands if c["rank"] == 1)

        base_winner = _winner(growth_rate, 1.0)
        tensions = []
        for delta in (-0.2, 0.2):
            tensions.append({"driver": "growth", "delta_pct": delta * 100,
                             "winner": _winner(growth_rate * (1 + delta), 1.0)})
            tensions.append({"driver": "budget", "delta_pct": delta * 100,
                             "winner": _winner(growth_rate, 1 + delta)})

        winners = {t["winner"] for t in tensions}
        stable = len(winners) == 1 and base_winner in winners
        return {
            "base_winner": base_winner,
            "scenarios": tensions,
            "ranking_stable": stable,
            "perturbation": "growth/budget ±20%",
        }

    def _recommendation_reason(self, best: Dict[str, Any], sensitivity: Dict[str, Any]) -> str:
        stability = "扰动后排名稳健" if sensitivity["ranking_stable"] else "扰动后排名存在翻转，需人工复核风险偏好"
        return (f"按 MCDA 加权(增长25%/ROI30%/风险25%/成本20%)，{best['label']} 得分 "
                f"{best['weighted_score']} 居首；{stability}；预算需求 {best['budget_required']}，"
                f"风险调整后价值 {best['risk_adjusted_value']}。")

    def _build_markdown_table(self, scenarios: List[Dict[str, Any]]) -> str:
        lines = [
            "| 排名 | 情景类型 | 预测产出值 | 置信区间 | 预期增速 | 预算需求 | 风险等级 | 预估 ROI | MCDA 得分 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for sc in sorted(scenarios, key=lambda s: s["rank"]):
            lines.append(
                f"| {sc['rank']} | **{sc['label']}** | {sc['forecast_value']} | "
                f"[{sc['forecast_low']}, {sc['forecast_high']}] | {sc['growth_rate_pct']}% | "
                f"{sc['budget_required']} | {sc['risk_profile']} | {sc['roi_expected']}x | "
                f"{sc['weighted_score']} |"
            )
        return "\n".join(lines)
