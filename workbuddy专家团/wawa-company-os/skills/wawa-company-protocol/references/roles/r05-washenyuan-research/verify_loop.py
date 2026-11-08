# -*- coding: utf-8 -*-
"""R05 verify_loop：15动作闭环矩阵（契约 × 执行 × 结构 × 评审门 四门全绿）。

每行四步验证：
1. 子进程真实运行 python agent.py <skill> <action> --input <examples 夹具>
2. contracts.validate_input + validate_output —— 契约双向校验（干净行硬门禁；
   脏行输入语义坏、允许契约放行，但输出结构必须仍合规）
3. review.review_packet —— T7 对抗评审（干净产出必须过评审；脏产出无矛盾也过）
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

# 行结构：{skill, action, input, expect_ok, full_check}
# full_check=True：契约双向校验 + 对抗评审都作为硬门禁
_CLEAN_ROWS = [
    ("research", "ledger", "research_ledger.json"),
    ("research", "report", "research_report.json"),
    ("industry", "landscape", "industry_landscape.json"),
    ("industry", "concentration", "industry_concentration.json"),
    ("competitor", "matrix", "competitor_matrix.json"),
    ("competitor", "battlecard", "competitor_battlecard.json"),
    ("business", "canvas", "business_canvas.json"),
    ("business", "monetize", "business_monetize.json"),
    ("sizing", "size", "sizing_size.json"),
    ("sizing", "sensitivity", "sizing_sensitivity.json"),
    ("scenario", "pestel", "scenario_pestel.json"),
    ("scenario", "premortem", "scenario_premortem.json"),
    ("auto", "plan", "auto_plan.json"),
    ("auto", "track", "auto_track.json"),
]
_DIRTY_ROWS = [
    ("research", "ledger", "research_ledger_dirty.json"),
    ("research", "report", "research_report_dirty.json"),
    ("industry", "landscape", "industry_landscape_dirty.json"),
    ("industry", "concentration", "industry_concentration_dirty.json"),
    ("competitor", "matrix", "competitor_matrix_dirty.json"),
    ("competitor", "battlecard", "competitor_battlecard_dirty.json"),
    ("business", "canvas", "business_canvas_dirty.json"),
    ("business", "monetize", "business_monetize_dirty.json"),
    ("sizing", "size", "sizing_size_dirty.json"),
    ("sizing", "sensitivity", "sizing_sensitivity_dirty.json"),
    ("scenario", "pestel", "scenario_pestel_dirty.json"),
    ("scenario", "premortem", "scenario_premortem_dirty.json"),
    ("auto", "plan", "auto_plan_dirty.json"),
    ("auto", "track", "auto_track_dirty.json"),
]

MATRIX: List[Dict[str, Any]] = (
    [{"skill": s, "action": a, "input": os.path.join(EX, f),
      "expect_ok": True, "full_check": True} for s, a, f in _CLEAN_ROWS]
    + [{"skill": s, "action": a, "input": os.path.join(EX, f),
        "expect_ok": False, "full_check": False} for s, a, f in _DIRTY_ROWS]
)


def _run_subprocess(skill: str, action: str, input_path: str):
    cmd = [sys.executable, "agent.py", skill, action, "--input", input_path]
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
        result, exit_code = _run_subprocess(skill, action, spec["input"])
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
        if full_check and not rv["ok"]:
            ok = False
            notes.append(f"对抗评审未过：{rv.get('failure_category')} route={rv.get('route')}")

        # 4. ok 语义
        if bool(result.get("ok")) != expect_ok:
            ok = False
            notes.append(f"ok={result.get('ok')} 与 expect_ok={expect_ok} 不符")
        want_exit = 0 if expect_ok else 1
        if exit_code != want_exit:
            ok = False
            notes.append(f"exit={exit_code} 应为 {want_exit}")

        row.update({"ok": ok, "result_ok": bool(result.get("ok")),
                    "exit": exit_code,
                    "verdict": result.get("verdict"),
                    "notes": notes})
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
        print(f"[{mark}] {row['skill']:<24} {row['input']:<36} "
              f"ok={row.get('result_ok')} verdict={row.get('verdict')}")
        for n in row.get("notes", []):
            print(f"    - {n}")
    print(f"\ntotal={out['total']} passed={out['passed']} failed={out['failed']} "
          f"verdict={out['verdict']}")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
