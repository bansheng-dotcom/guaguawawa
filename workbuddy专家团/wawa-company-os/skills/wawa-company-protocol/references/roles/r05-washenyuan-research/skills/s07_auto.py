# -*- coding: utf-8 -*-
"""s07 自动化研究辅助（auto）：plan / track 两动作。

- plan：研究计划——问题、来源类型、方法白名单、覆盖矩阵。
- track：研究运行追踪——完成率、问题覆盖缺口。
阈值：thresholds.json → auto.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "auto"
DESC = "自动化研究辅助：研究计划与运行追踪"

ACTIONS = {
    "plan": "生成/校验研究计划",
    "track": "研究运行追踪",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# plan
# --------------------------------------------------------------------------- #
def plan(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["auto"]
    method_whitelist = th["method_whitelist"]
    min_questions = th["min_questions"]

    topic = str(data.get("topic") or "")
    questions = data.get("research_questions") or []
    source_types = data.get("source_types") or []
    methods = data.get("methods") or []
    timeline = data.get("timeline") or {}
    checks: List[Dict[str, Any]] = []

    if not topic:
        checks.append(c.ck(False, "topic 为空", "auto:topic", "CRITICAL"))

    if len(questions) < min_questions:
        checks.append(c.ck(False, f"research_questions 数量 {len(questions)} < 最低要求 {min_questions}", "auto:min_questions", "HIGH"))
    else:
        checks.append(c.ck(True, f"research_questions 含 {len(questions)} 个问题", "auto:min_questions", **{"questions": len(questions)}))

    # 问题结构：每条须有 id + text
    for q in questions:
        qid = str(q.get("id") or "")
        qtext = str(q.get("text") or "")
        if not qid or not qtext:
            checks.append(c.ck(False, f"research_question {qid!r} 缺 id/text", "auto:question_fields", "HIGH", **{"question_id": qid}))

    if not source_types:
        checks.append(c.ck(False, "source_types 为空，无法构建覆盖矩阵", "auto:source_types", "HIGH"))
    else:
        checks.append(c.ck(True, f"source_types 含 {len(source_types)} 类来源", "auto:source_types", **{"source_types": len(source_types)}))

    # 方法白名单
    for m in methods:
        if m not in method_whitelist:
            checks.append(c.ck(False, f"method {m!r} 不在白名单", "auto:method_whitelist", "HIGH", **{"method": m}))
    if not methods:
        checks.append(c.ck(False, "methods 为空，研究路径不明", "auto:methods", "HIGH"))
    elif all(m in method_whitelist for m in methods):
        checks.append(c.ck(True, f"全部 {len(methods)} 个方法在白名单内", "auto:method_whitelist"))

    if not timeline:
        checks.append(c.ck(False, "timeline 为空，无研究节奏", "auto:timeline", "HIGH"))
    else:
        checks.append(c.ck(True, "timeline 就绪", "auto:timeline"))

    # 覆盖矩阵：每个问题 × 每类来源的取证计划
    coverage_matrix: List[Dict[str, Any]] = []
    for q in questions:
        qid = str(q.get("id") or "")
        coverage_matrix.append({"question_id": qid, "source_types": list(source_types)})

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   question_count=len(questions),
                   coverage_matrix=coverage_matrix,
                   verdict=verdict,
                   next="研究计划完整可执行" if ok else "修复问题/来源/方法/时间线后重新 plan",
                   )
    return out


# --------------------------------------------------------------------------- #
# track
# --------------------------------------------------------------------------- #
def track(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["auto"]
    status_enum = th["plan_statuses"]

    runs = data.get("runs") or []
    planned_questions = data.get("planned_questions") or []
    checks: List[Dict[str, Any]] = []

    if not runs:
        checks.append(c.ck(False, "runs 为空，无研究运行可追踪", "auto:track", "CRITICAL"))
    if not planned_questions:
        checks.append(c.ck(False, "planned_questions 为空，无覆盖基准", "auto:planned_questions", "HIGH"))

    # run 结构与状态白名单
    for r in runs:
        status = str(r.get("status") or "")
        if status not in status_enum:
            checks.append(c.ck(False, f"run status={status!r} 不在白名单", "auto:run_status", "HIGH", **{"status": status}))

    covered_ids: set = set()
    completed_runs = 0
    for r in runs:
        if str(r.get("status") or "") == "completed":
            completed_runs += 1
            for qid in (r.get("questions_covered") or []):
                covered_ids.add(str(qid))

    total_runs = len(runs)
    completion_rate = (completed_runs / total_runs) if total_runs > 0 else 0.0

    # 覆盖缺口：计划问题未被任何 completed run 覆盖
    coverage_gaps: List[str] = []
    for q in planned_questions:
        qid = str(q.get("id") or "")
        if qid and qid not in covered_ids:
            coverage_gaps.append(qid)

    if planned_questions and coverage_gaps:
        checks.append(c.ck(False, f"覆盖缺口 {len(coverage_gaps)} 个计划问题未被完成运行覆盖", "auto:coverage_gaps", "MEDIUM", **{"gaps": coverage_gaps}))
    elif planned_questions:
        checks.append(c.ck(True, f"全部 {len(planned_questions)} 个计划问题已被完成运行覆盖", "auto:coverage_gaps"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   run_count=total_runs,
                   completed_runs=completed_runs,
                   completion_rate=round(completion_rate, 4),
                   coverage_gaps=coverage_gaps,
                   verdict=verdict,
                   next="研究运行追踪完成" if ok else "补齐 run 状态与问题覆盖后重新 track",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "plan":
        result = plan(data)
    elif args.action == "track":
        result = track(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result
