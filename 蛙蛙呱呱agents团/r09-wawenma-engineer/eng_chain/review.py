# -*- coding: utf-8 -*-
"""第 10 段 Review：PR 审查清单 + 风险分级。

审查不是表态：每条清单必须有状态与风险级别，
安全与测试两项必须被显式审过，存在未闭环高风险项时整体不得通过。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)

_RISKS = ("low", "medium", "high")
_LEVELS = ("low", "medium", "high", "critical")


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    rev = brief.get("review") or {}
    art: Dict[str, Any] = {
        "artifact": "review",
        "stage": "review",
        "project": brief.get("project", ""),
        "checklist": [{"item": c.get("item", ""), "status": c.get("status", ""),
                       "risk": c.get("risk", "")}
                      for c in rev.get("checklist") or []],
        "risk_level": rev.get("risk_level", ""),
        "security_reviewed": bool(rev.get("security_reviewed")),
        "tests_reviewed": bool(rev.get("tests_reviewed")),
        "maintainability_notes": rev.get("maintainability_notes") or [],
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """审查门禁：清单≥6、全 pass、风险已分级、安全/测试已审、级别与最大风险匹配。"""
    items = art.get("checklist") or []
    level = str(art.get("risk_level", "")).lower()
    max_risk = "low"
    for it in items:
        r = str(it.get("risk", "")).lower()
        if r in _RISKS and _RISKS.index(r) > _RISKS.index(max_risk):
            max_risk = r
    level_ok = level in _LEVELS and \
        not (max_risk == "high" and level in ("low",))
    checks = [
        ck(len(items) >= 6 and all(nonempty_str(i.get("item")) for i in items),
           "PR 清单 ≥6 条", "review:checklist", "CRITICAL"),
        ck(all(i.get("status") == "pass" for i in items),
           "清单全部通过（无未闭环项）", "review:all_pass", "CRITICAL"),
        ck(all(str(i.get("risk", "")).lower() in _RISKS for i in items),
           "每条风险已分级", "review:risk_classified", "CRITICAL"),
        ck(bool(art.get("security_reviewed")),
           "安全审查已执行", "review:security_reviewed", "CRITICAL"),
        ck(bool(art.get("tests_reviewed")),
           "测试审查已执行", "review:tests_reviewed", "CRITICAL"),
        ck(level_ok, "整体风险级别与最大风险匹配", "review:risk_level", "CRITICAL"),
    ]
    return gate(checks, "review")


def render(art: Dict[str, Any]) -> str:
    rows = [[c.get("item"), c.get("status"), c.get("risk")]
            for c in art.get("checklist") or []]
    summary = (f"整体风险：**{art.get('risk_level', '')}**；"
               f"安全审查={art.get('security_reviewed')}，"
               f"测试审查={art.get('tests_reviewed')}。")
    tables = [
        "## 审查清单", "", md_table(["检查项", "状态", "风险"], rows),
        "", "## 可维护性备注", "",
        "\n".join(f"- {x}" for x in art.get("maintainability_notes") or []),
    ]
    return render_stage(art, summary, tables)
