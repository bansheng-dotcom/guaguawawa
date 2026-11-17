# -*- coding: utf-8 -*-
"""core/coverage —— 问题 → 能力 → 角色 → 覆盖度（升级 P2）。

替代 A/B 分支：不问“走 1 还是 2”，只问“这些问题被覆盖了多少”。

    real       1.0
    simulated  0.5
    blocked    0.0
    missing    0.0

    coverage = 加权得分 / 问题数
    verdict  = COMPLETE  当 coverage >= min_coverage 且没有 blocked/missing
               INCOMPLETE 否则

用法：
    python -m core.coverage --questions workspace/report_upgrade/questions_fruit.json \
        --graph workspace/report_upgrade/capability_graph.json \
        --json workspace/report_upgrade/coverage_fruit.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import capability_graph, question_library

SCORE = {"real": 1.0, "simulated": 0.5, "blocked": 0.0, "missing": 0.0}


def _norm_questions(items: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, q in enumerate(items):
        if isinstance(q, str):
            out.append({"id": f"Q{i + 1}", "text": q, "capability": q})
            continue
        cap = str(q.get("capability") or "")
        if not cap:
            needs = q.get("needs") or []
            cap = str(needs[0]) if needs else ""
        out.append({
            "id": str(q.get("id") or f"Q{i + 1}"),
            "text": str(q.get("text") or ""),
            "capability": cap,
        })
    return out


def load_questions(path: str | Path) -> List[Dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        items = data.get("questions") or data.get("items") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []
    return _norm_questions(items)


def questions_for_role(role: str) -> List[Dict[str, Any]]:
    return _norm_questions(question_library.by_role(role))


def compute(questions: List[Any], graph: Optional[Dict[str, Any]] = None,
            min_coverage: float = 0.8) -> Dict[str, Any]:
    g = graph or capability_graph.build()
    caps = g.get("capabilities") or {}
    qs = _norm_questions(questions)

    rows: List[Dict[str, Any]] = []
    required: List[str] = []
    for q in qs:
        cap = q["capability"]
        c = caps.get(cap) or {}
        status = c.get("status") or ("missing" if not cap else "missing")
        score = SCORE.get(status, 0.0)
        if cap and cap not in required:
            required.append(cap)
        rows.append({
            "id": q["id"],
            "text": q["text"],
            "capability": cap,
            "status": status,
            "score": score,
            "providers": [p.get("role") for p in (c.get("providers") or [])],
            "real_providers": c.get("real_providers") or [],
            "simulated_providers": c.get("simulated_providers") or [],
            "blocked_providers": c.get("blocked_providers") or [],
            "gap": status in ("blocked", "missing"),
            "partial": status == "simulated",
        })

    coverage = round(sum(r["score"] for r in rows) / max(1, len(rows)), 3)
    gaps = [r for r in rows if r["gap"]]
    partial = [r for r in rows if r["partial"]]
    verdict = "COMPLETE" if (coverage >= min_coverage and not gaps) else "INCOMPLETE"

    def cap_status(name: str) -> List[str]:
        return [c for c in required if (caps.get(c) or {}).get("status") == name]

    contributing = sorted({r for row in rows for r in row["real_providers"]})
    simulated = sorted({r for row in rows for r in row["simulated_providers"]})
    blocked_roles = sorted(set(g.get("counts", {}).get("blocked_roles") or []))
    excluded = sorted(set(blocked_roles))

    return {
        "schema": "dsh.coverage/v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "min_coverage": min_coverage,
        "coverage": coverage,
        "verdict": verdict,
        "questions": rows,
        "capabilities": {
            "required": required,
            "real": cap_status("real"),
            "simulated": cap_status("simulated"),
            "blocked": cap_status("blocked"),
            "missing": cap_status("missing"),
        },
        "roles": {
            "contributing": contributing,
            "simulated": simulated,
            "blocked": blocked_roles,
            "excluded": excluded,
            "gaps": [r["capability"] for r in gaps],
        },
        "summary": {
            "questions": len(rows),
            "covered_real": sum(1 for r in rows if r["status"] == "real"),
            "partial": len(partial),
            "gaps": len(gaps),
            "gap_questions": [r["id"] for r in gaps],
        },
    }


def write(path: str | Path, result: Dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="coverage",
                                 description="问题覆盖度：替代 A/B 分支")
    ap.add_argument("--questions", required=True, help="问题 JSON（list 或 {questions:[]}）")
    ap.add_argument("--graph", default=None, help="能力图 JSON；缺省现场构建")
    ap.add_argument("--json", default=None, help="输出 JSON 路径")
    ap.add_argument("--min-coverage", type=float, default=0.8)
    a = ap.parse_args(argv)

    graph = json.loads(Path(a.graph).read_text(encoding="utf-8-sig")) if a.graph else None
    res = compute(load_questions(a.questions), graph=graph, min_coverage=a.min_coverage)
    if a.json:
        p = write(a.json, res)
        print(f"wrote {p}")
    print(json.dumps({"coverage": res["coverage"], "verdict": res["verdict"],
                      "summary": res["summary"],
                      "capabilities": res["capabilities"]}, ensure_ascii=False, indent=2))
    return 0 if res["verdict"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
