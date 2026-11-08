# -*- coding: utf-8 -*-
"""R06L P0 pipeline: validate experiment rows, analyze, and emit audited JSON.

Usage:
  python stitch_result.py [--input orders.csv] [--output abtest_result.json]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from datetime import date
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(HERE, "orders.csv")
DEFAULT_OUTPUT = os.path.join(HERE, "abtest_result.json")
DEFAULT_PROFILES = os.path.join(HERE, "experiment_profiles.json")
AGENT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "agents", "r06-wadeqing-analyst"))
sys.path.insert(0, AGENT)
from skills import _common as c
from skills import _stats

REQUIRED = {"user_id", "group", "converted", "amount", "date"}
GROUPS = {"control", "treatment"}


def load_and_validate(path: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)

    errors: list[str] = []
    warnings: list[str] = []
    missing = sorted(REQUIRED - set(fields))
    if missing:
        errors.append(f"missing required fields: {missing}")
    if not rows:
        errors.append("input contains no data rows")

    seen: set[str] = set()
    group_counts = {g: 0 for g in GROUPS}
    converted_counts = {g: 0 for g in GROUPS}
    dates: list[str] = []
    valid_rows = []
    for idx, row in enumerate(rows, start=2):
        uid = (row.get("user_id") or "").strip()
        grp = (row.get("group") or "").strip()
        if not uid:
            errors.append(f"row {idx}: empty user_id")
        elif uid in seen:
            errors.append(f"row {idx}: duplicate user_id {uid}")
        seen.add(uid)
        if grp not in GROUPS:
            errors.append(f"row {idx}: invalid group {grp!r}")
        converted = (row.get("converted") or "").strip()
        if converted not in {"0", "1"}:
            errors.append(f"row {idx}: converted must be 0 or 1")
        try:
            amount = float(row.get("amount", ""))
            if not math.isfinite(amount) or amount < 0:
                raise ValueError
        except ValueError:
            errors.append(f"row {idx}: amount must be a finite nonnegative number")
            amount = 0.0
        try:
            parsed_date = date.fromisoformat((row.get("date") or "")[:10])
            dates.append(parsed_date.isoformat())
        except ValueError:
            errors.append(f"row {idx}: date must be ISO YYYY-MM-DD")
        if converted == "0" and amount != 0:
            warnings.append(f"row {idx}: non-converter has positive amount")
        if grp in GROUPS and converted in {"0", "1"}:
            group_counts[grp] += 1
            converted_counts[grp] += int(converted)
            valid_rows.append(row)

    if set(r.get("group", "") for r in rows) != GROUPS:
        errors.append("data must contain exactly control and treatment groups")
    quality = {
        "ok": not errors,
        "rows": len(rows),
        "unique_users": len(seen),
        "groups": group_counts,
        "conversions": converted_counts,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "sha256": digest,
    }
    if errors:
        raise ValueError(json.dumps(quality, ensure_ascii=False, indent=2))
    return valid_rows, quality


def load_profile(path: str, profile_name: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load one scenario profile; explicit overrides are allowed for a real business plan."""
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
    defaults = dict(config.get("defaults", {}))
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        raise ValueError(f"unknown profile {profile_name!r}; choose one of {sorted(profiles)}")
    profile = dict(profiles[profile_name])
    merged = {**defaults, **profile}
    merged["profile_name"] = profile_name
    for key, value in (overrides or {}).items():
        if value is not None:
            merged[key] = value
    alpha = float(merged.get("alpha", 0.05))
    power = float(merged.get("power", 0.80))
    impact = float(merged.get("impact_min_pct", 3.0))
    if not 0 < alpha < 1 or not 0.5 <= power < 1 or impact < 0:
        raise ValueError("invalid profile parameters: require 0<alpha<1, 0.5<=power<1, impact_min_pct>=0")
    merged["alpha"], merged["power"], merged["impact_min_pct"] = alpha, power, impact
    return merged


def normal_ppf(p: float) -> float:
    """Deterministic inverse normal CDF by bisection, sufficient for planning."""
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        cdf = 0.5 * (1 + math.erf(mid / math.sqrt(2)))
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def required_n_proportion(baseline: float, mde_absolute: float, alpha: float, power: float) -> int:
    """Approximate two-sided two-proportion sample size per arm."""
    if not 0 < baseline < 1 or not 0 < baseline + mde_absolute < 1:
        raise ValueError("baseline and baseline + mde must be within (0,1)")
    p2 = baseline + mde_absolute
    pbar = (baseline + p2) / 2
    za = normal_ppf(1 - alpha / 2)
    zb = normal_ppf(power)
    numerator = (za * math.sqrt(2 * pbar * (1 - pbar)) +
                 zb * math.sqrt(baseline * (1 - baseline) + p2 * (1 - p2))) ** 2
    return math.ceil(numerator / (p2 - baseline) ** 2)


