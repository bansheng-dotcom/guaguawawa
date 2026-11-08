# -*- coding: utf-8 -*-
"""S03 考勤与休假 —— 能力域 3。

整合自 frappe__hrms：`hr/doctype/attendance/attendance.json`
（status = Present | Absent | On Leave | Half Day | Work From Home；employee/
attendance_date 必填）、`hr/doctype/leave_application/leave_application.json`
（status = Open | Approved | Rejected | Cancelled；from_date/to_date/
total_leave_days；half_day 半日）。把「出勤 → 请假 → 额度」转成确定性校验：
状态白名单、日期时序、请假天数实算（含半日 0.5）、额度不超余额、重叠请假检测。

关键立场：**考勤与休假是薪酬计算的输入地基**。请假天数算错 → 薪酬扣款错
（下游 s05）；请假区间重叠 → 额度被重复消耗。这两类错误在源头上拦下，比在
薪酬层补救便宜一个数量级。

动作：
  attendance  出勤记录校验
  leave       请假申请校验（时序 + 天数实算 + 额度 + 重叠）
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List

from . import _common as c

NAME = "attendance"
DESC = "考勤与休假：attendance/leave"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("attendance", help="校验出勤记录")
    a.add_argument("--input", required=True)
    b = act.add_parser("leave", help="校验请假申请")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "attendance":
        return _validate_attendance(data)
    if args.action == "leave":
        return _validate_leave(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _parse_date(s: Any):
    if not isinstance(s, str):
        return None
    s = s.strip().replace("T", " ")[:10]
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
def _validate_attendance(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["attendance"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", attendance_count=0)

    missing = [k for k in th["required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"出勤必填齐备（缺 {missing or '无'}）",
                      "attendance.required"))

    status = data.get("status")
    ok_status = status in th["statuses"]
    checks.append(_ck(ok_status, f"出勤状态={status!r} 在白名单",
                      "attendance.status"))

    adate = _parse_date(data.get("attendance_date"))
    checks.append(_ck(adate is not None, "出勤日期可解析", "attendance.date"))

    # 工作时长：半日/在家办公需合理区间（0 < hours ≤ 24）
    hours = c._num(data.get("working_hours"))
    if data.get("working_hours") is not None:
        checks.append(_ck(0 < hours <= 24,
                          f"工作时长={hours:g} 在 (0,24]", "attendance.hours"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        attendance_count=1, status=status,
        narrative=f"出勤 {data.get('employee', '?')}（{status}）{data.get('attendance_date', '?')}")


# --------------------------------------------------------------------------- #
def _validate_leave(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["leave"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", leave_count=0)

    missing = [k for k in th["required"] if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"请假必填齐备（缺 {missing or '无'}）",
                      "leave.required"))

    status = data.get("status")
    ok_status = status in th["statuses"]
    checks.append(_ck(ok_status, f"请假状态={status!r} 在白名单", "leave.status"))

    frm = _parse_date(data.get("from_date"))
    to = _parse_date(data.get("to_date"))
    checks.append(_ck(frm is not None, "起始日期可解析", "leave.from"))
    checks.append(_ck(to is not None, "结束日期可解析", "leave.to"))

    if frm and to:
        checks.append(_ck(frm <= to, "起始不晚于结束", "leave.order"))
        days = (to - frm).days + 1
        if data.get("half_day"):
            days = th["half_day_value"]
        # 声明天数必须与实算一致（口径恒等）
        declared = c._num(data.get("total_leave_days"))
        ok_identity = abs(declared - days) < 0.001
        checks.append(_ck(ok_identity,
                          f"请假天数恒等：声明 {declared:g} = 实算 {days:g}",
                          "leave.identity"))
        # 额度不超余额
        if data.get("balance_days") is not None:
            balance = c._num(data.get("balance_days"))
            checks.append(_ck(days <= balance,
                              f"请假 {days:g} 天 ≤ 余额 {balance:g} 天",
                              "leave.balance"))

    # 重叠请假检测：同一员工与其他申请的区间不得重叠
    others = data.get("other_leaves") or []
    overlaps: List[Any] = []
    if frm and to and isinstance(others, list):
        for o in others:
            if not isinstance(o, dict):
                continue
            of = _parse_date(o.get("from_date"))
            ot = _parse_date(o.get("to_date"))
            if of and ot and not (ot < frm or of > to):
                overlaps.append(o.get("id", "?"))
    checks.append(_ck(not overlaps, f"请假区间无重叠（重叠 {overlaps or '无'}）",
                      "leave.overlap"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        leave_count=1, status=status, overlap_count=len(overlaps),
        narrative=(f"请假 {data.get('employee', '?')}（{status}）"
                   f"{data.get('from_date', '?')} → {data.get('to_date', '?')}"))
