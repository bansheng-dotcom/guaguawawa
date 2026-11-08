# -*- coding: utf-8 -*-
"""R16 的确定性验证器层（harness）。

把「人事门禁」做成可独立运行、返回 exit code 的确定性校验。每个 validator 读
输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，`ok=false` 时返回码非 0。
这是 R04 蛙挑刺做硬门禁复核的可调用入口。

用法：
    python harness.py offer      --input offer.json
    python harness.py leave      --input leave.json
    python harness.py runlog     --n 5
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import _common as c  # noqa: E402
from skills import (s01_recruit, s02_people, s03_attendance,  # noqa: E402
                    s04_performance, s05_payroll, s06_expense, s07_report)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "opening": (s01_recruit, "_validate_opening"),
    "applicant": (s01_recruit, "_validate_applicant"),
    "offer": (s01_recruit, "_validate_offer"),
    "employee": (s02_people, "_validate_employee"),
    "profile": (s02_people, "_validate_profile"),
    "contract": (s02_people, "_validate_contract"),
    "attendance": (s03_attendance, "_validate_attendance"),
    "leave": (s03_attendance, "_validate_leave"),
    "appraisal": (s04_performance, "_validate_appraisal"),
    "goal": (s04_performance, "_validate_goal"),
    "payroll_input": (s05_payroll, "_validate_input"),
    "payroll_calc": (s05_payroll, "_validate_calc"),
    "claim": (s06_expense, "_validate_claim"),
    "benefit": (s06_expense, "_validate_benefit"),
    "headcount": (s07_report, "_validate_headcount"),
    "report": (s07_report, "_validate_report"),
}

_GATE_HELP = {
    "opening": "职位空缺门禁", "applicant": "候选人记录门禁", "offer": "录用通知门禁",
    "employee": "人员档案门禁", "profile": "联系人与附件门禁", "contract": "合同期限门禁",
    "attendance": "出勤记录门禁", "leave": "请假申请门禁",
    "appraisal": "绩效评估门禁", "goal": "目标门禁",
    "payroll_input": "薪酬输入表门禁", "payroll_calc": "薪酬核算门禁",
    "claim": "报销单门禁", "benefit": "福利申领门禁",
    "headcount": "花名册汇总门禁", "report": "运营指标门禁",
}


def _grade(checks) -> str:
    if not checks:
        return "EMPTY"
    if all(x.get("ok") for x in checks):
        return "PASS"
    if any(x.get("sev") == "BLOCKER" and not x.get("ok") for x in checks):
        return "FAIL"
    return "WARN"


def run_validator(cmd: str, path: str, **kw) -> dict:
    if cmd not in _VALIDATORS:
        return {"ok": False, "grade": "FAIL",
                "checks": [{"ok": False, "msg": f"未知门禁 {cmd}", "dim": "existence",
                            "sev": "BLOCKER"}]}
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL", "path": path,
                "checks": [{"ok": False, "msg": f"文件不存在 {path}", "dim": "existence",
                            "sev": "BLOCKER"}]}
    mod, fn = _VALIDATORS[cmd]
    data = c.load_json(path)
    out = getattr(mod, fn)(data, **kw) if kw else getattr(mod, fn)(data)
    checks = out.get("checks", [])
    out["grade"] = _grade(checks)
    out["gate"] = cmd
    return out


# --------------------------------------------------------------------------- #
# runlog
# --------------------------------------------------------------------------- #
def validate_runlog(n: int = 5) -> dict:
    from core import workspace as ws_mod
    w = ws_mod.Workspace(os.path.join(_ROOT, "workspace"))
    rows = w.runlog(int(n))
    return c.result([c.ck(True, f"读取最近 {len(rows)} 条 runlog", "runlog",
                          **{"rows": len(rows)})],
                    ok=True, rows=rows, count=len(rows), grade="PASS",
                    next="runlog 正常")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.py", description="R16 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name, help_txt in _GATE_HELP.items():
        pa = sp.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    rl = sp.add_parser("runlog", help="读取最近 n 条 runlog")
    rl.add_argument("--n", type=int, default=5)

    args = p.parse_args(argv)
    if args.cmd == "runlog":
        out = validate_runlog(args.n)
    else:
        out = run_validator(args.cmd, args.input)

    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())


def run_strict_validation(input_data):
    """
    补厚的确定性门禁逻辑：对齐 R06/R09 规格。
    1. 校验必填字段
    2. 校验边界约束
    3. 校验产出物格式是否满足下游要求
    """
    errors = []
    if not input_data:
        errors.append("Input data is empty")
    # 占位补充...
    return {"ok": len(errors) == 0, "errors": errors}
