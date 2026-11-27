# -*- coding: utf-8 -*-
"""第 3 段 profile：六维数据质量 + 覆盖 + 偏差，先于任何结论。

方案 §13.4 / §17.2 要求逐项标注：
  缺失、重复、离群、泄漏、选择偏差、覆盖。
任一项不能证明“干净”时，后续阶段必须降级而不是补零。
"""
from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional

from skills import _common as c

from .common import ck, gate, now_iso, sha256_file

_SIX = ("completeness", "uniqueness", "validity", "leakage",
        "selection_bias", "coverage")
_LEAK_NAME_HINTS = ("future", "after", "next", "result", "target", "label",
                    "leak", "prediction", "score_final")
_WEIGHTS = {"completeness": 30, "uniqueness": 20, "validity": 15,
            "leakage": 15, "selection_bias": 10, "coverage": 10}


def _numeric_ratio(rows: List[Dict[str, str]], col: str) -> float:
    if not rows:
        return 0.0
    return len(c.numeric(rows, col)) / len(rows)


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 3:
        return 0.0
    mx, my = sum(xs[:n]) / n, sum(ys[:n]) / n
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    sxx = sum((xs[i] - mx) ** 2 for i in range(n))
    syy = sum((ys[i] - my) ** 2 for i in range(n))
    if sxx <= 0 or syy <= 0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def _iqr_outliers(vals: List[float], k: float = 1.5) -> Dict[str, Any]:
    if len(vals) < 4:
        return {"count": 0, "pct": 0.0, "low": None, "high": None}
    s = sorted(vals)
    def q(p: float) -> float:
        pos = (len(s) - 1) * p
        lo, hi = int(math.floor(pos)), int(math.ceil(pos))
        return s[lo] + (s[hi] - s[lo]) * (pos - lo)
    q1, q3 = q(0.25), q(0.75)
    iqr = q3 - q1
    low, high = q1 - k * iqr, q3 + k * iqr
    cnt = sum(1 for v in vals if v < low or v > high)
    return {"count": cnt, "pct": round(cnt / len(vals) * 100, 2),
            "low": round(low, 4), "high": round(high, 4)}


