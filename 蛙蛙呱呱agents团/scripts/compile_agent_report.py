#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/compile_agent_report.py —— 把「智能体写的东西」编译成产线能验的两种文件。

为什么需要它（v12）：
    报告不应该由方法库算出来，而应该由**智能体（模型 + 工具）调研后写出来**。
    但「模型写」不能直接进渲染器：每个数字都要能回溯，每条结论都要能被证伪。
    所以中间需要一层「编译」：把 agent 的产出转成

        evidence_pack.json   证据包：每个数字一个 id、单位、期次、来源文件
        draft_sections.json  章节稿：标题/问题/解读/refs/证伪/边界/表/图

    然后由 `core/report_flow` 逐节过账（每个数字必须能被 refs 或派生公式解释），
    `core/quality_gate` 过三层闸（证据/编辑/呈现），`core/report_renderer` 出 HTML。

    这一层**不含业务知识**：换行业只换 agent 的调研提纲（自然语言），不换代码。

输入（claims.json，由 agent 汇总）：
    {
      "meta": {"title": "...", "doc_type": "...", "audience": "..."},
      "numbers": [{"id","name","value","unit","period","source_file"}],
      "derived": [{"id","formula","value","unit","note"}],
      "sources": [{"file","kind","title","org","url","grade","quote"}],
      "standfirst": "…",
      "sections": [{"title","question","refs","reading":[{"text","refs","strong"}],
                    "falsifier","boundary","table","chart"}],
      "boundaries": ["…"]
    }

输出：<out>/evidence_pack.json、<out>/draft_sections.json

