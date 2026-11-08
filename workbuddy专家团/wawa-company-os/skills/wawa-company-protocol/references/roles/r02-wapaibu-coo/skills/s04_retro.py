# -*- coding: utf-8 -*-
"""S04 复盘与事故分析（能力域 4）。

来源：anthropics__knowledge-work-plugins/engineering/incident-response
（severity×urgency 1-5 分级、sev≥4 必须 30 分钟内升级、行动项闭环）
+ R01 decisionlog 的「复盘只对预承诺标准打分、LOSS 必闭环」纪律。

确定性口径：时间线单调、分级区间、升级时限、闭环窗全部外置。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from skills import _common as c

NAME = "retro"
DESC = "复盘与事故分析：postmortem/grade/action"

_ESCALATION_TOKENS = ["升级", "通报", "escalat", "通知", "拉响"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("postmortem", "事故复盘门禁（分级/时间线/升级时限/行动项）"),
                 ("grade", "复盘五维打分（只对预承诺标准，LOSS 必闭环）"),
                 ("action", "行动项闭环追踪（过期/闭环窗/闭环率）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"postmortem": _postmortem, "grade": _grade, "action": _action}[args.action]
    return fn(data)


def _within_min(ts_a: str, ts_b: str, minutes: int) -> bool:
    try:
        dt = datetime.fromisoformat(ts_b) - datetime.fromisoformat(ts_a)
        return dt.total_seconds() <= minutes * 60
    except (ValueError, TypeError):
        return False


def _parse_ok(ts: Any) -> bool:
    try:
        datetime.fromisoformat(str(ts))
        return True
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
def _postmortem(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["retro"]
    inc = data.get("incident", {}) or {}
    timeline = data.get("timeline", []) or []
    checks: List[Dict[str, Any]] = []
    sev = inc.get("severity")
    urg = inc.get("urgency")
    for k, v in (("severity", sev), ("urgency", urg)):
        if not isinstance(v, int) or isinstance(v, bool) \
                or not (1 <= v <= th["severity_max"]):
            checks.append(c.ck(False, f"incident.{k}={v} 越界 [1,"
                               f"{th['severity_max']}]", k, "CRITICAL"))
    checks.append(c.ck(bool(str(inc.get("title", "")).strip()),
                       "事故标题", "title", "CRITICAL" if not inc.get("title")
                       else "OK"))
    # 时间线：可解析、单调
    timeline_ok = True
    for i, ev in enumerate(timeline):
        ts = ev.get("ts")
        if not _parse_ok(ts):
            timeline_ok = False
            checks.append(c.ck(False, f"第 {i + 1} 条时间戳 {ts} 不可解析",
                               "timeline", "CRITICAL", item=i))
        elif i and str(ts) < str(timeline[i - 1].get("ts")):
            timeline_ok = False
            checks.append(c.ck(False, f"第 {i + 1} 条时间戳早于前一条（时间线必须"
                               "按时间顺序重建）", "timeline", "CRITICAL",
                               item=i))
    if not timeline:
        timeline_ok = False
        checks.append(c.ck(False, "timeline 为空（复盘必须重建时间线）",
                           "timeline", "CRITICAL"))
    # 升级时限：severity ≥ 4 必须在前 30 分钟内出现升级动作
    escalated = False
    need_esc = isinstance(sev, int) and sev >= th["escalation_severity"]
    if need_esc and timeline_ok:
        first_ts = str(timeline[0].get("ts"))
        esc_events = [ev for ev in timeline
                      if c.has_any(str(ev.get("event", "")), _ESCALATION_TOKENS)]
        escalated = bool(esc_events) and _within_min(
            first_ts, str(esc_events[0].get("ts")), th["escalation_within_min"])
        if not escalated:
            checks.append(c.ck(False, f"severity={sev} ≥ {th['escalation_severity']}"
                               f" 但前 {th['escalation_within_min']} 分钟无升级/通报"
                               "动作（P0 纪律）", "escalation", "CRITICAL"))
    # 根因与促成因素
    rc = str(data.get("root_cause", "")).strip()
    checks.append(c.ck(bool(rc), "根因必须写明（无根因的复盘是走过场）",
                       "root_cause", "CRITICAL" if not rc else "OK"))
    cf = data.get("contributing_factors", []) or []
    checks.append(c.ck(len(cf) >= 1, f"促成因素 {len(cf)} 条", "contributing",
                       "HIGH" if len(cf) < 1 else "OK"))
    # 行动项：owner+due，due 在闭环窗内
    detected_at = inc.get("detected_at", "")
    action_items = data.get("action_items", []) or []
    for i, a in enumerate(action_items):
        if not str(a.get("owner", "")).strip():
            checks.append(c.ck(False, f"行动项 {i + 1} 缺 owner", "action_owner",
                               "CRITICAL", item=i))
        due = str(a.get("due", "")).strip()
        if not due:
            checks.append(c.ck(False, f"行动项 {i + 1} 缺 due（无期限=不会做）",
                               "action_due", "CRITICAL", item=i))
        elif detected_at and _parse_ok(due) and _parse_ok(detected_at):
            days = (datetime.fromisoformat(due)
                    - datetime.fromisoformat(detected_at)).days
            if days > th["closure_window_days"]:
                checks.append(c.ck(False, f"行动项 {i + 1} due 超闭环窗 "
                                   f"{th['closure_window_days']} 天（{days} 天）",
                                   "closure_window", "HIGH", item=i))
    return c.result(checks, severity=sev, urgency=urg,
                    escalated=escalated, action_count=len(action_items),
                    timeline_ok=timeline_ok,
                    next="行动项进 action 闭环追踪")


# --------------------------------------------------------------------------- #
def _grade(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["retro"]
    dims = data.get("dimensions", []) or []
    losses = data.get("losses", []) or []
    checks: List[Dict[str, Any]] = []
    required = th["dimensions"]
    got = [d.get("dim") for d in dims]
    for d in required:
        if d not in got:
            checks.append(c.ck(False, f"复盘缺「{d}」维度（五维缺一不可）",
                               "dimensions", "CRITICAL", missing=d))
    grades: List[Dict[str, Any]] = []
    for d in dims:
        met = bool(d.get("met"))
        note = str(d.get("note", "")).strip()
        if not met and not note:
            checks.append(c.ck(False, f"「{d.get('dim')}」未达标且无说明",
                               "grade_note", "HIGH", dimension=d.get("dim")))
        grades.append({"dim": d.get("dim"), "met": met, "note": note})
    pass_count = sum(1 for g in grades if g["met"])
    # LOSS 必闭环（对齐 R01 decisionlog 纪律）
    unclosed = [l.get("loss", "") for l in losses
                if not l.get("closed")]
    for l in losses:
        if not l.get("closed"):
            checks.append(c.ck(False, f"损失「{l.get('loss', '')}」未闭环"
                               "（LOSS 必须有闭环动作）", "loss_closure",
                               "CRITICAL", loss=l.get("loss", "")))
    if not dims:
        checks.append(c.ck(False, "dimensions 为空", "structure", "CRITICAL"))
    overall = "FAIL" if unclosed or not dims else (
        "PASS" if pass_count == len(grades) and pass_count else "PARTIAL")
    checks.append(c.ck(overall in ("PASS", "PARTIAL"),
                       f"复盘总评 {overall}（通过 {pass_count}/{len(grades)} 维）",
                       "overall", "CRITICAL" if overall == "FAIL" else "OK",
                       overall=overall))
    return c.result(checks, grades=grades, pass_count=pass_count,
                    overall=overall, unclosed_losses=unclosed,
                    next="总评 PARTIAL 的维度进下个周期 OKR")


# --------------------------------------------------------------------------- #
def _action(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["retro"]
    items = data.get("items", []) or []
    today = str(data.get("today", "")).strip()
    checks: List[Dict[str, Any]] = []
    if not items:
        return c.result([c.ck(False, "items 行动项清单为空", "structure",
                              "CRITICAL")], overdue=[], on_track_count=0,
                        closure_rate=0.0, next="无行动项可追踪")
    overdue: List[Dict[str, Any]] = []
    done = 0
    for i, it in enumerate(items):
        if not str(it.get("owner", "")).strip():
            checks.append(c.ck(False, f"行动项「{it.get('action', '')}」缺 owner",
                               "owner", "CRITICAL", item=i))
        due = str(it.get("due", "")).strip()
        if not due:
            checks.append(c.ck(False, f"行动项 {i + 1} 缺 due", "due",
                               "CRITICAL", item=i))
            continue
        status = str(it.get("status", "")).strip() or "planned"
        if status == "done":
            done += 1
        elif today and due < today:
            overdue.append({"action": it.get("action", ""), "owner": it.get("owner"),
                            "due": due})
            checks.append(c.ck(False, f"行动项「{it.get('action', '')}」已过期"
                               f"（due {due} < today {today}）", "overdue",
                               "CRITICAL", item=i))
    closure_rate = round(done / len(items), 3)
    checks.append(c.ck(not overdue, f"闭环率 {closure_rate*100:.0f}%"
                       f"（{done}/{len(items)}）· 过期 {len(overdue)}",
                       "closure", "CRITICAL" if overdue else "OK",
                       overdue=len(overdue)))
    return c.result(checks, overdue=overdue, on_track_count=len(items) - done,
                    closure_rate=closure_rate, done_count=done,
                    next="过期行动项当天升级到周会 IDS")
