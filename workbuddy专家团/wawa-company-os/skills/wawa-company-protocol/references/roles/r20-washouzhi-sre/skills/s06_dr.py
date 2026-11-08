# -*- coding: utf-8 -*-
"""S06 灾难恢复与回滚接口 —— 能力域 6。

整合自业务连续性/灾难恢复（DR）与回滚语义：RPO（恢复点目标）、RTO
（恢复时间目标）、恢复类型（hot/warm/cold）、依赖顺序、回滚、人工决策点。
把「多快恢复、丢多少、谁先谁后、能否回滚」转成确定性校验：RPO/RTO 数值
合法（>0 且在上限内）、恢复类型白名单、依赖图无环（Kahn）、回滚计划非空。

关键立场：**灾难恢复是「预案」不是「已发生的切换」**。本角色只校验 RPO/RTO
与恢复手册结构是否成立，不擅自执行灾难切换（红线 2：不擅自灾难切换）。
依赖顺序必须无环，回滚是硬要求——没有回滚计划的恢复手册不可信。

动作：
  rpo_rto   RPO/RTO 与恢复手册校验
  rollback  回滚计划/人工决策点校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "dr"
DESC = "灾难恢复与回滚接口：rpo_rto/rollback"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("rpo_rto", "RPO/RTO 与恢复手册校验"), ("rollback", "回滚计划校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "rpo_rto":
        return _validate_rpo_rto(data)
    if args.action == "rollback":
        return _validate_rollback(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _has_cycle(nodes: List[str], edges: List[List[str]]) -> bool:
    """Kahn 拓扑：能剥完则无环，剩节点即有环。"""
    indeg = {n: 0 for n in nodes}
    adj: Dict[str, List[str]] = {n: [] for n in nodes}
    for e in edges:
        if not (isinstance(e, list) and len(e) == 2):
            continue
        u, v = str(e[0]), str(e[1])
        if u in adj and v in indeg:
            adj[u].append(v)
            indeg[v] += 1
    queue = [n for n in nodes if indeg[n] == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    return seen < len(nodes)


# --------------------------------------------------------------------------- #
def _validate_rpo_rto(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["dr"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", rpo_hours=None, rto_hours=None)

    rpo = c._num(data.get("rpo_hours"))
    rto = c._num(data.get("rto_hours"))
    checks.append(_ck(rpo > 0, f"RPO > 0（实际 {rpo:g} 小时）", "dr.rpo_positive"))
    checks.append(_ck(rto > 0, f"RTO > 0（实际 {rto:g} 小时）", "dr.rto_positive"))
    checks.append(_ck(rpo <= c._num(th.get("rpo_max_hours", 4)),
                      f"RPO {rpo:g} ≤ {c._num(th.get('rpo_max_hours', 4)):g} 小时上限",
                      "dr.rpo_max"))
    checks.append(_ck(rto <= c._num(th.get("rto_max_hours", 24)),
                      f"RTO {rto:g} ≤ {c._num(th.get('rto_max_hours', 24)):g} 小时上限",
                      "dr.rto_max"))

    rtype = data.get("recovery_type")
    checks.append(_ck(rtype in th["recovery_types"],
                      f"恢复类型={rtype!r} 在白名单 {th['recovery_types']}",
                      "dr.type"))

    # 依赖图无环（谁先谁后必须可排，环 = 无法恢复）
    nodes = [str(n) for n in (data.get("dependencies") or []) if str(n).strip()]
    edges = data.get("dependency_edges") or []
    if isinstance(edges, list) and len(edges) > 0:
        cyclic = _has_cycle(nodes, edges if isinstance(edges, list) else [])
        checks.append(_ck(not cyclic, "恢复依赖图无环（Kahn 拓扑）", "dr.acyclic"))

    # 回滚计划是硬要求
    rollback = str(data.get("rollback_plan", "")).strip()
    checks.append(_ck(bool(rollback), "回滚计划非空", "dr.rollback"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        rpo_hours=rpo, rto_hours=rto, recovery_type=rtype,
        rollback_plan=bool(rollback),
        narrative=f"恢复手册：RPO={rpo:g}h RTO={rto:g}h 类型={rtype}")


# --------------------------------------------------------------------------- #
def _validate_rollback(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["dr"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", rollback_plan="")

    plan = str(data.get("rollback_plan", "")).strip()
    checks.append(_ck(bool(plan), "回滚计划非空", "rollback.plan"))

    # 人工决策点：灾难切换/回滚是不可逆动作，必须显式声明人工决策点
    steps = data.get("steps") or []
    ok_steps = isinstance(steps, list) and len(steps) > 0
    checks.append(_ck(ok_steps,
                      f"回滚步骤 ≥1（实际 "
                      f"{len(steps) if isinstance(steps, list) else 0}）",
                      "rollback.steps"))

    decision_point = bool(data.get("human_decision_point")) or \
        bool(str(data.get("approver", "")).strip()) or bool(data.get("handoff"))
    checks.append(_ck(decision_point,
                      "回滚含人工决策点（不擅自执行灾难切换）",
                      "rollback.human_decision"))

    # 步骤顺序无环（回滚也要可排）
    if ok_steps:
        snodes = [str(s.get("step_id", i)) for i, s in enumerate(steps)
                  if isinstance(s, dict)]
        sedges = [[str(s.get("after", "")), str(s.get("step_id", ""))]
                  for s in (steps if isinstance(steps, list) else [])
                  if isinstance(s, dict) and str(s.get("after", "")).strip()]
        if any(e[0] for e in sedges):
            cyclic = _has_cycle(snodes, sedges)
            checks.append(_ck(not cyclic, "回滚步骤无环（Kahn 拓扑）", "rollback.acyclic"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        rollback_plan=plan,
        step_count=len(steps) if isinstance(steps, list) else 0,
        narrative=f"回滚计划：{len(steps) if isinstance(steps, list) else 0} 步骤")
