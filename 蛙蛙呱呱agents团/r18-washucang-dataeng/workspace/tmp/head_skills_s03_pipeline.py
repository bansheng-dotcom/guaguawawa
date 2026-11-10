# -*- coding: utf-8 -*-
"""S03 管道调度与编排 —— 能力域 3。

整合自 apache__airflow：DAG（有向无环图）、task 状态
（success/failed/skipped/upstream_failed/running/queued，见 airflow
models TaskInstanceState）、task 依赖边（upstream/downstream）、重试与回填
（retries/retry_delay/backfill）。把「DAG 结构 + 任务状态 + 依赖边」转成
确定性校验：DAG 无环（Kahn 拓扑）、每条边指向已声明任务、失败/上游失败拦截、
重试次数 ≤ 上限。

关键立场：**DAG 必须无环，且失败不能假装成功**。环依赖会让调度器死锁；
`failed`/`upstream_failed` 是阻断信号——任何下游任务都不该在未修复上游的情况下
继续。本角色只校验调度结构与状态，**不擅自触发回填**（回填是高风险运维动作，
红线 2，须人工授权，交 s07 审批）。

动作：
  dag     DAG 结构校验（无环 + 依赖完整性）
  run     DAG 运行状态校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "pipeline"
DESC = "管道调度与编排：dag/run"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("dag", "校验 DAG 结构"), ("run", "校验 DAG 运行状态")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "dag":
        return _validate_dag(data)
    if args.action == "run":
        return _validate_run(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _has_cycle(tasks: List[str], edges: List[List[str]]) -> bool:
    """Kahn 拓扑：能剥完则无环，剩节点即有环。"""
    indeg = {t: 0 for t in tasks}
    adj: Dict[str, List[str]] = {t: [] for t in tasks}
    for e in edges:
        if not (isinstance(e, list) and len(e) == 2):
            continue
        u, v = str(e[0]), str(e[1])
        if u in adj and v in indeg:
            adj[u].append(v)
            indeg[v] += 1
    queue = [t for t in tasks if indeg[t] == 0]
    seen = 0
    while queue:
        n = queue.pop()
        seen += 1
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    return seen < len(tasks)


# --------------------------------------------------------------------------- #
def _validate_dag(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["pipeline"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", dag_id="", task_count=0)

    dag_id = str(data.get("dag_id", "")).strip()
    checks.append(_ck(bool(dag_id), "DAG ID 非空", "dag.id"))

    tasks = [str(t) for t in (data.get("tasks") or []) if str(t).strip()]
    ok_tasks = len(tasks) > 0
    checks.append(_ck(ok_tasks, f"任务 ≥1（实际 {len(tasks)}）", "dag.tasks"))
    # 任务名唯一
    checks.append(_ck(len(tasks) == len(set(tasks)),
                      "任务名唯一", "dag.unique_tasks"))

    edges = data.get("edges") or []
    # 每条边指向已声明任务
    dangling = []
    for e in (edges if isinstance(edges, list) else []):
        if not (isinstance(e, list) and len(e) == 2):
            dangling.append(e)
            continue
        if str(e[0]) not in tasks or str(e[1]) not in tasks:
            dangling.append(e)
    checks.append(_ck(not dangling,
                      f"依赖边指向已声明任务（悬空 {dangling or '无'}）",
                      "dag.edge_integrity"))

    # DAG 无环
    cyclic = _has_cycle(tasks, edges if isinstance(edges, list) else [])
    checks.append(_ck(not cyclic, "DAG 无环（Kahn 拓扑）", "dag.acyclic"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        dag_id=dag_id, task_count=len(tasks),
        edge_count=len(edges) if isinstance(edges, list) else 0,
        narrative=f"DAG {dag_id}：{len(tasks)} 任务，"
                  f"{len(edges) if isinstance(edges, list) else 0} 条边")


# --------------------------------------------------------------------------- #
def _validate_run(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["pipeline"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", dag_id="", task_count=0)

    dag_id = str(data.get("dag_id", "")).strip()
    checks.append(_ck(bool(dag_id), "DAG ID 非空", "run.dag_id"))

    tasks = data.get("tasks") or []
    ok_tasks = isinstance(tasks, list) and len(tasks) > 0
    checks.append(_ck(ok_tasks,
                      f"任务 ≥1（实际 {len(tasks) if isinstance(tasks, list) else 0}）",
                      "run.tasks"))

    # 任务状态白名单
    bad_state = [t.get("id") for t in (tasks if isinstance(tasks, list) else [])
                 if isinstance(t, dict) and t.get("state") not in th["task_states"]]
    checks.append(_ck(not bad_state,
                      f"任务状态在白名单（越界 {bad_state or '无'}）",
                      "run.state_whitelist"))

    # 失败/上游失败拦截：任何 failed / upstream_failed 即阻断
    failed = [t.get("id") for t in (tasks if isinstance(tasks, list) else [])
              if isinstance(t, dict) and t.get("state") in ("failed", "upstream_failed")]
    checks.append(_ck(not failed,
                      f"无失败任务（失败 {failed or '无'}）", "run.no_failure"))

    # 重试次数 ≤ 上限
    max_retries = c._num(data.get("max_retries"))
    limit = c._num(th.get("default_max_retries", 3))
    checks.append(_ck(0 <= max_retries <= limit,
                      f"重试次数 {max_retries:g} ∈ [0,{limit:g}]", "run.retries"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        dag_id=dag_id, task_count=len(tasks) if isinstance(tasks, list) else 0,
        failed_count=len(failed),
        narrative=f"DAG {dag_id} 运行："
                  f"{len(tasks) if isinstance(tasks, list) else 0} 任务，失败 {len(failed)}")
