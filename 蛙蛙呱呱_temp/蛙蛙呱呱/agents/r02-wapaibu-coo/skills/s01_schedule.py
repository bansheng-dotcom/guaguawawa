# -*- coding: utf-8 -*-
"""S01 工作拆解与排期（能力域 1）。

来源：anthropics__knowledge-work-plugins/productivity/task-management
（WBS 八类任务、step 1-10、估算 0.05-3.0 人日、先拆解后会议的优先级排期）
+ operations/capacity-plan（负载表）。

与 R01 decompose 的边界：R01 管「拆给谁」（任务卡/波次/角色路由），
本技能管「怎么排」——WBS 结构门禁、按容量逐日填充的冲刺排期、
依赖图关键路径实算（最早/最晚/浮动/关键路径）。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from skills import _common as c

NAME = "schedule"
DESC = "工作拆解与排期：wbs/sprint/critpath"

_KIND_ORDER = {"analysis": 1, "design": 2, "implementation": 3, "testing": 4,
               "deployment": 5, "documentation": 6, "management": 7,
               "maintenance": 8}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("wbs", "WBS 结构门禁（八类任务/步数/估算区间）"),
                 ("sprint", "按容量逐日填充的冲刺排期"),
                 ("critpath", "依赖图关键路径实算（环检测/浮动/关键路径）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"wbs": _wbs, "sprint": _sprint, "critpath": _critpath}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _validate_items(items: Any, th: Dict[str, Any]) -> List[Dict[str, Any]]:
    """WBS 逐项门禁（sprint 内部复用，CRITICAL 失败时禁止排期）。"""
    checks: List[Dict[str, Any]] = []
    kinds: List[str] = th["task_kinds"]
    if not isinstance(items, list) or not items:
        return [c.ck(False, "work_breakdown 缺失或为空", "structure", "CRITICAL")]
    if len(items) > th["max_items"]:
        checks.append(c.ck(False, f"拆解项 {len(items)} 超上限 {th['max_items']}",
                           "structure", "HIGH", count=len(items)))
    steps_seen: List[int] = []
    total = 0.0
    for i, it in enumerate(items):
        name = str(it.get("name", "")).strip()
        if not name:
            checks.append(c.ck(False, f"第 {i + 1} 项缺 name", "structure",
                              "CRITICAL"))
        kind = it.get("kind")
        if kind not in kinds:
            checks.append(c.ck(False, f"「{name}」kind={kind} 不在八类任务白名单",
                               "kind", "CRITICAL", item=i))
        step = it.get("step")
        if not isinstance(step, int) or isinstance(step, bool) \
                or not (th["step_min"] <= step <= th["step_max"]):
            checks.append(c.ck(False, f"「{name}」step={step} 越界 "
                               f"[{th['step_min']},{th['step_max']}]",
                               "step", "CRITICAL", item=i))
        else:
            steps_seen.append(step)
        if not str(it.get("question", "")).strip():
            checks.append(c.ck(False, f"「{name}」缺 question（这项工作回答什么）",
                               "question", "CRITICAL", item=i))
        if not str(it.get("details", "")).strip():
            checks.append(c.ck(False, f"「{name}」缺 details（产出什么）",
                               "details", "HIGH", item=i))
        cost = it.get("estimated_cost")
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) \
                or not (th["cost_min"] <= cost <= th["cost_max"]):
            checks.append(c.ck(False, f"「{name}」estimated_cost={cost} 越界 "
                               f"[{th['cost_min']},{th['cost_max']}] 人日",
                               "cost", "CRITICAL", item=i))
        else:
            total += cost
    # 步数完整连续（从 1 起、无重复、无断档）
    if steps_seen:
        uniq = sorted(steps_seen)
        expected = list(range(1, len(uniq) + 1))
        if uniq != expected:
            checks.append(c.ck(False, f"step 序列 {uniq} 不连续（应从 1 起 "
                              "逐步递增，拆解完整性）", "step", "CRITICAL"))
    checks.append(c.ck(True, f"WBS {len(items)} 项 · 合计 {round(total, 2)} 人日",
                       "summary", total=round(total, 2), count=len(items)))
    return checks


def _wbs(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["schedule"]
    items = data.get("work_breakdown", [])
    checks = _validate_items(items, th)
    kinds_used = sorted({it.get("kind") for it in items
                         if isinstance(it, dict) and it.get("kind")})
    total = sum(it.get("estimated_cost", 0) for it in items
                if isinstance(it.get("estimated_cost"), (int, float))
                and not isinstance(it.get("estimated_cost"), bool))
    return c.result(checks, task_name=data.get("task_name", ""),
                    item_count=len(items) if isinstance(items, list) else 0,
                    total_cost=round(total, 2), kinds=kinds_used,
                    max_step=max((it.get("step", 0) for it in items
                                  if isinstance(it, dict)), default=0),
                    next="WBS 通过后进入 sprint 排期")


# --------------------------------------------------------------------------- #
def _parse_date(s: Any) -> date:
    return datetime.strptime(str(s), "%Y-%m-%d").date()


def _is_cadence_day(d: date, cadence: str) -> bool:
    if cadence == "daily":
        return True
    if cadence == "weekly":
        return d.weekday() == 0  # 周一
    return d.day == 1  # monthly：每月 1 号


def _next_workday(d: date) -> date:
    while d.weekday() >= 5:  # 跳过周六日
        d += timedelta(days=1)
    return d


def _sprint(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["schedule"]
    items = data.get("work_breakdown", [])
    checks = _validate_items(items, th)
    crit_fail = [x for x in checks
                 if not x["ok"] and x.get("sev") in ("CRITICAL", "BLOCKER")]
    if crit_fail:
        return c.result(checks, schedule=[], end_date="", total_workdays=0,
                        day_count=0, utilization=[],
                        next="WBS 存在 CRITICAL，先修拆解再排期")

    cadence = data.get("cadence") or th["default_cadence"]
    cap_day = data.get("capacity_per_day") or th["capacity_per_day_default"]
    cap_day = float(cap_day)
    if cadence not in th["cadences"]:
        checks.append(c.ck(False, f"cadence={cadence} 非法（daily/weekly/monthly）",
                           "cadence", "CRITICAL"))
        return c.result(checks, schedule=[], end_date="", total_workdays=0,
                        day_count=0, utilization=[], next="修正节奏后重排")
    if cap_day <= 0:
        checks.append(c.ck(False, "capacity_per_day 必须为正", "capacity",
                           "CRITICAL"))
        return c.result(checks, schedule=[], end_date="", total_workdays=0,
                        day_count=0, utilization=[], next="修正容量后重排")
    try:
        start = _parse_date(data.get("start_date"))
    except (TypeError, ValueError):
        checks.append(c.ck(False, "start_date 缺失或格式非 YYYY-MM-DD",
                           "start_date", "CRITICAL"))
        return c.result(checks, schedule=[], end_date="", total_workdays=0,
                        day_count=0, utilization=[], next="补 start_date 后重排")
    checks.append(c.ck(True, f"节奏 {cadence} · 容量 {cap_day} 人日/天 · "
                       f"起始 {start.isoformat()}", "config"))

    # 优先级：先拆解任务（kind_order + step），management 例会只在节奏日发生
    normal = sorted([it for it in items if it.get("kind") != "management"],
                    key=lambda x: (_KIND_ORDER.get(x.get("kind"), 9),
                                   x.get("step", 0)))
    mgmt = [it for it in items if it.get("kind") == "management"]
    remaining = {id(it): float(it.get("estimated_cost", 0)) for it in normal}
    started_d: Dict[int, date] = {}
    schedule: List[Dict[str, Any]] = []
    utilization: List[float] = []
    cur = _next_workday(start)
    day_count = 0
    qi = 0  # normal 队列指针
    last_day = cur
    while qi < len(normal) or mgmt:
        today_d = cur
        day_count += 1
        last_day = today_d
        cap = cap_day
        if mgmt and _is_cadence_day(today_d, cadence):
            m = mgmt.pop(0)
            schedule.append({"name": m["name"], "kind": "management",
                             "cost": m.get("estimated_cost"),
                             "start": today_d.isoformat(),
                             "end": today_d.isoformat(), "days_spanned": 1})
            cap = round(cap - float(m.get("estimated_cost", 0)), 4)
            if cap < 0:
                cap = 0.0
        while qi < len(normal) and cap > 1e-9:
            it = normal[qi]
            rem = remaining[id(it)]
            if rem <= 1e-9:
                qi += 1
                continue
            if id(it) not in started_d:
                started_d[id(it)] = today_d
            alloc = min(rem, cap)
            remaining[id(it)] = round(rem - alloc, 4)
            cap = round(cap - alloc, 4)
            if remaining[id(it)] <= 1e-9:
                s = started_d[id(it)]
                schedule.append({"name": it["name"], "kind": it["kind"],
                                 "cost": it.get("estimated_cost"),
                                 "start": s.isoformat(),
                                 "end": today_d.isoformat(),
                                 "days_spanned": (today_d - s).days + 1})
                qi += 1
        utilization.append(round((cap_day - cap) / cap_day, 3))
        cur = _next_workday(cur + timedelta(days=1))

    checks.append(c.ck(True,
                       f"排期 {day_count} 个工作日 · 结束 {last_day.isoformat()}",
                       "schedule", workdays=day_count))
    return c.result(checks, schedule=schedule, end_date=last_day.isoformat(),
                    total_workdays=day_count, day_count=day_count,
                    utilization=utilization, capacity_per_day=cap_day,
                    cadence=cadence,
                    next="排期冻结后按 critpath 校准关键路径")


# --------------------------------------------------------------------------- #
def _critpath(data: Any) -> Dict[str, Any]:
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return c.result([c.ck(False, "tasks 缺失或为空", "structure", "CRITICAL")],
                        order=[], critpath=[], duration_days=0, slack={},
                        cycle=[], next="补任务清单")
    checks: List[Dict[str, Any]] = []
    ids = [t.get("id") for t in tasks]
    idset = set(ids)
    if len(idset) != len(ids):
        checks.append(c.ck(False, "任务 id 重复", "structure", "CRITICAL"))
    deps_ok = True
    for t in tasks:
        for d in t.get("depends_on", []) or []:
            if d not in idset:
                checks.append(c.ck(False,
                                   f"任务 {t.get('id')} 依赖不存在的 {d}",
                                   "deps", "CRITICAL"))
                deps_ok = False
        dur = t.get("duration_days")
        if not isinstance(dur, (int, float)) or isinstance(dur, bool) or dur <= 0:
            checks.append(c.ck(False,
                               f"任务 {t.get('id')} duration_days={dur} 非正",
                               "duration", "CRITICAL"))
            deps_ok = False
    adj: Dict[str, List[str]] = {t["id"]: list(t.get("depends_on", []) or [])
                                 for t in tasks}
    # DFS 环检测（沿用 R01 wave 的确定性口径）
    color: Dict[str, int] = {i: 0 for i in ids}
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
        checks.append(c.ck(False, f"依赖图存在环：{' → '.join(cycle)}",
                           "cycle", "CRITICAL", cycle=cycle))
        return c.result(checks, order=[], critpath=[], duration_days=0,
                        slack={}, cycle=cycle, next="先解环再排期")
    checks.append(c.ck(deps_ok, "依赖引用完整", "deps",
                       "CRITICAL" if not deps_ok else "OK"))

    # Kahn 拓扑 + 正向最早开始（ES/EF）
    dependents: Dict[str, List[str]] = {i: [] for i in ids}
    indeg = {i: len(adj[i]) for i in ids}
    dur = {t["id"]: float(t.get("duration_days", 0)) for t in tasks}
    for t in tasks:
        for d in t.get("depends_on", []) or []:
            dependents[d].append(t["id"])
    es: Dict[str, float] = {i: 0.0 for i in ids}
    order: List[str] = []
    q = [i for i in ids if indeg[i] == 0]
    while q:
        u = q.pop(0)
        order.append(u)
        for v in dependents[u]:
            es[v] = max(es[v], es[u] + dur[u])
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    total = max(es[i] + dur[i] for i in ids) if ids else 0.0
    # 反向最晚（LF/LS）→ 浮动：后继先于本节点处理（reversed topo）
    ls: Dict[str, float] = {}
    lf: Dict[str, float] = {}
    for u in reversed(order):
        succ = dependents[u]
        lf[u] = min((ls[v] for v in succ), default=total)
        ls[u] = lf[u] - dur[u]
    slack = {i: round(ls[i] - es[i], 2) for i in ids}
    critpath = [i for i in order if abs(slack[i]) < 1e-9]
    checks.append(c.ck(True,
                       f"关键路径 {len(critpath)} 项 · 总工期 {round(total, 2)} 天",
                       "critpath", total=round(total, 2)))
    return c.result(checks, order=order, critpath=critpath,
                    duration_days=round(total, 2), slack=slack, cycle=[],
                    next="关键路径任务优先保障，浮动任务可并行")
