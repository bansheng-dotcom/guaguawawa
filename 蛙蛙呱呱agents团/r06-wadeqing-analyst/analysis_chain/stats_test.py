# -*- coding: utf-8 -*-
"""第 6 段 test：效应量 + 置信区间 + 假设检验 + 敏感性 + 多重检验校正。

方案 §13.4 / §17.2 的硬要求：
  - 有效应量、CI、前提检查、敏感性；
  - 样本不足不得下结论；
  - 多分段/多假设必须做 Holm 校正，不许挑显著的讲。
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional

from skills import _common as c
from skills import _stats

from .common import ck, gate, now_iso


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _skew(xs: List[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    m = _mean(xs)
    m2 = sum((x - m) ** 2 for x in xs) / n
    m3 = sum((x - m) ** 3 for x in xs) / n
    return m3 / (m2 ** 1.5) if m2 > 0 else 0.0


def _bootstrap_ci(a: List[float], b: List[float], seed: int = 0,
                  iters: int = 1000, alpha: float = 0.05) -> Dict[str, float]:
    if len(a) < 2 or len(b) < 2:
        return {"lo": 0.0, "hi": 0.0, "note": "样本不足"}
    rng = random.Random(seed)
    diffs = []
    for _ in range(iters):
        sa = [a[rng.randrange(len(a))] for _ in range(len(a))]
        sb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        diffs.append(_mean(sb) - _mean(sa))
    diffs.sort()
    lo = diffs[int((alpha / 2) * iters)]
    hi = diffs[min(iters - 1, int((1 - alpha / 2) * iters))]
    return {"lo": round(lo, 4), "hi": round(hi, 4),
            "iters": iters, "seed": seed, "alpha": alpha}


def _trimmed(xs: List[float], pct: float = 0.01) -> List[float]:
    if len(xs) < 100:
        return xs
    k = max(0, int(len(xs) * pct))
    s = sorted(xs)
    return s[k:len(s) - k] if len(s) > 2 * k else s


def _holm(pvals: List[float]) -> List[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    prev = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * pvals[i])
        prev = max(prev, val)
        adj[i] = prev
    return adj


def build(data_path: str, plan: Dict[str, Any], findings: Dict[str, Any],
          date: Optional[str] = None, seed: int = 0,
          min_n: int = 30) -> Dict[str, Any]:
    pg = plan.get("gate") or {}
    fg = findings.get("gate") or {}
    if not pg.get("ok") or not fg.get("ok"):
        return {"artifact": "stats", "gate": gate(
            [ck(False, "上游门禁未通过（plan/findings）", "upstream", "CRITICAL")], "test")}
    rows = c.load_csv(data_path)
    fields = list(rows[0].keys()) if rows else []
    metric = plan.get("metric", "")
    split = plan.get("split", "")
    date_col = date or "date"
    if metric not in fields or date_col not in fields or not split:
        return {"artifact": "stats", "gate": gate(
            [ck(False, "缺少指标/日期/切分点，无法检验", "schema", "CRITICAL")], "test")}

    before, after = [], []
    by_dim: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    dims = [d for d in (plan.get("dimensions") or []) if d in fields]
    chosen = dims[0] if dims else ""
    for r in rows:
        d = str(r.get(date_col, ""))[:10]
        if not d:
            continue
        try:
            v = float(r.get(metric, 0) or 0)
        except ValueError:
            continue
        per = "before" if d <= split else "after"
        (before if per == "before" else after).append(v)
        if chosen:
            seg = str(r.get(chosen, ""))
            by_dim.setdefault(chosen, {}).setdefault(seg, {"before": [], "after": []})[per].append(v)

    th = c.load_thresholds().get("statistics", {})
    alpha = float(th.get("alpha", 0.05))
    sd_b, sd_a = _sd(before), _sd(after)
    if len(before) < 2 or len(after) < 2 or (sd_b == 0 and sd_a == 0):
        headline = {"n_before": len(before), "n_after": len(after),
                    "mean_before": round(_mean(before), 4),
                    "mean_after": round(_mean(after), 4),
                    "diff": round(_mean(after) - _mean(before), 4),
                    "cohens_d": 0.0, "effect_grade": "small",
                    "p_value_approx": 1.0, "p_exact": None, "p_method": "degenerate",
                    "significant": False,
                    "note": "样本不足或方差为 0，未做 Welch t"}
    else:
        headline = _stats.welch_t(before, after, "before", "after")
    ci = _bootstrap_ci(before, after, seed=seed, alpha=alpha)
    mean_b, mean_a = _mean(before), _mean(after)
    rel_lift = (mean_a - mean_b) / mean_b * 100 if mean_b else None

    ratio = (max(sd_a, sd_b) / min(sd_a, sd_b)) if min(sd_a, sd_b) > 0 else 0.0
    assumptions = {
        "n_before": len(before), "n_after": len(after),
        "min_n": min_n,
        "sample_ok": len(before) >= min_n and len(after) >= min_n,
        "skew_before": round(_skew(before), 4), "skew_after": round(_skew(after), 4),
        "skew_ok": abs(_skew(before)) <= 1 and abs(_skew(after)) <= 1,
        "variance_ratio": round(ratio, 4),
        "variance_ok": ratio <= 3.0 if ratio else True,
    }

    trimmed_diff = _mean(_trimmed(after)) - _mean(_trimmed(before))
    raw_diff = mean_a - mean_b
    sensitivity = {
        "trim_pct": 0.01,
        "raw_diff": round(raw_diff, 4),
        "trimmed_diff": round(trimmed_diff, 4),
        "change_pct": round(abs(trimmed_diff - raw_diff) / abs(raw_diff) * 100, 2) if raw_diff else 0.0,
        "stable": (abs(trimmed_diff - raw_diff) / abs(raw_diff) <= 0.2) if raw_diff else True,
    }

    tests: List[Dict[str, Any]] = []
    pvals: List[float] = []
    for seg, groups in sorted((by_dim.get(chosen) or {}).items()):
        a, b = groups["before"], groups["after"]
        if len(a) < 2 or len(b) < 2:
            continue
        if _sd(a) == 0 and _sd(b) == 0:
            continue
        r = _stats.welch_t(a, b, f"{seg}:before", f"{seg}:after")
        p = r.get("p_exact") if r.get("p_exact") is not None else r.get("p_value_approx")
        p = float(p if p is not None else 1.0)
        pvals.append(p)
        tests.append({"segment": seg, "n_before": r.get("n_a"), "n_after": r.get("n_b"),
                      "mean_before": r["mean_a"], "mean_after": r["mean_b"],
                      "diff": r["diff"], "cohens_d": r["cohens_d"],
                      "effect_grade": r["effect_grade"],
                      "p_raw": round(p, 6)})
    adj = _holm(pvals) if pvals else []
    for t, padj in zip(tests, adj):
        t["p_adjusted"] = round(padj, 6)
        t["significant_after_correction"] = padj < alpha

    out = {
        "artifact": "stats",
        "version": "1.0",
        "generated_at": now_iso(),
        "metric": metric,
        "dimension": chosen,
        "alpha": alpha,
        "headline": {
            "test": "welch_t",
            "n_before": len(before), "n_after": len(after),
            "mean_before": round(mean_b, 4), "mean_after": round(mean_a, 4),
            "diff": round(raw_diff, 4), "relative_lift_pct": round(rel_lift, 2) if rel_lift is not None else None,
            "cohens_d": headline.get("cohens_d"),
            "effect_grade": headline.get("effect_grade"),
            "p_raw": headline.get("p_exact") if headline.get("p_exact") is not None
            else headline.get("p_value_approx"),
            "p_method": headline.get("p_method"),
            "ci": ci,
            "significant": bool(headline.get("significant")),
        },
        "assumptions": assumptions,
        "sensitivity": sensitivity,
        "segments": {"dimension": chosen, "holm_family_size": len(tests), "tests": tests},
        "method_note": "Welch t（正态近似 p）+ 百分位 bootstrap CI + Holm 校正；"
                       "p 值不等于效应量，显著不等于重要。",
    }
    out["gate"] = check(out, min_n)
    return out


def check(stats: Dict[str, Any], min_n: int = 30) -> Dict[str, Any]:
    checks = []
    h = stats.get("headline") or {}
    for k in ("n_before", "n_after", "mean_before", "mean_after", "diff",
              "cohens_d", "effect_grade", "p_raw", "ci"):
        empty = h.get(k) in (None, "", [], {})
        checks.append(ck(not empty, f"headline 含 {k}", "statistics",
                         "CRITICAL" if empty else "OK"))
    ci = h.get("ci") or {}
    checks.append(ck(isinstance(ci.get("lo"), (int, float)) and
                     isinstance(ci.get("hi"), (int, float)) and ci["lo"] <= ci["hi"],
                     f"置信区间 [{ci.get('lo')}, {ci.get('hi')}]", "uncertainty",
                     "CRITICAL" if not (isinstance(ci.get("lo"), (int, float)) and
                                        isinstance(ci.get("hi"), (int, float))) else "OK"))
    a = stats.get("assumptions") or {}
    checks.append(ck(bool(a.get("sample_ok")),
                     f"样本量 n={a.get('n_before')}/{a.get('n_after')}（每组≥{a.get('min_n', min_n)}）",
                     "sample", "CRITICAL" if not a.get("sample_ok") else "OK"))
    checks.append(ck(bool(a.get("skew_ok")), f"偏度检查={a.get('skew_ok')}", "assumptions",
                     "HIGH" if not a.get("skew_ok") else "OK"))
    checks.append(ck(bool(a.get("variance_ok")), f"方差比={a.get('variance_ratio')}",
                     "assumptions", "HIGH" if not a.get("variance_ok") else "OK"))
    s = stats.get("sensitivity") or {}
    checks.append(ck(s.get("stable") is True or s.get("change_pct") is not None,
                     f"敏感性：原始/截尾差 {s.get('raw_diff')}/{s.get('trimmed_diff')}",
                     "sensitivity", "HIGH" if s.get("stable") is False else "OK"))
    seg = stats.get("segments") or {}
    tests = seg.get("tests") or []
    if tests:
        checks.append(ck(all("p_adjusted" in t for t in tests),
                         f"分段检验已做 Holm 校正（n={len(tests)}）", "multiple_testing",
                         "CRITICAL" if not all("p_adjusted" in t for t in tests) else "OK"))
    if h.get("p_raw") is not None and h.get("cohens_d") is not None:
        weak = h.get("significant") and abs(h.get("cohens_d", 0)) < 0.2
        checks.append(ck(not weak, "显著但效应量过小，不得当重要结论", "interpretation",
                         "HIGH" if weak else "OK"))
    return gate(checks, "test")
