# -*- coding: utf-8 -*-
"""R05 确定性验证器（harness）：materials / verdict / plan / runlog。

- materials：研究物料 BLOCKED 判定（required 物料缺一即 BLOCKED，ok=false）。
- verdict：研究产出结构门禁——verdict 枚举 PASS/FAIL/BLOCKED、findings 带 severity、
  PASS 必须有证据链；干净产出 PASS、脏产出必须正确 FAIL。
- plan：复用 experience/plan_schema.json（r06 分析计划契约口径）。
- runlog：读 ../workspace/runlog.jsonl 最近 n 条（经 agents/core/workspace.py）。
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from skills import _common as c                                    # noqa: E402


# --------------------------------------------------------------------------- #
# materials
# --------------------------------------------------------------------------- #
def _inventory_core(data: Dict[str, Any], base_dir: str) -> Dict[str, Any]:
    items = data.get("items") or []
    checks: List[Dict[str, Any]] = []
    missing_required: List[str] = []
    present = 0
    for i, it in enumerate(items):
        rel = str(it.get("path") or "")
        required = bool(it.get("required", False))
        if not rel:
            checks.append(c.ck(False, f"items[{i}] 缺 path", "materials:path", "CRITICAL"))
            continue
        full = rel if os.path.isabs(rel) else os.path.join(base_dir, rel)
        if not os.path.isfile(full):
            if required:
                missing_required.append(rel)
                checks.append(c.ck(False, f"必需物料缺失：{rel}", "materials:missing", "CRITICAL", **{"path": rel}))
            else:
                checks.append(c.ck(True, f"可选物料缺失（不阻断）：{rel}", "materials:optional", "INFO", **{"path": rel}))
            continue
        size = os.path.getsize(full)
        if size <= 0:
            if required:
                missing_required.append(rel)
                checks.append(c.ck(False, f"必需物料为空：{rel}", "materials:empty", "CRITICAL", **{"path": rel}))
            else:
                checks.append(c.ck(True, f"可选物料为空（不阻断）：{rel}", "materials:optional", "INFO", **{"path": rel}))
            continue
        present += 1
        checks.append(c.ck(True, f"物料就绪：{rel}（{size}B）", "materials:present", **{"path": rel, "size": size}))
    verdict = "BLOCKED" if missing_required else "COMPLETE"
    return {"checks": checks, "item_count": len(items), "present": present,
            "missing_required": missing_required,
            "missing_required_count": len(missing_required), "verdict": verdict}


def validate_materials(path: str) -> Dict[str, Any]:
    data = c.load_json(path)
    base_dir = os.path.dirname(os.path.abspath(path))
    res = _inventory_core(data, base_dir)
    checks = list(res.get("checks") or [])
    missing = list(res.get("missing_required") or [])
    blocked = res.get("verdict") == "BLOCKED"
    out = c.result(checks,
                   grade="BLOCKED" if blocked else "PASS",
                   item_count=res.get("item_count", 0),
                   missing_required=res.get("missing_required", []),
                   missing_required_count=res.get("missing_required_count", 0),
                   verdict=res.get("verdict"),
                   next="研究材料齐备" if not blocked else "BLOCKED：补齐必需物料再进流程",
                   )
    out["ok"] = out["ok"] and not blocked
    return out


# --------------------------------------------------------------------------- #
# verdict：研究产出结构门禁
# --------------------------------------------------------------------------- #
def _has_evidence_chain(result: Dict[str, Any]) -> bool:
    evidence_keys = set(c.load_thresholds()["review"]["evidence_keys"])

    def walk(node: Any) -> bool:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in evidence_keys and _truthy(v):
                    return True
                if walk(v):
                    return True
        elif isinstance(node, list):
            for v in node:
                if walk(v):
                    return True
        return False

    return walk(result)


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, (str, list, dict)):
        return len(v) > 0
    return bool(v)


def validate_verdict(path: str) -> Dict[str, Any]:
    data = c.load_json(path)
    th = c.load_thresholds()["review"]
    verdict_enum = list(th["verdict_enum"])
    checks: List[Dict[str, Any]] = []
    verdict = data.get("verdict")
    findings = data.get("findings")

    if verdict not in verdict_enum:
        checks.append(c.ck(False, f"verdict={verdict!r} 不在枚举 {verdict_enum}",
                           "harness:verdict", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"verdict={verdict}", "harness:verdict"))
    if findings is None:
        checks.append(c.ck(False, "缺 findings 字段（研究产出必须带 findings 数组）",
                           "harness:findings", "CRITICAL"))
    else:
        if not isinstance(findings, list):
            checks.append(c.ck(False, f"findings 应为 array，实际 {type(findings).__name__}",
                               "harness:findings", "CRITICAL"))
        else:
            bad = [i for i, f in enumerate(findings)
                   if not isinstance(f, dict) or not str(f.get("severity") or "").strip()]
            if bad:
                checks.append(c.ck(False, f"findings 中缺 severity 的条目序号：{bad}",
                                   "harness:findings", "CRITICAL"))
            else:
                checks.append(c.ck(True, f"findings={len(findings)} 条，severity 完整",
                                   "harness:findings", **{"finding_count": len(findings)}))
    if verdict == "PASS" and not _has_evidence_chain(data):
        checks.append(c.ck(False, "verdict=PASS 却没有证据链（evidence/sources/claims/… 任一非空）",
                           "harness:evidence_chain", "CRITICAL"))
    if verdict == "BLOCKED":
        reason = str(data.get("blocked_reason") or "").strip()
        has_finding = isinstance(findings, list) and len(findings) > 0
        if not reason and not has_finding:
            checks.append(c.ck(False, "verdict=BLOCKED 必须带 blocked_reason 或至少一条 finding",
                               "harness:blocked_reason", "CRITICAL"))
        else:
            checks.append(c.ck(True, "BLOCKED 有理由记录", "harness:blocked_reason"))
    ok = all(ch.get("ok") for ch in checks)
    out = c.result(checks,
                    grade="PASS" if ok else "FAIL",
                    verdict=verdict,
                    finding_count=len(findings) if isinstance(findings, list) else None,
                    has_evidence_chain=_has_evidence_chain(data),
                    next="研究产出结构合规" if ok else "研究产出结构不合规：修 result 再验",
                    )
    out["ok"] = ok
    return out


# --------------------------------------------------------------------------- #
# plan：复用 plan_schema.json
# --------------------------------------------------------------------------- #
def validate_plan(path: str) -> Dict[str, Any]:
    with open(os.path.join(_HERE, "experience", "plan_schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    data = c.load_json(path)
    checks: List[Dict[str, Any]] = []
    for k in schema["required_fields"]:
        if k not in data:
            checks.append(c.ck(False, f"计划缺必填字段：{k}", f"plan:{k}", "CRITICAL"))
    step = data.get("analytical_step")
    if step not in schema["analytical_step_enum"]:
        checks.append(c.ck(False,
                           f"analytical_step={step!r} 不在枚举 {schema['analytical_step_enum']}",
                           "plan:analytical_step", "CRITICAL"))
    for key, field in (("query_spec", "query_spec_required"),
                       ("expected_output", "expected_output_required"),
                       ("acceptance_criteria", "acceptance_criteria_required"),
                       ("stop_condition", "stop_condition_required")):
        node = data.get(key)
        if isinstance(node, dict):
            missing = [f for f in schema[field] if f not in node]
            if missing:
                checks.append(c.ck(False, f"{key} 缺子字段：{missing}",
                                   f"plan:{key}", "CRITICAL"))
            else:
                checks.append(c.ck(True, f"{key} 子字段齐备", f"plan:{key}"))
    ok = all(ch.get("ok") for ch in checks)
    out = c.result(checks,
                   grade="PASS" if ok else "FAIL",
                   next="研究计划合规，可执行" if ok else "计划不合规：补齐字段再执行",
                   )
    out["ok"] = ok
    return out


# --------------------------------------------------------------------------- #
# runlog：读 ../workspace/runlog.jsonl
# --------------------------------------------------------------------------- #
def validate_runlog(n: int = 5) -> Dict[str, Any]:
    from core import workspace as ws_mod
    w = ws_mod.Workspace(os.path.join(_ROOT, "workspace"))
    rows = w.runlog(int(n))
    checks = [c.ck(True, f"读取最近 {len(rows)} 条 runlog", "runlog",
                   **{"rows": len(rows)})]
    out = c.result(checks,
                   rows=rows,
                   count=len(rows),
                   grade="PASS",
                   next="runlog 正常",
                   )
    out["ok"] = True
    return out


# --------------------------------------------------------------------------- #
# CLI：python harness.py <materials|verdict|plan|runlog> ...
# --------------------------------------------------------------------------- #
def run_validator(cmd: str, path: str) -> Dict[str, Any]:
    if cmd == "materials":
        return validate_materials(path)
    if cmd == "verdict":
        return validate_verdict(path)
    if cmd == "plan":
        return validate_plan(path)
    raise SystemExit(f"未知验证器：{cmd}")


def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R05 确定性验证器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    mp = sub.add_parser("materials", help="研究物料门禁（BLOCKED 判定）")
    mp.add_argument("--input", required=True)
    vp = sub.add_parser("verdict", help="研究产出结构门禁")
    vp.add_argument("--input", required=True)
    pp = sub.add_parser("plan", help="研究计划门禁（plan_schema）")
    pp.add_argument("--input", required=True)
    rp = sub.add_parser("runlog", help="读取最近 n 条 runlog")
    rp.add_argument("--n", type=int, default=5)
    args = ap.parse_args()
    if args.cmd == "runlog":
        out = validate_runlog(args.n)
    else:
        out = run_validator(args.cmd, args.input)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
