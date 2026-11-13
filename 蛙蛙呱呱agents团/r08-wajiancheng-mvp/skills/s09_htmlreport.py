# -*- coding: utf-8 -*-
"""S09 单文件 HTML 报告（走内核，单一渲染器）。

  plan  结构门禁：由 core/report_kernel/structure.py 判定六条（S1–S6）
  html  渲染：报告 JSON → 内核 contract → core/report_renderer 确定性渲染

变更（2026-11-12）：本模块不再自带渲染器与规则表。
  - 六条结构门禁下沉到 `report_kernel.structure.guard`（与内核同一把尺子）；
  - 渲染统一走 `core/report_renderer`（REPORT-STANDARD §四：不许手写一次性 HTML）；
  - 报告 JSON 可带 `dataset` / `claims`，带上即产出保留率/溯源率/弃置率与记录层，
    不带则如实标 N/A，不估算。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from . import _common as c

NAME = "htmlreport"
DESC = "单文件 HTML 报告：plan/html（内核渲染）"


def _ck(ok: bool, msg: str, dim: str = "", sev: str = "") -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev or ("OK" if ok else "BLOCKER")}


def _structure():
    """延迟导入内核：技能层只在执行时需要内核，导入失败给出可执行的处置。"""
    try:
        from core.report_kernel import structure  # noqa: F401
        return structure
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "内核不可用（core/report_kernel/structure.py）：六条结构门禁只有一份实现，"
            "不再内置副本。请在角色根目录（含 core/）运行，或先修复内核导入。"
            f" 原始错误：{type(exc).__name__}: {exc}") from exc


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    pl = act.add_parser("plan", help="校验报告结构")
    pl.add_argument("--input", required=True)
    ht = act.add_parser("html", help="渲染单文件 HTML")
    ht.add_argument("--input", required=True)
    ht.add_argument("--out", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    try:
        if args.action == "plan":
            return _validate(data)
        return _render(data, args.out)
    except RuntimeError as exc:
        return c.result([_ck(False, str(exc), "kernel")], ok=False, verdict="FAIL",
                        next="在含 core/ 的角色根目录运行 python agent.py htmlreport ...")


def _validate(data: Any) -> Dict[str, Any]:
    gate = _structure().guard(data)
    chapters = data.get("chapters") if isinstance(data, dict) else None
    sources = data.get("sources") if isinstance(data, dict) else None
    ok = bool(gate["ok"])
    return c.result(gate["checks"], ok=ok, verdict="PASS" if ok else "FAIL",
                    chapter_count=len(chapters or []), source_count=len(sources or []),
                    rules_violated=gate["violations"],
                    next="结构通过，可渲染 html" if ok else "按 checks 补齐（S1–S6）")


def _render(data: Any, out_path: str) -> Dict[str, Any]:
    structure = _structure()
    gate = _validate(data)
    if not gate.get("ok"):
        gate["next"] = "结构未过门禁，先修 plan"
        return gate

    from core import report_renderer

    contract = structure.to_contract(data)
    verrs: List[str] = report_renderer.validate_contract(contract)
    layout = structure.layout_errors(contract, require_appendix=bool(data.get("dataset")))
    if verrs or layout:
        return c.result(
            list(gate["checks"]) + [_ck(False, e, "contract") for e in verrs]
            + [_ck(False, e, "layout") for e in layout],
            ok=False, verdict="FAIL", next="contract/版式不合规，先修")

    doc = report_renderer.render(contract)
    d = os.path.dirname(os.path.abspath(out_path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)

    fid = contract.get("fidelity") or {}
    checks = list(gate["checks"]) + [
        _ck(doc.startswith("<!doctype html>"), "单文件 HTML", "report.html"),
        _ck("http" not in doc, "无外部资源引用", "report.offline"),
        _ck("@media print" in doc, "含打印样式", "report.print"),
    ] + [_ck(True, "版式四规则通过（R1–R4）", "report.layout")]
    extra: Dict[str, Any] = {}
    if data.get("dataset"):
        extra = {"obs_total": len(data["dataset"]), "retention": fid.get("retention"),
                 "trace": fid.get("trace"), "discard": fid.get("discard")}
    return c.result(checks, ok=True, verdict="PASS", out=out_path,
                    size_bytes=os.path.getsize(out_path),
                    chapter_count=len(data.get("chapters") or []),
                    source_count=len(data.get("sources") or []),
                    engine="core/report_kernel.structure + report_renderer",
                    next="可直接交付或打印为 PDF", **extra)
