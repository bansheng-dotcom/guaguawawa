# -*- coding: utf-8 -*-
"""S07 项目群与 Agent 编排（能力域 7）。

来源：anthropics__knowledge-work-plugins/operations/status-report
（项目群 RAG 状态汇总：on_track/at_risk/behind/missed → G/A/R/R）
+ safishamsi__graphify（图谱口径：边置信三态 EXTRACTED=1.0 / INFERRED 0.4-0.9 /
AMBIGUOUS 0.1-0.3、引用完整性=不许无中生有、god 节点、BFS 3 / DFS 6 深度上限、
语料规模阈值）+ 人工审批门（P0 变更/对外资金/红线事件必须 human gate）。

与 R01 decompose 的边界：R01 把 brief 拆成任务卡分波次路由（拆给谁）；
本技能对「已存在的多任务项目群」做执行编排——波次 + 审批门 + 状态汇总，
并对协作依赖图做图谱门禁（置信/完整性/规模）。
"""
from __future__ import annotations

import re
from collections import deque
from typing import Any, Dict, List

from skills import _common as c

NAME = "portfolio"
DESC = "项目群与 Agent 编排：status/plan/graph"

_ROLE_RE = re.compile(r"\br\d{2}\b")


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("status", "项目群 RAG 状态汇总 + 需创始人关注清单"),
                 ("plan", "执行编排：波次 + 人工审批门 + 每波负载"),
                 ("graph", "协作/知识图谱门禁：置信三态 + 引用完整性 + god 节点")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"status": _status, "plan": _plan, "graph": _graph}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _status(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["portfolio"]
    projects = data.get("projects", []) or []
    checks: List[Dict[str, Any]] = []
    if not projects:
        return c.result([c.ck(False, "projects 项目群清单为空", "structure",
                              "CRITICAL")], rag={}, counts={}, attention=[],
                        next="先登记项目群")
    rag: Dict[str, List[str]] = {"G": [], "A": [], "R": []}
    counts: Dict[str, int] = {s: 0 for s in th["statuses"]}
    attention: List[Dict[str, Any]] = []
    for i, p in enumerate(projects):
        name = str(p.get("name", "")).strip()
        status = p.get("status")
        if not name:
            checks.append(c.ck(False, f"第 {i + 1} 个项目缺 name", "structure",
                              "CRITICAL"))
            continue
        if status not in th["statuses"]:
            checks.append(c.ck(False, f"项目「{name}」status={status} 非法",
                               "status", "CRITICAL", project=name))
            continue
        if not str(p.get("owner", "")).strip():
            checks.append(c.ck(False, f"项目「{name}」缺 owner", "owner",
                               "CRITICAL", project=name))
            continue
        counts[status] += 1
        rag[th["rag_map"][status]].append(name)
        blockers = p.get("blockers", []) or []
        if status == "missed":
            checks.append(c.ck(False, f"项目「{name}」已 missed（已逾期，必须当场"
                               "重定范围或砍掉）", "missed", "CRITICAL",
                               project=name))
        if status in ("behind", "missed", "at_risk"):
            cross = sorted({m.group(0) for b in blockers
                            if (m := _ROLE_RE.search(str(b)))})
            attention.append({"project": name, "owner": p.get("owner", ""),
                              "status": status,
                              "blockers": blockers,
                              "cross_role_deps": cross})
    attention.sort(key=lambda a: (a["status"] != "missed",
                                  a["status"] != "behind",
                                  -len(a["blockers"]), a["project"]))
    checks.append(c.ck(True, f"项目群 {len(projects)} 个 · "
                       f"G={len(rag['G'])} A={len(rag['A'])} R={len(rag['R'])}",
                       "summary", g=len(rag["G"]), a=len(rag["A"]),
                       r=len(rag["R"])))
    return c.result(checks, rag=rag, counts=counts, attention=attention,
                    next="R 项目逐个进 IDS，跨角色依赖交 R01 调度")


# --------------------------------------------------------------------------- #
def _plan(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["portfolio"]
    tasks = data.get("tasks", []) or []
    gates = data.get("gates", []) or []
    checks: List[Dict[str, Any]] = []
    if not tasks:
        return c.result([c.ck(False, "tasks 编排清单为空", "structure",
                              "CRITICAL")], waves=[], human_gates=[], cycle=[],
                        wave_load={}, next="先有任务卡再编排")
    ids = [t.get("id") for t in tasks]
    idset = set(ids)
    if len(idset) != len(ids):
        checks.append(c.ck(False, "任务 id 重复", "structure", "CRITICAL"))
    for t in tasks:
        for d in t.get("depends_on", []) or []:
            if d not in idset:
                checks.append(c.ck(False, f"任务 {t.get('id')} 依赖不存在的 {d}",
                                   "deps", "CRITICAL"))
        if not _ROLE_RE.match(str(t.get("owner_role", ""))):
            checks.append(c.ck(False, f"任务 {t.get('id')} owner_role="
                               f"{t.get('owner_role')} 非法（r01-r20）",
                               "owner_role", "CRITICAL"))
    # 环检测（DFS，对齐 R01 wave 口径）
    adj = {t["id"]: list(t.get("depends_on", []) or []) for t in tasks}
    color = {i: 0 for i in ids}
    cycle: List[str] = []

    def dfs(node: str, stack: List[str]) -> None:
        color[node] = 1
        stack.append(node)
        for nxt in adj[node]:
            if color.get(nxt) == 1:
                cycle.extend(stack[stack.index(nxt):] + [nxt])
            elif color.get(nxt) == 0:
                dfs(nxt, stack)
        stack.pop()
        color[node] = 2

    for i in ids:
        if color[i] == 0:
            dfs(i, [])
    if cycle:
        checks.append(c.ck(False, f"依赖环：{' → '.join(cycle)}", "cycle",
                           "CRITICAL", cycle=cycle))
        return c.result(checks, waves=[], human_gates=[], cycle=cycle,
                        wave_load={}, next="先解环再编排")
    # Kahn 分波
    indeg = {i: len(adj[i]) for i in ids}
    dependents: Dict[str, List[str]] = {i: [] for i in ids}
    for t in tasks:
        for d in t.get("depends_on", []) or []:
            dependents[d].append(t["id"])
    hours = {t["id"]: float(t.get("est_hours") or 0) for t in tasks}
    remaining = set(ids)
    waves: List[List[str]] = []
    while remaining:
        ready = sorted([i for i in remaining if indeg[i] == 0])
        waves.append(ready)
        for u in ready:
            remaining.discard(u)
            for v in dependents[u]:
                indeg[v] -= 1
    # 人工审批门：P0 变更/对外资金/红线必须 human gate 且已审批
    human_gates: List[Dict[str, Any]] = []
    for g in gates:
        gtype = g.get("type")
        is_human = gtype in th["human_gate_types"]
        if gtype not in th["human_gate_types"] + ["normal"]:
            checks.append(c.ck(False, f"审批门「{g.get('name', '')}」type={gtype}"
                               " 非法", "gate_type", "CRITICAL"))
        entry = {"name": g.get("name", ""), "type": gtype,
                 "human_approval_required": is_human,
                 "approved": bool(g.get("approved")),
                 "blocks": g.get("blocks", []) or []}
        if is_human:
            human_gates.append(entry)
            if not entry["approved"]:
                checks.append(c.ck(False, f"人工审批门「{entry['name']}」"
                                   f"（{gtype}）未获批，对应波次禁止启动",
                                   "human_gate", "CRITICAL", gate=entry["name"]))
        for b in entry["blocks"]:
            if b not in idset:
                checks.append(c.ck(False, f"审批门「{entry['name']}」拦截不存在的"
                                   f"任务 {b}", "gate_blocks", "CRITICAL"))
    # 每波负载
    wave_load: Dict[str, float] = {}
    for wi, w in enumerate(waves, 1):
        load = round(sum(hours[i] for i in w), 2)
        wave_load[f"wave_{wi}"] = load
        if load > th["wave_hours_warn"]:
            checks.append(c.ck(False, f"wave_{wi} 负载 {load}h 超预警 "
                               f"{th['wave_hours_warn']}h", "wave_load", "HIGH",
                               wave=wi))
    checks.append(c.ck(True, f"编排 {len(waves)} 波 · 人工审批门 "
                       f"{len(human_gates)} 个", "summary",
                       waves=len(waves), gates=len(human_gates)))
    return c.result(checks, waves=waves, human_gates=human_gates, cycle=[],
                    wave_load=wave_load,
                    next="每波完成跑 status 汇总，异常进 retro")


# --------------------------------------------------------------------------- #
def _graph(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["portfolio"]
    nodes = data.get("nodes", []) or []
    edges = data.get("edges", []) or []
    checks: List[Dict[str, Any]] = []
    ids = [n.get("id") for n in nodes]
    idset = set(ids)
    if len(idset) != len(ids):
        checks.append(c.ck(False, "节点 id 重复", "structure", "CRITICAL"))
    if not nodes:
        return c.result([c.ck(False, "nodes 为空", "structure", "CRITICAL")],
                        node_count=0, edge_count=0, violations=[], god_nodes=[],
                        max_depth=0, next="无节点无图")
    # 引用完整性（不许无中生有）+ 置信三态打分区间
    violations: List[Dict[str, Any]] = []
    cs_rules = th["confidence_score"]
    degree: Dict[str, int] = {i: 0 for i in ids}
    for i, e in enumerate(edges):
        for side in ("from", "to"):
            if e.get(side) not in idset:
                violations.append({"edge": i, "kind": "hallucinated_ref",
                                  "msg": f"边引用不存在的节点 {e.get(side)}"})
                checks.append(c.ck(False, f"边 {i + 1} 引用不存在的节点"
                                   f"「{e.get(side)}」（无中生有 = 幻觉）",
                                   "integrity", "CRITICAL", item=i))
        conf = e.get("confidence")
        if conf not in th["confidence_types"]:
            checks.append(c.ck(False, f"边 {i + 1} confidence={conf} 非三态",
                               "confidence", "CRITICAL", item=i))
        else:
            lo, hi = cs_rules[conf]
            score = e.get("score", lo)
            if not (lo - 1e-9 <= float(score) <= hi + 1e-9):
                violations.append({"edge": i, "kind": "score_mismatch",
                                   "msg": f"{conf} 分 {score} 越界 [{lo},{hi}]"})
                checks.append(c.ck(False, f"边 {i + 1} 置信 {conf} 分 {score} "
                                   f"越界 [{lo},{hi}]", "confidence", "HIGH",
                                   item=i))
        if conf == "AMBIGUOUS" and not str(e.get("note", "")).strip():
            violations.append({"edge": i, "kind": "ambiguous_no_note",
                              "msg": "AMBIGUOUS 边必须带待确认说明"})
            checks.append(c.ck(False, f"边 {i + 1} AMBIGUOUS 无 note（诚实规则："
                               "存疑边必须写明存疑点）", "honesty", "HIGH",
                               item=i))
        if e.get("from") in degree and e.get("to") in degree:
            degree[e["from"]] += 1
            degree[e["to"]] += 1
    # god 节点：度 > 20%×节点数（且节点数 ≥ 10 才判，小图不判）
    god_nodes: List[Dict[str, Any]] = []
    if len(nodes) >= th["god_node_min_nodes"]:
        threshold = th["god_node_pct"] * len(nodes)
        for nid, deg in degree.items():
            if deg > threshold:
                god_nodes.append({"node": nid, "degree": deg,
                                  "threshold": round(threshold, 1)})
                checks.append(c.ck(False, f"节点「{nid}」度 {deg} > "
                                   f"{round(threshold, 1)}（god 节点，拆分子图"
                                   "再检索）", "god_node", "HIGH", node=nid))
    # 规模阈值 + 深度实测（BFS 3 / DFS 6 为检索建议口径）
    if len(nodes) > th["node_warn_threshold"]:
        checks.append(c.ck(False, f"节点 {len(nodes)} 超阈值 "
                           f"{th['node_warn_threshold']}（分批处理）", "scale",
                           "HIGH"))
    adj_map: Dict[str, List[str]] = {i: [] for i in ids}
    for e in edges:
        if e.get("from") in adj_map and e.get("to") in idset:
            adj_map[e["from"]].append(e["to"])
    max_depth = 0
    for start in ids:
        seen = {start}
        q: deque = deque([(start, 0)])
        while q:
            u, d = q.popleft()
            max_depth = max(max_depth, d)
            if d >= th["dfs_depth_max"]:
                continue
            for v in adj_map[u]:
                if v not in seen:
                    seen.add(v)
                    q.append((v, d + 1))
    if max_depth > th["dfs_depth_max"]:
        checks.append(c.ck(False, f"可达深度 {max_depth} > DFS 上限 "
                           f"{th['dfs_depth_max']}（检索走 BFS ≤ "
                           f"{th['bfs_depth_max']}）", "depth", "HIGH",
                           depth=max_depth))
    checks.append(c.ck(not violations,
                       f"图完整性：{len(nodes)} 节点 / {len(edges)} 边 · "
                       f"违例 {len(violations)}", "integrity",
                       "CRITICAL" if any(v["kind"] == "hallucinated_ref"
                                         for v in violations) else
                       ("HIGH" if violations else "OK")))
    return c.result(checks, node_count=len(nodes), edge_count=len(edges),
                    violations=violations, god_nodes=god_nodes,
                    max_depth=max_depth,
                    next="图谱入知识库，检索走 BFS 深度 3")
