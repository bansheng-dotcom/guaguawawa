# -*- coding: utf-8 -*-
"""S03 交接与验收追踪（能力域 3）。

来源：anthropics__knowledge-work-plugins/productivity/start
（新工单开工四要素：process_doc/artifact/owner/rev）
+ engineering/runbook（交接包必须带复现命令）
+ cowork 工作流（上游工件→下游字段→审计轨迹）。

确定性口径：交接包字段门禁、验收逐条 pass/fail、审计轨迹时间单调性，
事件类型白名单全部外置 thresholds.json。
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from skills import _common as c

NAME = "handoff"
DESC = "交接与验收追踪：package/accept/trace"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("package", "交接包门禁（工单四要素+复现命令+下游字段）"),
                 ("accept", "验收：逐条 pass/fail + 退回条件 + 审计事件"),
                 ("trace", "审计轨迹完整性（时间单调/事件白名单/链路闭环）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"package": _package, "accept": _accept, "trace": _trace}[args.action]
    return fn(data)


def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


# --------------------------------------------------------------------------- #
def _package(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["handoff"]
    checks: List[Dict[str, Any]] = []
    for f in th["required_fields"]:
        ok = bool(str(data.get(f, "")).strip())
        checks.append(c.ck(ok, f"工单字段 {f}", "fields",
                           "CRITICAL" if not ok else "OK", field=f))
    atype = data.get("artifact_type")
    checks.append(c.ck(atype in th["artifact_types"],
                       f"artifact_type={atype} 在白名单", "artifact_type",
                       "CRITICAL" if atype not in th["artifact_types"] else "OK"))
    repro = data.get("repro_commands", []) or []
    checks.append(c.ck(len(repro) >= th["min_repro"],
                       f"复现命令 {len(repro)} 条（交接包必须可复现，"
                       f"≥{th['min_repro']}）", "repro",
                       "CRITICAL" if len(repro) < th["min_repro"] else "OK"))
    down = data.get("downstream_fields", []) or []
    checks.append(c.ck(len(down) >= th["min_downstream"],
                       f"下游字段 {len(down)} 个", "downstream",
                       "HIGH" if len(down) < th["min_downstream"] else "OK"))
    acc = data.get("acceptance_criteria", []) or []
    checks.append(c.ck(len(acc) >= th["min_acceptance"],
                       f"验收标准 {len(acc)} 条", "acceptance",
                       "HIGH" if len(acc) < th["min_acceptance"] else "OK"))
    pid = "HP-" + _sha8(f"{data.get('artifact', '')}|{data.get('rev', '')}|"
                        f"{data.get('owner', '')}")
    checks.append(c.ck(True, f"交接包 ID {pid}", "package_id", pid=pid))
    return c.result(checks, package_id=pid,
                    artifact_type=atype, repro_count=len(repro),
                    downstream_fields=down,
                    downstream_count=len(down),
                    criteria_count=len(acc),
                    next="交接包就绪后发 accept 验收")


# --------------------------------------------------------------------------- #
def _accept(data: Any) -> Dict[str, Any]:
    criteria = data.get("criteria", [])
    checks: List[Dict[str, Any]] = []
    pid = str(data.get("package_id", "")).strip()
    checks.append(c.ck(bool(pid), "验收必须挂到交接包 ID", "package_id",
                       "CRITICAL" if not pid else "OK"))
    if not isinstance(criteria, list) or not criteria:
        return c.result(checks + [c.ck(False, "criteria 验收清单为空",
                                      "structure", "CRITICAL")],
                        verdict="FAIL", passed_count=0, failed=[],
                        audit={"type": "rejected", "reason": "验收清单为空"},
                        next="先写验收标准再验收")
    failed: List[Dict[str, Any]] = []
    passed = 0
    for i, cr in enumerate(criteria):
        ev = str(cr.get("evidence", "")).strip()
        ok = bool(cr.get("passed")) and bool(ev)
        if not ev:
            checks.append(c.ck(False, f"第 {i + 1} 条「{cr.get('criterion', '')}」"
                              "无证据（口头通过不算过）", "evidence",
                              "CRITICAL", item=i))
        if cr.get("passed") and ev:
            passed += 1
        elif not cr.get("passed"):
            failed.append({"criterion": cr.get("criterion", ""),
                           "reason": cr.get("reason", "未达标准")})
    verdict = "PASS" if (passed == len(criteria) and not failed) else "FAIL"
    checks.append(c.ck(verdict == "PASS",
                       f"验收 {passed}/{len(criteria)} 通过", "verdict",
                       "CRITICAL" if verdict == "FAIL" else "OK",
                       verdict=verdict))
    audit = {"type": "accepted" if verdict == "PASS" else "rejected",
             "package_id": pid, "passed": passed, "total": len(criteria)}
    return c.result(checks, verdict=verdict, passed_count=passed,
                    failed=failed, audit=audit,
                    next="验收 PASS 后产物归档并 trace 留痕"
                    if verdict == "PASS"
                    else "按 failed 清单退回上游重做")


# --------------------------------------------------------------------------- #
def _ts(s: Any) -> str:
    return str(s or "")


def _trace(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["handoff"]
    events = data.get("events", [])
    checks: List[Dict[str, Any]] = []
    if not isinstance(events, list) or not events:
        return c.result([c.ck(False, "events 审计轨迹为空", "structure",
                              "CRITICAL")], event_count=0, types_used=[],
                        monotonic=False, chain_complete=False,
                        next="无轨迹无法追溯")
    monotonic = True
    types_used: List[str] = []
    for i, ev in enumerate(events):
        ts = _ts(ev.get("ts"))
        try:
            if i and ts < _ts(events[i - 1].get("ts")):
                monotonic = False
                checks.append(c.ck(False, f"第 {i + 1} 条时间戳 {ts} 早于前一条"
                                   "（审计轨迹必须单调不减）", "monotonic",
                                   "CRITICAL", item=i))
        except TypeError:
            pass
        et = ev.get("type")
        if et not in th["event_types"]:
            checks.append(c.ck(False, f"第 {i + 1} 条事件类型 {et} 不在白名单",
                               "event_type", "CRITICAL", item=i))
        elif et not in types_used:
            types_used.append(et)
        if not str(ev.get("actor", "")).strip():
            checks.append(c.ck(False, f"第 {i + 1} 条事件缺 actor（谁干的）",
                               "actor", "HIGH", item=i))
    first = events[0].get("type")
    last = events[-1].get("type")
    chain_complete = first == "created" and last in ("closed", "accepted")
    checks.append(c.ck(chain_complete,
                       f"链路 {first} → {last}"
                       + ("（闭环）" if chain_complete else "（未闭环或链头非法）"),
                       "chain", "HIGH", first=first, last=last))
    return c.result(checks, event_count=len(events), types_used=types_used,
                    monotonic=monotonic, chain_complete=chain_complete,
                    next="审计轨迹随交接包归档")
