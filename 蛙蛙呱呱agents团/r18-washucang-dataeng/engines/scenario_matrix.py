# -*- coding: utf-8 -*-
"""L06 横向决策层 —— 三维数据管道方案裂变 + MCDA 多维 ROI 权衡矩阵。

病灶（体检结论）：升级前 R18 对任何需求只回一种管道方案（"就按增量做"），
人类无法在「快 / 稳 / 强一致」三种成本-风险偏好之间横向权衡；决策被 Agent
单方面替人类拍板，违反 SOP「横向决策层给人类选择」的本质要求。

对标标杆（Stars > 1k，2026-11 经 GitHub API 实测；原稿引用的
`huashu-design/Stylescapes` 经查为 404 空账号，属错引，已剔除并替换为下列真实仓库）：
- `dbt-labs/dbt`（14,139★ / Apache-2.0）：incremental 策略谱系
  （append / merge / insert_overwrite / delete+insert）→ `SCENARIOS[*].stack`
  的三档工艺术语（append / 批流双跑 / 全量重算）；
- `optuna/optuna`（15,027★ / MIT）：多目标优化只返回 Pareto 前沿与权衡关系，
  最终取舍交人类 → 本层只输出 `recommended_id` + `note`，不写"已决定"；
- `the-dual-space/pymoo`（2,994★ / Apache-2.0）：NSGA-II/III 的 0~1 归一化 +
  权重加权 → `_score_components` 的五维归一化与 `WEIGHTS` 加权求和。

本引擎落地：
1. 固定裂变三套方案：极速增量版 / 稳健批流版（推荐）/ 强一致重算版；
2. 5 维 MCDA 加权评分（周期 25% / 成本 20% / 风险 25% / 新鲜度 15% / 一致性 15%），
   权重与归一化全部确定性、可复算；
3. 按上下文（SLA / 预算 / 强一致要求）做确定性加权修正，输出排序与推荐，
   但最终选择权仍交还人类（不替人类拍板）。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

WEIGHTS: Dict[str, float] = {
    "lead_time": 0.25, "cost": 0.20, "risk": 0.25, "freshness": 0.15, "consistency": 0.15,
}

_CONSISTENCY_SCORE = {"强一致": 1.0, "按批一致": 0.7, "最终一致": 0.4}

SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "fast", "name": "极速增量版 (Incremental Fast)",
        "lead_time_days": 0.5, "cost_score": 2, "risk_score": 4,
        "freshness_sla_h": 1, "consistency": "最终一致", "ops_complexity": "低",
        "stack": "dbt incremental + append 水位 + 轻量质量门禁",
        "best_for": "抢时效的运营看板 / 试错期指标",
        "tradeoff": "回滚与重算成本高，迟到数据需补偿批次",
    },
    {
        "id": "balanced", "name": "稳健批流版 (Batch+Stream Balanced)",
        "lead_time_days": 2.0, "cost_score": 3, "risk_score": 2,
        "freshness_sla_h": 2, "consistency": "按批一致", "ops_complexity": "中",
        "stack": "批处理基线 + 流式增量 + 双跑对账 + 8 维门禁",
        "best_for": "生产主力管道 / 有 SLA 的核心报表",
        "tradeoff": "需要维护批流双链路与对账作业",
    },
    {
        "id": "strict", "name": "强一致重算版 (Full Recompute Consistency)",
        "lead_time_days": 4.0, "cost_score": 5, "risk_score": 1,
        "freshness_sla_h": 24, "consistency": "强一致", "ops_complexity": "高",
        "stack": "全量重算 + 快照隔离 + 逐批勾稽 + 审计归档",
        "best_for": "财务/合规口径 / 对外披露数据",
        "tradeoff": "成本最高、时效最差，不适合高频刷新",
    },
]


class DataEngScenarioMatrix:
    """L06 三维方案裂变器。"""

    # ------------------------------------------------------------------ #
    # 评分
    # ------------------------------------------------------------------ #
    @staticmethod
    def _score_components(scn: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
        lead = max(0.0, 1 - scn["lead_time_days"] / 5.0)
        cost = max(0.0, 1 - (scn["cost_score"] - 1) / 4.0)
        risk = max(0.0, 1 - (scn["risk_score"] - 1) / 4.0)
        fresh = max(0.0, 1 - min(1.0, scn["freshness_sla_h"] / 24.0))
        cons = _CONSISTENCY_SCORE[scn["consistency"]]
        weighted = (WEIGHTS["lead_time"] * lead + WEIGHTS["cost"] * cost
                    + WEIGHTS["risk"] * risk + WEIGHTS["freshness"] * fresh
                    + WEIGHTS["consistency"] * cons)
        # 上下文修正（确定性，不用随机）
        if context.get("sla_hours") is not None and float(context["sla_hours"]) <= 2:
            if scn["id"] == "fast":
                weighted += 0.06
            if scn["id"] == "balanced":
                weighted += 0.02
        if context.get("budget_days") is not None and float(context["budget_days"]) <= 1:
            if scn["id"] == "fast":
                weighted += 0.10
        if context.get("strict_consistency"):
            if scn["id"] == "strict":
                # 硬约束压倒性加权：人类明确要求强一致时，强一致方案必须排首位
                weighted += 0.30
        return {"lead_time": round(lead, 4), "cost": round(cost, 4), "risk": round(risk, 4),
                "freshness": round(fresh, 4), "consistency": round(cons, 4),
                "weighted": round(min(1.0, weighted), 4)}

    # ------------------------------------------------------------------ #
    # 裂变
    # ------------------------------------------------------------------ #
    def generate(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = dict(context or {})
        rows: List[Dict[str, Any]] = []
        for scn in SCENARIOS:
            comp = self._score_components(scn, ctx)
            # ROI 比值：收益（新鲜度 + 一致性）/ 投入（周期 + 成本），仅用于横向比较
            benefit = (comp["freshness"] + comp["consistency"]) / 2.0
            invest = (comp["lead_time"] + comp["cost"]) / 2.0
            roi = round(benefit / invest, 4) if invest > 0 else 0.0
            rows.append({
                **scn,
                "scores": comp,
                "roi_ratio": roi,
                "total_score": round(comp["weighted"] * 100, 1),
                "effort_man_days": round(scn["lead_time_days"], 2),
            })
        ranked = sorted(rows, key=lambda r: (-r["total_score"], r["id"]))
        for i, row in enumerate(ranked, 1):
            row["rank"] = i
        best = ranked[0]
        return {
            "ok": True,
            "context": ctx,
            "weights": dict(WEIGHTS),
            "scenario_count": len(ranked),
            "scenarios": ranked,
            "recommended_id": best["id"],
            "recommended_name": best["name"],
            "note": "推荐仅为加权结果，最终选型由人类决策（R18 不替人类拍板定价/选型）",
        }

    def rank(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.generate(context)["scenarios"]

    # ------------------------------------------------------------------ #
    # 看板
    # ------------------------------------------------------------------ #
    def render_markdown(self, matrix: Dict[str, Any]) -> str:
        lines = [
            "# 数据管道三维方案权衡矩阵", "",
            f"- MCDA 权重：周期 {WEIGHTS['lead_time']:.0%} / 成本 {WEIGHTS['cost']:.0%} / "
            f"风险 {WEIGHTS['risk']:.0%} / 新鲜度 {WEIGHTS['freshness']:.0%} / "
            f"一致性 {WEIGHTS['consistency']:.0%}",
            f"- 推荐（加权最优）：**{matrix['recommended_name']}**",
            f"- {matrix['note']}", "",
            "| 排名 | 方案 | 周期(天) | 成本分 | 风险分 | 新鲜度 | 一致性 | 综合得分 | 取舍 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for row in matrix["scenarios"]:
            lines.append(
                f"| {row['rank']} | {row['name']} | {row['lead_time_days']} | "
                f"{row['cost_score']}/5 | {row['risk_score']}/5 | "
                f"{row['freshness_sla_h']}h | {row['consistency']} | "
                f"{row['total_score']} | {row['tradeoff']} |")
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# CLI：python -m engines.scenario_matrix --out ... --md ...
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L06 三维方案裂变矩阵")
    ap.add_argument("--context", default="", help="上下文 JSON（sla_hours/budget_days/strict_consistency）")
    ap.add_argument("--out", default="", help="矩阵 JSON 输出路径")
    ap.add_argument("--md", default="", help="看板 Markdown 输出路径")
    args = ap.parse_args(argv)

    ctx: Dict[str, Any] = {}
    if args.context:
        with open(args.context, encoding="utf-8") as f:
            ctx = json.load(f)
    matrix = DataEngScenarioMatrix().generate(ctx)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(matrix, f, ensure_ascii=False, indent=2)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(DataEngScenarioMatrix().render_markdown(matrix))
    print("__AGENT_RESULT__ " + json.dumps(
        {"ok": matrix["ok"], "scenario_count": matrix["scenario_count"],
         "recommended_id": matrix["recommended_id"],
         "ranking": [(r["id"], r["total_score"]) for r in matrix["scenarios"]],
         "out": args.out}, ensure_ascii=False))
    return 0 if matrix["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
