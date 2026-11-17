# -*- coding: utf-8 -*-
"""core/report_build —— P4 唯一入口：问题树 → 能力覆盖 → v9 框架 → 报告。

替代 A/B 分支与「三个走法」：

    意图 + 数据
      → 选问题（question_library + report_framework.match）
      → 算覆盖度（coverage）
      → v9 通用框架（report_compose, thesis=analysis）
      → 唯一渲染器 + 强制门禁
      → 一份报告 + manifest（含 coverage / questions / lens）

    python -m core.report_build --intent "…" --dir <项目> --out <目录> --lens market
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import (analysis_desk, capability_graph, coverage, question_library,
                  report_compose, report_flow, report_framework)

LENS_PREFIXES: Dict[str, List[str]] = {
    "market": ["research", "market", "competition", "content", "channel"],
    "ops": ["finance", "supply", "commerce", "people", "customer"],
    "chain": ["supply", "commerce", "risk"],
    "fix": ["finance", "risk", "compliance", "supply"],
}

# 方法 finding → 问题（用于“报告实际回答了哪些问题”的覆盖度）
FINDING_QUESTION: Dict[str, str] = {
    "structure": "q.r06.structure",
    "momentum": "q.r06.momentum",
    "trajectory": "q.r06.trajectory",
    "contribution": "q.r06.contribution",
    "economics": "q.r15.tco",
    "transmission": "q.r15.chain",
    "arbitrage": "q.r15.chain",
    "risk": "q.r01.risk",
    "sample": "q.r18.quality",
    "coverage": "q.r05.sources",
    "size": "q.r05.size",
    "growth": "q.r05.size",
    "demand": "q.r06.structure",
    "volume": "q.r06.structure",
    "channel": "q.r12.channel",
    "region": "q.r05.landscape",
    "supply": "q.r05.landscape",
    "policy": "q.r03.tax",
    "consistency": "q.r04.evidence",
    "concentration": "q.r05.landscape",
}


def questions_from_findings(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_id = {q["id"]: q for q in question_library.QUESTIONS}
    out: List[Dict[str, Any]] = []
    seen = set()
    for f in trace.get("findings") or []:
        qid = FINDING_QUESTION.get(str(f.get("key") or ""))
        if qid and qid in by_id and qid not in seen:
            out.append(by_id[qid])
            seen.add(qid)
    return out


def select_questions(intent: str, profile: Dict[str, Any],
                     lens: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    dims = report_framework.match(intent, profile)
    keys = {d["key"] for d in dims}
    qs = [q for q in question_library.QUESTIONS if q["dimension"] in keys]
    if lens:
        prefixes = set(LENS_PREFIXES.get(lens) or [])
        filtered = [q for q in qs if q["capability"].split(".")[0] in prefixes]
        if len(filtered) >= 3:
            qs = filtered
    qs.sort(key=lambda q: (not q["primary"], q["role"], q["id"]))
    if not qs:
        qs = [q for q in question_library.QUESTIONS if q["primary"]]
    return qs[:limit]


def build(intent: str, project_dir: str, out_dir: str,
          lens: Optional[str] = None, quote_mode: str = "strict",
          min_coverage: float = 0.8, theme: str = "paper",
          pdf: bool = False, audience: str = "业务负责人",
          record_outcomes: bool = False,
          outcome_deadline: Optional[str] = None) -> Dict[str, Any]:
    engine = os.environ.get("REPORT_ENGINE", "v9")
    if engine not in ("v9", "v10"):
        raise ValueError("REPORT_ENGINE=v8 已下线；只支持 v9/v10，回滚请用 git tag")
    if os.environ.get("REPORT_QUOTE_GATE") == "0":
        quote_mode = "off"
    desk = analysis_desk.scan(project_dir)
    prof = analysis_desk.profile(desk)
    graph = capability_graph.build()
    qs = select_questions(intent, prof, lens)
    cov = coverage.compute(qs, graph, min_coverage=min_coverage)

    fallback = False
    try:
        res = report_compose.build(
            intent=intent, project_dir=project_dir, out_dir=out_dir,
            thesis="analysis", theme=theme, pdf=pdf, audience=audience,
            quote_mode=quote_mode, lens=lens)
    except report_flow.FlowError:
        if not lens:
            raise
        # lens 过滤后没有可判定方法：退回全维度，但记录 fallback
        res = report_compose.build(
            intent=intent, project_dir=project_dir, out_dir=out_dir,
            thesis="analysis", theme=theme, pdf=pdf, audience=audience,
            quote_mode=quote_mode, lens=None)
        fallback = True

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    trace: Dict[str, Any] = {}
    # 用“报告实际回答的问题”重算覆盖度：不是先拍一个问题清单再硬套
    trace_path = out / "analysis_trace.json"
    if trace_path.exists():
        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8-sig"))
            qs2 = questions_from_findings(trace)
            if qs2:
                qs = qs2
                cov = coverage.compute(qs, graph, min_coverage=min_coverage)
        except (OSError, json.JSONDecodeError):
            pass
    quotes = res.get("quotes") or {}
    quotes_ok = bool(quotes.get("ok", True)) if quotes else True
    cov_path = out / "coverage.json"
    cov_path.write_text(json.dumps(cov, ensure_ascii=False, indent=2), encoding="utf-8")

    man_path = out / "manifest.json"
    if man_path.exists():
        man = json.loads(man_path.read_text(encoding="utf-8-sig"))
        man["coverage"] = {
            "schema": cov["schema"],
            "coverage": cov["coverage"],
            "verdict": cov["verdict"],
            "questions": [q["id"] for q in qs],
            "gaps": cov["roles"].get("gaps", []),
            "min_coverage": cov["min_coverage"],
        }
        man["lens"] = lens
        man["lens_fallback"] = fallback
        man["questions"] = [{"id": q["id"], "text": q["text"],
                             "capability": q["capability"]} for q in qs]
        man["generated_by"] = "core/report_build.py"
        man["quotes_ok"] = quotes_ok
        man["claims"] = res.get("claim_gate")
        man["gates"] = {
            "quote": "pass" if quotes_ok else "block",
            "coverage": "pass" if cov["verdict"] == "COMPLETE" else "block",
            "claim": ("pass" if (res.get("claim_gate") or {}).get("ok", True)
                      else "block"),
            "quality": "pass" if (res.get("quality") or {}).get("ok", True) else "warn",
            "render": "pass" if res.get("files", {}).get("html") else "block",
        }
        man["ok"] = (bool(man.get("ok")) and cov["verdict"] == "COMPLETE"
                     and quotes_ok)
        man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

        if record_outcomes and trace:
            from core import outcome_ledger
            rid = ((man.get("contract") or {}).get("report_id")
                   or man.get("report_id") or f"RPT-{datetime.now():%Y%m%d}-{lens or 'analysis'}")
            seeded = outcome_ledger.seed_from_trace(
                rid, intent, trace, deadline=outcome_deadline)
            man["outcomes"] = {"seeded": len(seeded),
                               "path": str(outcome_ledger.DEFAULT_PATH)}
            man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    return {
        **res,
        "ok": (bool(res.get("ok")) and cov["verdict"] == "COMPLETE" and quotes_ok),
        "coverage": cov["coverage"],
        "coverage_verdict": cov["verdict"],
        "quotes_ok": quotes_ok,
        "claims": res.get("claim_gate"),
        "gates": {"quote": "pass" if quotes_ok else "block",
                  "coverage": cov["verdict"],
                  "claim": ("pass" if (res.get("claim_gate") or {}).get("ok", True)
                            else "block")},
        "questions": [q["id"] for q in qs],
        "lens": lens,
        "lens_fallback": fallback,
        "coverage_file": str(cov_path),
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="report_build",
                                 description="P4 唯一入口：问题树 → 覆盖度 → v9 → 报告")
    ap.add_argument("--intent", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lens", choices=("market", "ops", "chain", "fix"), default=None)
    ap.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="strict")
    ap.add_argument("--min-coverage", type=float, default=0.8)
    ap.add_argument("--theme", default="paper")
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--audience", default="业务负责人")
    ap.add_argument("--record-outcomes", action="store_true")
    ap.add_argument("--outcome-deadline", default=None)
    a = ap.parse_args(argv)
    res = build(a.intent, a.dir, a.out, lens=a.lens, quote_mode=a.quote_mode,
                min_coverage=a.min_coverage, theme=a.theme, pdf=a.pdf,
                audience=a.audience, record_outcomes=a.record_outcomes,
                outcome_deadline=a.outcome_deadline)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:8000])
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