用法：
    python scripts/compile_agent_report.py claims.json --out <目录>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _hash(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def build_pack(claims: Dict[str, Any]) -> Dict[str, Any]:
    """证据包：数字 + 来源。来源按文件聚合，供报告的「记录层」表使用。"""
    nums = claims.get("numbers") or []
    srcs = claims.get("sources") or []
    counts: Dict[str, int] = {}
    for n in nums:
        f = str(n.get("source_file") or "agent")
        counts[f] = counts.get(f, 0) + 1
    sources = []
    for s in srcs:
        f = str(s.get("file") or s.get("url") or "agent")
        sources.append({
            "file": f, "kind": s.get("kind") or "web",
            "title": s.get("title") or "", "org": s.get("org") or "",
            "url": s.get("url") or "", "grade": s.get("grade") or "C",
            "quote": s.get("quote") or "",
            "numbers": counts.get(f, 0),
            "hash": _hash(s),
        })
    return {
        "schema": "dsh.evidence_pack/v1",
        "project": claims.get("meta", {}).get("title") or "agent_report",
        # 2026-11-22：封面标题/副题/KPI 取这里，不再从首节结论反推
        "meta": claims.get("meta") or {},
        "numbers": nums,
        "sources": sources,
        "counts": {"numbers": len(nums), "sources": len(sources),
                   "files": len(sources)},
    }


def _infer_strong(text: str) -> str:
    """老 claims 常把「【事实】/【机理】/【反例】」写在正文开头，strong 字段为空；
    这里把它还原成块标签，否则渲染层会把所有内容都塞进「事实」。"""
    t = str(text or "").lstrip()
    for label in ("事实", "机理", "反例", "所以", "观察", "解释", "落点"):
        if t.startswith(f"【{label}】") or t.startswith(label + "　") or t.startswith(label + "："):
            return label + "　"
    return ""


def _strip_label(text: str) -> str:
    t = str(text or "").lstrip()
    for label in ("事实", "机理", "反例", "所以", "观察", "解释", "落点"):
        for pref in (f"【{label}】", label + "　", label + "："):
            if t.startswith(pref):
                return t[len(pref):].lstrip()
    return t


def check_11_fields(claims: Dict[str, Any]) -> List[str]:
    """每节 11 字段硬校验（REPORT-FLOW §0.4）。

    verdict/question/fact/evidence/mechanism/alternative/signal/implication/
    action/stop/boundary。缺一项就拒绝编译，避免「数字多、论证短」的稿子进渲染。
    """
    issues: List[str] = []
    for i, s in enumerate(claims.get("sections") or [], 1):
        tag = str(s.get("title") or f"第{i}节")[:24]
        reads = [r for r in (s.get("reading") or []) if isinstance(r, dict)]
        strong = " ".join(str(r.get("strong") or "") for r in reads)
        text = " ".join(str(r.get("text") or "") for r in reads)
        checks = {
            "verdict": bool(str(s.get("title") or "").strip()),
            "question": bool(str(s.get("question") or "").strip()),
            "fact": ("事实" in strong) or ("事实" in text),
            "evidence": bool(s.get("refs")),
            "mechanism": ("机理" in strong) or ("机理" in text),
            "alternative": ("反例" in strong) or ("反例" in text),
            "signal": ("判别方法" in text) or ("判别方法" in strong)
                      or ("信号" in text) or ("信号" in strong),
            "implication": ("所以" in strong) or ("所以" in text),
            "action": ("所以" in strong) or ("所以" in text) or bool(s.get("action")),
            "stop": bool(str(s.get("falsifier") or "").strip()),
            "boundary": bool(str(s.get("boundary") or "").strip()),
        }
        missing = [k for k, ok in checks.items() if not ok]
        if missing:
            issues.append(f"{tag}: 缺 {', '.join(missing)}")
    return issues


def build_draft(claims: Dict[str, Any]) -> Dict[str, Any]:
    meta = claims.get("meta") or {}
    sections = []
    for i, s in enumerate(claims.get("sections") or [], 1):
        readings = []
        for r in (s.get("reading") or []):
            txt = str(r.get("text") or "")
            strong = str(r.get("strong") or "") or _infer_strong(txt)
            readings.append({"text": _strip_label(txt) if strong else txt,
                             "refs": list(r.get("refs") or []),
                             **({"strong": strong} if strong else {})})
        sec: Dict[str, Any] = {
            "index": i,
            "title": str(s.get("title") or ""),
            "question": str(s.get("question") or ""),
            "refs": list(dict.fromkeys(s.get("refs") or [])),
            "reading": readings,
        }
        for k in ("table", "chart", "falsifier", "boundary", "appendix",
                  "reading_style", "decision_rank", "headline", "headline_ref",
                  "role", "tier", "action", "relation"):
            if s.get(k):
                sec[k] = s[k]
        sections.append(sec)

    # 指标带：优先用 agent 给的，否则由 report_editorial 从 refs 指到的数字记录里取
    metrics = claims.get("metrics") or []
    # 标题：卡里没写就退到 intent。以前退到「研究报告」，被编辑层当成
    # 占位标题替换成「首节结论」，于是报告 H1 变成了半句话（2026-11-20）。
    title0 = meta.get("title") or meta.get("intent") or ""
    return {
        "profile": meta.get("profile") or "research",
        "schema": "dsh.agent.draft/v1",
        "intent": meta.get("intent") or "",
        "doc_type": meta.get("doc_type") or "研究报告",
        "title_lines": meta.get("title_lines") or [title0 or "研究报告",
                                                   f"{len(sections)} 节 · "
                                                   f"{meta.get('doc_type') or '研究报告'}"],
        "standfirst": claims.get("standfirst") or "",
        "metrics": metrics,
        "summary": [s["title"] for s in sections[:4]],
        "sections": sections,
        "boundaries": list(claims.get("boundaries") or [])[:10],
        "derived": claims.get("derived") or [],
        "degraded": list(meta.get("degraded") or []),
        # 收卡阶段的核验结论要一路带到 manifest：否则 attest 只能说「未执行」，
        # 而实际上 source_verify 已经跑过（2026-11-20 调研稿就是这样被误报的）。
        "source_verify": {k: v for k, v in (claims.get("source_verify") or {}).items()
                          if k != "rows"},
        "dispatch": claims.get("dispatch") or {},
        "questions": claims.get("questions") or {},
        "exchange": claims.get("exchange") or {},
        "explore": claims.get("explore") or [],
        "evidence_meta": {k: (claims.get("evidence") or {}).get(k)
                          for k in ("unique_sources", "min_sources",
                                    "min_sources_scope", "verified_rate")},
        "counts": claims.get("counts") or {},
        "audience": meta.get("audience") or "业务负责人",
        "decision": {"auto": True, "mode": "agent"},
    }


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="compile_agent_report",
                                 description="智能体产出 → 证据包 + 章节稿")
    ap.add_argument("claims", help="claims.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-consistency", action="store_true",
                    help="跳过交叉质询（只用于排障，不给交付物用）")
    a = ap.parse_args(argv)

    claims = json.loads(Path(a.claims).read_text(encoding="utf-8-sig"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # 每节 11 字段硬校验：缺字段不编译（REPORT-FLOW §0.4）
    spec_issues = check_11_fields(claims)
    if spec_issues:
        print(json.dumps({"ok": False, "stage": "prose_spec",
                          "issues": spec_issues[:12],
                          "hint": "每节补 verdict/question/fact/evidence/"
                                  "mechanism/alternative/signal/implication/"
                                  "action/stop/boundary 后再编译"},
                         ensure_ascii=False, indent=2))
        return 2

    # 交叉质询：同一个数两个说法、只有 D 级来源、头条无 A/B 支撑、没写边界。
    # 这一步不通过就不编译——报告宁可不发，也不发一份自相矛盾的稿。
    from core import claim_consistency
    cons = claim_consistency.check(claims)
    (out / "consistency.json").write_text(
        json.dumps(cons, ensure_ascii=False, indent=2), encoding="utf-8")
    if not cons["ok"] and not a.skip_consistency:
        print(json.dumps({"ok": False, "stage": "consistency",
                          "issues": cons["issues"],
                          "conflicts_unexplained": cons["conflicts_unexplained"],
                          "hint": "在 claims.json 的 conflicts 里写清每个冲突的口径差（name+reason）"},
                         ensure_ascii=False, indent=2))
        return 2

    pack = build_pack(claims)
    draft = build_draft(claims)
    (out / "evidence_pack.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "draft_sections.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "numbers": len(pack["numbers"]),
                      "sources": len(pack["sources"]),
                      "sections": len(draft["sections"]),
                      "consistency": cons["ok"],
                      "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
