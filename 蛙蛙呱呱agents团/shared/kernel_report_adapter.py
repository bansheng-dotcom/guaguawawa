# -*- coding: utf-8 -*-
"""REP-001 深度报告 → 内核 contract 适配器。

背景：r03/r06/r07 的 `deep`/`depth` 命令历史上走 `shared/report_generator.py`
（REP-001 五段式模板，自带一套 HTML/CSS）。为了统一到「sticker」版式，
这里把同一份 spec 映射成 core/report_renderer 的 contract，仍保留原有内容：
结论、KPI、分析小节、图表、三级归因、护栏、灰度、下一步、附录、证据。

回滚：`GUAGUA_DEEP_ENGINE=legacy` 时仍走旧模板。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from agents.shared.report_generator import generate_professional_report

AGENTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_STATUS = {"green": "healthy", "red": "critical", "normal": "none", "": "none"}


def _plain(text: Any) -> str:
    """去掉轻量 markdown 标记，避免内核转义后露出 ** 与 #。"""
    s = str(text or "")
    return (s.replace("**", "").replace("##", "").replace("###", "")
             .replace("- ", "").strip())


def _cell(text: Any) -> Dict[str, str]:
    return {"lines": [{"text": _plain(text)}]}


def _table(headers: List[str], rows: List[List[Any]], caption: str) -> Dict[str, Any]:
    return {"caption": caption,
            "columns": [{"text": h} for h in headers],
            "rows": [[_cell(c) for c in row] for row in rows]}


def _to_contract(spec: Dict[str, Any]) -> Dict[str, Any]:
    role = str(spec.get("role_id", "r00")).lower()
    name = str(spec.get("agent_name", "专家"))
    title = str(spec.get("report_title", "深度分析报告"))
    sections: List[Dict[str, Any]] = []
    idx = 1

    for sec in spec.get("analysis_sections") or []:
        reading = [{"text": _plain(sec.get("content", ""))}] if sec.get("content") else []
        for b in sec.get("bullets") or []:
            reading.append({"text": _plain(b)})
        sections.append({"index": idx, "title": _plain(sec.get("title", f"分析 {idx}")),
                         "question": "这一节回答什么问题、给出什么证据？",
                         "reading": reading or [{"text": "（原报告未提供正文）"}]})
        idx += 1

    for fig in spec.get("figures") or []:
        t = str(fig.get("type", "line"))
        t = {"bar": "vbar", "horizontal_bar": "hbar"}.get(t, t)
        chart = {"type": t, "title": _plain(fig.get("title", "图表")),
                 "unit_meta": _plain(fig.get("note", "")) or "原报告图表",
                 "source": "REP-001 深度分析图表规格"}
        for k in ("xlabels", "series", "bars", "vbars", "steps", "items", "points", "stages"):
            if k in fig:
                chart[k] = fig[k]
        sections.append({"index": idx, "title": f"图：{_plain(fig.get('title', ''))}",
                         "question": "这张图支撑哪一个判断？", "chart": chart,
                         "reading": [{"text": _plain(fig.get("note", ""))}] if fig.get("note") else []})
        idx += 1

    rca = spec.get("rca") or []
    if rca:
        sections.append({"index": idx, "title": "三级归因：数据 → 经营 → 商业",
                         "question": "问题从哪一层来、证据是什么？",
                         "table": _table(["层级", "判断", "证据"],
                                         [[r.get("level", ""), _plain(r.get("title", "")), _plain(r.get("finding", "") or r.get("evidence", ""))] for r in rca],
                                         "REP-001 三级归因")})
        idx += 1

    guard = spec.get("guardrails") or []
    if guard:
        sections.append({"index": idx, "title": "护栏与熔断阈值",
                         "question": "哪些指标越界就必须停？",
                         "table": _table(["维度", "指标", "基线", "阈值"],
                                         [[g.get("dim", ""), g.get("metric", ""), g.get("base", ""), g.get("threshold", "")] for g in guard],
                                         "护栏清单")})
        idx += 1

    rollout = spec.get("rollout_plan") or []
    if rollout:
        sections.append({"index": idx, "title": "灰度与放量路径",
                         "question": "分几步放、每步的放量条件是什么？",
                         "table": _table(["阶段", "范围", "时长", "条件"],
                                         [[r.get("phase", ""), r.get("scope", ""), r.get("duration", ""), r.get("condition", "")] for r in rollout],
                                         "灰度计划")})
        idx += 1

    nxt = spec.get("next_steps") or []
    if nxt:
        sections.append({"index": idx, "title": "下一步行动",
                         "question": "谁在什么时候做什么？",
                         "reading": [{"text": _plain(x)} for x in nxt]})
        idx += 1

    # 附录：原 appendix + 证据/可复现
    app_rows: List[List[Any]] = []
    for item in spec.get("appendix") or []:
        t = item.get("table") or {}
        headers = t.get("headers") or t.get("columns") or []
        for row in t.get("rows") or []:
            app_rows.append([_plain(item.get("title", "附录"))] + [_plain(c) for c in row])
    if app_rows:
        sections.append({"index": "A1", "title": "记录层：附录与证据",
                         "question": "原始表格能不能复核？",
                         "table": _table(["来源"] + [f"列{i+1}" for i in range(max(len(r) - 1 for r in app_rows))],
                                         app_rows, "原报告附录"),
                         "appendix": True})
    prov = spec.get("provenance") or {}
    prov_rows = [[_plain(k), _plain(v)] for k, v in prov.items()]
    if prov_rows:
        sections.append({"index": "A2", "title": "记录层：证据与可复现",
                         "question": "这份报告的数据从哪来、怎么复算？",
                         "table": _table(["项", "值"], prov_rows, "证据与可复现"),
                         "appendix": True})

    sections.append({
        "index": idx,
        "title": "口径与分数",
        "question": "这份深度报告的边界是什么？",
        "table": _table(["指标", "值", "说明"], [
            ["分析小节", str(len(spec.get("analysis_sections") or [])), "来自 REP-001 spec"],
            ["图表", str(len(spec.get("figures") or [])), "内核图表库渲染"],
            ["渲染器", "core/report_renderer.py", "sticker 主题，确定性渲染"],
            ["生成时间", datetime.now().strftime("%Y-%m-%d %H:%M"), "本地时间"],
        ], "自检"),
        "reading": [{"text": "本报告由 REP-001 spec 映射为内核 contract 后渲染；数字与结论沿用原 spec，未做二次计算。"}],
    })

    kpis = []
    for k in (spec.get("kpi_metrics") or [])[:5]:
        kpis.append({"label": _plain(k.get("label", "")),
                     "value": _plain(k.get("value", "")),
                     "note": _plain(k.get("sub", "")) or "—",
                     "status": _STATUS.get(str(k.get("status", "")).lower(), "none")})

    summary = [{"label": "决策指令：", "text": _plain(spec.get("decision_directive", ""))}]
    if spec.get("executive_summary"):
        summary.insert(0, {"label": "结论：", "text": _plain(spec["executive_summary"])})

    return {
        "doc_type": f"{name} · 深度分析报告（REP-001）",
        "theme": "sticker",
        "toc": True,
        "title_lines": [title, "七步深度分析 · 决策版"],
        "standfirst": _plain(spec.get("executive_summary", ""))[:120] + "…"
                      if len(_plain(spec.get("executive_summary", ""))) > 120
                      else _plain(spec.get("executive_summary", "")),
        "meta": [f"{role.upper()} {name}", "渲染 core/report_renderer.py（sticker）",
                 datetime.now().strftime("生成 %Y-%m-%d %H:%M")],
        "metric_strip": kpis,
        "summary": summary,
        "sections": sections,
        "notes": {"summary": "口径与证据边界",
                  "items": [{"label": "来源：", "text": "REP-001 深度分析 spec（同一份数据与结论）。"},
                            {"label": "版式：", "text": "sticker（墨绿封面 + 粗黑描边 + 贴纸卡片）；旧模板可用 GUAGUA_DEEP_ENGINE=legacy 回滚。"}],
                  "tail": "内核渲染不改变原报告的数字；只改呈现。"},
        "footer": [f"{role.upper()} {name} · 深度分析", "core/report_renderer.py 确定性渲染"],
    }


