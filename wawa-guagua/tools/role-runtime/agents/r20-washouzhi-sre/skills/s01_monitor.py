# -*- coding: utf-8 -*-
"""S01 可用性监控 —— 能力域 1。

整合自 louislam__uptime-kuma：监控项（http/tcp/ping/dns/port 等类型）、
心跳间隔、重试、心跳 URL、端口、请求方法。把「监控什么、多久查一次、
怎么判不可用」转成确定性校验：监控类型白名单、目标非空、间隔在合理区间、
重试次数非负、端口范围 1-65535。

关键立场：**监控项是「探测定义」不是「探测结果」**。本角色只校验监控项
结构是否成立、能否被调度器稳定探测，不代 Uptime Kuma 实际发起探测、
不判「现在通不通」（那是运行期事实，由状态页 s03 承载）。

动作：
  monitor  监控项结构校验
  uptime   可用性记录/历史校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "monitor"
DESC = "可用性监控：monitor/uptime"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("monitor", "监控项结构校验"), ("uptime", "可用性记录校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "monitor":
        return _validate_monitor(data)
    if args.action == "uptime":
        return _validate_uptime(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_monitor(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["monitor"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", monitor_id="", monitor_count=0)

    monitor_id = str(data.get("monitor_id", "")).strip()
    checks.append(_ck(bool(monitor_id), "监控项 ID 非空", "monitor.id"))

    mtype = data.get("type")
    checks.append(_ck(mtype in th["monitor_types"],
                      f"监控类型={mtype!r} 在白名单 {th['monitor_types']}",
                      "monitor.type"))

    target = str(data.get("target", "")).strip()
    checks.append(_ck(bool(target), "监控目标非空（URL/主机/端口）", "monitor.target"))

    # 心跳间隔在合理区间（外置阈值）
    interval = c._num(data.get("interval"))
    lo = c._num(th.get("interval_min", 30))
    hi = c._num(th.get("interval_max", 86400))
    checks.append(_ck(lo <= interval <= hi,
                      f"心跳间隔 {interval:g} 秒 ∈ [{lo:g},{hi:g}]",
                      "monitor.interval"))

    # 重试次数非负
    retries = c._num(data.get("retries"))
    checks.append(_ck(retries >= 0, f"重试次数 {retries:g} ≥ 0", "monitor.retries"))

    # http/https 类型须有合法 method
    if mtype in ("http", "https"):
        method = str(data.get("method", "GET")).upper()
        checks.append(_ck(method in th["methods"],
                          f"HTTP method={method!r} 在白名单 {th['methods']}",
                          "monitor.method"))
    # tcp/port 类型须有合法端口
    if mtype in ("tcp", "port"):
        port = c._num(data.get("port"))
        checks.append(_ck(1 <= port <= 65535,
                          f"端口 {port:g} ∈ [1,65535]", "monitor.port"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        monitor_id=monitor_id, monitor_count=1,
        monitor_type=mtype,
        narrative=f"监控项 {monitor_id}：类型 {mtype}，目标 {target}")


# --------------------------------------------------------------------------- #
def _validate_uptime(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["monitor"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", monitor_id="", uptime_ratio=None)

    monitor_id = str(data.get("monitor_id", "")).strip()
    checks.append(_ck(bool(monitor_id), "监控项 ID 非空", "uptime.id"))

    checks_total = c._num(data.get("checks_total"))
    checks.append(_ck(checks_total > 0,
                      f"探测总次数 > 0（实际 {checks_total:g}）", "uptime.total"))

    up = c._num(data.get("up_count"))
    checks.append(_ck(0 <= up <= checks_total,
                      f"成功次数 {up:g} ∈ [0,{checks_total:g}]", "uptime.up"))

    # 可用率在 [0,1]，由 up/checks_total 实算（不是声明什么信什么）
    ratio = c.safe_div(up, checks_total)
    declared = data.get("uptime_ratio")
    if declared is not None:
        checks.append(_ck(abs(c._num(declared) - ratio) <= 0.001,
                          f"可用率实算 {ratio} 与声明 {declared} 一致（容差 0.001）",
                          "uptime.ratio_recompute"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        monitor_id=monitor_id, uptime_ratio=ratio,
        narrative=f"监控项 {monitor_id}：可用率 {ratio}")
