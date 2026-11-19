# -*- coding: utf-8 -*-
"""core.coverage_cli —— plan / confirm / preflight / audit 四个动作。

contract:
    python -m core.coverage_cli plan --input project.json --out out/
    python -m core.coverage_cli confirm --plan out/coverage_plan.json --by 用户 --note "确认"
    python -m core.coverage_cli preflight --frame ... --plan ... --sources ... --confirmation ...
    python -m core.coverage_cli audit --frame ... --plan ... --html report.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from core import coverage_confirm, coverage_plan, coverage_policy, task_frame, task_research


def _write(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_plan(a) -> int:
    src = json.loads(Path(a.input).read_text(encoding="utf-8-sig"))
    pol = coverage_policy.load(a.policy)
    ledger = task_research.SourceLedger(no_new_streak=int(pol["coverage"]["saturation_no_new"]))
    for s in src.get("sources") or []:
        ledger.add(s)
    st = ledger.status()
    frame = task_frame.build(
        brief={"task_id": src.get("task_id"), "brief": src.get("brief")},
        decision=src["decision"], units=src["units"], dimensions=src["dimensions"],
        depth=src["depth"], maps=src["maps"], page_floor=int(src.get("page_floor", 21)),
        source_policy=pol["research"], saturation=st, conflicts=src.get("conflicts") or [],
    )
    plan = coverage_plan.build(frame, src["cells"], int(src.get("page_estimate", 21)),
                               [m["level"] for m in src["maps"]], src.get("charts") or [])
    errs = task_frame.validate(frame, pol) + coverage_plan.validate(plan, frame)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "task_frame.json", frame)
    _write(out / "coverage_plan.json", plan)
    _write(out / "source_ledger.json", {"sources": ledger.sources, "status": st})
    (out / "coverage_matrix.md").write_text(
        coverage_confirm.matrix_markdown(frame, plan), encoding="utf-8")
    print(json.dumps({"ok": not errs, "errors": errs, "sources": st,
                      "plan_hash": coverage_plan.plan_hash(plan),
                      "out": str(out)}, ensure_ascii=False, indent=2))
    return 0 if not errs else 1


def cmd_confirm(a) -> int:
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8-sig"))
    conf = coverage_confirm.confirm(plan, a.by, a.note or "", a.edit or [])
    out = Path(a.out or (Path(a.plan).parent / "confirmation.json"))
    _write(out, conf)
    print(json.dumps({"ok": True, "confirmation": str(out), "hash": conf["plan_hash"]},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_preflight(a) -> int:
    frame = json.loads(Path(a.frame).read_text(encoding="utf-8-sig"))
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8-sig"))
    src = json.loads(Path(a.sources).read_text(encoding="utf-8-sig"))
    conf = json.loads(Path(a.confirmation).read_text(encoding="utf-8-sig")) if a.confirmation else None
    pol = coverage_policy.load(a.policy)
    res = coverage_plan.pre_gate(frame, plan, src.get("status", src), conf, pol)
    _write(Path(a.json) if a.json else Path(a.plan).parent / "pre_gate.json", res)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


def cmd_audit(a) -> int:
    frame = json.loads(Path(a.frame).read_text(encoding="utf-8-sig"))
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8-sig"))
    res = coverage_confirm.audit_coverage(plan, frame, a.html, int(a.min_pages))
    _write(Path(a.json) if a.json else Path(a.html).parent / "coverage_gate.json", res)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="coverage_cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--input", required=True); p.add_argument("--out", required=True); p.add_argument("--policy"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("confirm"); p.add_argument("--plan", required=True); p.add_argument("--by", default="用户"); p.add_argument("--note"); p.add_argument("--edit", action="append"); p.add_argument("--out"); p.set_defaults(fn=cmd_confirm)
    p = sub.add_parser("preflight"); p.add_argument("--frame", required=True); p.add_argument("--plan", required=True); p.add_argument("--sources", required=True); p.add_argument("--confirmation"); p.add_argument("--policy"); p.add_argument("--json"); p.set_defaults(fn=cmd_preflight)
    p = sub.add_parser("audit"); p.add_argument("--frame", required=True); p.add_argument("--plan", required=True); p.add_argument("--html", required=True); p.add_argument("--min-pages", type=int, default=21); p.add_argument("--json"); p.set_defaults(fn=cmd_audit)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
