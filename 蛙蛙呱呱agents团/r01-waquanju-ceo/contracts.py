# -*- coding: utf-8 -*-
"""R01 技能契约（T6）：每技能机器可读的「输入 + 输出」JSON Schema。

把「CEO 技能能吃什么、吐什么」升级为可校验的 JSON Schema。
`agent.py contract validate` 用它做确定性校验：技能实际输出不符契约即 FAIL。

schema 是 JSON Schema 的子集（对齐 skills._common.validate_schema）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

_s = {"type": "string"}
_b = {"type": "boolean"}
_n = {"type": "number"}
_i = {"type": "integer"}
_arr = {"type": "array"}
_obj = {"type": "object"}


def _o(required: List[str], props: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "object", "required": required, "properties": props}


def _ok(required: List[str], **props: Any) -> Dict[str, Any]:
    base = {"ok": _b, "checks": _arr}
    base.update(props)
    return _o(["ok", "checks"] + required, base)


CONTRACTS: Dict[str, Any] = {
"ev": {
    "desc": "决策期望值：EV/盈亏平衡/敏感性",
    "input": {"args": {"input": _s}},
    "output": {"ev": _ok(["ev"], ev=_obj)},
},
"intent": {
    "desc": "意图识别与任务分级：brief/clarify/triage",
    "input": {"args": {"input": _s}},
    "output": {
        "brief": _ok(["brief_fields"], brief_fields=_arr, option_count=_i),
        "clarify": _ok(["light", "action"], light=_s, action=_s,
                       answered=_i, evidenced=_i),
        "triage": _ok(["level", "domains", "boardroom", "next"],
                      level=_s, domains=_arr, boardroom=_b, next=_s),
    },
},
"decompose": {
    "desc": "跨部门拆解：taskcard/wave/route",
    "input": {"args": {"input": _s}},
    "output": {
        "taskcard": _ok(["sections"], sections=_arr),
        "wave": _ok(["wave_count", "waves"], wave_count=_i, waves=_arr,
                    cycle=_arr),
        "route": _ok(["roles", "boardroom", "next"], roles=_arr,
                     boardroom=_b, next=_s, matched=_arr),
    },
},
"decide": {
    "desc": "经营与硬决策：reversibility/card/escalate",
    "input": {"args": {"input": _s}},
    "output": {
        "reversibility": _ok(["topic", "reversibility", "cost_if_wrong",
                              "action"], topic=_s, reversibility=_s,
                             cost_if_wrong=_s, action=_s,
                             before_decide=_arr),
        "card": _ok(["reversibility", "card_fields"], reversibility=_s,
                    card_fields=_arr),
        "escalate": _ok(["must_escalate", "reasons", "human_signoff_required"],
                        must_escalate=_b, reasons=_arr,
                        human_signoff_required=_b, rule=_s),
    },
},
"redteam": {
    "desc": "反方质询：devil/crosseval/grove",
    "input": {"args": {"input": _s}},
    "output": {
        "devil": _ok(["concern_count", "levels"], concern_count=_i,
                     levels=_arr),
        "crosseval": _ok(["verdict", "action", "counts", "has_critical"],
                         verdict=_s, action=_s, counts=_obj,
                         has_critical=_b),
        "grove": _ok([],),
    },
},
"companyos": {
    "desc": "公司OS与治理：os/scorecard/ids/freeze",
    "input": {"args": {"input": _s}},
    "output": {
        "os": _ok(["components"], components=_arr),
        "scorecard": _ok(["metric_count", "red_items"], metric_count=_i,
                         red_items=_arr),
        "ids": _ok(["issue_count"], issue_count=_i),
        "freeze": _ok(["decision_type", "freeze_days", "days_elapsed",
                       "in_lock", "re_decide_allowed"], decision_type=_s,
                      freeze_days=_i, days_elapsed=_i, in_lock=_b,
                      re_decide_allowed=_b),
    },
},
"decisionlog": {
    "desc": "决策留痕与复盘：entry/conflict/retro",
    "input": {"args": {"input": _s}},
    "output": {
        "entry": _ok(["entry_fields"], entry_fields=_arr),
        "conflict": _ok(["dns_hits", "contradictions"], dns_hits=_arr,
                        contradictions=_arr),
        "retro": _ok(["trigger", "has_loss", "retro_grades"], trigger=_s,
                     has_loss=_b, retro_grades=_arr),
    },
},
"boardroom": {
    "desc": "高层汇报与创始人陪练：memo/coach",
    "input": {"args": {"input": _s}},
    "output": {
        "memo": _ok(["sections", "win_count", "miss_count"], sections=_arr,
                    win_count=_i, miss_count=_i),
        "coach": _ok(["coach_fields", "action_count"], coach_fields=_arr,
                     action_count=_i),
    },
},
}


def skill_names() -> List[str]:
    return list(CONTRACTS)


def get(skill: str) -> Dict[str, Any]:
    return CONTRACTS.get(skill, {})


def actions(skill: str) -> List[str]:
    return list(get(skill).get("output", {}).keys())


def validate_output(skill: str, action: str, result: Any) -> Dict[str, Any]:
    schema = get(skill).get("output", {}).get(action)
    if schema is None:
        return {"ok": False, "skill": skill, "action": action,
                "errors": [f"契约未定义动作 {action}（可用 {actions(skill)}）"]}
    errs = c.validate_schema(result, schema)
    return {"ok": not errs, "skill": skill, "action": action, "errors": errs,
            "schema": schema}
