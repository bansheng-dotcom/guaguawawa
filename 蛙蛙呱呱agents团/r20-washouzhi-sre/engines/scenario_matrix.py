# -*- coding: utf-8 -*-
"""L06 横向决策层 —— 三维处置方案裂变 + MCDA / 敏感性权衡。

SOP v13.0 L06 体检病灶（R20 真实断点）：
    故障处置只有「按手册做」一条路，一锤子买卖；没有「先止血再论因」
    「稳健 SLO 修复」「停服加固」三种成本-风险偏好的横向对比，
    也没有 MCDA 打分与权重敏感性，决策者无法在不同风险偏好间选择。

对标开源标杆（Stars > 1k）：
    * Scenario Planning (Schoemaker) —— 多情景规划
    * MCDA / TOPSIS 家族 —— 多准则加权裁决
    * huashu-design/Stylescapes —— 三维方案对照看板

落地的最低 3 项架构升级：
    1. 三维处置方案裂变（极速抢修 / 稳健 SLO / 防御加固）；
    2. 四准则加权 MCDA（恢复速度/风险/成本/证据合规）与推荐判定；
    3. ±20% 权重敏感性分析 + Markdown 决策看板。

用法：
    python agent.py evolve scenario --service 支付服务 --severity critical --out ...
"""
from __future__ import annotations

import datetime
import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_CRITERIA = [
    {"id": "speed", "name": "恢复速度", "weight": 0.30, "higher_better": True},
    {"id": "risk", "name": "风险控制", "weight": 0.30, "higher_better": True},
    {"id": "cost", "name": "成本效率", "weight": 0.15, "higher_better": True},
    {"id": "evidence", "name": "证据与合规", "weight": 0.25, "higher_better": True},
]

_SCENARIOS = [
    {"id": "SCN_A_RUSH", "name": "极速抢修版", "recovery_minutes": 15,
     "person_hours": 4, "risk_score": 45, "evidence_score": 55,
     "desc": "先回滚/限流止血，根因后置；适合 P1 正在资损"},
    {"id": "SCN_B_STEADY", "name": "稳健 SLO 版", "recovery_minutes": 45,
     "person_hours": 10, "risk_score": 80, "evidence_score": 85,
     "desc": "按 SLO 口径定位并修复，保留完整证据链；适合 P2/P3"},
    {"id": "SCN_C_HARDEN", "name": "防御加固版", "recovery_minutes": 120,
     "person_hours": 24, "risk_score": 92, "evidence_score": 96,
     "desc": "停服窗口内修复 + 容量/依赖加固 + 演练验证；适合反复故障"},
]


def _round(x: float) -> float:
    return round(float(x) + 1e-12, 4)


