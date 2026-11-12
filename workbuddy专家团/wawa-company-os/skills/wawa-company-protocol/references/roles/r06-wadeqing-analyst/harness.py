#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R06 的确定性验证器层（harness）。

对齐 data-analysis-report-agent 的 harness 设计：把「质量门禁」做成可独立
运行、返回 exit code 的确定性校验，而非写进正文的叙述。每个 validator 读
输入工件 → 逐条判据 → 输出 `{ok, checks[]}`，`ok=false` 时返回码非 0。

用法：
    python harness.py dataset --input examples/orders.csv [--semantic semantic_model.json]
    python harness.py report  --input report.md
    python harness.py semantic --input semantic_model.json
    python harness.py chart    --input chart_spec.json
    python harness.py verify   --data orders.csv --report report.md --semantic semantic_model.json

这是「可审计」的关键：编排器 / R04 蛙挑刺 可直接调用它做硬门禁复核。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from skills import _common as c        # noqa: E402
from skills import s01_semantics, s08_viz  # noqa: E402

BANNED_WORDS = ["有待进一步分析", "可能吧", "大概也许", "差不多就行", "TODO"]


def _t() -> dict:
    return c.load_thresholds()


def check(ok: bool, msg: str, dim: str, sev: str = "OK", **evidence) -> dict:
    d = {"ok": ok, "msg": msg, "dim": dim, "sev": sev}
    d.update(evidence)
    return d


def _grade(checks) -> str:
    if not checks:
        return "EMPTY"
    if all(x["ok"] for x in checks):
        return "PASS"
    if any(x["sev"] == "CRITICAL" and not x["ok"] for x in checks):
        return "FAIL"
    return "WARN"


# --------------------------------------------------------------------------- #
# Validators
# --------------------------------------------------------------------------- #
def validate_dataset(path: str, semantic_path: str = None) -> dict:
    t = _t()["quality"]
    checks = []
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL", "path": path,
                "checks": [check(False, f"文件不存在 {path}", "existence", "CRITICAL")]}
    rows = c.load_csv(path)
    checks.append(check(len(rows) > 0, f"行数={len(rows)}", "existence",
                        "OK" if rows else "CRITICAL", rows=len(rows)))
    if not rows:
        return {"ok": False, "grade": "FAIL", "path": path, "checks": checks}

    fields = list(rows[0].keys())
    checks.append(check(len(fields) > 0, f"字段数={len(fields)}", "schema", "OK"))

    # 缺失率门禁（阈值外置）
    for col in fields:
        miss = sum(1 for r in rows if not str(r.get(col, "")).strip())
        pct = miss / len(rows) * 100
        if pct >= t["missing_fail_pct"]:
            checks.append(check(False, f"{col} 缺失率 {pct:.1f}% ≥ {t['missing_fail_pct']}%",
                                "completeness", "CRITICAL", pct=round(pct, 1)))
        elif pct >= t["missing_warn_pct"]:
            checks.append(check(False, f"{col} 缺失率 {pct:.1f}% ≥ {t['missing_warn_pct']}%",
                                "completeness", "HIGH", pct=round(pct, 1)))
        else:
            checks.append(check(True, f"{col} 缺失率 {pct:.1f}%", "completeness",
                                "OK", pct=round(pct, 1)))

    # 数值列值域 sanity / 防幻觉：对「多数值可解析为数值」的列，检测少数非数值/空
    for col in fields:
        vals = c.numeric(rows, col)
        n_numeric = len(vals)
        if n_numeric / len(rows) >= 0.5:      # 视为数值列（分类列如 id/date/status 跳过）
            n_nonnum = len(rows) - n_numeric
            if n_nonnum:
                checks.append(check(False, f"{col} 有 {n_nonnum} 行非数值（含空）",
                                    "accuracy", "HIGH", non_numeric=n_nonnum))

    # 语义↔数据真联动（T5）：语义模型的每个 expr 必须落到真实数据列，否则是幻觉
    if semantic_path and os.path.exists(semantic_path):
        sem = json.loads(open(semantic_path, encoding="utf-8").read())
        link = s01_semantics._link(sem, rows)
        for lk in link["links"]:
            present = lk.get("present", False)
            obj, name, expr = lk.get("obj"), lk.get("name"), lk.get("expr")
            checks.append(check(present,
                                f"语义{obj}[{name}] expr={expr} 列{'存在' if present else '缺失(幻觉)'}",
                                "semantic",
                                "CRITICAL" if not present else "OK",
                                expr=expr))
            if obj == "measure" and present and not lk.get("computable", True):
                checks.append(check(False, f"measure[{name}] {lk.get('reason')}",
                                    "semantic", "HIGH"))
            if obj == "dimension" and lk.get("type_mismatch"):
                mm = lk["type_mismatch"]
                checks.append(check(False,
                                    f"dimension[{name}] 类型不符 声明={mm['declared']} 推断={mm['inferred']}",
                                    "semantic", "HIGH"))
    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "grade": _grade(checks), "path": path, "checks": checks}


