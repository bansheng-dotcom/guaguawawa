# -*- coding: utf-8 -*-
"""L06 横向决策层 —— R19 三维发布方案裂变 + MCDA 权衡矩阵。

SOP v13.0 L06 体检病灶（R19 真实断点）：
    1. 发布只有「放行 / 驳回」一个开关，一锤子买卖，逼人类无脑接受；
    2. 没有「快而轻 / 稳而全 / 严而保」三种成本-风险偏好的横向对比，
       决策者看不到工期、样本量、门禁强度、风险的取舍；
    3. 无 MCDA 打分、无 ±20% 敏感性分析，推荐结论是拍脑袋而非可复算。

对标开源标杆（Stars > 1k）：
    * huashu-design/Stylescapes (>1k) —— 多风格方案对比看板
    * Scenario Planning / MCDA     —— 多准则决策与权重敏感性
    * Grafana / Superset           —— 决策看板渲染

落地的最低 3 项架构升级：
    1. 三维方案裂变：SCN_A_QUICK 极速轻量 / SCN_B_STEADY 稳健基准 / SCN_C_STRICT 严苛高保障；
    2. 四准则加权 MCDA（速度/证据/风险/成本）+ 推荐方案判定；
    3. ±20% 权重敏感性分析 + Markdown 决策看板渲染。

用法：
    python -m engines.scenario_matrix --model-name 客服助手 --dataset-size 500 \
        --out workspace/rounds/L06_scenarios.json --md workspace/rounds/L06_scenarios.md
"""
from __future__ import annotations

import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

WEIGHTS: Dict[str, float] = {"speed": 0.20, "evidence": 0.35,
                             "risk": 0.30, "cost": 0.15}


