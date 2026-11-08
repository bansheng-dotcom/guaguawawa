# -*- coding: utf-8 -*-
"""S01 产品切片与 MVP —— 能力域 1。

整合自 makerskills（产品切片 + MVP 设计）。把「一颗想验证的假设」切到能
最快上线的可测形态：artifact_type 必须在 7 类可交付形态内、slices 每个都有
可验证假设与成功判据、MVP 五 gate 齐全且实验可测。

动作：
  slice  校验产品切片（artifact_type 白名单 + slices ≥1）
  mvp    校验 MVP 设计（五 gate + 假设风险类型 + 实验 method/metric + 成败判据）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "slice"
DESC = "产品切片与MVP：slice/mvp"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _nonempty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (dict, list)):
        return len(v) > 0
    return True


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    s = act.add_parser("slice", help="校验产品切片（形态白名单 + slices）")
    s.add_argument("--input", required=True)
    m = act.add_parser("mvp", help="校验 MVP 设计（五 gate + 实验可测）")
    m.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "slice":
        return _validate_slice(data)
    if args.action == "mvp":
        return _validate_mvp(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_slice(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    artifact_types = th["slice"]["artifact_types"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    at = str(data.get("artifact_type", "")).strip().lower()
    ok_at = at in artifact_types
    checks.append(_ck(ok_at,
                      f"artifact_type ∈ {artifact_types}"
                      if ok_at else f"artifact_type 非法/缺失: {at!r}",
                      "slice.artifact_type"))

    slices = data.get("slices")
    ok_slices = isinstance(slices, list) and len(slices) >= 1
    checks.append(_ck(ok_slices,
                      f"slices ≥1（实际 {len(slices) if isinstance(slices, list) else 0}）",
                      "slice.count"))
    slice_ok = ok_slices
    if isinstance(slices, list):
        for i, s in enumerate(slices):
            if not isinstance(s, dict):
                checks.append(_ck(False, f"slice[{i}] 非对象", "slice.type"))
                slice_ok = False
                continue
            for f in ("name", "testable_hypothesis", "success_criterion"):
                if not _nonempty(s.get(f)):
                    checks.append(_ck(False, f"slice[{i}] 缺 {f}", f"slice.{f}"))
                    slice_ok = False

    ok = ok_at and slice_ok
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    artifact_type=at,
                    slice_count=len(slices) if isinstance(slices, list) else 0)


# --------------------------------------------------------------------------- #
def _validate_mvp(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    gates = th["mvp"]["gates"]
    risk_types = th["mvp"]["risk_types"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    ok = True
    passed = 0
    for g in gates:
        if _nonempty(data.get(g)):
            passed += 1
            checks.append(_ck(True, f"gate {g} 非空", f"mvp.{g}"))
        else:
            checks.append(_ck(False, f"gate {g} 缺失或为空", f"mvp.{g}"))
            ok = False

    assumption = data.get("assumption")
    if isinstance(assumption, dict):
        rt = str(assumption.get("risk_type", "")).strip().lower()
        if rt in risk_types:
            checks.append(_ck(True, f"assumption.risk_type={rt}", "mvp.risk_type"))
        else:
            checks.append(_ck(False, f"assumption.risk_type 非法/缺失: {rt!r}",
                              "mvp.risk_type"))
            ok = False
    else:
        checks.append(_ck(False, "assumption 非对象或缺失", "mvp.risk_type"))
        ok = False

    experiment = data.get("experiment")
    if isinstance(experiment, list) and len(experiment) >= 1:
        for i, e in enumerate(experiment):
            if not isinstance(e, dict):
                checks.append(_ck(False, f"experiment[{i}] 非对象", "mvp.experiment"))
                ok = False
                continue
            for f in ("method", "metric"):
                if not _nonempty(e.get(f)):
                    checks.append(_ck(False, f"experiment[{i}] 缺 {f}",
                                      f"mvp.experiment.{f}"))
                    ok = False
    else:
        checks.append(_ck(False, "experiment ≥1 项（含 method+metric）",
                          "mvp.experiment"))
        ok = False

    criteria = data.get("criteria")
    if isinstance(criteria, dict):
        for f in ("success", "fail"):
            if _nonempty(criteria.get(f)):
                checks.append(_ck(True, f"criteria.{f} 非空", "mvp.criteria"))
            else:
                checks.append(_ck(False, f"criteria.{f} 缺失", "mvp.criteria"))
                ok = False
    else:
        checks.append(_ck(False, "criteria 非对象或缺失", "mvp.criteria"))
        ok = False

    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    passed_gates=passed)