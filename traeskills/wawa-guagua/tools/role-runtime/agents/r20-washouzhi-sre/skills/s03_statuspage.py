# -*- coding: utf-8 -*-
"""S03 状态页与事件沟通 —— 能力域 3。

整合自 louislam__uptime-kuma 的状态页（status page）功能 + 事件沟通语义：
服务组件状态、事件时间线、对外状态信息。把「组件状态、事件时间线、对外通报」
转成确定性校验：组件状态白名单、事件状态白名单、时间线时序单调非递减、
resolved 事件必须带结束时间。

关键立场：**状态页是「对外事实」不是「内部判断」**。本角色只校验状态页
组件与事件时间线结构是否成立、能否对外如实呈现，不替业务判断「严重不严重」
（那是告警 s02 的事）。事件时间线必须单调，倒挂 = 沟通失实。

动作：
  statuspage  组件状态校验
  incident    事件时间线/通报校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "statuspage"
DESC = "状态页与事件沟通：statuspage/incident"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("statuspage", "组件状态校验"), ("incident", "事件时间线校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "statuspage":
        return _validate_statuspage(data)
    if args.action == "incident":
        return _validate_incident(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_statuspage(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["statuspage"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", component_id="", component_count=0)

    page_id = str(data.get("page_id", "")).strip()
    checks.append(_ck(bool(page_id), "状态页 ID 非空", "statuspage.id"))

    components = data.get("components") or []
    ok_comp = isinstance(components, list) and len(components) > 0
    checks.append(_ck(ok_comp,
                      f"组件 ≥1（实际 "
                      f"{len(components) if isinstance(components, list) else 0}）",
                      "statuspage.components"))

    # 每组件须含 component_id/name/status 且 status 在白名单
    bad = [i for i, cp in enumerate(components if isinstance(components, list) else [])
           if not isinstance(cp, dict)
           or not str(cp.get("component_id", "")).strip()
           or not str(cp.get("name", "")).strip()
           or cp.get("status") not in th["component_statuses"]]
    checks.append(_ck(not bad,
                      f"组件含 id/name/status(白名单)（缺 {bad or '无'}）",
                      "statuspage.required"))

    # 组件 id 唯一
    ids = [cp.get("component_id") for cp in (components if isinstance(components, list) else [])
           if isinstance(cp, dict)]
    checks.append(_ck(len(ids) == len(set(ids)),
                      "组件 ID 唯一", "statuspage.unique"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        component_id=page_id,
        component_count=len(components) if isinstance(components, list) else 0,
        narrative=f"状态页 {page_id}："
                  f"{len(components) if isinstance(components, list) else 0} 组件")


# --------------------------------------------------------------------------- #
def _validate_incident(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["statuspage"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", incident_id="", timeline_count=0)

    incident_id = str(data.get("incident_id", "")).strip()
    checks.append(_ck(bool(incident_id), "事件 ID 非空", "incident.id"))

    timeline = data.get("timeline") or []
    ok_tl = isinstance(timeline, list) and len(timeline) > 0
    checks.append(_ck(ok_tl,
                      f"时间线 ≥1（实际 "
                      f"{len(timeline) if isinstance(timeline, list) else 0}）",
                      "incident.timeline"))

    # 每节点须含 ts/status 且 status 在白名单
    bad = [i for i, e in enumerate(timeline if isinstance(timeline, list) else [])
           if not isinstance(e, dict)
           or not str(e.get("ts", "")).strip()
           or e.get("status") not in th["incident_statuses"]]
    checks.append(_ck(not bad,
                      f"时间线节点含 ts/status(白名单)（缺 {bad or '无'}）",
                      "incident.required"))

    # 时间线时序单调非递减（倒挂 = 沟通失实）
    ts_list = [str(e.get("ts", "")) for e in (timeline if isinstance(timeline, list) else [])
               if isinstance(e, dict)]
    monotonic = ts_list == sorted(ts_list)
    checks.append(_ck(monotonic,
                      "时间线时序单调非递减", "incident.monotonic"))

    # resolved 事件必须带结束时间（resolved_at 或末节点 ts）
    final_status = (timeline[-1].get("status") if isinstance(timeline, list) and timeline else None)
    if final_status == "resolved":
        has_end = bool(data.get("resolved_at")) or len(ts_list) > 0
        checks.append(_ck(has_end, "resolved 事件带结束时间", "incident.resolved_at"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        incident_id=incident_id,
        timeline_count=len(timeline) if isinstance(timeline, list) else 0,
        narrative=f"事件 {incident_id}："
                  f"{len(timeline) if isinstance(timeline, list) else 0} 节点")


def _validate_resolved_has_end(data: Any) -> bool:
    # 供 harness 复用：resolved 事件是否带结束时间
    tl = data.get("timeline") if isinstance(data, dict) else None
    if not (isinstance(tl, list) and tl):
        return False
    if tl[-1].get("status") != "resolved":
        return True
    return bool(data.get("resolved_at")) or bool(str(tl[-1].get("ts", "")).strip())
