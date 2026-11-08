# -*- coding: utf-8 -*-
"""S04 绩效与目标 —— 能力域 4。

整合自 frappe__hrms：`hr/doctype/appraisal/appraisal.json`、
`hr/doctype/appraisal_template/appraisal_template.json`、
`hr/doctype/appraisal_cycle/appraisal_cycle.json`
（status = Not Started | In Progress | Completed）、
`hr/doctype/goal/goal.json`（status = Pending | In Progress | Completed |
Archived | Closed；progress 百分制 0–100；KRA 通过 key_result 关联）。
把「目标 → 评估 → 打分」转成确定性校验：评分区间、周期状态、目标进度、
KRA 引用完整、评分与目标进度的口径一致。

关键立场：**绩效是薪酬/晋升的输入，但评分是管理动作不是数学结论**。本角色
只校验评分是否落在合法区间、目标是否可追溯，**不替人定档、不写评级结论**
（评级结论交 R01 决策 + R03 合规）。

动作：
  appraisal  绩效评估校验（周期 + 评分区间 + 打分完整）
  goal       目标校验（状态 + 进度 + KRA 引用）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "performance"
DESC = "绩效与目标：appraisal/goal"

_CYCLE_STATUSES = ["Not Started", "In Progress", "Completed"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("appraisal", "校验绩效评估"), ("goal", "校验目标")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "appraisal":
        return _validate_appraisal(data)
    if args.action == "goal":
        return _validate_goal(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_appraisal(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["appraisal"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", appraisal_count=0)

    # 周期非空且状态合法
    cycle = str(data.get("appraisal_cycle", "")).strip()
    checks.append(_ck(bool(cycle), "评估周期非空", "appraisal.cycle"))
    cycle_status = data.get("cycle_status")
    if cycle_status is not None:
        checks.append(_ck(cycle_status in _CYCLE_STATUSES,
                          f"周期状态={cycle_status!r} 在白名单",
                          "appraisal.cycle_status"))

    lo, hi = th["score_min"], th["score_max"]
    # 总分：必须在 [score_min, score_max] 内（默认 0–5）
    total = c._num(data.get("total_score"))
    checks.append(_ck(lo <= total <= hi,
                      f"总分={total:g} 在 [{lo:g},{hi:g}]", "appraisal.total_score"))

    # 各 KRA 单项分也须落区间
    kras = data.get("kras") or []
    bad_scores: List[str] = []
    if isinstance(kras, list):
        for k in kras:
            if not isinstance(k, dict):
                continue
            sc = c._num(k.get("score"))
            if not (lo <= sc <= hi):
                bad_scores.append(str(k.get("name", "?")))
    checks.append(_ck(not bad_scores,
                      f"KRA 单项分均在 [{lo:g},{hi:g}]（越界 {bad_scores or '无'}）",
                      "appraisal.kra_scores"))

    # 打分完整：若有 KRA 却缺分数，拦下
    missing_kra = [str(k.get("name", "?")) for k in kras
                   if isinstance(k, dict) and k.get("score") in (None, "")]
    checks.append(_ck(not missing_kra,
                      f"KRA 打分完整（缺 {missing_kra or '无'}）",
                      "appraisal.kra_complete"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        appraisal_count=1, cycle=cycle,
        narrative=f"评估 {data.get('employee', '?')}（周期 {cycle}）总分 {total:g}")


# --------------------------------------------------------------------------- #
def _validate_goal(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["goal"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", goal_count=0)

    status = data.get("status")
    checks.append(_ck(status in th["statuses"],
                      f"目标状态={status!r} 在白名单", "goal.status"))

    lo, hi = th["progress_min"], th["progress_max"]
    progress = c._num(data.get("progress"))
    checks.append(_ck(lo <= progress <= hi,
                      f"进度={progress:g}% 在 [{lo:g},{hi:g}]", "goal.progress"))

    # KRA 引用完整：每项须带 measurable_result 或 key_result
    kras = data.get("kras") or []
    bad_kra: List[str] = []
    if isinstance(kras, list):
        for k in kras:
            if not isinstance(k, dict):
                continue
            measurable = str(k.get("measurable_result", "")).strip()
            key_result = str(k.get("key_result", "")).strip()
            if not measurable and not key_result:
                bad_kra.append(str(k.get("name", "?")))
    checks.append(_ck(not bad_kra,
                      f"KRA 引用完整（缺量化结果 {bad_kra or '无'}）",
                      "goal.kra_ref"))

    # 目标若已完成，进度须达 100
    if status == "Completed":
        checks.append(_ck(progress >= hi,
                          f"已完成目标进度={progress:g}% 达 100", "goal.completed"))
    else:
        checks.append(_ck(True, f"{status} 态不要求满进度", "goal.completed"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        goal_count=1, status=status, progress=progress,
        narrative=f"目标 {data.get('name', '?')}（{status}）进度 {progress:g}%")


if __name__ == "__main__":
    import json
    import sys
    d = json.load(open(sys.argv[2], encoding="utf-8"))
    print(json.dumps(_validate_goal(d) if sys.argv[1] == "goal"
                     else _validate_appraisal(d), ensure_ascii=False))
