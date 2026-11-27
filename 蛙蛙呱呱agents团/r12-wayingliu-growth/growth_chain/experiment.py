# -*- coding: utf-8 -*-
"""第 2 段 · 实验设计：两比例功效 / MDE / 样本量 / 预注册 / 停止条件。

门禁：有可检验假设、有停止条件、预注册指纹存在、样本量可复算、
声明样本量必须达标；样本不足不得下结论。
"""
from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any, Dict

from . import common as c


def required_sample(p1: float, p2: float, alpha: float,
                    power: float) -> Dict[str, Any]:
    """经典两比例样本量（每臂）。

    n = (z_{1-α/2}·sqrt(2·p̄(1-p̄)) + z_power·sqrt(p1q1+p2q2))² / (p2-p1)²
    """
    z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
    z_beta = NormalDist().inv_cdf(power)
    pbar = (p1 + p2) / 2
    numerator = (z_alpha * math.sqrt(2 * pbar * (1 - pbar))
                 + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    per_arm = math.ceil(numerator / ((p2 - p1) ** 2))
    return {"per_arm": per_arm, "z_alpha": c.rnd(z_alpha, 4),
            "z_beta": c.rnd(z_beta, 4), "p_bar": c.rnd(pbar, 6)}


def check(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """独立门禁复核（样本不足不得下结论）。"""
    design = artifact.get("design") or {}
    p1 = float(design.get("baseline_rate") or 0)
    p2 = min(p1 + float(design.get("mde_abs") or 0), 0.999)
    required = artifact.get("required_sample_size_per_arm") or 0
    if p1 > 0 and p2 > p1:
        recomputed = required_sample(p1, p2, float(design.get("alpha", 0.05)),
                                    float(design.get("power", 0.8)))["per_arm"]
    else:
        recomputed = 0
    declared = artifact.get("declared_sample_size_per_arm")
    observed = artifact.get("observed_sample_size")
    claimed = bool(artifact.get("claimed_significant"))
    conclusion_ok = True
    if claimed:
        try:
            conclusion_ok = observed is not None and float(observed) >= float(required)
        except (TypeError, ValueError):
            conclusion_ok = False
    checks = [
        c.check("有假设", len(str(artifact.get("hypothesis") or "")) >= 8, ""),
        c.check("有停止条件", bool(artifact.get("stop_conditions")), ""),
        c.check("预注册指纹", bool(artifact.get("preregistration_sha256")), ""),
        c.check("样本量可复算", int(recomputed) == int(required),
                f"recomputed={recomputed} required={required}"),
        c.check("声明的样本量达标",
                declared is not None and float(declared) >= float(required),
                f"declared={declared} required={required}"),
        c.check("样本量不足不得下结论", conclusion_ok,
                f"observed={observed} required={required} claimed={claimed}"),
    ]
    return c.gate(checks)


def build(spec_path: str) -> Dict[str, Any]:
    """跑实验设计段并返回带门禁的工件。"""
    spec = c.load_json(spec_path)
    hypothesis = str(spec.get("hypothesis") or "").strip()
    metric = str(spec.get("metric") or "order_cvr")
    p1 = float(spec.get("baseline_rate", 0))
    mde_rel = float(spec.get("mde_rel", 0))
    alpha = float(spec.get("alpha", 0.05))
    power = float(spec.get("power", 0.80))
    traffic = float(spec.get("daily_traffic", 0) or 0)
    allocation = float(spec.get("allocation", 0.5) or 0.5)
    stops = [s for s in (spec.get("stop_conditions") or []) if str(s).strip()]
    preregistered = bool(spec.get("preregistered"))
    data_read_before = bool(spec.get("data_read_before_plan"))
    declared_n = spec.get("sample_size_per_arm")
    observed_n = spec.get("observed_sample_size")
    claimed = bool(spec.get("claimed_significant"))

    p2 = min(p1 * (1 + mde_rel), 0.999)
    size = required_sample(p1, p2, alpha, power) if 0 < p1 < p2 <= 1 else {
        "per_arm": 0, "z_alpha": None, "z_beta": None, "p_bar": None}
    required_n = int(size["per_arm"])
    min_days = math.ceil(required_n / (traffic * allocation)) if traffic > 0 and allocation > 0 else None

    recompute_ok = True
    if declared_n is not None:
        try:
            recompute_ok = abs(float(declared_n) - required_n) <= max(1.0, required_n * 0.02)
        except (TypeError, ValueError):
            recompute_ok = False

    declared_enough = True
    if declared_n is not None:
        try:
            declared_enough = float(declared_n) >= required_n
        except (TypeError, ValueError):
            declared_enough = False

    conclusion_ok = True
    if claimed:
        try:
            conclusion_ok = observed_n is not None and float(observed_n) >= required_n
        except (TypeError, ValueError):
            conclusion_ok = False

    checks = [
        c.check("有假设", len(hypothesis) >= 8, hypothesis[:40]),
        c.check("有停止条件", len(stops) >= 1, f"n={len(stops)}"),
        c.check("预注册指纹", preregistered and bool(spec.get("preregistered_at")),
                str(spec.get("preregistered_at"))),
        c.check("样本量可复算", recompute_ok,
                f"declared={declared_n} computed={required_n}"),
        c.check("声明的样本量达标", declared_enough,
                f"declared={declared_n} required={required_n}"),
        c.check("样本量不足不得下结论", conclusion_ok,
                f"observed={observed_n} required={required_n} claimed={claimed}"),
        c.check("未提前看数据", not data_read_before,
                f"data_read_before_plan={data_read_before}"),
    ]

    return c.stage_artifact("experiment", {
        "hypothesis": hypothesis,
        "metric": metric,
        "design": {
            "baseline_rate": c.rnd(p1, 6),
            "mde_rel": c.rnd(mde_rel, 4),
            "mde_abs": c.rnd(p2 - p1, 6),
            "alpha": alpha, "power": power,
            "allocation": allocation,
            "daily_traffic": traffic,
        },
        "required_sample_size_per_arm": required_n,
        "min_runtime_days": min_days,
        "declared_sample_size_per_arm": declared_n,
        "observed_sample_size": observed_n,
        "stop_conditions": stops,
        "preregistration_sha256": c.hash_obj({
            "hypothesis": hypothesis, "metric": metric, "baseline_rate": p1,
            "mde_rel": mde_rel, "alpha": alpha, "power": power,
            "stops": stops,
        }),
    }, checks)