def render_deep_report(spec: Dict[str, Any], out_dir: str, report_slug: str) -> Dict[str, str]:
    """渲染深度报告：默认内核（sticker）；env=legacy 时回滚旧模板。"""
    if os.environ.get("GUAGUA_DEEP_ENGINE", "kernel").strip().lower() == "legacy":
        return generate_professional_report(out_dir=out_dir, report_slug=report_slug, **spec)

    import sys
    if AGENTS_ROOT not in sys.path:
        sys.path.insert(0, AGENTS_ROOT)
    from core import report_bridge, report_renderer

    os.makedirs(out_dir, exist_ok=True)
    contract = _to_contract(spec)
    errs = report_renderer.validate_contract(contract)
    if errs:
        # 不因为版式问题挡住出报告：退回旧模板，并留下错误信息
        files = generate_professional_report(out_dir=out_dir, report_slug=report_slug, **spec)
        files["contract_errors"] = errs
        return files

    charts = os.path.join(AGENTS_ROOT, "core", "charts")
    if os.path.isdir(charts):
        report_renderer.set_chart_dir(charts)
    html = report_renderer.render(contract)
    html_path = os.path.join(out_dir, f"{report_slug}.html")
    md_path = os.path.join(out_dir, f"{report_slug}.md")
    with open(html_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    _write_md(contract, md_path)
    return {"html": html_path, "md": md_path}


def _md_cell(cell: Dict[str, Any]) -> str:
    if "text" in cell:
        return str(cell["text"])
    if "lines" in cell:
        return " ".join(str(x.get("text", "")) for x in cell["lines"])
    return ""


def _write_md(contract: Dict[str, Any], path: str) -> None:
    L: List[str] = [f"# {contract['title_lines'][0]}", ""]
    if len(contract.get("title_lines", [])) > 1:
        L += [f"> {contract['title_lines'][1]}", ""]
    if contract.get("standfirst"):
        L += [contract["standfirst"], ""]
    for item in contract.get("summary") or []:
        L.append(f"**{item.get('label', '')}**{item.get('text', '')}")
    L.append("")
    for sec in contract.get("sections") or []:
        L.append(f"## {sec.get('title', '')}")
        if sec.get("question"):
            L += ["", f"> {sec['question']}"]
        for r in sec.get("reading") or []:
            L += ["", f"- **{r.get('strong', '')}**{r.get('text', '')}" if r.get("strong") else f"- {r.get('text', '')}"]
        t = sec.get("table")
        if t:
            L += ["", f"**{t.get('caption', '表格')}**", ""]
            L.append("| " + " | ".join(str(c.get("text", "")) for c in t.get("columns", [])) + " |")
            L.append("|" + "|".join("---" for _ in t.get("columns", [])) + "|")
            for row in t.get("rows", []):
                L.append("| " + " | ".join(_md_cell(c) for c in row) + " |")
        L.append("")
    notes = contract.get("notes") or {}
    if notes.get("items"):
        L += ["## " + notes.get("summary", "口径与边界"), ""]
        for it in notes["items"]:
            L.append(f"- **{it.get('label', '')}**{it.get('text', '')}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
