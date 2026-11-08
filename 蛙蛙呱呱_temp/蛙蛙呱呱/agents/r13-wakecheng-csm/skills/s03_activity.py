# -*- coding: utf-8 -*-
"""S03 销售活动与跟进 —— 能力域 3。

整合自 twentyhq__twenty 的 `task.workspace-entity.ts` / `note` / `timeline-activity`
（活动记录 + 任务截止 + 承诺跟进）。把「跟进」从口头提醒转成确定性校验：活动类型
白名单、承诺三件套（what/owner/due）、逾期识别（宽限 1 天）、开放商机活动覆盖
（≥1 条活动，否则就是「失联商机」）。

动作：
  activity  跟进计划与活动日志（类型 + 承诺 + 逾期 + 覆盖）
  log       活动日志完整性（单条活动记录）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "activity"
DESC = "销售活动与跟进：activity/log"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("activity", help="校验跟进计划与活动日志")
    a.add_argument("--input", required=True)
    b = act.add_parser("log", help="校验单条活动记录")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "activity":
        return _validate_activity(data)
    if args.action == "log":
        return _validate_log(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def _days_overdue(due: str, grace: float) -> float:
    """确定性逾期计算：YYYY-MM-DD 与今天的日差，超过宽限期才判逾期。"""
    import datetime
    today = datetime.date.today()
    try:
        d = datetime.date.fromisoformat(str(due)[:10])
    except ValueError:
        return -1.0
    return (today - d).days - grace


# --------------------------------------------------------------------------- #
def _validate_activity(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ath = c.load_thresholds()["activity"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", activity_count=0)

    activities = data.get("activities")
    if not isinstance(activities, list):
        return c.result([_ck(False, "activities 必须为列表", "activity.list")],
                        ok=False, verdict="FAIL", activity_count=0)

    types = ath["activity_types"]
    bad_type = [a.get("type") for a in activities
                if not isinstance(a, dict) or a.get("type") not in types]
    checks.append(_ck(not bad_type, f"活动类型在白名单（越界 {bad_type or '无'}）",
                      "activity.type_enum"))

    # 承诺三件套
    no_commit = [a.get("what") for a in activities if isinstance(a, dict)
                 and any(not str(a.get(k, "")).strip() for k in ath["commitment_required"])]
    checks.append(_ck(not no_commit,
                      f"承诺三件套（what/owner/due）齐备（缺 {no_commit or '无'}）",
                      "activity.commitment"))

    # 逾期（宽限 1 天）
    overdue = [a.get("what") for a in activities if isinstance(a, dict)
               and _days_overdue(str(a.get("due", "")), ath["overdue_grace_days"]) > 0]
    checks.append(_ck(not overdue, f"无逾期承诺（逾期 {overdue or '无'}）",
                      "activity.overdue"))

    # 开放商机活动覆盖：每条开放商机至少 1 条活动
    open_opps = data.get("open_opportunities") or []
    ok_opps = isinstance(open_opps, list)
    covered: set = set()
    if ok_opps:
        for a in activities:
            if isinstance(a, dict) and a.get("opportunity"):
                covered.add(a["opportunity"])
        uncovered = [o for o in open_opps if o not in covered]
        checks.append(_ck(not uncovered, f"开放商机均有活动覆盖（缺 {uncovered or '无'}）",
                          "activity.coverage"))
    else:
        checks.append(_ck(True, "未提供开放商机清单，跳过覆盖检查", "activity.coverage"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        activity_count=len(activities),
        overdue_count=len(overdue),
        next_due=min([str(a.get("due", "")) for a in activities if isinstance(a, dict)],
                     default="无"),
        narrative=(f"活动 {len(activities)} 条、逾期 {len(overdue)} 条、"
                   f"类型覆盖 {len(set(a.get('type') for a in activities if isinstance(a, dict)))} 种"))


# --------------------------------------------------------------------------- #
def _validate_log(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ath = c.load_thresholds()["activity"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", activity_count=0)

    ok_type = data.get("type") in ath["activity_types"]
    checks.append(_ck(ok_type, f"活动类型={data.get('type')!r} 在白名单", "log.type"))

    missing = [k for k in ath["commitment_required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"承诺三件套齐备（缺 {missing or '无'}）", "log.commitment"))

    due = str(data.get("due", ""))
    ok_due = _days_overdue(due, 0) != -1.0  # -1.0 是 _days_overdue 的「不可解析」哨兵
    checks.append(_ck(ok_due, f"跟进日期可解析（{due}）", "log.due"))

    summary = str(data.get("summary", "")).strip()
    checks.append(_ck(bool(summary), "活动摘要非空", "log.summary"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    activity_count=1, type=data.get("type"),
                    narrative=f"{data.get('type')} → {data.get('what', '?')}（due {due}）")
