# -*- coding: utf-8 -*-
"""core.flow_report —— 项目化 flow 报告构建器（facts + charts + 可选 prose_specs）。

一个项目目录三件套：
    facts.py        META / KPI / SUMMARY / SECTIONS / ACTIONS / SOURCES / FILES
    charts.py       每个 section 的 chart 字段对应一个返回 SVG 的函数
    prose_specs.py  可选：SECTIONS 每节的十段证据，走 core.report_prose_gen 生成 1,000 字正文

用法：
    from core import flow_report
    flow_report.build("workspace/liquor_flow_2026-11-19", "out", pdf=True)

CLI：
    python guagua.py report flow --project <项目目录> --out <输出目录> [--paper] [--pdf]
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent


def _load(path: Path, name: str):
    if not path.exists():
        raise FileNotFoundError(f"缺 {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _stamp(pdf_path: str) -> None:
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        n = doc.page_count
        for i in range(1, n):
            doc[i].insert_text((520, 812), f"{i + 1:02d} / {n:02d}", fontsize=8,
                               fontname="helv", color=(0.45, 0.48, 0.51))
        doc.saveIncr()
    except Exception:  # noqa: BLE001  页码只是装饰
        pass


def _assemble(facts: Any, charts: Any, meta: Dict[str, Any]) -> Dict[str, Any]:
    from core.report_theme import kit
    sections = facts.SECTIONS
    total = 3 + len(sections) + 5
    pages: Dict[str, int] = {}
    p = 4
    figures = tables = 0
    engines = {"pro": 0, "legacy": 0, "table": 0}
    for s in sections:
        if isinstance(s.get("chart"), dict) and not s.get("chart_spec"):
            s["chart_spec"] = s["chart"]
        if s.get("chart_spec"):
            s["chart"] = str((s["chart_spec"] or {}).get("type") or "spec")
            engines["pro"] += 1
        elif s.get("chart"):
            engines["legacy"] += 1
        else:
            engines["table"] += 1
        if s.get("chart"):
            figures += 1
            s["_fig_no"] = f"图 {figures}"
        else:
            tables += 1
            s["_fig_no"] = f"表 {tables}"
        pages[s["id"]] = p
        p += 1
    pages["actions"] = p
    pages["appendix"] = p + 1
    pages["appendix2"] = p + 2
    pages["appendix3"] = p + 3
    pages["back"] = p + 4

    cover = kit.cover(meta, facts.KPI)
    summary = kit.summary_page(meta, facts.SUMMARY, meta["one_x"],
                               facts.ACTIONS[:3] and [
                                   (a[1], a[5]) for a in facts.ACTIONS[:3]],
                               2, total)
    toc_rows = [(s["no"], s["id"], s["kicker"], s["title"][:22], pages[s["id"]])
                for s in sections]
    toc_rows += [("A", "actions", "动作", "谁 / 何时 / 停止线", pages["actions"]),
                 ("B1", "appendix", "附录 A", "来源", pages["appendix"]),
                 ("B2", "appendix2", "附录 B", "来源（续）", pages["appendix2"]),
                 ("B3", "appendix3", "附录 C", "数据文件", pages["appendix3"])]
    toc = kit.toc_page(meta, toc_rows, 3, total)

    body = [cover, summary, toc]
    for s in sections:
        fn = None
        if s.get("chart_spec"):
            from core.report_theme.charts_pro import spec as spec_layer
            spec_layer.validate(s["chart_spec"])
            fn = (lambda sp: (lambda: spec_layer.render(sp)))(s["chart_spec"])
        elif s.get("chart"):
            fn = getattr(charts, s["chart"], None)
            if fn is None:
                raise AttributeError(f"charts.py 缺图表函数 {s['chart']}")
        body.append(kit.section_page(s, pages[s["id"]], total, s["_fig_no"], fn, meta))

    body.append(kit.action_page(
        "谁、何时、花多少、什么条件停", "没有停止线的动作，不是动作，是愿望。",
        facts.ACTIONS, meta.get("stop_rule") or "各节证伪条件成立即停。",
        pages["actions"], total, meta))
    src = list(facts.SOURCES)
    half = (len(src) + 1) // 2
    body.append(kit.appendix_page(
        "来源与数据文件（1/2）", f"{len(src)} 个来源；每条结论可回溯。",
        src[:half], [], pages["appendix"], total, meta))
    body.append(kit.appendix_page(
        "来源与数据文件（2/2）", "来源续；数字在证据底稿中可逐条回抓。",
        src[half:], [], pages["appendix2"], total, meta))
    body.append(kit.appendix_page(
        "数据文件", "事实、图与证据底稿。", [], facts.FILES,
        pages["appendix3"], total, meta))
    body.append(kit.back_page(meta))

    html = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<title>{meta["title"]}</title><style>{kit.CSS}</style></head><body>'
            + "".join(body) + "</body></html>")
    return {"html": html, "pages": total, "figures": figures,
            "tables": tables, "sections": len(sections), "engines": engines}


def build(project_dir: str, out_dir: str, pdf: bool = True,
          layout: str = "flow", use_specs: bool = True,
          author_first: bool = False,
          md: bool = True, prose_hard: bool = False,
          gate_hard: bool = False) -> Dict[str, Any]:
    proj = Path(project_dir)
    facts = _load(proj / "facts.py", "flow_facts")
    charts = _load(proj / "charts.py", "flow_charts") if (proj / "charts.py").exists() else None

    # 文笔：默认 spec 生成覆盖 body；author_first 只校验 11 字段，保留人工正文
    spec_issues: List[str] = []
    has_specs = (proj / "prose_specs.py").exists()
    prose_mode = "none"
    if author_first:
        prose_mode = "author-first"
        if not has_specs:
            spec_issues.append("author-first 需要 prose_specs.py 做 11 字段校验")
        else:
            from core import prose_spec
            specs = _load(proj / "prose_specs.py", "flow_specs").SPECS
            spec_issues = prose_spec.validate(specs, facts.SECTIONS)
    elif use_specs and has_specs:
        prose_mode = "specs"
        from core import prose_spec, report_prose_gen
        specs = _load(proj / "prose_specs.py", "flow_specs").SPECS
        spec_issues = prose_spec.validate(specs, facts.SECTIONS)
        bodies = report_prose_gen.generate(facts.SECTIONS, specs)
        for s in facts.SECTIONS:
            if s["id"] in bodies:
                s["body"] = bodies[s["id"]]

    meta = dict(facts.META)
    built = _assemble(facts, charts, meta)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if layout == "flow":
        from core.report_theme.flow import flowify
        html = flowify(built["html"], list(facts.SOURCES))
    else:
        html = built["html"]

    html_path = out / "report.html"
    html_path.write_text(html, encoding="utf-8")
    files: Dict[str, Any] = {"html": str(html_path), "pdf": None,
                             "pages_estimate": built["pages"],
                             "figures": built["figures"], "tables": built["tables"],
                             "sections": built["sections"],
                             "chart_engine": built.get("engines", {})}

    if md:
        lines = [f"# {meta['title']}", "", meta.get("standfirst", ""), ""]
        for s in facts.SECTIONS:
            lines += [f"## {s['no']}. {s['title']}", "", s.get("body", ""), "",
                      f"边界：{s.get('boundary', '')}", ""]
        (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
        files["md"] = str(out / "report.md")

    if pdf:
        from core.report_theme import kit
        pdf_path = out / "report.pdf"
        r = kit.to_pdf(html_path, pdf_path)
        if r.get("ok"):
            _stamp(str(pdf_path))
            files["pdf"] = str(pdf_path)
            files["pdf_status"] = "created"
        else:
            files["pdf_status"] = r.get("error") or "failed"

    from core import prose_style
    prose = prose_style.audit_html(html)
    files["prose"] = {k: prose.get(k) for k in
                      ("ok", "sections", "avg_chars", "score", "hard_fail")}
    files["prose_spec"] = {"ok": not spec_issues, "issues": spec_issues[:20]}
    files["prose_mode"] = prose_mode
    files["author_first"] = bool(author_first)
    ok = bool(prose.get("ok")) if prose_hard else True
    if prose_hard and spec_issues:
        ok = False

    # v3 的同一条门禁：有覆盖三件套就跑 r04 五项（页数读 PDF 实际页数）
    r04: Dict[str, Any] = {}
    cov = proj / "coverage"
    if (cov / "task_frame.json").exists() and (cov / "coverage_plan.json").exists():
        from core import r04_audit
        frame = json.loads((cov / "task_frame.json").read_text(encoding="utf-8"))
        plan = json.loads((cov / "coverage_plan.json").read_text(encoding="utf-8"))
        src_path = cov / "source_ledger.json"
        sources = (json.loads(src_path.read_text(encoding="utf-8"))
                   if src_path.exists() else {"sources": []})
        min_pages = int(plan.get("page_floor") or frame.get("page_floor") or 21)
        res = r04_audit.audit(frame, plan, sources, str(html_path),
                              min_pages, prose_hard,
                              files.get("pdf") or None)
        (cov / "r04_gate.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        r04 = {"ok": res.get("ok"), "verdict": res.get("verdict"),
               "failed": res.get("failed"),
               "layers": {l["layer"]: l.get("ok") for l in res.get("layers") or []}}
        files["r04"] = r04
        if gate_hard:
            ok = ok and bool(res.get("ok"))
    files["prose_hard"] = prose_hard
    files["gate_hard"] = gate_hard
    (out / "flow_manifest.json").write_text(
        json.dumps({"ok": ok, "files": files, "layout": layout,
                    "prose": files["prose"], "prose_spec": files["prose_spec"],
                    "prose_hard": prose_hard,
                    "gate_hard": gate_hard, "r04": r04},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": ok, "layout": layout, "files": files,
            "pages_estimate": built["pages"], "prose": files["prose"],
            "prose_spec": files["prose_spec"],
            "prose_hard": prose_hard, "gate_hard": gate_hard, "r04": r04}
