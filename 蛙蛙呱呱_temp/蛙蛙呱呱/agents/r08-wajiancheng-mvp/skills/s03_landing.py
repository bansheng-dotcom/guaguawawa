# -*- coding: utf-8 -*-
"""S03 落地页与 H5 —— 能力域 3。

整合自 makerskills（landing-page / form）。把 PRD 转成单文件可交付的落地页：
目标/标题/副标题/佐证点/表单/按钮/FAQ/提交后动作八要素俱全，佐证≥3 条，
并锁定 5 条技术约束（单文件/禁 JS 库/表单可交付/移动优先/单一主色按钮）。

动作：
  landing  校验落地页（八要素 + 佐证≥3 + 技术约束全 True + 最大异议）
  form     校验表单（提交端点 + fields 各带 name/label）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "landing"
DESC = "落地页与H5：landing/form"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    l = act.add_parser("landing", help="校验落地页（八要素 + 技术约束）")
    l.add_argument("--input", required=True)
    f = act.add_parser("form", help="校验表单（端点 + 字段）")
    f.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "landing":
        return _validate_landing(data)
    if args.action == "form":
        return _validate_form(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_landing(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    keys = th["landing"]["keys"]
    proof_min = th["landing"]["proof_min"]
    tech_constraints = th["landing"]["tech_constraints"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    ok = True
    for k in keys:
        v = data.get(k)
        if k == "proof_points":
            nonempty = isinstance(v, list) and len(v) >= 1
        else:
            nonempty = bool(str(v or "").strip())
        if nonempty:
            checks.append(_ck(True, f"{k} 非空", f"landing.{k}"))
        else:
            checks.append(_ck(False, f"{k} 缺失或为空", f"landing.{k}"))
            ok = False

    proof = data.get("proof_points")
    proof_count = len(proof) if isinstance(proof, list) else 0
    ok_proof = proof_count >= proof_min
    checks.append(_ck(ok_proof,
                      f"proof_points ≥{proof_min}（实际 {proof_count}）",
                      "landing.proof"))
    if not ok_proof:
        ok = False

    for tc in tech_constraints:
        v = data.get(tc)
        ok_tc = v is True
        if ok_tc:
            checks.append(_ck(True, f"技术约束 {tc}=true", f"landing.{tc}"))
        else:
            checks.append(_ck(False, f"技术约束 {tc} 缺失或非 True",
                              f"landing.{tc}"))
            ok = False

    max_obj = str(data.get("max_objection", "")).strip()
    ok_mo = bool(max_obj)
    checks.append(_ck(ok_mo,
                      "max_objection 非空" if ok_mo else "max_objection 缺失",
                      "landing.max_objection"))
    if not ok_mo:
        ok = False

    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    proof_count=proof_count)


# --------------------------------------------------------------------------- #
def _validate_form(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    endpoint = str(data.get("formspree_endpoint", "")).strip()
    mailto = str(data.get("mailto", "")).strip()
    ok_target = bool(endpoint or mailto)
    checks.append(_ck(ok_target,
                      "formspree_endpoint 或 mailto 至少其一"
                      if ok_target else "缺提交端点（formspree_endpoint/mailto）",
                      "form.target"))

    fields = data.get("fields")
    ok_fields = isinstance(fields, list) and len(fields) >= 1
    checks.append(_ck(ok_fields,
                      f"fields ≥1（实际 {len(fields) if isinstance(fields, list) else 0}）",
                      "form.fields"))
    field_ok = ok_fields
    if isinstance(fields, list):
        for i, f in enumerate(fields):
            if not isinstance(f, dict):
                checks.append(_ck(False, f"field[{i}] 非对象", "form.field"))
                field_ok = False
                continue
            for k in ("name", "label"):
                if not str(f.get(k, "")).strip():
                    checks.append(_ck(False, f"field[{i}] 缺 {k}",
                                      f"form.field.{k}"))
                    field_ok = False

    ok = ok_target and field_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    field_count=len(fields) if isinstance(fields, list) else 0)