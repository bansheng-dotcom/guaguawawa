# -*- coding: utf-8 -*-
"""core/decision_report —— 决策优先的报告装配（report decide）。

与 `report build` 的区别只有一处，但顺序相反：

    build ：数据 → 方法 → findings → 问题（反推）→ 报告
    decide：决策契约（3–5 问）→ 方法 → findings → 逐问作答 → 报告

因此本模块能做旧产线做不到的三件事：
1. 答不了的问题必须显式列出（binding < 1 时 ok=false，不许用 1.0 掩盖）；
2. 每节标题对应一个决策问题，而不是一个方法名；
3. 图由「对照类型」选（decision.CHART_POLICY），并强制过 chart_spec 契约。

用法：
    python guagua.py report decide --intent "…" --dir <项目> --out <目录> \
        [--decision data/decision.json] [--min-binding 0.8]
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import (analysis_desk, analysis_methods, decision, methods,
                  report_assembly, report_flow)


def _json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build(intent: str, project_dir: str, out_dir: str,
          decision_path: Optional[str] = None, min_binding: float = 0.8,
          theme: str = "paper", pdf: bool = False,
          quote_mode: str = "off", audience: str = "业务负责人") -> Dict[str, Any]:
    desk = analysis_desk.scan(project_dir)
    prof = analysis_desk.profile(desk)
    views = analysis_methods.build_views(desk)
    os.makedirs(out_dir, exist_ok=True)
    tmpdir = os.path.join(out_dir, "_work")
    os.makedirs(tmpdir, exist_ok=True)
    ctx = analysis_methods.Ctx(
        desk=desk, views=views, skills=analysis_methods.Skills(),
        cite=analysis_methods.Cite(desk), profile=prof, tmpdir=tmpdir,
        ft=getattr(desk, "ft", None))
    ctx.frame = "decision"
    ctx.intent = intent

    plan = methods.plan(desk, views, prof, "analysis")
    mounted = [m["key"] for m in plan.get("mounted") or []]

    # 1) 决策契约：人给的文件优先；没有就从数据能力起草，并明确标记 auto
    src = decision_path or os.path.join(project_dir, "data", "decision.json")
    auto = not os.path.exists(src)
    if auto:
        ctr = decision.draft(intent, mounted, audience=audience)
    else:
        ctr = decision.load(src)
    v = decision.validate(ctr)
    if not v["ok"]:
        raise report_flow.FlowError("决策契约不成立：" + "；".join(v["errors"]))
    _json(os.path.join(out_dir, "decision.json"), ctr)

    # 2) 跑全量方法：方法之间通过 ctx.memo 有隐式依赖（如 breakeven 读 economics），
    #    只跑「声明需要的几个」会静默断链。声明只决定用哪些 finding，不决定跑哪些。
    plan_obj = plan
    findings, gaps = methods.run(plan_obj, ctx)

    # 3) 逐问作答；图由对照类型选，并过 chart_spec
    sections: List[Dict[str, Any]] = []
    picked: List[Any] = []
    chart_rows: List[Dict[str, Any]] = []
    unanswered: List[Dict[str, Any]] = []
    boundaries_all: List[str] = []
    label_of: Dict[str, int] = {}
    for i, q in enumerate(ctr["questions"], 1):
        f = findings.get(str(q.get("finding") or ""))
        if f is None:
            skipped = {m.get("key"): (m.get("missing") or [])
                       for m in (plan_obj.get("skipped") or [])}
            unanswered.append({"id": q["id"], "question": q["text"],
                               "finding": q["finding"],
                               "missing": skipped.get(q["finding"]) or []})
            continue
        sec = report_assembly._section_of(f)
        # 标题是判断（带数字），问题是「问什么」：渲染器会把 question 放在节首
        sec["title"] = f.title
        # 边界只留第一节一处（门禁要求），其余统一收到末节，避免正文与末节重复
        boundary = sec.pop("boundary", "")
        if boundary:
            if not sections:
                sec["boundary"] = boundary
            elif boundary not in boundaries_all:
                boundaries_all.append(str(boundary))
        # 每节以「所以」收口：读者要的是动作，不是又一段描述
        if f.so_what:
            refs = list(dict.fromkeys(sec.get("refs") or []))[:6]
            sec.setdefault("reading", []).append(
                {"text": f"所以：{f.so_what}", "refs": refs})
        # 只对方法真出的图做「对照选型」；没有图就明记缺口，不从表格凑数（凑出来的点不可回溯）
        base = sec.get("chart")
        chart = decision.choose_chart(base, q) if base else None
        if chart is not None:
            cc = decision.chart_contract_ok(chart)
            if not cc["ok"]:
                chart_rows.append({"section": i, "type": chart.get("type"),
                                   "ok": False, "errors": cc["errors"]})
                chart = None
            else:
                chart_rows.append({"section": i, "type": chart.get("type"),
                                   "ok": True, "policy": chart.get("policy")})
                sec["chart"] = chart
        else:
            chart_rows.append({"section": i, "type": "", "ok": False,
                               "errors": ["方法未产出图；不从表格凑数（凑出的点不可回溯）"]})
        sec["question"] = q["text"]
        sec["decision"] = q["decision"]
        sec["falsifier"] = sec.get("falsifier") or q["falsifier"]
        sections.append(sec)
        label_of[f.key] = len(sections)
        picked.append(f)

    if not sections:
        raise report_flow.FlowError(
            "没有一个决策问题能落到证据：" +
            "；".join(f"{u['id']} 缺 {','.join(u['missing']) or '数据'}"
                     for u in unanswered))

    # 4) 绑定：declared vs answered（与 findings 无关，先算清楚）
    binding = decision.bind(ctr, findings, plan_obj)

    # 5) 装配 draft
    first = sections[0]["title"]
    answered = binding["answered"]
    declared = binding["declared"]
    standfirst = (f"{answered}/{declared} 个决策问题有证据：{first}"
                  if answered < declared else f"{declared} 个决策问题全部有证据：{first}")
    title = ""
    meta_path = desk.root / "data" / "meta.json"
    if meta_path.exists():
        try:
            title = str(json.loads(meta_path.read_text(encoding="utf-8-sig"))
                        .get("title") or "")
        except (OSError, json.JSONDecodeError):
            title = ""
    title = title or f"{report_assembly._subject(desk.project)}决策分析"
    boundaries = [f"未答：{u['id']}「{u['question']}」缺 {','.join(u['missing']) or '可进报告的证据'}"
                  for u in unanswered]
    for b in boundaries_all:
        if b not in boundaries:
            boundaries.append(b)

    draft = {
        "profile": "decision",
        "schema": "dsh.decision.draft/v1",
        "intent": intent,
        "doc_type": "决策分析" if not auto else "数据探索（自动起草决策契约）",
        "title_lines": [title, f"{declared} 问 · {answered} 答 · "
                                f"图由对照选型（{len(chart_rows)} 个判定）"],
        "standfirst": standfirst,
        "metrics": report_assembly._metrics(picked, label_of),
        "summary": [s["title"] for s in sections[:4]],
        "sections": sections,
        "boundaries": boundaries[:8],
        "derived": desk.derived,
        "counts": report_assembly._counts(views, sections, list(findings.values()), desk),
        "decision": {"auto": auto, "min_binding": min_binding,
                     "binding": binding["binding"], "decision": ctr["decision"]},
    }
    pack_path = os.path.join(out_dir, "evidence_pack.json")
    _json(pack_path, desk.pack)
    draft_path = os.path.join(out_dir, "draft_sections.json")
    _json(draft_path, draft)

    res = report_flow.run(intent=intent, evidence=pack_path, draft=draft,
                          out_dir=out_dir, theme=theme, pdf=pdf,
                          quote_mode=quote_mode)

    # 6) 门禁：绑定 + 图契约 + 渲染（质量分只告警：该 rubric 是关键词型，
    #    会把「问题短、节数少」的决策稿判低，不能拿它当唯一放行依据）
    from core import report_quality
    html = (res.get("files") or {}).get("html") or ""
    qa = report_quality.audit(html) if html else {
        "ok": False, "score": 0, "checks": [], "sections": 0, "chars": 0,
        "numbers": 0, "density": 0}
    _json(os.path.join(out_dir, "quality.json"), qa)
    chart_ok = sum(1 for r in chart_rows if r["ok"])
    chart_ratio = chart_ok / len(chart_rows) if chart_rows else 0.0
    chart_gate = chart_ratio >= 0.8
    bind_ok = binding["binding"] >= min_binding
    ok = bool(res.get("ok")) and bind_ok and chart_gate

    man_path = os.path.join(out_dir, "manifest.json")
    man: Dict[str, Any] = {}
    if os.path.exists(man_path):
        man = json.loads(Path(man_path).read_text(encoding="utf-8-sig"))
        man.update({
            "generated_by": "core/decision_report.py",
            "decision": {
                "schema": decision.SCHEMA,
                "auto": auto,
                "decision": ctr["decision"],
                "audience": ctr.get("audience"),
                "questions": ctr["questions"],
                "binding": binding,
                "min_binding": min_binding,
            },
            "chart_audit": {
                "sections": len(sections),
                "with_chart": chart_ok,
                "ratio": round(chart_ratio, 3),
                "min_ratio": 0.8,
                "types": sorted({r["type"] for r in chart_rows if r["ok"]}),
                "rows": chart_rows,
            },
            "gates": {
                "render": "pass" if res.get("ok") else "block",
                "binding": "pass" if bind_ok else "block",
                "chart": "pass" if chart_gate else "block",
                "quality": "pass" if qa.get("ok") else "warn",
            },
            "quality": {"ok": qa.get("ok"), "score": qa.get("score"),
                        "sections": qa.get("sections"), "density": qa.get("density")},
            "ok": ok,
        })
        _json(man_path, man)

    _json(os.path.join(out_dir, "binding.json"), binding)
    _json(os.path.join(out_dir, "chart_audit.json"),
          {"rows": chart_rows, "gates": man.get("gates")})
    trace = {
        "schema": "dsh.decision.trace/v1",
        "intent": intent,
        "project": str(desk.root),
        "auto": auto,
        "questions": ctr["questions"],
        "binding": binding,
        "findings": [{"key": f.key, "title": f.title,
                      "chart": (f.chart or {}).get("type")} for f in picked],
        "charts": chart_rows,
        "skills": [{"role": r["role"], "skill": r["skill"], "action": r["action"],
                    "ok": r["ok"]} for r in (ctx.skills.runs or [])],
    }
    _json(os.path.join(out_dir, "decision_trace.json"), trace)
    if not os.environ.get("KEEP_TMP"):
        shutil.rmtree(tmpdir, ignore_errors=True)

    return {
        "ok": ok,
        "auto": auto,
        "declared": declared,
        "answered": answered,
        "binding": binding["binding"],
        "unanswered": binding["unanswered"],
        "sections": len(sections),
        "charts": {"with_chart": chart_ok, "ratio": round(chart_ratio, 3),
                   "types": sorted({r["type"] for r in chart_rows if r["ok"]})},
        "gates": man.get("gates"),
        "quality": {"ok": qa.get("ok"), "score": qa.get("score")},
        "files": res.get("files"),
        "out": out_dir,
    }
