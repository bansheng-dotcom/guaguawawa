# -*- coding: utf-8 -*-
"""core.r04_audit —— R04 五项全审：覆盖 / 数据 / 图表 / 版式硬，文笔软。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from core import coverage_confirm


def _read(p: str) -> str:
    return Path(p).read_text(encoding="utf-8", errors="replace")


def data_audit(sources: Dict[str, Any], plan: Dict[str, Any], html: str) -> Dict[str, Any]:
    srcs = sources.get("sources") or []
    n = len(srcs)
    url_ok = sum(1 for s in srcs if str(s.get("url") or "").strip())
    quote_ok = sum(1 for s in srcs if str(s.get("quote") or "").strip())
    by = {(c.get("unit"), c.get("dimension")): c for c in (plan.get("cells") or [])}
    core = plan.get("core_units") or []
    no_source = [f"{u}" for u in core if not any(
        by.get((u, d), {}).get("sources") for d in {k[1] for k in by if k[0] == u})]
    estimated = sum(1 for c in (plan.get("cells") or []) if c.get("status") == "estimated")
    mark = html.count("*")
    issues: List[str] = []
    if n < 50:
        issues.append(f"来源 {n} < 50")
    if url_ok / max(n, 1) < 0.9:
        issues.append(f"URL 覆盖 {url_ok}/{n} < 90%")
    if quote_ok / max(n, 1) < 0.9:
        issues.append(f"quote 覆盖 {quote_ok}/{n} < 90%")
    if no_source:
        issues.append(f"核心单元无来源: {no_source}")
    if estimated and mark < estimated:
        issues.append(f"估算单元格 {estimated}，正文 * 标记 {mark} 不足")
    return {"layer": "data", "ok": not issues,
            "detail": {"sources": n, "url": url_ok, "quote": quote_ok,
                       "estimated_cells": estimated, "star_marks": mark, "issues": issues}}


def _pdf_pages(pdf_path: str | None) -> int | None:
    """PDF 实际页数：优先 pymupdf/pypdf，最后退回字节扫描。

    2026-11-20：CI 的 gate-unify 在没装 pymupdf 的环境里永远拿不到页数，
    只能退回 DOM 而被判失败。这里补一条只用标准库的兜底（Chrome 导出的
    PDF 里 `/Type /Page` 是明文对象时可用；读不出返回 None，不编数字）。
    """
    if not pdf_path or not Path(pdf_path).exists():
        return None
    for mod in ("pymupdf", "fitz", "pypdf", "PyPDF2"):
        try:
            m = __import__(mod)
        except Exception:  # noqa: BLE001
            continue
        try:
            if hasattr(m, "open"):
                return int(m.open(pdf_path).page_count)
            reader = m.PdfReader(pdf_path)
            return int(len(reader.pages))
        except Exception:  # noqa: BLE001
            continue
    try:
        raw = Path(pdf_path).read_bytes()
        n = len(re.findall(rb"/Type\s*/Page[^s]", raw))
        return n or None
    except Exception:  # noqa: BLE001
        return None


def chart_audit(html: str, plan: Dict[str, Any] | None = None) -> Dict[str, Any]:
    svgs = html.count("<svg")
    srcs = html.count('class="ex-src"')
    need_maps = len((plan or {}).get("maps") or [])
    maps = sum(1 for k in ("全国", "区域", "地图") if k in html)
    issues = []
    if svgs < 3:
        issues.append(f"svg {svgs} < 3")
    if srcs < max(1, svgs - 2):
        issues.append(f"图下来源 {srcs} 少于图数 {svgs}")
    # 地图是「计划里声明了才要求」：没有地图项的报告不该被这条判死
    if need_maps and maps < min(2, need_maps):
        issues.append("计划声明了地图，但正文没有全国/区域地图页")
    from core.data_shape import fits
    bad = [f"{c.get('id', '?')}:{c.get('chart')}≠{c.get('shape')}"
           for c in ((plan or {}).get("charts") or [])
           if not fits(c.get("chart"), c.get("shape"))]
    if bad:
        issues.append("图型不适配 shape: " + ", ".join(bad))
    return {"layer": "charts", "ok": not issues,
            "detail": {"svg": svgs, "source_lines": srcs, "map_keywords": maps,
                       "maps_required": need_maps, "issues": issues}}


def layout_audit(html: str, min_pages: int = 21,
                 pdf_path: str | None = None) -> Dict[str, Any]:
    # 页数以 PDF 实际页数为准；没有 PDF 时退回 DOM（页式数 page，flow 数 block）
    pdf_pages = _pdf_pages(pdf_path)
    if pdf_pages is not None:
        pages = pdf_pages
    else:
        pages = html.count('class="page') or html.count("flow-block")
    footers = html.count('class="pn"')
    has_page_css = "@page" in html
    is_flow = 'class="page' not in html and "flow-block" in html
    issues = []
    if pages < min_pages:
        issues.append(f"页数 {pages} < {min_pages}")
    # flow 的页码由导出后盖，HTML 里没有 .pn 是设计如此；页式才查
    if not is_flow and pdf_pages is None and footers < pages - 2:
        issues.append(f"页码 {footers} 少于页数 {pages}")
    if not has_page_css:
        issues.append("缺 @page A4 规则")
    return {"layer": "layout", "ok": not issues,
            "detail": {"pages": pages, "source": "pdf" if pdf_pages is not None else "dom",
                       "footers": footers, "a4": has_page_css,
                       "flow": is_flow, "issues": issues}}


def prose_audit(html: str) -> Dict[str, Any]:
    from core import prose_style
    res = prose_style.audit_html(html)
    return {"layer": "prose", "ok": bool(res.get("ok")), "hard": False,
            "detail": {k: res.get(k) for k in ("sections", "avg_chars", "score",
                                               "hard_fail", "markers_total",
                                               "contrast_total")}}


def audit(frame: Dict[str, Any], plan: Dict[str, Any],
          sources: Dict[str, Any], html_path: str, min_pages: int = 21,
          prose_hard: bool = False, pdf_path: str | None = None) -> Dict[str, Any]:
    html = _read(html_path)
    layers = [
        {"layer": "coverage", **coverage_confirm.audit_coverage(
            plan, frame, html_path, min_pages, pdf_path)},
        data_audit(sources, plan, html),
        chart_audit(html, plan),
        layout_audit(html, min_pages, pdf_path),
        prose_audit(html),
    ]
    hard = ["coverage", "data", "charts", "layout"]
    if prose_hard:
        hard.append("prose")
    failed = [l["layer"] for l in layers if l["layer"] in hard and not l["ok"]]
    return {"schema": "dsh.r04_audit/v1", "ok": not failed,
            "verdict": "PASS" if not failed else "BLOCK",
            "failed": failed, "layers": layers}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="r04_audit")
    ap.add_argument("--frame", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--sources", required=True)
    ap.add_argument("--html", required=True)
    ap.add_argument("--min-pages", type=int, default=21)
    ap.add_argument("--pdf", default=None, help="PDF 路径：页数以实际页数为准")
    ap.add_argument("--prose-hard", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    r = audit(json.loads(Path(a.frame).read_text(encoding="utf-8")),
              json.loads(Path(a.plan).read_text(encoding="utf-8")),
              json.loads(Path(a.sources).read_text(encoding="utf-8")),
              a.html, a.min_pages, a.prose_hard, a.pdf)
    out = Path(a.json) if a.json else Path(a.html).parent / "r04_gate.json"
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
