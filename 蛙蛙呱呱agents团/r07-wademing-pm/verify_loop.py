# -*- coding: utf-8 -*-
"""R07 verify_loop：29 动作闭环矩阵（契约 × 执行 × 结构 × 评审门 四门全绿）。

每行四步验证（对齐 SOP 第八节「smoke ≠ 闭环」）：
1. 子进程真实运行 python agent.py <skill> <action> --input <examples 夹具>
2. contracts.validate_input + validate_output —— 契约双向校验（干净行硬门禁；
   脏行输入语义坏、允许契约放行，但输出结构必须仍合规）
3. review.review_packet —— T7 对抗评审（干净产出必须过评审）
4. ok 语义 —— result.ok == expect_ok 且 exit code 与 expect_ok 一致

运行：python verify_loop.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import contracts                                                      # noqa: E402
import review as review_lib                                          # noqa: E402

EX = os.path.join(_HERE, "examples")

# 行结构：(skill, action, input 文件名, 额外 CLI 参数)
# 干净行：expect_ok=True，full_check=True（契约双向 + 评审全硬门禁）
_CLEAN_ROWS: List[tuple] = [
    ("discover", "jobstory", "jobstory.json", ()),
    ("discover", "discover", "discover.json", ()),
    ("discover", "interview", "interview.json", ()),
    ("ost", "ost", "ost.json", ()),
    ("ost", "poc", "poc.json", ()),
    ("ost", "assumption", "assumption.json", ()),
    ("ost", "research", "research.json", ()),
    ("prd", "prd", "prd.json", ()),
    ("prd", "story", "story_user.json", ("--kind", "user")),
    ("prd", "acceptance", "acceptance.json", ()),
    ("priority", "opportunity", "opportunity.json", ()),
    ("priority", "ice", "ice.json", ()),
    ("priority", "rice", "rice.json", ()),
    ("priority", "backlog", "backlog.json", ()),
    ("roadmap", "roadmap", "roadmap.json", ()),
    ("roadmap", "releasenotes", "releasenotes.json", ()),
    ("roadmap", "premortem", "premortem.json", ()),
    ("metrics", "northstar", "northstar.json", ()),
    ("metrics", "metrics", "metrics.json", ()),
    ("metrics", "okr", "okr.json", ()),
    ("metrics", "vision", "vision.json", ()),
    ("metrics", "canvas", "canvas.json", ()),
    ("techbrief", "techbrief", "techbrief.json", ()),
    ("techbrief", "uibrief", "uibrief.json", ()),
    ("techbrief", "codetoprd", "codetoprd.json", ()),
    ("techbrief", "releasegate", "releasegate.json", ()),
    ("decision", "decision", "decision.json", ()),
    ("decision", "demand", "demand.json", ()),
    ("decision", "experience", "experience.json", ()),
]

# 脏行：expect_ok=False，exit=1，full_check=False（只要求输出结构合规）
_DIRTY_ROWS: List[tuple] = [
    ("discover", "jobstory", "jobstory_dirty.json", ()),
    ("discover", "discover", "discover_dirty.json", ()),
    ("discover", "interview", "interview_dirty.json", ()),
    ("ost", "ost", "ost_dirty.json", ()),
    ("ost", "poc", "poc_dirty.json", ()),
    ("ost", "assumption", "assumption_dirty.json", ()),
    ("ost", "research", "research_dirty.json", ()),
    ("prd", "prd", "prd_dirty.json", ()),
    ("prd", "story", "story_user_dirty.json", ("--kind", "user")),
    ("prd", "acceptance", "acceptance_dirty.json", ()),
    ("priority", "opportunity", "opportunity_dirty.json", ()),
    ("priority", "ice", "ice_dirty.json", ()),
    ("priority", "rice", "rice_dirty.json", ()),
    ("priority", "backlog", "backlog_dirty.json", ()),
    ("roadmap", "roadmap", "roadmap_dirty.json", ()),
    ("roadmap", "releasenotes", "releasenotes_dirty.json", ()),
    ("roadmap", "premortem", "premortem_dirty.json", ()),
    ("metrics", "northstar", "northstar_dirty.json", ()),
    ("metrics", "metrics", "metrics_dirty.json", ()),
    ("metrics", "okr", "okr_dirty.json", ()),
    ("metrics", "vision", "vision_dirty.json", ()),
    ("metrics", "canvas", "canvas_dirty.json", ()),
    ("techbrief", "techbrief", "techbrief_dirty.json", ()),
    ("techbrief", "uibrief", "uibrief_dirty.json", ()),
    ("techbrief", "codetoprd", "codetoprd_dirty.json", ()),
    ("techbrief", "releasegate", "releasegate_dirty.json", ()),
    ("decision", "decision", "decision_dirty.json", ()),
    ("decision", "demand", "demand_dirty.json", ()),
    ("decision", "experience", "experience_dirty.json", ()),
]

MATRIX: List[Dict[str, Any]] = (
    [{"skill": s, "action": a, "input": os.path.join(EX, f),
      "extra": list(x), "expect_ok": True, "full_check": True}
     for s, a, f, x in _CLEAN_ROWS]
    + [{"skill": s, "action": a, "input": os.path.join(EX, f),
        "extra": list(x), "expect_ok": False, "full_check": False}
       for s, a, f, x in _DIRTY_ROWS]
)


def _run_subprocess(skill: str, action: str, input_path: str, extra: List[str]):
    cmd = [sys.executable, "agent.py", skill, action, "--input", input_path] + extra
    proc = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)
    result = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            result = json.loads(line[len("__AGENT_RESULT__ "):])
            break
    return result, proc.returncode


def run_all() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    passed = 0
    failed = 0
    for spec in MATRIX:
        skill, action = spec["skill"], spec["action"]
        expect_ok = spec["expect_ok"]
        full_check = spec["full_check"]
        row: Dict[str, Any] = {"skill": f"{skill}/{action}",
                               "input": os.path.basename(spec["input"]),
                               "expect_ok": expect_ok}
        ok = True
        notes: List[str] = []

        # 1. 子进程真实运行
        result, exit_code = _run_subprocess(skill, action, spec["input"],
                                            spec["extra"])
        if result is None:
            ok = False
            notes.append("无 __AGENT_RESULT__ 输出")
            row.update({"ok": False, "notes": notes})
            rows.append(row)
            failed += 1
            continue

        # 2. 契约双向校验（干净行硬门禁；脏行只要求输出结构合规）
        try:
            with open(spec["input"], encoding="utf-8") as f:
                input_data = json.load(f)
        except (OSError, ValueError) as e:
            ok = False
            notes.append(f"夹具不可读：{e}")
            input_data = None
        if input_data is not None:
            vi = contracts.validate_input(skill, action, input_data)
            if full_check and not vi["ok"]:
                ok = False
                notes.append(f"契约输入不合规：{vi['errors']}")
            vo = contracts.validate_output(skill, action, result)
            if not vo["ok"]:
                ok = False
                notes.append(f"契约输出不合规：{vo['errors']}")

        # 3. T7 对抗评审（干净产出必须过评审）
        rv = review_lib.review_packet({"skill": skill, "action": action,
                                       "result": result})
        if full_check and rv["verdict"] != "PASS":
            ok = False
            notes.append(f"对抗评审未过：{rv.get('failure_category')}")

        # 4. ok 语义
        if bool(result.get("ok")) != expect_ok:
            ok = False
            notes.append(f"ok={result.get('ok')} 与 expect_ok={expect_ok} 不符")
        want_exit = 0 if expect_ok else 1
        if exit_code != want_exit:
            ok = False
            notes.append(f"exit={exit_code} 应为 {want_exit}")

        row.update({"ok": ok, "result_ok": bool(result.get("ok")),
                    "exit": exit_code, "notes": notes})
        if ok:
            passed += 1
        else:
            failed += 1
        rows.append(row)

    total = len(rows)
    out = {"ok": failed == 0,
           "matrix": rows,
           "total": total,
           "passed": passed,
           "failed": failed,
           "verdict": "PASS" if failed == 0 else "FAIL",
           "next": "闭环矩阵全绿，可交付" if failed == 0
                   else "存在红行：按 notes 修复后重跑"}
    return out


def _cli() -> int:
    out = run_all()
    for row in out["matrix"]:
        mark = "OK" if row["ok"] else "XX"
        print(f"[{mark}] {row['skill']:<22} {row['input']:<28} "
              f"ok={row.get('result_ok')} exit={row.get('exit')}")
        for n in row.get("notes", []):
            print(f"    - {n}")
    print(f"\ntotal={out['total']} passed={out['passed']} failed={out['failed']} "
          f"verdict={out['verdict']}")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
