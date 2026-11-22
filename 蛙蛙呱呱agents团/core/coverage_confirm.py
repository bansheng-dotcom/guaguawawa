# -*- coding: utf-8 -*-
"""core.coverage_confirm —— 覆盖矩阵确认与交付审计。"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.coverage_plan import plan_hash


def confirm(plan: Dict[str, Any], by: str, note: str = "",
            edits: List[str] | None = None) -> Dict[str, Any]:
    return {
        "schema": "dsh.coverage_confirmation/v1",
        "plan_hash": plan_hash(plan),
        "confirmed_by": by,
        "confirmed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "note": note,
        "edits": edits or [],
    }


def matrix_markdown(frame: Dict[str, Any], plan: Dict[str, Any]) -> str:
    units = [u["id"] for u in frame.get("units") or []]
    names = {u["id"]: u.get("name", u["id"]) for u in frame.get("units") or []}
    dims = [d["id"] for d in frame.get("dimensions") or []]
    dnames = {d["id"]: d.get("name", d["id"]) for d in frame.get("dimensions") or []}
    cells = {(c["unit"], c["dimension"]): c for c in plan.get("cells") or []}
    head = "| 单元 | 深度 | " + " | ".join(dnames[d] for d in dims) + " |"
    sep = "|---|---|" + "---|" * len(dims)
    rows = []
    for u in units:
        vals = []
        for d in dims:
            c = cells.get((u, d), {})
            mark = {"verified": "有", "estimated": "估*", "missing": "缺"}.get(c.get("status"), "—")
            vals.append(mark)
        rows.append(f"| {names[u]} | {plan.get('depth', {}).get(u, '')} | " + " | ".join(vals) + " |")
    return "\n".join([head, sep, *rows])


def _pdf_pages(pdf_path: str | None) -> int | None:
    if not pdf_path or not Path(pdf_path).exists():
        return None
    try:
        import pymupdf
        return int(pymupdf.open(pdf_path).page_count)
    except Exception:  # noqa: BLE001
        return None


def audit_coverage(plan: Dict[str, Any], frame: Dict[str, Any],
                   html_path: str, min_pages: int = 21,
                   pdf_path: str | None = None) -> Dict[str, Any]:
    html = Path(html_path).read_text(encoding="utf-8", errors="replace")
    pages = _pdf_pages(pdf_path)
    if pages is None:
        pages = html.count('class="page') or html.count("flow-block")
    svgs = html.count("<svg")
    issues: List[str] = []
    if pages < min_pages:
        issues.append(f"页数 {pages} < {min_pages}")
    if svgs < 2:
        issues.append(f"图表/地图 {svgs} < 2")
    # 地图只在计划声明时才要求：没有地图项的报告别被这条误杀
    need_maps = len(frame.get("maps") or [])
    if need_maps:
        if "全国" not in html:
            issues.append("计划声明了地图，但未检测到全国地图页")
        if "区域" not in html and "地图" not in html:
            issues.append("计划声明了地图，但未检测到区域地图页")
    for u in plan.get("core_units") or []:
        if plan.get("depth", {}).get(u) != "deep":
            issues.append(f"核心单元 {u} 非深链")
    return {"ok": not issues, "pages": pages, "svgs": svgs,
            "source": "pdf" if pdf_path and Path(pdf_path).exists() else "dom",
            "issues": issues}
