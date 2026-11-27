# -*- coding: utf-8 -*-
"""第 6 段 size：双口径市场测算 + 确定性蒙特卡洛敏感性。

- top-down：分品类规模加总；
- bottom-up：客户数 × 可服务比例 × 年购买量 × 单价，再除以 1e8 转为亿元；
- 敏感性：对每条假设在 [low, high] 内均匀抽样，用固定 LCG（无第三方随机源），
  输出 p10/p50/p90；同一 fixture 在任何机器上结果一致。
假设清单必填，且每条假设必须挂到已登记证据（evidence_id），否则门禁失败。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import as_number, ck, gate

MC_N = 4000
MC_SEED = 20261127


class LCG:
    """确定性线性同余生成器（与 r06 同口径，便于跨角色复算）。"""

    def __init__(self, seed: int = MC_SEED) -> None:
        self.state = int(seed) % 2147483648 or 1

    def uniform(self) -> float:
        self.state = (self.state * 1103515245 + 12345) % 2147483648
        return self.state / 2147483648.0


def percentile(values: List[float], p: float) -> float:
    """最近秩百分位（p ∈ 0–100），避免插值引入实现差异。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((p / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(len(ordered) - 1, idx))]


def check_sizing(art: Dict[str, Any]) -> Dict[str, Any]:
    """测算门禁：双口径、假设、区间、方差与蒙特卡洛。"""
    top = art.get("top_down") or {}
    bottom = art.get("bottom_up") or {}
    assumptions = art.get("assumptions") or []
    mc = art.get("monte_carlo") or {}
    checks = [
        ck("size:top_down", bool(top.get("components")) and float(top.get("tam") or 0) > 0,
           "top-down 必须有分项且合计 >0"),
        ck("size:bottom_up_fields",
           all(k in bottom for k in ("customer_count", "addressable_fraction",
                                     "annual_quantity", "price_per_unit"))
           and float(bottom.get("tam") or 0) > 0, "bottom-up 四要素与结果必填"),
        ck("size:assumptions", len(assumptions) >= 3, "假设清单至少 3 条"),
        ck("size:assumption_evidence",
           all(bool(str(a.get("evidence_id") or "")) for a in assumptions),
           "每条假设必须挂 evidence_id"),
        ck("size:assumption_bounds",
           all(as_number(a.get("low")) <= as_number(a.get("value")) <= as_number(a.get("high"))
               for a in assumptions), "假设值必须在 [low, high] 内"),
        ck("size:variance", float(art.get("variance") or 0) <= 0.5,
           "双口径差异 >50% 说明口径不自洽"),
        ck("size:order",
           float(mc.get("p10") or 0) <= float(mc.get("p50") or 0) <= float(mc.get("p90") or 0),
           "必须满足 p10 ≤ p50 ≤ p90"),
        ck("size:mc_samples", int(mc.get("n") or 0) >= 1000,
           "蒙特卡洛样本数 ≥1000"),
        ck("size:bottom_up_in_range",
           float(mc.get("p10") or 0) <= float(bottom.get("tam") or 0)
           <= float(mc.get("p90") or 0), "bottom-up 结果应落在 p10–p90 区间"),
    ]
    return gate(checks)


def build(sizing: Dict[str, Any], seed: int = MC_SEED) -> Dict[str, Any]:
    """执行双口径测算与敏感性抽样，产出 sizing 工件。"""
    top = sizing.get("top_down") or {}
    components = []
    top_total = 0.0
    for raw in top.get("components") or []:
        value = as_number(raw.get("value"))
        components.append({"name": str(raw.get("name") or ""), "value": value})
        top_total += value

    raw_bottom = sizing.get("bottom_up") or {}
    customer_count = as_number(raw_bottom.get("customer_count"))
    addressable = as_number(raw_bottom.get("addressable_fraction"))
    quantity = as_number(raw_bottom.get("annual_quantity"))
    price = as_number(raw_bottom.get("price_per_unit"))
    bottom_tam = customer_count * addressable * quantity * price / 1e8

    assumptions: List[Dict[str, Any]] = []
    for raw in sizing.get("assumptions") or []:
        assumptions.append({
            "name": str(raw.get("name") or ""),
            "value": as_number(raw.get("value")),
            "low": as_number(raw.get("low")),
            "high": as_number(raw.get("high")),
            "unit": str(raw.get("unit") or ""),
            "evidence_id": str(raw.get("evidence_id") or ""),
            "basis": str(raw.get("basis") or ""),
        })

    rng = LCG(seed)
    draws: List[float] = []
    for _ in range(MC_N):
        total = 1.0
        for item in assumptions:
            low, high = item["low"], item["high"]
            u = rng.uniform()
            total *= low + (high - low) * u
        draws.append(total / 1e8)

    mean = (top_total + bottom_tam) / 2.0
    variance = abs(top_total - bottom_tam) / mean if mean else 1.0
    art: Dict[str, Any] = {
        "artifact": "sizing",
        "method": "top_down + bottom_up + deterministic_monte_carlo",
        "unit": "亿元",
        "top_down": {"tam": round(top_total, 4), "components": components},
        "bottom_up": {
            "tam": round(bottom_tam, 4),
            "customer_count": customer_count,
            "addressable_fraction": addressable,
            "annual_quantity": quantity,
            "price_per_unit": price,
        },
        "assumptions": assumptions,
        "monte_carlo": {
            "n": MC_N,
            "seed": seed,
            "p10": round(percentile(draws, 10), 4),
            "p50": round(percentile(draws, 50), 4),
            "p90": round(percentile(draws, 90), 4),
        },
        "variance": round(variance, 6),
    }
    art["gate"] = check_sizing(art)
    return art
