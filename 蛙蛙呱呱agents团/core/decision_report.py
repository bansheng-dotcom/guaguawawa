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
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent

from core import (analysis_desk, analysis_methods, decision, methods,
                  orchestrator, report_assembly, report_flow)


def _json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build(intent: str, project_dir: str, out_dir: str,
          decision_path: Optional[str] = None, min_binding: float = 0.8,
          theme: str = "paper", pdf: bool = False,
          quote_mode: str = "off", audience: str = "业务负责人",
          layout: str = "paper") -> Dict[str, Any]:
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

    # 0) 专家编排（v11）：先定「谁出场」，再定「问什么」。
    #    这是修「问招聘答水果」的关键一步：编排器判 unbound 时整份报告失败，
    #    不许退回「用数据能算的东西出报告」。
    orch = orchestrator.plan(intent, method_plan=plan)
    _json(os.path.join(out_dir, "decisions.json"), orch)
    blocked = orch.get("blocked") or []
    review_only = bool(blocked) and all(r.get("review_only") for r in blocked)
    if orch.get("mode") == "unbound":
        hint = ("。这些专家只产评审/人工交付物，不产数据报告——"
                "改走 `guagua.py plan` / `chat` 人工线，或换一个数据可答的问题。"
                if review_only else
                "。这份数据回答不了这个问题——补数据后重跑，或换一个与数据匹配的问题。")
        raise report_flow.FlowError(
            "INTENT_UNBOUND: " + str(orch.get("reason")) + hint)

    # 1) 决策契约：人给的文件优先；没有就按出场专家起草，并明确标记 auto
    src = decision_path or os.path.join(project_dir, "data", "decision.json")
    auto = not os.path.exists(src)
    if not auto:
        ctr = decision.load(src)
    elif orch.get("mode") == "data":
        # 没有任何专家命中意图 → 这是**唯一**允许的数据驱动兜底（decisions.json 已标 mode=data）。
        # 注意：专家命中但答不了不走这里（2026-11-19 体检：那会让「问文案」静默出水果报告）。
        ctr = decision.draft(intent, mounted, audience=audience)
    else:
        try:
            ctr = decision.draft_from_roster(intent, orch.get("roster") or [],
                                             audience=audience)
        except ValueError as exc:
            hint = ("。出场专家只产评审/人工交付物，不产数据报告；"
                    "不许改用「数据能算什么」出报告。"
                    if review_only else
                    "。出场专家答不了这个问题——补数据后重跑，或换一个与专家能力匹配的问题；"
                    "不许改用「数据能算什么」出报告。")
            raise report_flow.FlowError("INTENT_UNBOUND: " + str(exc) + hint) from exc
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
        sec["title"] = report_assembly.judged_title(f)
        # 边界只留第一节一处（门禁要求），其余统一收到末节，避免正文与末节重复
        boundary = sec.pop("boundary", "")
        if boundary:
            if not sections:
                sec["boundary"] = boundary
            elif boundary not in boundaries_all:
                boundaries_all.append(str(boundary))
        # 每节以「所以」收口：读者要的是动作，不是又一段描述。
        # 但 Claim 型 finding 的落点已经作为「落点　」一句渲染过，再抄一遍就是复读（Q6 判红）。
        has_implication = any(
            str(r.get("strong") or "").startswith(("落点", "含义"))
            or str(r.get("text") or "").startswith(("所以", "因此"))
            for r in (sec.get("reading") or []) if isinstance(r, dict))
        if f.so_what and not has_implication:
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
        # 专家归属：报告页要能看出「这一节是哪位专家答的」（问→专家→证据 可追溯）
        sec["owner"] = str(q.get("owner") or "")
        sec["owner_name"] = str(q.get("owner_name") or "")
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

    # 4b) 动作与停止条件（v11 / P3）：由 finding 的 so_what 生成，不手写建议。
    #     finding 自带的 actions 目前为空，所以这一节从「所以：…」抽动作，
    #     前置条件取该节的数据前提，停止条件取该节的证伪条件——三者同源，可回溯。
    acts: List[Dict[str, str]] = []
    for f, sec in zip(picked, sections[:len(picked)]):
        # Claim 型 finding 的落点已经渲染成「落点　」一句；再抄进动作节会变成
        # 跨节复读（Q6 判红）。动作节只服务「有 so_what 但没有落点句」的方法族。
        if (getattr(f, "meta", None) or {}).get("claim") is not None:
            continue
        so = str(getattr(f, "so_what", "") or "").strip()
        if not so:
            for r in (sec.get("reading") or []):
                if str(r.get("strong") or "").startswith("所以"):
                    so = str(r.get("text") or "").removeprefix("所以：").strip()
                    break
        if not so:
            continue
        do = re.split(r"[；;。]", so)[0].strip()
        if not do or any(a["do"] == do for a in acts):
            continue
        acts.append({
            "do": do,
            "condition": "本节的数据前提成立（同期同口径、样本已达最小期数）",
            "stop": str(sec.get("falsifier") or "下一期方向反转即停手复盘"),
            "refs": list(sec.get("refs") or [])[:3],
        })
        if len(acts) >= 5:
            break
    # 动作文字里如果带阿拉伯数字，那些数字没有 refs，会被逐节过账拦下。
    # 动作是「做什么」，不是「证据数字」：这里把动作文本里的数字改成中文/口语，
    # 保留可执行性（「一周」「三成」），同时让正文数字仍然只来自证据。
    _NUM_WORDS = {"12": "十二", "15": "十五", "20": "二十", "30": "三十",
                  "60": "六十", "90": "九十", "1": "一", "2": "两", "3": "三",
                  "4": "四", "5": "五", "6": "六", "7": "七", "8": "八",
                  "9": "九", "10": "十"}

    def _plain(s: str) -> str:
        t = str(s or "")
        # 小数先处理（1.5 → 一点五），否则会被整数规则拆成「一.五」
        t = re.sub(r"(\d+)\.(\d+)",
                   lambda m: f"{_NUM_WORDS.get(m.group(1), m.group(1))}点{_NUM_WORDS.get(m.group(2), m.group(2))}",
                   t)
        for k, v in sorted(_NUM_WORDS.items(), key=lambda kv: -len(kv[0])):
            t = re.sub(rf"(?<![\d.]){k}(?![\d.])", v, t)
        return t

    if acts:
        rows = [[_plain(a["do"]), _plain(a["condition"]), _plain(a["stop"])]
                for a in acts]
        sec_actions = {
            "title": (f"动作：{len(acts)} 条动作全部带停止条件，"
                      "前置不成立就不执行"),
            "question": "接下来做什么，什么情况下必须停？",
            "reading_style": "list",
            "reading": [
                {"text": f"{_plain(a['do'])}；前置：{_plain(a['condition'])}；"
                         f"停止：{_plain(a['stop'])}",
                 "refs": a["refs"]}
                for a in acts
            ],
            "table": {"caption": "动作 / 前置条件 / 停止条件",
                      "columns": [{"text": h} for h in ("动作", "前置", "停止")],
                      "rows": [[{"text": c} for c in r] for r in rows]},
            "falsifier": ("若任一动作的前置条件未成立，该动作不得执行；"
                          "若停止条件命中，立即停手复盘，不许加码。"),
            "owner": "",
            "owner_name": "",
        }
        # 动作节也要有「机理 + 判别方法」：为什么是这几条、怎么判断做错了。
        refs_all = list(dict.fromkeys(
            [r for a in acts for r in (a["refs"] or [])]))[:6]
        sec_actions["reading"].append({
            "text": ("这几条动作不是通用建议，而是从前面各节的机理反推出来的："
                     "哪一节的机理成立，对应动作才成立；哪一节被证伪，对应动作立即停止。"
                     "判别方法是盯每节给出的阈值——阈值不动说明动作可以继续，"
                     "阈值被击穿说明前提已变，先停手再复盘。"),
            "refs": refs_all, "strong": "机理　"})
        sections.append(sec_actions)

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
    # finding 自带的边界（Claim.boundary）也要进「边界与缺口」：
    # 它们原本只在 inline_boundary=True 时进正文，其余会被静默丢掉，
    # 结果是一份「每条判断都有前提」的报告却过不了「至少写一处边界」的门禁。
    for f in picked:
        b = str(getattr(f, "boundary", "") or "").strip()
        if b and b not in boundaries:
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
                          quote_mode=quote_mode, layout=layout)

    # 6) 三层质检（v11 / P5）：证据 / 编辑 / 呈现，三层全过才放行。
    #    binding 与图契约是决策稿特有的两道，和三层并列，不互相替代。
    #    flow 版没有 A4 页容器，编辑/呈现两层（按页 DOM 写）不适用，改用文笔门禁。
    from core import quality_gate, report_quality
    html = (res.get("files") or {}).get("html") or ""
    if layout == "flow":
        fg = res.get("flow_gate") or {}
        _hard = os.environ.get("GUAGUA_PROSE_HARD", "0") == "1"
        qa = {"ok": bool(fg.get("ok")) or not _hard, "score": fg.get("score", 0),
              "checks": [], "sections": fg.get("sections", 0),
              "chars": 0, "numbers": 0, "density": 0, "mode": "flow",
              "prose_hard": _hard}
    else:
        qa = report_quality.audit(html) if html else {
            "ok": False, "score": 0, "checks": [], "sections": 0, "chars": 0,
            "numbers": 0, "density": 0}
    _json(os.path.join(out_dir, "quality.json"), qa)

    sc_path = os.path.join(out_dir, "section_check.json")
    sc: Optional[Dict[str, Any]] = None
    if os.path.exists(sc_path):
        try:
            sc = json.loads(Path(sc_path).read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            sc = None
    if layout == "flow":
        gate = {"schema": "dsh.quality_gate/v1", "ok": bool(qa.get("ok")),
                "verdict": "PASS" if qa.get("ok") else "BLOCK",
                "layers": [{"layer": "prose", "ok": bool(qa.get("ok")),
                            "detail": {"score": qa.get("score")}}],
                "failed": [] if qa.get("ok") else ["prose"],
                "note": "flow 版按文笔门禁判；页式两层不适用"}
    else:
        gate = quality_gate.check(draft=draft, pack=desk.pack, html=html or None,
                                  section_check=sc)
    _json(os.path.join(out_dir, "quality_gate.json"), gate)

    chart_ok = sum(1 for r in chart_rows if r["ok"])
    chart_ratio = chart_ok / len(chart_rows) if chart_rows else 0.0
    chart_gate = chart_ratio >= 0.8
    bind_ok = binding["binding"] >= min_binding
    layers = {l["layer"]: l["ok"] for l in (gate.get("layers") or [])}
    ok = (bool(res.get("ok")) and bind_ok and chart_gate and bool(gate.get("ok")))

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
                **({"prose": "pass" if layers.get("prose") else "block"}
                   if layout == "flow" else {
                       "evidence": "pass" if layers.get("evidence") else "block",
                       "editorial": "pass" if layers.get("editorial") else "block",
                       "presentation": "pass" if layers.get("presentation") else "block",
                   }),
            },
            "quality": {"ok": qa.get("ok"), "score": qa.get("score"),
                        "sections": qa.get("sections"), "density": qa.get("density")},
            "quality_gate": gate,
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