class R19ScenarioMatrix:
    """三维发布方案裂变 + MCDA ROI 权衡矩阵。"""

    ENGINE = "R19ScenarioMatrix"
    LAYER = "L06"
    CAPABILITIES = [
        "三维方案裂变 (SCN_A_QUICK / SCN_B_STEADY / SCN_C_STRICT)",
        "四准则加权 MCDA 打分 (speed/evidence/risk/cost) 与推荐判定",
        "±20% 权重敏感性分析 + Markdown 决策看板渲染",
        "[C2] TOPSIS 相对贴近度排序 (向量归一 + 正负理想解)",
        "[C2] Pareto 非支配前沿识别",
        "[C2] Minimax Regret 最坏后悔值稳健裁决",
    ]

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = dict(weights or WEIGHTS)
        total = sum(self.weights.values()) or 1.0
        self.weights = {k: round(v / total, 4) for k, v in self.weights.items()}

    # ------------------------------------------------------------------ #
    def generate(self, model_name: str = "客服助手", dataset_size: int = 500,
                 target_metric: str = "accuracy", risk_tier: str = "medium") -> List[Dict[str, Any]]:
        size = max(1, int(dataset_size or 100))
        sample_a = max(30, size // 5)
        sample_b = max(120, size)
        sample_c = max(300, size * 2)

        specs = [
            {
                "id": "SCN_A_QUICK", "name": "极速轻量实验版 (Quick Experiment)",
                "summary": "小样本快速试跑，只过 3 维门禁，适合探索期与内部实验",
                "days": 0.5, "sample_size": sample_a, "gate_count": 3,
                "risk_level": "medium", "cost_level": "low",
                "scores": {"speed": 10.0, "evidence": 5.5, "risk": 5.0, "cost": 9.5},
                "deliverables": ["experiment_log", "evaluation(小样本)", "exploratory_report"],
            },
            {
                "id": "SCN_B_STEADY", "name": "稳健基准发布版 (Steady Release)",
                "summary": "全量评估 + fail-before/pass-after 回归 + 8 维门禁，适合正式发布",
                "days": 1.5, "sample_size": sample_b, "gate_count": 8,
                "risk_level": "low", "cost_level": "medium",
                "scores": {"speed": 7.0, "evidence": 9.5, "risk": 9.0, "cost": 6.5},
                "deliverables": ["evaluation", "regression_report", "release_candidate",
                                 "ml_bundle + SARIF", "modelcard"],
            },
            {
                "id": "SCN_C_STRICT", "name": "严苛高保障版 (Strict Assurance)",
                "summary": "双倍样本 + 红队复核 + 人工签核，适合高风险/金融医疗场景",
                "days": 3.0, "sample_size": sample_c, "gate_count": 8,
                "risk_level": "low", "cost_level": "high",
                "scores": {"speed": 3.5, "evidence": 10.0, "risk": 10.0, "cost": 3.0},
                "deliverables": ["evaluation(双倍样本)", "regression_report", "redteam_review",
                                 "release_candidate", "human_signoff", "modelcard"],
            },
        ]
        scenarios: List[Dict[str, Any]] = []
        for s in specs:
            s = dict(s)
            s["model_name"] = model_name
            s["target_metric"] = target_metric
            s["risk_tier_hint"] = risk_tier
            s["roi_score"] = self._weighted(s["scores"])
            scenarios.append(s)
        best = max(scenarios, key=lambda x: x["roi_score"])
        for s in scenarios:
            s["is_recommended"] = s["id"] == best["id"]
        return scenarios

    def _weighted(self, scores: Dict[str, float]) -> float:
        return round(sum(float(scores.get(k, 0)) * w for k, w in self.weights.items()), 2)

    # ------------------------------------------------------------------ #
    def sensitivity(self, scenarios: List[Dict[str, Any]], delta: float = 0.20) -> Dict[str, Any]:
        base_rank = [s["id"] for s in sorted(scenarios, key=lambda x: -x["roi_score"])]
        perturbed: Dict[str, Dict[str, float]] = {}
        rankings: Dict[str, List[str]] = {}
        for key in self.weights:
            up = dict(self.weights)
            up[key] = round(up[key] * (1 + delta), 4)
            down = dict(self.weights)
            down[key] = round(down[key] * (1 - delta), 4)
            for label, w in (("up", up), ("down", down)):
                total = sum(w.values()) or 1.0
                norm = {k: v / total for k, v in w.items()}
                rois = {s["id"]: round(sum(s["scores"][k] * norm[k] for k in norm), 2)
                        for s in scenarios}
                tag = f"{key}_{label}"
                perturbed[tag] = rois
                rankings[tag] = [k for k, _ in sorted(rois.items(), key=lambda kv: -kv[1])]
        stable = all(r[0] == base_rank[0] for r in rankings.values())
        return {"base_ranking": base_rank, "perturbations": perturbed,
                "rankings": rankings, "delta": delta, "ranking_stable": stable}

    # ------------------------------------------------------------------ #
    # [Cycle 2] TOPSIS / Pareto / Minimax Regret
    # ------------------------------------------------------------------ #
    def topsis(self, scenarios: List[Dict[str, Any]],
               weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        keys = list((weights or self.weights).keys())
        w = {k: float(v) for k, v in (weights or self.weights).items()}
        total = sum(w.values()) or 1.0
        w = {k: v / total for k, v in w.items()}
        norm = {}
        for key in keys:
            denom = sum(float(s["scores"].get(key, 0)) ** 2 for s in scenarios) ** 0.5 or 1.0
            norm[key] = denom
        weighted = {s["id"]: {k: round(float(s["scores"].get(k, 0)) / norm[k] * w[k], 6)
                              for k in keys} for s in scenarios}
        best = {k: max(v[k] for v in weighted.values()) for k in keys}
        worst = {k: min(v[k] for v in weighted.values()) for k in keys}
        rows = []
        for sid, vec in weighted.items():
            d_best = sum((vec[k] - best[k]) ** 2 for k in keys) ** 0.5
            d_worst = sum((vec[k] - worst[k]) ** 2 for k in keys) ** 0.5
            closeness = d_worst / (d_best + d_worst) if (d_best + d_worst) else 0.0
            rows.append({"id": sid, "d_best": round(d_best, 6),
                         "d_worst": round(d_worst, 6),
                         "closeness": round(closeness, 4)})
        rows.sort(key=lambda x: -x["closeness"])
        for i, row in enumerate(rows, 1):
            row["rank"] = i
        return {"ok": True, "weights": {k: round(v, 4) for k, v in w.items()},
                "ranking": [r["id"] for r in rows], "rows": rows,
                "winner": rows[0]["id"] if rows else None}

    def pareto_frontier(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        keys = list(self.weights.keys())
        vectors = {s["id"]: {k: float(s["scores"].get(k, 0)) for k in keys}
                   for s in scenarios}
        frontier = []
        for sid, vec in vectors.items():
            dominated = False
            for other, ovec in vectors.items():
                if other == sid:
                    continue
                if all(ovec[k] >= vec[k] for k in keys) and any(ovec[k] > vec[k] for k in keys):
                    dominated = True
                    break
            if not dominated:
                frontier.append(sid)
        return {"ok": True, "frontier": sorted(frontier),
                "dominated": sorted(set(vectors) - set(frontier)),
                "frontier_size": len(frontier)}

    def minimax_regret(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        keys = list(self.weights.keys())
        best = {k: max(float(s["scores"].get(k, 0)) for s in scenarios) for k in keys}
        rows = []
        for s in scenarios:
            regrets = {k: round(best[k] - float(s["scores"].get(k, 0)), 4) for k in keys}
            weighted = round(sum(regrets[k] * self.weights[k] for k in keys), 4)
            rows.append({"id": s["id"], "regrets": regrets,
                         "max_regret": max(regrets.values()),
                         "weighted_regret": weighted})
        by_max = sorted(rows, key=lambda r: (r["max_regret"], r["weighted_regret"]))
        return {"ok": True, "rows": rows, "winner": by_max[0]["id"],
                "ranking": [r["id"] for r in by_max],
                "worst_case_regret": by_max[0]["max_regret"]}

    # ------------------------------------------------------------------ #
    def compile_matrix(self, model_name: str = "客服助手", dataset_size: int = 500,
                       target_metric: str = "accuracy", risk_tier: str = "medium"
                       ) -> Dict[str, Any]:
        scenarios = self.generate(model_name, dataset_size, target_metric, risk_tier)
        sens = self.sensitivity(scenarios)
        recommended = next(s for s in scenarios if s["is_recommended"])
        return {
            "ok": len(scenarios) == 3 and sens["ranking_stable"],
            "engine": self.ENGINE, "layer": self.LAYER,
            "weights": dict(self.weights),
            "scenarios": scenarios,
            "recommended": recommended["id"],
            "recommended_name": recommended["name"],
            "sensitivity": sens,
            "topsis": self.topsis(scenarios),
            "pareto": self.pareto_frontier(scenarios),
            "minimax_regret": self.minimax_regret(scenarios),
            "capabilities": list(self.CAPABILITIES),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    def render_markdown(self, matrix: Dict[str, Any]) -> str:
        lines = ["# R19 三维发布方案决策看板", "",
                 f"- 推荐：**{matrix['recommended']}** {matrix['recommended_name']}",
                 f"- 权重：速度 {matrix['weights']['speed']} / 证据 {matrix['weights']['evidence']} / "
                 f"风险 {matrix['weights']['risk']} / 成本 {matrix['weights']['cost']}",
                 f"- 敏感性（±20% 权重）：排名{'稳定' if matrix['sensitivity']['ranking_stable'] else '不稳定'}",
                 "", "| 方案 | 工期(天) | 样本量 | 门禁数 | ROI | 推荐 |",
                 "| :--- | ---: | ---: | ---: | ---: | :---: |"]
        for s in matrix["scenarios"]:
            lines.append(f"| {s['id']}<br>{s['name']} | {s['days']} | {s['sample_size']} | "
                         f"{s['gate_count']}/8 | {s['roi_score']} | "
                         f"{'⭐ 推荐' if s['is_recommended'] else '—'} |")
        lines += ["", "## 方案要点", ""]
        for s in matrix["scenarios"]:
            lines += [f"### {s['id']} · {s['name']}", "",
                      f"- 定位：{s['summary']}",
                      f"- 交付物：{', '.join(s['deliverables'])}",
                      f"- 风险/成本：{s['risk_level']} / {s['cost_level']}", ""]
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L06 三维方案与 MCDA 矩阵")
    ap.add_argument("--model-name", default="客服助手")
    ap.add_argument("--dataset-size", type=int, default=500)
    ap.add_argument("--target-metric", default="accuracy")
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args(argv)

    eng = R19ScenarioMatrix()
    out = eng.compile_matrix(args.model_name, args.dataset_size, args.target_metric)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(eng.render_markdown(out))
    print(json.dumps({"ok": out["ok"], "scenarios": len(out["scenarios"]),
                      "recommended": out["recommended"],
                      "stable": out["sensitivity"]["ranking_stable"],
                      "out": args.out}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
