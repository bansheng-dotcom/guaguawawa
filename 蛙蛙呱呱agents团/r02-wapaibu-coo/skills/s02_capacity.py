# -*- coding: utf-8 -*-
"""S02 容量与委派（能力域 2）。

来源：anthropics__knowledge-work-plugins/operations/capacity-plan
（负载表：可用工时=周工时-承诺工时、紧急任务 1.2 倍权重、单项目 >50% 容量红旗、
lead time 60% 开发 / 15% 发布 / 10% 高价值维护 / 15% 创新）
+ productivity/task-management（>8 小时任务必须拆、单阻塞规则、最小必要上下文）。

确定性口径：容量/委派/拆分全部实算，阈值外置 thresholds.json。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from skills import _common as c

NAME = "capacity"
DESC = "容量与委派：check/delegate/split"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("check", "容量负载表实算（紧急 1.2×/单项目 50% 红线/lead time 配比）"),
                 ("delegate", "派工包门禁（>8h 必拆/单阻塞/最小必要上下文）"),
                 ("split", ">8h 超大任务确定性拆分（口径恒等：子任务和=原任务）")):
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    fn = {"check": _check, "delegate": _delegate, "split": _split}[args.action]
    return fn(data)


# --------------------------------------------------------------------------- #
def _check(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["capacity"]
    team = data.get("team", [])
    checks: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    overloaded: List[str] = []
    red_flags: List[Dict[str, Any]] = []
    lead_time_report: Dict[str, Any] = {}
    if not isinstance(team, list) or not team:
        return c.result([c.ck(False, "team 负载表缺失或为空", "structure",
                              "CRITICAL")], rows=[], overloaded=[],
                        red_flags=[], lead_time={},
                        next="先登记每人周工时与承诺工时")
    for m in team:
        name = str(m.get("name", "")).strip()
        weekly = m.get("weekly_hours")
        committed = m.get("committed_hours") or 0
        urgent = m.get("urgent_hours") or 0
        if not name:
            checks.append(c.ck(False, "负载行缺 name", "structure", "CRITICAL"))
            continue
        if not isinstance(weekly, (int, float)) or weekly <= 0:
            checks.append(c.ck(False, f"「{name}」weekly_hours={weekly} 非正",
                               "weekly", "CRITICAL"))
            continue
        weighted = float(committed) + float(urgent) * th["urgent_weight"]
        util_pct = round(weighted / float(weekly) * 100, 1)
        available_pct = round((float(weekly) - weighted) / float(weekly) * 100, 1)
        row = {"name": name, "weekly_hours": weekly,
               "committed_hours": committed, "urgent_hours": urgent,
               "weighted_load": round(weighted, 2),
               "utilization_pct": util_pct,
               "available_pct": available_pct}
        if util_pct > th["overalloc_pct"]:
            checks.append(c.ck(False, f"「{name}」负载 {util_pct}% 超载"
                               f"（>{th['overalloc_pct']}%，需减负或再分配）",
                               "overalloc", "CRITICAL", member=name))
            overloaded.append(name)
        # 单项目占比红线
        for pj in m.get("projects", []) or []:
            ph = pj.get("hours")
            if isinstance(ph, (int, float)) and ph > 0:
                pct = ph / float(weekly) * 100
                if pct > th["single_project_cap_pct"]:
                    checks.append(c.ck(False,
                                       f"「{name}」项目「{pj.get('name')}」"
                                       f"占 {round(pct, 1)}% 容量"
                                       f"（>{th['single_project_cap_pct']}% 红线）",
                                       "single_project", "HIGH", member=name,
                                       project=pj.get("name")))
                    red_flags.append({"member": name, "project": pj.get("name"),
                                      "pct": round(pct, 1)})
        # lead time 配比（有 category 字段才启用，如实降级）
        by_cat: Dict[str, float] = {}
        for pj in m.get("projects", []) or []:
            cat = pj.get("category")
            if cat:
                by_cat[cat] = by_cat.get(cat, 0) + float(pj.get("hours", 0) or 0)
        if by_cat:
            cat_total = sum(by_cat.values())
            shares = {k: round(v / cat_total * 100, 1) for k, v in by_cat.items()}
            lead_time_report[name] = shares
            dev_share = shares.get("development", 0)
            dev_target = th["lead_time_pcts"]["development"]
            if dev_share < dev_target:
                checks.append(c.ck(False,
                                   f"「{name}」开发占比 {dev_share}% 低于 lead time "
                                   f"目标 {dev_target}%（长期交付能力受损）",
                                   "lead_time", "HIGH", member=name))
        rows.append(row)
    if not overloaded and not red_flags:
        checks.append(c.ck(True, f"负载表 {len(rows)} 人 · 无过载 · 无单项目红线",
                           "summary"))
    return c.result(checks, rows=rows, overloaded=overloaded,
                    red_flags=red_flags, lead_time=lead_time_report,
                    next="过载成员按 delegate 派工减负")


# --------------------------------------------------------------------------- #
def _delegate(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["delegate"]
    tasks = data.get("tasks", [])
    checks: List[Dict[str, Any]] = []
    packages: List[Dict[str, Any]] = []
    oversized: List[str] = []
    if not isinstance(tasks, list) or not tasks:
        return c.result([c.ck(False, "tasks 派工清单缺失或为空", "structure",
                              "CRITICAL")], packages=[], oversized=[],
                        next="先拆 WBS 再派工")
    for i, t in enumerate(tasks):
        name = str(t.get("name", "")).strip()
        owner = str(t.get("owner", "")).strip()
        hours = t.get("hours")
        blocked = t.get("blocked_by", []) or []
        must_read = t.get("must_read", []) or []
        kr = t.get("key_results", []) or []
        if not name:
            checks.append(c.ck(False, f"第 {i + 1} 项缺任务名", "structure",
                              "CRITICAL"))
            continue
        if not owner:
            checks.append(c.ck(False, f"「{name}」缺 owner（委派必须有人负责）",
                               "owner", "CRITICAL", task=name))
            continue
        if not isinstance(hours, (int, float)) or isinstance(hours, bool) or hours <= 0:
            checks.append(c.ck(False, f"「{name}」hours={hours} 非正", "hours",
                              "CRITICAL", task=name))
            continue
        if hours > th["max_task_hours"]:
            checks.append(c.ck(False, f"「{name}」{hours}h 超过 "
                               f"{th['max_task_hours']}h 上限，先 split 再派",
                               "oversize", "CRITICAL", task=name))
            oversized.append(name)
        if len(blocked) > th["max_blocked_by"]:
            checks.append(c.ck(False, f"「{name}」阻塞依赖 {len(blocked)} 个（单阻塞"
                               f"规则：≤{th['max_blocked_by']}，多阻塞先解耦）",
                               "blocked", "HIGH", task=name))
        if len(must_read) > th["max_must_read"]:
            checks.append(c.ck(False, f"「{name}」must_read {len(must_read)} 项超"
                               f"上限 {th['max_must_read']}（最小必要上下文，防"
                               "上下文淹没）", "context", "HIGH", task=name))
        if len(kr) < th["min_key_results"]:
            checks.append(c.ck(False, f"「{name}」key_results 为空（委派必须给"
                               "可度量的关键结果）", "key_results", "CRITICAL",
                               task=name))
        packages.append({"task": name, "owner": owner, "hours": hours,
                         "blocked_by": blocked, "must_read": must_read,
                         "key_results": kr,
                         "context_size": len(must_read)})
    if not oversized:
        checks.append(c.ck(True, f"派工包 {len(packages)} 份 · 全部 ≤ "
                       f"{th['max_task_hours']}h · 单阻塞 · 最小上下文",
                       "summary", packages=len(packages)))
    return c.result(checks, packages=packages, oversized=oversized,
                    next="派工包发 handoff 交接流程")


# --------------------------------------------------------------------------- #
def _split(data: Any) -> Dict[str, Any]:
    th = c.load_thresholds()["delegate"]
    t = data.get("task", {}) or {}
    checks: List[Dict[str, Any]] = []
    name = str(t.get("name", "")).strip()
    hours = t.get("hours")
    if not name:
        return c.result([c.ck(False, "task.name 缺失", "structure", "CRITICAL")],
                        subtasks=[], subtask_count=0, max_hours=0,
                        split_required=False, sum_hours=0,
                        next="补任务名后重拆")
    if not isinstance(hours, (int, float)) or isinstance(hours, bool) or hours <= 0:
        return c.result([c.ck(False, f"「{name}」hours={hours} 非正", "hours",
                              "CRITICAL")], subtasks=[], subtask_count=0,
                        max_hours=0, split_required=False, sum_hours=0,
                        next="补工时后重拆")
    max_h = th["max_task_hours"]
    if hours <= max_h:
        checks.append(c.ck(True, f"「{name}」{hours}h ≤ {max_h}h，无需拆分",
                           "size"))
        return c.result(checks, subtasks=[], subtask_count=0, max_hours=hours,
                       split_required=False, sum_hours=hours,
                       next="直接进 delegate 派工")
    n = math.ceil(hours / max_h)
    base = round(hours / n, 2)
    subtasks: List[Dict[str, Any]] = []
    allocated = 0.0
    krs = t.get("key_results", []) or []
    skills = t.get("required_skills", []) or []
    must_read = t.get("must_read", []) or []
    for i in range(1, n + 1):
        h = base if i < n else round(hours - allocated, 2)
        allocated = round(allocated + h, 2)
        subtasks.append({
            "name": f"{name}.{i}",
            "hours": h,
            "owner": t.get("owner", ""),
            "required_skills": skills,
            "blocked_by": ([f"{name}.{i - 1}"] if i > 1 else []),
            "must_read": must_read,
            "key_results": [krs[(i - 1) % len(krs)]] if krs else [],
        })
    max_actual = max(s["hours"] for s in subtasks)
    sum_actual = round(sum(s["hours"] for s in subtasks), 2)
    # 口径恒等：子任务之和必须回到原任务（对齐 R06 口径恒等门禁的纪律）
    checks.append(c.ck(abs(sum_actual - hours) < 0.011,
                       f"口径恒等：Σ子任务 {sum_actual}h == 原任务 {hours}h",
                       "identity", "CRITICAL", sum=sum_actual))
    checks.append(c.ck(max_actual <= max_h,
                       f"最大子任务 {max_actual}h ≤ {max_h}h", "size",
                       "CRITICAL", max=max_actual))
    return c.result(checks, subtasks=subtasks, subtask_count=len(subtasks),
                    max_hours=max_actual, split_required=True,
                    sum_hours=sum_actual,
                    next="子任务重新进 delegate 派工")
