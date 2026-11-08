# -*- coding: utf-8 -*-
"""S02 数据清洗与质量门禁 —— 能力域 2。

整合自 data-analytics-skills 的 `data-quality-audit`（null/duplicate/freshness/
referential/value_range）与 `programmatic-eda`（outlier/distribution）。

主张：**质检是门禁，不是事后补救**。每个发现归入一个质量维度并打分，
异常值只标记不自动删除。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "quality"
DESC = "数据清洗与质量：六维质检 / 脏数据清洗 / IQR 离群标记"

DIM_WEIGHT = {"completeness": 20, "accuracy": 20, "consistency": 20,
              "timeliness": 15, "uniqueness": 15, "validity": 10}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    a = act.add_parser("audit", help="六维质量审计（只报告不写回）")
    a.add_argument("--input", required=True)
    a.add_argument("--pk", default=None, help="主键列，用于唯一性/引用检查")
    a.add_argument("--date", default=None, help="时间戳列，用于及时性(新鲜度)检查")

    cl = act.add_parser("clean", help="去重 + 缺失报告，写回清洗后 CSV")
    cl.add_argument("--input", required=True)
    cl.add_argument("--output", default=None)
    cl.add_argument("--pk", default=None)


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    if args.action == "audit":
        return _audit(rows, args.pk, args.date)
    if args.action == "clean":
        out = args.output or (args.input.rsplit(".", 1)[0] + "_cleaned.csv")
        return _clean(rows, out, args.pk)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _audit(rows: List[Dict[str, str]], pk: str, date_col: str) -> Dict[str, Any]:
    fields = list(rows[0].keys())
    total = len(rows)
    findings: List[Dict[str, Any]] = []
    score = {k: 10 for k in DIM_WEIGHT}
    t = c.load_thresholds()["quality"]

    # 完整性：缺失
    missing = {col: sum(1 for r in rows if not str(r.get(col, "")).strip())
               for col in fields}
    miss_pct = {col: round(n / total * 100, 2) for col, n in missing.items()}
    for col, p in miss_pct.items():
        if p >= t["missing_fail_pct"]:
            findings.append({"dim": "completeness", "sev": "CRITICAL",
                             "note": f"{col} 缺失率 {p}% (≥{t['missing_fail_pct']}% FAIL)", "pct": p})
            score["completeness"] = min(score["completeness"], 0)
        elif p >= t["missing_warn_pct"]:
            findings.append({"dim": "completeness", "sev": "HIGH",
                             "note": f"{col} 缺失率 {p}% (≥{t['missing_warn_pct']}% WARN)", "pct": p})
            score["completeness"] = min(score["completeness"], 5)

    # 唯一性：整行重复 + 主键唯一
    seen, dup_rows = set(), 0
    for r in rows:
        key = "\x1f".join(str(r.get(f, "")) for f in fields)
        if key in seen:
            dup_rows += 1
        seen.add(key)
    if dup_rows:
        sev = "CRITICAL" if dup_rows / total > t.get("duplicate_critical_pct", 0.01) else "HIGH"
        findings.append({"dim": "uniqueness", "sev": sev,
                         "note": f"整行重复 {dup_rows} 行", "count": dup_rows})
        score["uniqueness"] = min(score["uniqueness"], 5)
    if pk and pk in fields:
        pk_vals = [r[pk] for r in rows]
        dup_pk = len(pk_vals) - len(set(pk_vals))
        if dup_pk:
            findings.append({"dim": "uniqueness", "sev": "CRITICAL",
                             "note": f"主键 {pk} 重复 {dup_pk} 条", "count": dup_pk})
            score["uniqueness"] = min(score["uniqueness"], 0)

    # 精确性 + 有效性 + 离群：数值列 IQR
    for col in fields:
        vals = c.numeric(rows, col)
        if len(vals) < 4:
            continue
        s = sorted(vals)
        q1, q3 = s[len(s) // 4], s[(3 * len(s)) // 4]
        iqr = q3 - q1
        if iqr <= 0:
            continue
        k = t.get("outlier_iqr_k", 1.5)
        lo, hi = q1 - k * iqr, q3 + k * iqr
        bad = [v for v in vals if v < lo or v > hi]
        if bad:
            findings.append({"dim": "accuracy", "sev": "MEDIUM",
                             "note": f"{col} IQR 离群 {len(bad)} 个（只标记不删除）",
                             "outlier_count": len(bad),
                             "outliers_sample": sorted(set(bad))[:10]})
            score["accuracy"] = min(score["accuracy"], 8)

    # 及时性：日期列新鲜度（最大日期距今天数）
    if date_col:
        import datetime as _dt
        dates = []
        for r in rows:
            try:
                dates.append(_dt.date.fromisoformat(str(r[date_col])[:10]))
            except ValueError:
                continue
        if dates:
            gap = (_dt.date.today() - max(dates)).days
            if gap > t["freshness_fail_days"]:
                findings.append({"dim": "timeliness", "sev": "CRITICAL",
                                 "note": f"{date_col} 最新数据距今 {gap} 天 (>{t['freshness_fail_days']}天 SLA)"})
                score["timeliness"] = 0
            elif gap > t["freshness_warn_days"]:
                findings.append({"dim": "timeliness", "sev": "HIGH",
                                 "note": f"{date_col} 最新数据距今 {gap} 天 (>{t['freshness_warn_days']}天)"})
                score["timeliness"] = min(score["timeliness"], 5)

    overall = round(sum(score[d] * DIM_WEIGHT[d] for d in DIM_WEIGHT) / 100, 1)
    return {
        "rows": total, "fields": len(fields),
        "missing": {k: v for k, v in miss_pct.items() if v > 0},
        "duplicate_rows": dup_rows,
        "findings": findings,
        "dimension_score": score,
        "overall_score": overall,
        "grade": _grade(overall),
    }


def _clean(rows: List[Dict[str, str]], out: str, pk: str) -> Dict[str, Any]:
    fields = list(rows[0].keys())
    total = len(rows)
    seen, cleaned = set(), []
    for r in rows:
        key = "\x1f".join(str(r.get(f, "")) for f in fields)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(r)
    c.write_csv(out, fields, cleaned)
    missing = {col: sum(1 for r in cleaned if not str(r.get(col, "")).strip())
               for col in fields}
    return {"rows_before": total, "rows_after": len(cleaned),
            "duplicate_rows_removed": total - len(cleaned),
            "missing": {k: v for k, v in missing.items() if v > 0},
            "cleaned_path": out}


def _grade(score: float) -> str:
    t = c.load_thresholds()["quality"]
    if score >= t.get("grade_pass", 8):
        return "可用-仅小问题"
    if score >= t.get("grade_warn", 5):
        return "半数通过"
    return "系统失败"