def validate_report(path: str) -> dict:
    checks = []
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL", "path": path,
                "checks": [check(False, f"文件不存在 {path}", "existence", "CRITICAL")]}
    text = open(path, encoding="utf-8").read()
    checks.append(check("## 结论" in text or "# 结论" in text,
                        "含结论段（金字塔：先结论后证据）", "structure"))
    checks.append(check("QA 清单" in text, "含 QA 清单", "structure"))
    hits = [b for b in BANNED_WORDS if b in text]
    checks.append(check(not hits, f"禁用语: {hits or '无'}", "integrity",
                        "CRITICAL" if hits else "OK"))
    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "grade": _grade(checks), "path": path, "checks": checks}


def validate_semantic(path: str, data: str = None) -> dict:
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL",
                "checks": [check(False, f"文件不存在 {path}", "existence", "CRITICAL")]}
    r = s01_semantics._validate(c.load_json(path))
    out = {"ok": r["ok"], "grade": "PASS" if r["ok"] else "FAIL", **r}
    # T5 语义↔数据真联动：提供了数据就做防幻觉联动，任一 expr 落空即 FAIL
    if data and os.path.exists(data):
        link = s01_semantics._link(c.load_json(path), c.load_csv(data))
        out["link"] = link
        if not link["ok"]:
            out["ok"] = False
            out["grade"] = "FAIL"
    return out


def validate_chart_spec(path: str) -> dict:
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL",
                "checks": [check(False, f"文件不存在 {path}", "existence", "CRITICAL")]}
    r = s08_viz._validate_spec(c.load_json(path))
    return {"ok": r["ok"], "grade": "PASS" if r["ok"] else "FAIL", **r}


def validate_plan(path: str) -> dict:
    """分析计划门禁（对齐 report-agent harness/plan_validator + experience/plan_schema.json）。"""
    schema_path = os.path.join(_HERE, "experience", "plan_schema.json")
    schema = c.load_json(schema_path) if os.path.exists(schema_path) else {}
    checks = []
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL",
                "checks": [check(False, f"文件不存在 {path}", "existence", "CRITICAL")]}
    plan = c.load_json(path)
    for f in schema.get("required_fields", []):
        checks.append(check(bool(plan.get(f)), f"含必填字段 {f}", "structure",
                            "CRITICAL" if not plan.get(f) else "OK", field=f))
    step = plan.get("analytical_step", "")
    enum = schema.get("analytical_step_enum", [])
    if step and enum and step not in enum:
        checks.append(check(False, f"analytical_step 非法 {step!r} ∈ {enum}",
                            "structure", "CRITICAL", field="analytical_step"))
    for grp in ("query_spec", "expected_output", "acceptance_criteria", "stop_condition"):
        grp_keys = schema.get(f"{grp}_required", [])
        obj = plan.get(grp) or {}
        for k in grp_keys:
            checks.append(check(bool(obj.get(k)), f"{grp}.{k} 存在", "structure",
                                "HIGH" if not obj.get(k) else "OK", field=f"{grp}.{k}"))
    ok = all(x["ok"] for x in checks)
    return {"ok": ok, "grade": _grade(checks), "path": path, "checks": checks}


def verify_all(data: str, report: str, semantic: str = None) -> dict:
    parts = {
        "dataset": validate_dataset(data, semantic),
        "report": validate_report(report),
    }
    if semantic:
        parts["semantic"] = validate_semantic(semantic, data)
    ok = all(v["ok"] for v in parts.values())
    return {"ok": ok, "parts": parts,
            "verdict": "PASS" if ok else "FAIL"}


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.py", description="R06 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)

    d = sp.add_parser("dataset")
    d.add_argument("--input", required=True)
    d.add_argument("--semantic", default=None)

    r = sp.add_parser("report")
    r.add_argument("--input", required=True)

    sm = sp.add_parser("semantic")
    sm.add_argument("--input", required=True)
    sm.add_argument("--data", default=None, help="提供数据 CSV 时做语义↔数据联动")

    ch = sp.add_parser("chart")
    ch.add_argument("--input", required=True)

    pl = sp.add_parser("plan")
    pl.add_argument("--input", required=True)

    v = sp.add_parser("verify")
    v.add_argument("--data", required=True)
    v.add_argument("--report", required=True)
    v.add_argument("--semantic", default=None)

    args = p.parse_args(argv)
    if args.cmd == "dataset":
        out = validate_dataset(args.input, args.semantic)
    elif args.cmd == "report":
        out = validate_report(args.input)
    elif args.cmd == "semantic":
        out = validate_semantic(args.input, args.data)
    elif args.cmd == "chart":
        out = validate_chart_spec(args.input)
    elif args.cmd == "plan":
        out = validate_plan(args.input)
    else:
        out = verify_all(args.data, args.report, args.semantic)

    c.emit(out)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())