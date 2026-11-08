# -*- coding: utf-8 -*-
"""R02 输出契约（T6）：每个技能动作的输出 schema，供 contracts 命令与
对抗评审的 contract 挑战共用。契约先行 = 改输出结构必须先改契约。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

_A = {"type": "array"}
_S = {"type": "string"}
_B = {"type": "boolean"}
_O = {"type": "object"}
_N = {"type": "number", "minimum": 0}
_I = {"type": "integer", "minimum": 0}

CONTRACTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "schedule": {
        "wbs": {"ok": _B, "checks": _A, "item_count": _I, "total_cost": _N,
                "kinds": _A, "max_step": _I, "next": _S},
        "sprint": {"ok": _B, "checks": _A, "schedule": _A, "end_date": _S,
                   "total_workdays": _I, "day_count": _I, "utilization": _A,
                   "capacity_per_day": _N, "cadence": _S, "next": _S},
        "critpath": {"ok": _B, "checks": _A, "order": _A, "critpath": _A,
                     "duration_days": _N, "slack": _O, "cycle": _A, "next": _S},
    },
    "capacity": {
        "check": {"ok": _B, "checks": _A, "rows": _A, "overloaded": _A,
                  "red_flags": _A, "lead_time": _O, "next": _S},
        "delegate": {"ok": _B, "checks": _A, "packages": _A, "oversized": _A,
                     "next": _S},
        "split": {"ok": _B, "checks": _A, "subtasks": _A, "subtask_count": _I,
                  "max_hours": _N, "split_required": _B, "sum_hours": _N,
                  "next": _S},
    },
    "handoff": {
        "package": {"ok": _B, "checks": _A, "package_id": _S,
                    "artifact_type": _S, "repro_count": _I,
                    "downstream_fields": _A, "downstream_count": _I,
                    "criteria_count": _I, "next": _S},
        "accept": {"ok": _B, "checks": _A, "verdict": {"type": "string",
                                                       "enum": ["PASS", "FAIL"]},
                   "passed_count": _I, "failed": _A, "audit": _O, "next": _S},
        "trace": {"ok": _B, "checks": _A, "event_count": _I, "types_used": _A,
                  "monotonic": _B, "chain_complete": _B, "next": _S},
    },
    "retro": {
        "postmortem": {"ok": _B, "checks": _A, "severity": _I, "urgency": _I,
                       "escalated": _B, "action_count": _I, "timeline_ok": _B,
                       "next": _S},
        "grade": {"ok": _B, "checks": _A, "grades": _A, "pass_count": _I,
                  "overall": {"type": "string",
                             "enum": ["PASS", "PARTIAL", "FAIL"]},
                  "unclosed_losses": _A, "next": _S},
        "action": {"ok": _B, "checks": _A, "overdue": _A, "on_track_count": _I,
                   "closure_rate": _N, "done_count": _I, "next": _S},
    },
    "process": {
        "sop": {"ok": _B, "checks": _A, "step_count": _I, "control_points": _I,
                "critical_uncovered": _A, "cp_ratio": _N, "next": _S},
        "waste": {"ok": _B, "checks": _A, "wastes": _O, "opportunity": _S,
                  "quick_wins": _A, "transformations": _A, "next": _S},
        "meeting": {"ok": _B, "checks": _A, "timebox": _I, "within_timebox": _B,
                    "action_count": _I, "coverage": _N, "next": _S},
    },
    "knowledge": {
        "digest": {"ok": _B, "checks": _A, "chapters": _N, "token_report": _O,
                   "fingerprint": _S, "duplicate": _B, "next": _S},
        "entry": {"ok": _B, "checks": _A, "sha": _S, "duplicate": _B,
                  "too_large": _B, "stale": _B, "tokens": _I, "next": _S},
        "search": {"ok": _B, "checks": _A, "results": _A, "top_k": _I,
                   "stale_count": _I, "next": _S},
    },
    "portfolio": {
        "status": {"ok": _B, "checks": _A, "rag": _O, "counts": _O,
                   "attention": _A, "next": _S},
        "plan": {"ok": _B, "checks": _A, "waves": _A, "human_gates": _A,
                 "cycle": _A, "wave_load": _O, "next": _S},
        "graph": {"ok": _B, "checks": _A, "node_count": _I, "edge_count": _I,
                  "violations": _A, "god_nodes": _A, "max_depth": _I,
                  "next": _S},
    },
}


def list_skills() -> List[str]:
    return sorted(CONTRACTS.keys())


def list_actions(skill: str) -> List[str]:
    return sorted(CONTRACTS.get(skill, {}).keys())


def validate_output(skill: str, action: str, result: Any) -> List[str]:
    schema = CONTRACTS.get(skill, {}).get(action)
    if schema is None:
        return [f"未知契约 {skill}/{action}"]
    return c.validate_schema(result, {"type": "object",
                                      "required": list(schema.keys()),
                                      "properties": schema})
