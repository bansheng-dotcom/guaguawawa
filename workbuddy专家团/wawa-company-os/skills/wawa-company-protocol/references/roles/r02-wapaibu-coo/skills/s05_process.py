# -*- coding: utf-8 -*-
"""S05 流程与 SOP（能力域 5）。

来源：anthropics__knowledge-work-plugins/operations/process-doc
（SOP 四要素：inputs/steps/outputs/approvers）
+ operations/process-optimization（浪费检测：返工/等待/过度加工；
机会陈述三段式：现状→优化→量化目标；quick wins vs transformations）
+ engineering/standup（站会时间盒与发言三问）。

确定性口径：关键步骤控制点覆盖、会议时间盒、浪费识别与机会陈述全部实算。
"""
from __future__ import annotations

from typing import Any, Dict, List

from skills import _common as c

NAME = "process"
DESC = "流程与 SOP：sop/waste/meeting"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("sop", "SOP 结构门禁（四要素+关键步骤控制点）"),
                 ("waste", "流程浪费检测 + 机会陈述（现状→优化→量化目标）"),
                 ("meeting", "会议机制门禁（时间盒+三问+行动项出口）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"sop": _sop, "waste": _waste, "meeting": _meeting}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _sop(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["process"]
    steps = data.get("steps", []) or []
    checks: List[Dict[str, Any]] = []
    checks.append(c.ck(bool(str(data.get("process_name", "")).strip()),
                       "流程名", "process_name",
                       "CRITICAL" if not data.get("process_name") else "OK"))
    checks.append(c.ck(len(data.get("inputs", []) or []) >= 1, "输入清单 ≥1",
                       "inputs",
                       "HIGH" if len(data.get("inputs", []) or []) < 1 else "OK"))
    checks.append(c.ck(len(steps) >= th["min_steps"],
                       f"步骤数 {len(steps)}（≥{th['min_steps']}）", "steps",
                       "CRITICAL" if len(steps) < th["min_steps"] else "OK"))
    checks.append(c.ck(len(data.get("outputs", []) or []) >= 1, "产出清单 ≥1",
                       "outputs",
                       "HIGH" if len(data.get("outputs", []) or []) < 1 else "OK"))
    checks.append(c.ck(len(data.get("approvers", []) or []) >= 1,
                       "审批人 ≥1（SOP 必须有人把关）", "approvers",
                       "HIGH" if len(data.get("approvers", []) or []) < 1
                       else "OK"))
    control_points = 0
    critical_uncovered: List[str] = []
    for i, s in enumerate(steps):
        if not str(s.get("owner", "")).strip():
            checks.append(c.ck(False, f"步骤 {i + 1}「{s.get('name', '')}」缺 owner",
                               "step_owner", "CRITICAL", item=i))
        if not str(s.get("action", "")).strip():
            checks.append(c.ck(False, f"步骤 {i + 1}「{s.get('name', '')}」缺 action",
                               "step_action", "HIGH", item=i))
        if s.get("control_point"):
            control_points += 1
        if s.get("is_critical") and not s.get("control_point"):
            critical_uncovered.append(str(s.get("name", f"步骤{i+1}")))
            checks.append(c.ck(False, f"关键步骤「{s.get('name', '')}」无控制点"
                               "（关键步骤必须可检验）", "control_point",
                               "CRITICAL", item=i))
    ratio = round(control_points / len(steps), 3) if steps else 0.0
    if steps and ratio < th["control_point_min_ratio"] and not critical_uncovered:
        checks.append(c.ck(False, f"控制点比例 {ratio} 低于 "
                           f"{th['control_point_min_ratio']}", "cp_ratio",
                           "HIGH", ratio=ratio))
    return c.result(checks, step_count=len(steps), control_points=control_points,
                    critical_uncovered=critical_uncovered, cp_ratio=ratio,
                    next="SOP 定稿后入知识库 knowledge 沉淀")


# --------------------------------------------------------------------------- #
def _waste(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["process"]
    steps = data.get("steps", []) or []
    checks: List[Dict[str, Any]] = []
    if len(steps) < th["min_steps"]:
        return c.result([c.ck(False, f"步骤数 {len(steps)} < "
                              f"{th['min_steps']}，无从谈优化", "structure",
                              "CRITICAL")], wastes={}, opportunity="",
                        quick_wins=[], transformations=[],
                        next="先按 sop 固化流程")
    rework_steps = [s.get("name", "") for s in steps if s.get("rework")]
    long_wait = [{"name": s.get("name", ""),
                  "wait_days": s.get("wait_days", 0)}
                 for s in steps
                 if (s.get("wait_days") or 0) > th["wait_threshold_days"]]
    cp = sum(1 for s in steps if s.get("is_control_point"))
    cp_ratio = round(cp / len(steps), 3)
    overprocessing = (len(steps) > th["overprocess_step_threshold"]
                      and cp_ratio < th["control_point_min_ratio"])
    total_wait = sum(s.get("wait_days") or 0 for s in steps)
    # 机会陈述三段式：现状 → 优化 → 量化目标（确定性计算，不编数字）
    base_total = total_wait + len(steps)  # 每步基线 1 天
    reduction = sum(max(0, (s.get("wait_days") or 0) - 1) for s in steps) \
        + len(rework_steps)  # 返工步骤按消除 1 天计
    pct = round(reduction / base_total * 100) if base_total else 0
    opportunity = (f"现状：{len(steps)} 步、返工 {len(rework_steps)} 处、"
                   f"等待 {total_wait} 天 → 优化：消除返工、把等待压到 "
                   f"≤{th['wait_threshold_days']} 天 → 量化目标：周期时间 "
                   f"−{pct}%")
    checks.append(c.ck(len(rework_steps) == 0,
                       f"返工 {len(rework_steps)} 处（{rework_steps}）", "rework",
                       "HIGH" if rework_steps else "OK"))
    checks.append(c.ck(not long_wait,
                       f"长等待 {len(long_wait)} 步（>{th['wait_threshold_days']} 天）",
                       "waiting", "HIGH" if long_wait else "OK"))
    checks.append(c.ck(not overprocessing,
                       f"过度加工检测（{len(steps)} 步 · 控制点比例 {cp_ratio}）",
                       "overprocessing", "HIGH" if overprocessing else "OK"))
    quick_wins = rework_steps + [w["name"] for w in long_wait]
    transformations = ["重构流程结构（步骤/控制点重排）"] if overprocessing else []
    checks.append(c.ck(True, opportunity, "opportunity", reduction_pct=pct))
    return c.result(checks,
                    wastes={"rework": rework_steps, "waiting": long_wait,
                            "overprocessing": overprocessing,
                            "cp_ratio": cp_ratio},
                    opportunity=opportunity, quick_wins=quick_wins,
                    transformations=transformations,
                    next="quick wins 两周内落地，transformations 进季度排期")


# --------------------------------------------------------------------------- #
def _meeting(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["process"]
    mtype = data.get("meeting_type", "")
    timeboxes = th["timebox_min"]
    checks: List[Dict[str, Any]] = []
    if mtype not in timeboxes:
        return c.result([c.ck(False, f"meeting_type={mtype} 非法"
                              f"（{list(timeboxes)}）", "type", "CRITICAL")],
                        timebox=0, within_timebox=False, action_count=0,
                        coverage=0.0, next="按 daily/weekly/monthly 分类")
    timebox = timeboxes[mtype]
    duration = data.get("duration_min")
    within = isinstance(duration, (int, float)) and 0 < duration <= timebox
    checks.append(c.ck(within, f"时长 {duration} 分钟 ≤ 时间盒 {timebox}",
                       "timebox", "CRITICAL" if not within else "OK"))
    items = data.get("items", []) or []
    covered = 0
    for i, it in enumerate(items):
        missing = [q for q in th["meeting_questions"] if not str(it.get(q, "")).strip()]
        if missing:
            checks.append(c.ck(False, f"发言 {i + 1}（{it.get('speaker', '')}）缺三问:"
                              f"{missing}", "three_questions", "HIGH", item=i))
        else:
            covered += 1
    coverage = round(covered / len(items), 3) if items else 0.0
    checks.append(c.ck(bool(items), "发言清单非空", "items",
                       "CRITICAL" if not items else "OK"))
    ais = data.get("action_items", []) or []
    checks.append(c.ck(len(ais) >= th["min_action_items"],
                       f"行动项出口 {len(ais)} 条（会议必须有 owner+动作出口）",
                       "action_items",
                       "CRITICAL" if len(ais) < th["min_action_items"] else "OK"))
    for i, a in enumerate(ais):
        if not str(a.get("owner", "")).strip() or not str(a.get("due", "")).strip():
            checks.append(c.ck(False, f"行动项 {i + 1} 缺 owner/due", "ai_owner",
                               "HIGH", item=i))
    return c.result(checks, timebox=timebox, within_timebox=within,
                    action_count=len(ais), coverage=coverage,
                    next="行动项同步进 retro/action 闭环")