class R20ScenarioMatrix:
    """R20 三维处置方案与 MCDA 权衡矩阵。"""

    ENGINE = "R20ScenarioMatrix"
    LAYER = "L06"
    CAPABILITIES = [
        "三维处置方案裂变 (极速抢修 / 稳健 SLO / 防御加固)",
        "四准则加权 MCDA (速度/风险/成本/证据) 与推荐判定",
        "±20% 权重敏感性分析 + Markdown 决策看板",
    ]

    def _raw_scores(self, severity: str) -> List[Dict[str, Any]]:
        # 严重度只影响速度维度权重感：P1 更看重速度，P3 更看重证据。
        rows = []
        for s in _SCENARIOS:
            speed = max(0.0, 100.0 - s["recovery_minutes"] * 0.7)
            cost = max(0.0, 100.0 - s["person_hours"] * 3.0)
            rows.append({
                "id": s["id"], "name": s["name"], "desc": s["desc"],
                "recovery_minutes": s["recovery_minutes"],
                "person_hours": s["person_hours"],
                "raw": {"speed": _round(speed), "risk": float(s["risk_score"]),
                        "cost": _round(cost), "evidence": float(s["evidence_score"])},
            })
        return rows

    def _weights(self, severity: str) -> Dict[str, float]:
        w = {c["id"]: c["weight"] for c in _CRITERIA}
        if severity == "critical":
            w["speed"] += 0.10
            w["evidence"] -= 0.05
            w["cost"] -= 0.05
        elif severity == "minor":
            w["evidence"] += 0.10
            w["speed"] -= 0.10
        total = sum(w.values())
        return {k: _round(v / total) for k, v in w.items()}

    def _normalize(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for c in _CRITERIA:
            vals = [r["raw"][c["id"]] for r in rows]
            lo, hi = min(vals), max(vals)
            for i, r in enumerate(rows):
                v = r["raw"][c["id"]]
                norm = 1.0 if hi == lo else (v - lo) / (hi - lo)
                if not c["higher_better"]:
                    norm = 1.0 - norm
                r.setdefault("norm", {})[c["id"]] = _round(norm)
        return rows

    def compile_matrix(self, service: str = "核心服务",
                       severity: str = "major") -> Dict[str, Any]:
        severity = (severity or "major").lower()
        rows = self._normalize(self._raw_scores(severity))
        weights = self._weights(severity)
        for r in rows:
            r["score"] = _round(sum(r["norm"][k] * w for k, w in weights.items()))
        ranked = sorted(rows, key=lambda r: (-r["score"], r["id"]))
        for i, r in enumerate(ranked, start=1):
            r["rank"] = i
        recommended = ranked[0]

        sensitivity = []
        for c in _CRITERIA:
            for delta in (0.8, 1.2):
                w2 = dict(weights)
                w2[c["id"]] = _round(w2[c["id"]] * delta)
                total = sum(w2.values())
                w2 = {k: v / total for k, v in w2.items()}
                best = max(rows, key=lambda r: sum(r["norm"][k] * v for k, v in w2.items()))
                sensitivity.append({"criterion": c["id"], "factor": delta,
                                    "winner": best["id"]})
        winners = {s["winner"] for s in sensitivity}
        return {
            "ok": len(rows) == 3,
            "engine": self.ENGINE, "layer": self.LAYER,
            "service": service, "severity": severity,
            "criteria": _CRITERIA, "weights": weights,
            "scenarios": ranked,
            "recommended": recommended["id"],
            "recommended_name": recommended["name"],
            "ranking": [r["id"] for r in ranked],
            "sensitivity": sensitivity,
            "rank_stable": len(winners) == 1,
            "sensitivity_winners": sorted(winners),
            "capabilities": list(self.CAPABILITIES),
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    def render_markdown(self, matrix: Dict[str, Any]) -> str:
        lines = [
            f"# {matrix['service']} · 三维处置方案权衡（严重度 {matrix['severity']}）", "",
            "| 方案 | 恢复时长 | 人时 | 速度 | 风险 | 成本 | 证据 | 加权得分 | 排名 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for r in matrix["scenarios"]:
            n = r["norm"]
            lines.append(
                f"| {r['name']} | {r['recovery_minutes']}min | {r['person_hours']} | "
                f"{n['speed']:.2f} | {n['risk']:.2f} | {n['cost']:.2f} | {n['evidence']:.2f} | "
                f"{r['score']:.3f} | {r['rank']} |")
        lines += ["", f"**推荐：{matrix['recommended_name']}**"
                      f"（{matrix['recommended']}）",
                  f"- 权重：{matrix['weights']}",
                  f"- 敏感性稳健：{matrix['rank_stable']}，获胜集合 {matrix['sensitivity_winners']}"]
        return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R20 L06 三维处置方案")
    ap.add_argument("--service", default="核心服务")
    ap.add_argument("--severity", default="major")
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args(argv)
    eng = R20ScenarioMatrix()
    out = eng.compile_matrix(args.service, args.severity)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(eng.render_markdown(out))
    print(json.dumps({"ok": out["ok"], "recommended": out["recommended"],
                      "stable": out["rank_stable"]}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