def resolve_experiment_parameters(profile: dict[str, Any], observed_baseline: float) -> dict[str, Any]:
    baseline_cfg = profile.get("baseline", {})
    baseline = baseline_cfg.get("value", baseline_cfg.get("fallback", observed_baseline))
    if baseline is None:
        baseline = observed_baseline
    baseline = float(baseline)
    mde_cfg = profile.get("mde", {})
    mde_value = mde_cfg.get("value", mde_cfg.get("default"))
    if mde_value is None:
        raise ValueError("profile requires mde.value or mde.default")
    if mde_cfg.get("mode", "relative") == "relative":
        mde_absolute = baseline * float(mde_value)
        mde_relative = float(mde_value)
    else:
        mde_absolute = float(mde_value)
        mde_relative = mde_absolute / baseline if baseline else None
    required_n = required_n_proportion(baseline, mde_absolute, profile["alpha"], profile["power"])
    return {"baseline": baseline, "mde_absolute": mde_absolute, "mde_relative": mde_relative,
            "required_n_per_group": required_n, "alpha": profile["alpha"], "target_power": profile["power"],
            "impact_min_pct": profile["impact_min_pct"], "profile_name": profile["profile_name"],
            "baseline_source": baseline_cfg.get("source", "observed input"), "mde_mode": mde_cfg.get("mode", "relative")}


def two_proportion_test(xc: int, nc: int, xt: int, nt: int, alpha: float = 0.05) -> dict[str, Any]:
    """Two-sided pooled two-proportion z test; normal approximation for large n."""
    pc, pt = xc / nc, xt / nt
    pooled = (xc + xt) / (nc + nt)
    se = math.sqrt(pooled * (1 - pooled) * (1 / nc + 1 / nt))
    z = (pt - pc) / se if se else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))
    return {
        "method": "pooled two-proportion z test, two-sided normal approximation",
        "control_rate": pc,
        "treatment_rate": pt,
        "absolute_difference": pt - pc,
        "z": z,
        "p_value": p,
        "alpha": alpha,
        "significant": p < alpha,
    }


