# -*- coding: utf-8 -*-
"""第 9 段 Incident：时间线 + 根因 + 行动项 + SLO/错误预算。

复盘不追责，但必须有行动项；没有时间线和预算消耗的复盘只是故事。
错误预算耗尽时门禁失败：先止损与降级，再谈新功能。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    inc = brief.get("incident") or {}
    slo = inc.get("slo") or {}
    det = inc.get("detection") or {}
    art: Dict[str, Any] = {
        "artifact": "incident",
        "stage": "incident",
        "project": brief.get("project", ""),
        "title": inc.get("title", ""),
        "severity": inc.get("severity", ""),
        "timeline": [{"t": x.get("t", ""), "event": x.get("event", "")}
                     for x in inc.get("timeline") or []],
        "root_cause": inc.get("root_cause", ""),
        "actions": [{"id": a.get("id", ""), "owner": a.get("owner", ""),
                     "due": a.get("due", ""), "status": a.get("status", ""),
                     "item": a.get("item", "")}
                    for a in inc.get("actions") or []],
        "slo": {"target": slo.get("target", ""), "window": slo.get("window", ""),
                "error_budget_min": float(slo.get("error_budget_min", 0) or 0),
                "consumed_min": float(slo.get("consumed_min", 0) or 0)},
        "blameless": bool(inc.get("blameless")),
        "detection": {"mttd_min": float(det.get("mttd_min", 0) or 0),
                      "mttr_min": float(det.get("mttr_min", 0) or 0)},
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """复盘门禁：时间线≥4、根因、行动项≥2、预算未超、不追责、检测指标。"""
    slo = art.get("slo") or {}
    det = art.get("detection") or {}
    actions = art.get("actions") or []
    checks = [
        ck(len(art.get("timeline") or []) >= 4 and
           all(nonempty_str(x.get("t")) and nonempty_str(x.get("event"))
               for x in art.get("timeline") or []),
           "时间线 ≥4 个带时刻的事件", "incident:timeline", "CRITICAL"),
        ck(nonempty_str(art.get("root_cause")),
           "根因明确", "incident:root_cause", "CRITICAL"),
        ck(len(actions) >= 2 and all(nonempty_str(a.get("owner")) and
                                     nonempty_str(a.get("item")) and
                                     nonempty_str(a.get("status")) for a in actions),
           "≥2 个有负责人/状态的行动项", "incident:actions", "CRITICAL"),
        ck(nonempty_str(slo.get("target")) and slo.get("error_budget_min", 0) > 0 and
           0 <= slo.get("consumed_min", 0) <= slo.get("error_budget_min", 0),
           "SLO 目标与错误预算未超支", "incident:error_budget", "CRITICAL"),
        ck(bool(art.get("blameless")),
           "复盘不追责（blameless）", "incident:blameless", "CRITICAL"),
        ck(det.get("mttd_min", 0) > 0 and det.get("mttr_min", 0) > 0,
           "记录 MTTD/MTTR", "incident:detection", "CRITICAL"),
    ]
    return gate(checks, "incident")


def render(art: Dict[str, Any]) -> str:
    tl_rows = [[x.get("t"), x.get("event")] for x in art.get("timeline") or []]
    act_rows = [[a.get("id"), a.get("item"), a.get("owner"), a.get("due"),
                 a.get("status")] for a in art.get("actions") or []]
    slo = art.get("slo") or {}
    det = art.get("detection") or {}
    summary = (f"**{art.get('title', '')}**（{art.get('severity', '')}）\n\n"
               f"**根因**：{art.get('root_cause', '')}\n\n"
               f"SLO {slo.get('target')} / {slo.get('window')}；错误预算消耗 "
               f"{slo.get('consumed_min')} / {slo.get('error_budget_min')} 分钟；"
               f"MTTD {det.get('mttd_min')} 分，MTTR {det.get('mttr_min')} 分。")
    tables = [
        "## 时间线", "", md_table(["时刻", "事件"], tl_rows),
        "", "## 行动项", "", md_table(["ID", "事项", "负责人", "截止", "状态"], act_rows),
    ]
    return render_stage(art, summary, tables)