def profile(data_path: str, plan: Optional[Dict[str, Any]] = None,
            pk: Optional[str] = None, date: Optional[str] = None,
            semantic: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rows = c.load_csv(data_path)
    if not rows:
        return {"artifact": "data_profile", "gate": gate(
            [ck(False, "空数据或无法读取", "existence", "CRITICAL")], "profile")}
    fields = list(rows[0].keys())
    th = c.load_thresholds().get("quality", {})
    miss_warn = float(th.get("missing_warn_pct", 5.0))
    miss_fail = float(th.get("missing_fail_pct", 30.0))
    dup_crit = float(th.get("duplicate_critical_pct", 1.0))
    iqr_k = float(th.get("outlier_iqr_k", 1.5))

    metric = (plan or {}).get("metric") or ""
    dims = [d for d in ((plan or {}).get("dimensions") or []) if d in fields]

    # 1) 完整性
    cols = []
    for col in fields:
        miss = sum(1 for r in rows if not str(r.get(col, "")).strip())
        pct = miss / len(rows) * 100
        status = "FAIL" if pct >= miss_fail else ("WARN" if pct >= miss_warn else "PASS")
        cols.append({"column": col, "missing": miss, "missing_pct": round(pct, 2),
                     "status": status})
    worst = max(cols, key=lambda x: x["missing_pct"])
    completeness = {
        "status": "FAIL" if worst["status"] == "FAIL" else (
            "WARN" if worst["status"] == "WARN" else "PASS"),
        "score": round(max(0.0, 100 - worst["missing_pct"] * 2), 1),
        "columns": cols, "worst": worst,
    }

    # 2) 唯一性
    if pk and pk in fields:
        keys = [str(r.get(pk, "")) for r in rows]
        dup = len(keys) - len(set(keys))
        basis = f"主键 {pk}"
    else:
        keys = [tuple(str(r.get(f, "")) for f in fields) for r in rows]
        dup = len(keys) - len(set(keys))
        basis = "整行"
    dup_pct = dup / len(rows) * 100
    uniqueness = {
        "status": "FAIL" if dup_pct >= dup_crit else ("WARN" if dup else "PASS"),
        "score": round(max(0.0, 100 - dup_pct * 10), 1),
        "duplicate_rows": dup, "duplicate_pct": round(dup_pct, 2), "basis": basis,
    }

    # 3) 有效性（离群 + 非数值）
    valid_cols = []
    for col in fields:
        ratio = _numeric_ratio(rows, col)
        if ratio < 0.9:
            continue
        vals = c.numeric(rows, col)
        o = _iqr_outliers(vals, iqr_k)
        valid_cols.append({"column": col, **o, "numeric_ratio": round(ratio, 3)})
    max_out = max((v["pct"] for v in valid_cols), default=0.0)
    validity = {
        "status": "WARN" if max_out >= 5 or any(v["pct"] >= 10 for v in valid_cols) else "PASS",
        "score": round(max(0.0, 100 - max_out * 3), 1),
        "columns": valid_cols, "max_outlier_pct": round(max_out, 2),
    }
    if any(v["pct"] >= 20 for v in valid_cols):
        validity["status"] = "FAIL"

    # 4) 泄漏（与目标近乎一一对应，或列名像未来/结果）
    suspects = []
    metric_vals = c.numeric(rows, metric) if metric in fields else []
    for col in fields:
        if col == metric or col in (dims or []):
            continue
        low = col.lower()
        if any(h in low for h in _LEAK_NAME_HINTS):
            suspects.append({"column": col, "reason": "列名含未来/结果语义",
                             "correlation": None})
            continue
        if metric_vals and _numeric_ratio(rows, col) >= 0.9:
            vals = c.numeric(rows, col)
            if len(vals) == len(metric_vals):
                r = _pearson(vals, metric_vals)
                if abs(r) >= 0.999:
                    suspects.append({"column": col, "reason": "与目标相关性 ≥0.999",
                                     "correlation": round(r, 4)})
    leakage = {
        "status": "FAIL" if any(s["correlation"] is None for s in suspects) else (
            "WARN" if suspects else "PASS"),
        "score": 0.0 if any(s["correlation"] is None for s in suspects) else (
            50.0 if suspects else 100.0),
        "suspects": suspects,
    }

    # 5) 选择偏差（单一分段占比过高 / 分段不足）
    bias_dims, bias_fail = [], False
    for col in dims:
        counts: Dict[str, int] = {}
        for r in rows:
            k = str(r.get(col, ""))
            counts[k] = counts.get(k, 0) + 1
        total = sum(counts.values()) or 1
        top, top_n = max(counts.items(), key=lambda kv: kv[1])
        share = top_n / total
        status = "PASS"
        if len(counts) < 2:
            status = "FAIL"
            bias_fail = True
        elif share >= 0.8:
            status = "WARN"
        bias_dims.append({"column": col, "distinct": len(counts), "max_share": round(share, 4),
                          "top_value": top, "status": status})
    selection_bias = {
        "status": "FAIL" if bias_fail else (
            "WARN" if any(d["status"] == "WARN" for d in bias_dims) else "PASS"),
        "score": 40.0 if bias_fail else (70.0 if any(d["status"] == "WARN" for d in bias_dims) else 100.0),
        "dimensions": bias_dims,
    }

    # 6) 覆盖（日期跨度 + 分段覆盖）
    date_min = date_max = ""
    distinct_days = 0
    span_days = 0
    if date and date in fields:
        ds = sorted({str(r.get(date, ""))[:10] for r in rows if str(r.get(date, "")).strip()})
        if ds:
            date_min, date_max = ds[0], ds[-1]
            distinct_days = len(ds)
            try:
                import datetime as _dt
                span_days = (_dt.date.fromisoformat(date_max) - _dt.date.fromisoformat(date_min)).days + 1
            except ValueError:
                span_days = distinct_days
    cov_dims = []
    for col in dims:
        vals = {str(r.get(col, "")) for r in rows}
        cov_dims.append({"column": col, "distinct": len(vals),
                         "coverage_ratio": 1.0 if vals else 0.0})
    coverage = {
        "status": "PASS",
        "score": 100.0,
        "rows": len(rows),
        "date_min": date_min, "date_max": date_max,
        "distinct_days": distinct_days, "span_days": span_days,
        "day_coverage": round(distinct_days / span_days, 4) if span_days else 0.0,
        "dimensions": cov_dims,
    }
    if span_days and distinct_days / span_days < 0.8:
        coverage["status"] = "WARN"
        coverage["score"] = 70.0

    dims_out = {"completeness": completeness, "uniqueness": uniqueness,
                "validity": validity, "leakage": leakage,
                "selection_bias": selection_bias, "coverage": coverage}
    overall = sum(_WEIGHTS[k] * (dims_out[k]["score"] / 100.0) for k in _SIX)
    out: Dict[str, Any] = {
        "artifact": "data_profile",
        "version": "1.0",
        "generated_at": now_iso(),
        "source": {"path": os.path.abspath(data_path), "rows": len(rows),
                   "fields": fields,
                   "sha256": sha256_file(data_path) if os.path.exists(data_path) else ""},
        "plan_ref": {"metric": metric, "dimensions": dims,
                     "window": (plan or {}).get("window", "")},
        "dimensions": dims_out,
        "overall_score": round(overall, 1),
        "grade": "A" if overall >= 85 else ("B" if overall >= 70 else (
            "C" if overall >= 60 else "D")),
    }
    if semantic is not None:
        out["semantic_link"] = _semantic_link(semantic, rows)
    out["gate"] = check(out, plan)
    return out


def _semantic_link(semantic: Dict[str, Any], rows: List[Dict[str, str]]) -> Dict[str, Any]:
    try:
        from skills import s01_semantics
        return s01_semantics._link(semantic, rows)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"语义联动失败: {exc}"}


