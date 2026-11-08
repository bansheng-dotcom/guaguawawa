# -*- coding: utf-8 -*-
"""S06 服务预约 —— 能力域 6。

整合自 alextselegidis__easyappointments 的预约模型：`application/models/
Appointments_model.php` 的必填语义（id_users_customer / id_users_provider /
id_services / start_datetime / end_datetime）+ OpenAPI 的 appointment status
（Booked 等）。把「预约记录」转成确定性校验：预约五要素、时长区间（≤240 分钟）、
起止时间合法性、状态白名单。

关键立场：**预约的「冲突」由日历系统判定，本角色只校验预约记录本身的完整性**。
起止时间倒挂（end ≤ start）是最常见的脏数据，直接判 BLOCKER。

动作：
  appointment  预约记录完整性校验
  calendar     预约日历事件校验
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List

from . import _common as c

NAME = "appointment"
DESC = "服务预约：appointment/calendar"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("appointment", help="校验预约记录")
    a.add_argument("--input", required=True)
    b = act.add_parser("calendar", help="校验预约日历事件")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "appointment":
        return _validate_appointment(data)
    if args.action == "calendar":
        return _validate_calendar(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _parse_dt(s: Any):
    """解析 YYYY-MM-DD HH:MM 或 ISO；不可解析返回 None。"""
    if not isinstance(s, str):
        return None
    s = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s[:19] if fmt == "%Y-%m-%d %H:%M:%S" else s, fmt)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
def _validate_appointment(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ath = c.load_thresholds()["appointment"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", appointment_count=0)

    missing = [k for k in ath["appointment_required"]
               if not str(data.get(k, "")).strip()]
    checks.append(_ck(not missing, f"预约五要素齐备（缺 {missing or '无'}）",
                      "appointment.required"))

    status = str(data.get("status", "")).lower()
    ok_status = status in ath["statuses"]
    checks.append(_ck(ok_status, f"预约状态={status!r} 在白名单", "appointment.status"))

    start = _parse_dt(data.get("start_datetime"))
    end = _parse_dt(data.get("end_datetime"))
    ok_start = start is not None
    ok_end = end is not None
    checks.append(_ck(ok_start, "开始时间可解析", "appointment.start"))
    checks.append(_ck(ok_end, "结束时间可解析", "appointment.end"))

    if ok_start and ok_end:
        duration = (end - start).total_seconds() / 60.0
        ok_order = duration > 0
        checks.append(_ck(ok_order, f"起止时间顺序正确（时长 {duration:.0f} 分钟）",
                          "appointment.order"))
        ok_dur = 0 < duration <= ath["max_duration_min"]
        checks.append(_ck(ok_dur,
                          f"时长 {duration:.0f} 分钟 ≤ {ath['max_duration_min']}",
                          "appointment.duration"))
    else:
        checks.append(_ck(False, "起止时间不可比较", "appointment.order"))
        checks.append(_ck(False, "时长不可判定", "appointment.duration"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        appointment_count=1, status=status,
        narrative=(f"预约 {data.get('service_id', '?')}（{status}）"
                   f"起 {data.get('start_datetime', '?')} 止 {data.get('end_datetime', '?')}"))


# --------------------------------------------------------------------------- #
def _validate_calendar(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ath = c.load_thresholds()["appointment"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", appointment_count=0)

    events = data.get("events") or data.get("appointments")
    if not isinstance(events, list) or not events:
        return c.result([_ck(False, "events 必须是非空列表", "calendar.list")],
                        ok=False, verdict="FAIL", appointment_count=0)

    # 日历事件：每条必须可解析起止，且起止顺序正确
    bad = [e.get("id", i) for i, e in enumerate(events)
           if not isinstance(e, dict) or _parse_dt(e.get("start")) is None
           or _parse_dt(e.get("end")) is None]
    checks.append(_ck(not bad, f"日历事件起止可解析（异常 {bad or '无'}）",
                      "calendar.parse"))

    bad_order = [e.get("id", i) for i, e in enumerate(events) if isinstance(e, dict)
                 and _parse_dt(e.get("start")) is not None
                 and _parse_dt(e.get("end")) is not None
                 and _parse_dt(e.get("end")) <= _parse_dt(e.get("start"))]
    checks.append(_ck(not bad_order, f"日历事件顺序正确（倒挂 {bad_order or '无'}）",
                      "calendar.order"))

    # 重叠检测（确定性）：按开始时间排序，相邻事件不重叠（缓冲 5 分钟）
    sorted_ev = sorted([e for e in events if isinstance(e, dict)
                        and _parse_dt(e.get("start")) and _parse_dt(e.get("end"))],
                       key=lambda e: _parse_dt(e.get("start")))
    overlaps: List[Any] = []
    for a, b in zip(sorted_ev, sorted_ev[1:]):
        a_end = _parse_dt(a.get("end"))
        b_start = _parse_dt(b.get("start"))
        if b_start < a_end + datetime.timedelta(minutes=ath["overlap_buffer_min"]):
            overlaps.append(b.get("id", "?"))
    checks.append(_ck(not overlaps, f"日历事件无重叠（重叠 {overlaps or '无'}）",
                      "calendar.overlap"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        appointment_count=len(events), overlap_count=len(overlaps),
        narrative=f"日历事件 {len(events)} 条、重叠 {len(overlaps)} 条")
