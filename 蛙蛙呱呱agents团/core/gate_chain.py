# -*- coding: utf-8 -*-
"""core.gate_chain —— 一条门禁链（SOP S6）。

四层门禁串成一个入口：
    L1 拆卡（S1–S12 发卡前 + G1–G25 收卡后）
    L2 语义一致性（resolved model vs contract）
    L3 图拟合（每节 chart_validation）
    L4 呈现（flow 门禁 F1–F11，有 html 才跑）

用法：
    from core import gate_chain
    res = gate_chain.run(project_dir, html_path)
    # res = {"ok": bool, "layers": {"L1": {...}, "L2": {...}, ...}, "failures": [...]}
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def _load(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}


def _find_out(project: Path) -> Path:
    """兼容「报告在项目根」和「报告在 out/ 或 report/」三种布局。"""
    for cand in (project, project / "out", project / "report", project / "out" / "report2"):
        if (cand / "contract.json").is_file():
            return cand
    return project


def _l1(project: Path) -> Dict[str, Any]:
    plan = project / "plan"
    pre = _load(plan / "pre_issue_gates.json")
    post = _load(plan / "post_gates.json")
    detail = {"pre": "ok" if pre else "missing",
              "post": "ok" if post else "missing"}
    if pre:
        detail["pre_passed"] = "%s/%s" % (pre.get("passed"), pre.get("total"))
    if post:
        detail["post_passed"] = "%s/%s" % (post.get("passed"), post.get("total"))
        detail["post_fail"] = [c.get("id") for c in (post.get("checks") or [])
                               if not c.get("ok")]
    # 没跑过收卡门禁的老项目：只按发卡门禁判，但 detail 里明确标 missing
    ok = bool(pre.get("ok", True)) and bool(post.get("ok", True)) if post else bool(pre)
    return {"ok": ok, "detail": detail}


def _l2(project: Path, out: Path) -> Dict[str, Any]:
    """语义一致性：影子 resolved model 的每个内容节，都要能在 contract 里找到。

    不用"数节数"（渲染器会补决策纸/附录/口径节，数必然不等），改按标题包含匹配：
    只要 resolved 的每一节标题都出现在 contract 的某节标题里，就说明语义没丢。
    """
    resolved = _load(out / "ir_shadow.json")
    contract = _load(out / "contract.json")
    rs = resolved.get("sections") or []
    # contract 里短标题在 title、全称在 full_title，两个都要比
    ctitles: List[str] = []
    for s in (contract.get("sections") or []):
        if s.get("title"):
            ctitles.append(str(s["title"]))
        if s.get("full_title"):
            ctitles.append(str(s["full_title"]))
    if not rs:
        return {"ok": False,
                "detail": {"why": "没有 ir_shadow.json（影子未跑）"}}
    unmatched = []
    for s in rs:
        t = str(s.get("title") or "")[:16]
        if t and not any(t in c for c in ctitles):
            unmatched.append(t)
    detail = {"resolved_sections": len(rs), "contract_sections": len(ctitles),
              "unmatched": unmatched[:6]}
    return {"ok": not unmatched, "detail": detail}


def _l3(out: Path) -> Dict[str, Any]:
    """图拟合：contract 里每节 chart_validation.ok 的比例。"""
    contract = _load(out / "contract.json")
    secs = [s for s in (contract.get("sections") or []) if s.get("chart")]
    vals = [(s.get("chart") or {}).get("chart_validation") or {} for s in secs]
    checked = [v for v in vals if v]
    bad = [{"index": s.get("index"), "reason": (s.get("chart") or {})
            .get("chart_validation", {}).get("reason")}
           for s, v in zip(secs, vals) if v and not v.get("ok")]
    detail = {"sections_with_chart": len(secs), "checked": len(checked),
              "bad": bad[:6]}
    return {"ok": not bad, "detail": detail}


def _l4(html: Optional[str]) -> Dict[str, Any]:
    if not html or not os.path.exists(html):
        return {"ok": True, "detail": {"skipped": "无 html"}}
    try:
        import sys
        root = Path(__file__).resolve().parent.parent
        scripts = root / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from check_report_flow import check_html  # noqa: PLC0415
        r = check_html(html)
        return {"ok": bool(r.get("ok")), "detail": {"violations": r.get("violations") or [],
                                                    "stats": r.get("stats") or {}}}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": {"why": str(exc)}}


def run(project_dir: str, html_path: Optional[str] = None,
        out_dir: Optional[str] = None) -> Dict[str, Any]:
    """project_dir 用来找 plan/（L1）；out_dir 用来找 contract/影子（L2/L3）。

    不传 out_dir 时按「报告在项目根 / out / report / out/report2」自动找。
    """
    project = Path(project_dir)
    out = Path(out_dir) if out_dir else _find_out(project)
    layers = {
        "L1": _l1(project),
        "L2": _l2(project, out),
        "L3": _l3(out),
        "L4": _l4(html_path),
    }
    failures: List[str] = [k for k, v in layers.items() if not v.get("ok")]
    return {"ok": not failures, "layers": layers, "failures": failures,
            "out_dir": str(out)}
