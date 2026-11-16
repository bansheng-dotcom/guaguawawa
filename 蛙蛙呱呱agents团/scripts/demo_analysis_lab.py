# -*- coding: utf-8 -*-
"""用合成数据演示分析引擎：归因 / A/B / DiD / 弹性 / 队列。

目的：证明这些方法不是文案，是能复算的算法。
运行：python scripts/demo_analysis_lab.py --out <file.md>
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import analysis_lab as L  # noqa: E402


def demo() -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # 1) 归因：销售额从 100 → 106，拆价与结构
    out["mix_rate"] = L.decompose_mix_rate(
        weights0=[0.55, 0.30, 0.15], rates0=[100, 80, 50],
        weights1=[0.50, 0.35, 0.15], rates1=[105, 82, 48],
        names=["主品", "次品", "引流品"])

    # 2) A/B：每组 5000，基线 10%，实验 12%
    out["ab"] = L.ab_proportion(5000, 500, 5000, 600)
    out["ab"]["sample_size_for_1pp"] = L.sample_size_proportion(0.10, 0.11)
    out["ab"]["mde_at_5000"] = L.mde_proportion(5000, 0.10)
    out["ab"]["bh"] = L.bh_correction([0.001, 0.02, 0.08, 0.5])

    # 3) DiD：60 个单位 × 8 期，真实效应 2.0
    rng = random.Random(7)
    rows: List[Dict[str, Any]] = []
    for u in range(60):
        treat = 1 if u < 30 else 0
        ufe = rng.gauss(0, 1)
        for t in range(8):
            post = 1 if t >= 4 else 0
            y = 10 + ufe + 0.5 * t + 1.5 * treat + 2.0 * treat * post + rng.gauss(0, 0.3)
            rows.append({"unit": u, "period": f"P{t}", "treat": treat, "y": y})
    out["did"] = L.did_twfe(rows, post_period="P4")
    out["event"] = L.event_study(rows, base_period="P0")
    out["placebo"] = L.placebo_did(rows, "P2")

    # 4) 弹性：真实 -1.5
    prices = [1 + 0.2 * i for i in range(12)]
    rng2 = random.Random(3)
    qty = [100 * p ** -1.5 * math.exp(rng2.gauss(0, 0.02)) for p in prices]
    out["elasticity"] = L.elasticity(prices, qty)

    # 5) 队列留存
    out["cohort"] = L.cohort_retention(
        ["2026-01", "2026-02", "2026-03"], [0, 1, 2, 3],
        [[1000, 520, 360, 280], [1200, 660, 470, 0], [900, 500, 0, 0]])
    return out


def to_md(d: Dict[str, Any]) -> str:
    L: List[str] = ["# 分析引擎演示（合成数据，可复算）\n",
                    "> 这些数字由 `core/analysis_lab.py` 用真实统计算法算出，"
                    "不是文案；测试见 `tests/test_analysis_lab.py`。\n",
                    "> 单独调用：`python -m core.analysis_lab ab --input ab.json`"
                    "（mix/ab/did/event/placebo/elasticity/cohort/power）。\n"]
    m = d["mix_rate"]
    L.append("## 1. 量价/结构归因\n")
    L.append(f"- 总变化 **{m['delta']:+.4f}** = 率效应 {m['rate_effect']:+.4f} "
             f"+ 结构效应 {m['mix_effect']:+.4f} + 交叉 {m['interaction']:+.4f}")
    L.append(f"- 闭合校验：误差 {m['closure_gap']:.2e}（必须为 0）")
    L.append(f"- 结论：{m['claim']}\n")

    a = d["ab"]
    L.append("## 2. A/B 检验\n")
    L.append(f"- 对照 {a['p_a']:.2%} vs 实验 {a['p_b']:.2%}，相对提升 {a['rel_lift']:.1%}")
    L.append(f"- z={a['z']}，p={a['p_value']}，95% CI {a['ci95']}，"
             f"观测功效 {a['power_at_observed']:.0%}")
    L.append(f"- 要把 10%→11% 做到 80% 功效，每组需 **{a['sample_size_for_1pp']}** 人；"
             f"每组 5000 人能检出 **{a['mde_at_5000']:.2%}** 的提升")
    L.append("- 多重比较（BH）：" + "；".join(
        f"p={x['p']}→q={x['q']} {'拒绝' if x['reject'] else '保留'}" for x in a["bh"]))
    L.append("")

    did = d["did"]
    L.append("## 3. DiD（双向固定效应）\n")
    pv = did["p_value"]
    ptxt = "<0.001" if pv < 0.001 else f"{pv:.4f}"
    L.append(f"- 真实效应设定 2.0，估计 **{did['estimate']:+.4f}**"
             f"（SE {did['se']:.4f}，95% CI {did['ci95']}，p={ptxt}）")
    L.append(f"- 前趋势：{d['event']['claim']}")
    L.append(f"- 安慰剂：{d['placebo']['claim']}\n")

    e = d["elasticity"]
    L.append("## 4. 价格弹性\n")
    L.append(f"- 真实 -1.5，估计 **{e['elasticity']:+.4f}**"
             f"（95% CI {e['ci95']}，R²={e['r2']}）\n")

    c = d["cohort"]
    L.append("## 5. 队列留存\n")
    L.append(f"- 加权留存：{c['weighted_rate']}")
    L.append(f"- 对数衰减斜率：{c['decay_slope']}\n")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    d = demo()
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_md(d) + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
