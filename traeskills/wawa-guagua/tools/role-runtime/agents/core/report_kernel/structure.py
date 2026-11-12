# -*- coding: utf-8 -*-
"""report_kernel · structure —— 结构门禁与版式规则（单一实现）。

两件事，都只在这里写一次：

1. **六条结构门禁**（原 r08 `skills/s09_htmlreport.py` 自带一份，现下沉）：
   S1 标题非空 · S2 meta 含 audience/purpose · S3 章节 ≥3 ·
   S4 每章有 title+summary · S5 核心论点 ≥3 · S6 来源 ≥3 且每条有 label

2. **四条版式硬规则**（REPORT-STANDARD §八，原 `scripts/contract_test.py`
   里的 `_layout_errors`，现下沉）：R1 首屏无保真分数 · R2 末节「口径与分数」·
   R3 附录折叠 · R4 无结论清单类重复章节

r08 的 `htmlreport` 与内核产物共用这两个判定，避免「同一份报告两把尺子」。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

MIN_CHAPTERS = 3
MIN_THESIS = 3
MIN_SOURCES = 3

FIDELITY_WORDS = ("保留率", "溯源率", "弃置率")
DUP_TITLE_WORDS = ("结论清单", "结论速览", "摘要复述", "结论汇总", "结论摘录")

RULE_IDS = ("S1", "S2", "S3", "S4", "S5", "S6")


def _ck(ok: bool, rule: str, msg: str, dim: str) -> Dict[str, Any]:
    return {"ok": bool(ok), "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER",
            "rule": rule}


def guard(report: Any) -> Dict[str, Any]:
    """对「报告 JSON」（r08 的输入形态）跑六条结构门禁。

    返回 `{"ok", "checks": [...], "violations": [rule...]}`；
    `checks` 结构与 r08 `_common.ck` 一致，可直接喂 `c.result()`。
    """
    if not isinstance(report, dict):
        return {"ok": False,
                "checks": [_ck(False, "S1", "报告必须是 JSON 对象", "report")],
                "violations": ["S1"]}

    checks: List[Dict[str, Any]] = []

    title = str(report.get("title", "")).strip()
    checks.append(_ck(title, "S1", "报告标题非空", "report.title"))

    meta = report.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    checks.append(_ck(
        all(str(meta.get(k, "")).strip() for k in ("audience", "purpose")),
        "S2", "meta 含 audience 与 purpose", "report.meta"))

    chapters = report.get("chapters") or []
    chapters = chapters if isinstance(chapters, list) else []
    checks.append(_ck(len(chapters) >= MIN_CHAPTERS, "S3",
                      f"章节 ≥{MIN_CHAPTERS}（实际 {len(chapters)}）", "report.chapters"))
    for i, ch in enumerate(chapters):
        ok_ch = isinstance(ch, dict) and bool(str(ch.get("title", "")).strip()) \
            and bool(str(ch.get("summary", "")).strip())
        checks.append(_ck(ok_ch, "S4", f"第 {i + 1} 章有标题与摘要", "report.chapter"))

    thesis = report.get("thesis") or []
    thesis = thesis if isinstance(thesis, list) else []
    checks.append(_ck(len(thesis) >= MIN_THESIS, "S5",
                      f"核心论点 ≥{MIN_THESIS}（实际 {len(thesis)}）", "report.thesis"))

    sources = report.get("sources") or []
    sources = sources if isinstance(sources, list) else []
    checks.append(_ck(len(sources) >= MIN_SOURCES, "S6",
                      f"来源 ≥{MIN_SOURCES}（实际 {len(sources)}）", "report.sources"))
    for i, s in enumerate(sources):
        ok_s = isinstance(s, dict) and bool(str(s.get("label", "")).strip())
        checks.append(_ck(ok_s, "S6", f"来源[{i}] 有 label", "report.source.label"))

    violations = sorted({c["rule"] for c in checks if not c["ok"]})
    return {"ok": all(c["ok"] for c in checks), "checks": checks,
            "violations": violations}


def layout_errors(contract: Dict[str, Any], *, require_appendix: bool = True) -> List[str]:
    """四条版式硬规则（REPORT-STANDARD §八）。

    `require_appendix=False` 用于没有观测集、因此没有记录层的报告。
    """
    errs: List[str] = []
    secs = contract.get("sections") or []
    if not secs:
        return ["无章节"]
    if contract.get("layout_skip"):
        return []

    last = secs[-1]
    if last.get("title") != "口径与分数":
        errs.append(f"末节不是「口径与分数」: {last.get('title')}")
    if require_appendix and not any(s.get("appendix") for s in secs):
        errs.append("记录层未标 appendix（应折叠）")
    for s in secs:
        if any(w in str(s.get("title", "")) for w in DUP_TITLE_WORDS):
            errs.append(f"出现重复章节: {s.get('title')}")
    for m in contract.get("metric_strip") or []:
        if m.get("label") in FIDELITY_WORDS:
            errs.append(f"首页指标带仍含自检分数: {m.get('label')}")
    # R1：首屏（standfirst + 标题行）不得出现保真分数
    hero = " ".join(str(x) for x in (contract.get("standfirst"),
                                     *(contract.get("title_lines") or [])))
    for w in FIDELITY_WORDS:
        if w in hero:
            errs.append(f"首屏出现保真分数: {w}")
    return errs


def to_contract(report: Dict[str, Any], *, doc_type: str = "单文件 HTML 报告",
                author: str = "r08") -> Dict[str, Any]:
    """把「报告 JSON」翻译成内核 contract（交给唯一渲染器）。

    数字全部来自 report 自身：`dataset` 给了才算保真分数，没给就是 N/A，
    不估、不填。
    """
    from .layers import (compute_fidelity, fidelity_section, normalize_tables,
                         record_table)

    meta = report.get("meta") or {}
    title = str(report.get("title", "")).strip()
    chapters = [c for c in (report.get("chapters") or []) if isinstance(c, dict)]
    thesis = [str(t) for t in (report.get("thesis") or []) if str(t).strip()]
    sources = [s for s in (report.get("sources") or []) if isinstance(s, dict)]
    dataset = report.get("dataset") or []
    claims = [c for c in (report.get("claims") or []) if isinstance(c, dict)]

    used = {str(r.get("item")) for r in dataset} if dataset else set()
    fid = compute_fidelity(dataset, used, claims)

    def _count(label: str, value: int, note: str) -> Dict[str, Any]:
        return {"label": label, "value": str(value), "note": note, "status": "none"}

    strip = [_count("章节", len(chapters), "正文分节数"),
             _count("论点", len(thesis), "可被反驳的核心判断"),
             _count("来源", len(sources), "可核来源数")]
    if dataset:
        strip.append({"label": "观测", "value": f"{len(dataset):,}",
                      "note": "参与计算的观测条数", "status": "accent"})

    sections: List[Dict[str, Any]] = []
    for i, ch in enumerate(chapters, 1):
        sec: Dict[str, Any] = {
            "index": i,
            "title": str(ch.get("title", "")),
            "question": str(ch.get("summary", "")) or f'{ch.get("title", "")}：结论是什么？',
        }
        paras = [str(p) for p in (ch.get("paragraphs") or []) if str(p).strip()]
        if paras:
            sec["reading"] = [{"text": p} for p in paras]
        if ch.get("table"):
            sec["table"] = ch["table"]
        sections.append(sec)

    if sources:
        sections.append({
            "index": len(sections) + 1,
            "title": "来源",
            "question": "每个结论靠哪条来源支撑？",
            "table": {"caption": "来源清单",
                      "columns": ["编号", "来源", "链接"],
                      "rows": [[f"[{i}]", str(s.get("label", "")), str(s.get("url", "—"))]
                               for i, s in enumerate(sources, 1)]},
        })

    if dataset:
        sections.append({
            "index": f"A{1}",
            "title": "记录层",
            "question": "观测明细是否可复核？",
            "table": record_table(dataset),
            "reading": [{"text": "全量观测逐条列出，供审计复算；默认折叠，不占首屏。"}],
            "appendix": True,
        })

    sections.append(fidelity_section(fid, {"role": author, "extends": "report-json",
                                           "tier": "—"}, len(sections) + 1))

    contract = {
        "doc_type": doc_type,
        "toc": True,
        "fidelity": fid,
        "title_lines": [title, str(meta.get("purpose", "")).strip() or "单文件 HTML 报告"],
        "standfirst": str(report.get("standfirst", "")).strip()
                      or f'读者：{meta.get("audience", "—")}；{thesis[0] if thesis else title}',
        "metric_strip": strip,
        "meta": [f'读者 {meta.get("audience", "—")}',
                 f'目的 {meta.get("purpose", "—")}',
                 f"生成 {author}"],
        "summary": ([{"label": "结论：", "text": thesis[0]}] if thesis else [])
                   + [{"label": "依据：", "text": t} for t in thesis[1:2]],
        "sections": sections,
        "notes": {"summary": "口径、来源与证据边界",
                  "items": [{"label": "结构门禁：", "text": "S1–S6 由 core/report_kernel/structure.py 判定"},
                            {"label": "来源：", "text": f"{len(sources)} 条，逐条可核，见「来源」节"},
                            {"label": "边界：", "text": "结论只对本文列出的章节与来源成立"}]},
        "footer": [f"{author} · {doc_type}", "core/report_kernel.structure + report_renderer"],
    }
    return normalize_tables(contract)