def check(profile: Dict[str, Any], plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    checks = []
    dims = profile.get("dimensions") or {}
    for k in _SIX:
        d = dims.get(k)
        checks.append(ck(isinstance(d, dict) and bool(d.get("status")),
                         f"六维之 {k} 已标注", "structure",
                         "CRITICAL" if not (isinstance(d, dict) and d.get("status")) else "OK"))
    if "completeness" in dims:
        st = dims["completeness"].get("status")
        checks.append(ck(st != "FAIL", f"完整性={st}（缺失率未超失败线）", "completeness",
                         "CRITICAL" if st == "FAIL" else "OK"))
    if "leakage" in dims:
        st = dims["leakage"].get("status")
        checks.append(ck(st != "FAIL", f"泄漏={st}（无未来/结果列）", "leakage",
                         "CRITICAL" if st == "FAIL" else "OK"))
    if "selection_bias" in dims:
        st = dims["selection_bias"].get("status")
        checks.append(ck(st != "FAIL", f"选择偏差={st}（分段可变）", "selection_bias",
                         "CRITICAL" if st == "FAIL" else "OK"))
    cov = dims.get("coverage") or {}
    if cov.get("date_min"):
        checks.append(ck(cov.get("day_coverage", 0) >= 0.8,
                         f"日期覆盖={cov.get('day_coverage')}", "coverage",
                         "HIGH" if cov.get("day_coverage", 0) < 0.8 else "OK"))
    score = profile.get("overall_score")
    checks.append(ck(isinstance(score, (int, float)) and score >= 50,
                     f"综合质量分={score}", "quality",
                     "CRITICAL" if not isinstance(score, (int, float)) or score < 50 else "OK"))
    if plan:
        plan_dims = [d for d in (plan.get("dimensions") or [])]
        cov_cols = {d.get("column") for d in (dims.get("coverage") or {}).get("dimensions", [])}
        missing = [d for d in plan_dims if d not in cov_cols]
        checks.append(ck(not missing, f"计划维度都有覆盖记录 {plan_dims}", "coverage",
                         "CRITICAL" if missing else "OK", missing=missing))
    link = profile.get("semantic_link")
    if link is not None:
        checks.append(ck(bool(link.get("ok")), "语义模型与真实数据联动",
                         "semantic", "CRITICAL" if not link.get("ok") else "OK"))
    return gate(checks, "profile")