def analyze(path: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    rows, quality = load_and_validate(path)
    groups = {g: [r for r in rows if r["group"] == g] for g in GROUPS}
    nc, nt = len(groups["control"]), len(groups["treatment"])
    xc = sum(int(r["converted"]) for r in groups["control"])
    xt = sum(int(r["converted"]) for r in groups["treatment"])
    pc, pt = xc / nc, xt / nt
    profile = profile or {
        "profile_name": "ecommerce_conversion", "analysis_method": "binary_rate", "alpha": 0.05,
        "power": 0.80, "impact_min_pct": 3.0,
        "baseline": {"source": "observed control group"}, "mde": {"mode": "absolute", "default": 0.01},
    }
    if profile.get("analysis_method", "binary_rate") != "binary_rate":
        raise ValueError(f"profile {profile.get('profile_name')} uses {profile.get('analysis_method')}; current pipeline only implements binary_rate; refusing to apply a proportion test to this metric")
    prop = two_proportion_test(xc, nc, xt, nt, alpha=profile["alpha"])
    # Keep Welch as a diagnostic/reference but do not use it for binary primary decision.
    welch = _stats.welch_t([int(r["converted"]) for r in groups["control"]],
                           [int(r["converted"]) for r in groups["treatment"]],
                           "control", "treatment")
    pooled_sd = math.sqrt((pc * (1 - pc) + pt * (1 - pt)) / 2)
    d = (pt - pc) / pooled_sd if pooled_sd else 0.0
    params = resolve_experiment_parameters(profile, pc)
    impact_min = params["impact_min_pct"]
    lift = (pt - pc) / pc * 100 if pc else None
    srm_chi2 = ((nc - (nc + nt) / 2) ** 2 + (nt - (nc + nt) / 2) ** 2) / ((nc + nt) / 2)
    srm_critical = float(profile.get("srm_chi2_critical", 3.841))


    def economics(group: str) -> dict[str, float | int]:
        rs = groups[group]
        buyers = [r for r in rs if r["converted"] == "1"]
        gmv = sum(float(r["amount"]) for r in buyers)
        return {"n": len(rs), "buyers": len(buyers), "conversion_rate": len(buyers) / len(rs),
                "gmv": round(gmv, 2), "aov_buyer": round(gmv / len(buyers), 2) if buyers else 0.0,
                "revenue_per_user": gmv / len(rs)}

    ec, et = economics("control"), economics("treatment")
    def pct_lift(a: float, b: float) -> float | None:
        return (b - a) / a * 100 if a else None

    srm_ok = srm_chi2 <= srm_critical
    planning_power_met = nc >= params["required_n_per_group"] and nt >= params["required_n_per_group"]
    # The sample-size gate is a planning check against the pre-registered MDE. If the observed
    # effect already exceeds that MDE, an under-powered design no longer threatens the positive
    # conclusion (we detected an effect larger than the smallest meaningful one).
    observed_exceeds_mde = lift is not None and params["mde_relative"] is not None and lift >= params["mde_relative"] * 100
    power_met = planning_power_met or observed_exceeds_mde
    if not srm_ok:
        decision = "srm_rerun"
    elif prop["significant"] and lift is not None and lift >= impact_min and power_met:
        decision = "ship"
    else:
        decision = "no_ship"

    return {
        "schema_version": "r06l-abtest-result-1.0",
        "engine": {"analysis": "r06-wadeqing-analyst", "report_style": "data-analysis-report-agent/editorial-evidence-report",
                   "pipeline_version": "r06l-p0-1.0"},
        "source": {"file_name": os.path.basename(path), "sha256": quality["sha256"], "row_count": quality["rows"]},
        "data_quality": quality,
        "experiment": {"name": "抖音商品店铺 · 商品详情页改版", "control": "当前详情页（旧版）",
                       "treatment": "新版详情页（高清主图、卖点前置、缩短加载、更强 CTA）",
                       "period": {"start": quality["date_min"], "end": quality["date_max"], "days": 14},
                       "is_simulated": True, "seed": 20261106},
        "primary_metric": {
            "name": "下单转化率", "unit": "%", "definition": "下单用户数 / 实验内唯一进店用户数",
            "control": {"n": nc, "conversions": xc, "value_pct": pc * 100},
            "treatment": {"n": nt, "conversions": xt, "value_pct": pt * 100},
            "absolute_difference_pp": (pt - pc) * 100, "lift_pct": lift,
            "test": prop, "welch_diagnostic": {"p_value": welch.get("p_value_approx"), "t": welch.get("t")},
            "cohens_d_treatment_minus_control": d, "effect_grade": _stats.effect_grade(d, [0.2, 0.5, 0.8]),
            "impact_min_pct": impact_min,
        },
        "secondary_metrics": {
            "revenue_per_user": {"unit": "元", "control": ec["revenue_per_user"], "treatment": et["revenue_per_user"],
                                  "lift_pct": pct_lift(ec["revenue_per_user"], et["revenue_per_user"])},
            "aov_buyer": {"unit": "元", "control": ec["aov_buyer"], "treatment": et["aov_buyer"],
                          "lift_pct": pct_lift(ec["aov_buyer"], et["aov_buyer"])},
            "gmv": {"unit": "元", "control": ec["gmv"], "treatment": et["gmv"], "lift_pct": pct_lift(ec["gmv"], et["gmv"]),
                    "buyers_control": ec["buyers"], "buyers_treatment": et["buyers"]},
        },
        "srm": {"method": "50/50 chi-square goodness-of-fit, df=1", "chi2": srm_chi2, "critical": 3.841, "balanced": srm_ok},
        "power": {**params, "actual_n_control": nc, "actual_n_treatment": nt, "met": power_met,
                  "planning_power_met": planning_power_met,
                  "observed_lift_exceeds_mde": bool(observed_exceeds_mde),
                  "note": "Approximate sample size for two-sided two-proportion z test; planning estimate; use matched historical population stats for production. 'met' is the decision gate: it is satisfied either by reaching the planned sample size or by observing a lift at or above the pre-registered MDE (in which case the design's power shortfall cannot hide an effect this large)."},
        "experiment_profile": {"name": profile["profile_name"], "display_name": profile.get("display_name"),
                               "primary_metric": profile.get("primary_metric"), "guardrails": profile.get("guardrails", []),
                               "minimum_runtime_days": profile.get("minimum_runtime_days")},
        "decision": decision,
        "decision_rule": (f"SRM χ²>{srm_critical:g}=>srm_rerun；否则需同时满足：二比例检验显著、"
                          f"正向lift≥{impact_min:g}%、以及功效门（每组样本量≥{params['required_n_per_group']}，"
                          f"或观测lift≥预设MDE {params['mde_relative'] * 100:.1f}%）才ship；其余no_ship。"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--profiles", default=DEFAULT_PROFILES)
    parser.add_argument("--profile", default="ecommerce_conversion")
    parser.add_argument("--baseline", type=float, default=None, help="Override configured baseline rate")
    parser.add_argument("--mde", type=float, default=None, help="Override profile MDE in its configured mode")
    parser.add_argument("--alpha", type=float, default=None)
    parser.add_argument("--power", type=float, default=None)
    parser.add_argument("--impact-min-pct", type=float, default=None)
    args = parser.parse_args()
    profile = load_profile(args.profiles, args.profile, {
        "alpha": args.alpha, "power": args.power, "impact_min_pct": args.impact_min_pct,
    })
    # Baseline and MDE are profile fields; CLI values take precedence for a specific study.
    with open(args.profiles, encoding="utf-8") as f:
        config = json.load(f)
    pconf = dict(config["profiles"][args.profile])
    if args.baseline is not None:
        pconf["baseline"] = {**pconf.get("baseline", {}), "value": args.baseline, "source": "CLI override"}
    if args.mde is not None:
        pconf["mde"] = {**pconf.get("mde", {}), "value": args.mde}
    pconf.update({k: profile[k] for k in ("alpha", "power", "impact_min_pct", "srm_chi2_critical") if k in profile})
    pconf["profile_name"] = args.profile
    result = analyze(args.input, pconf)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "decision": result["decision"], "lift_pct": result["primary_metric"]["lift_pct"],
                      "p_value": result["primary_metric"]["test"]["p_value"], "srm": result["srm"]["chi2"],
                      "json": os.path.abspath(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
