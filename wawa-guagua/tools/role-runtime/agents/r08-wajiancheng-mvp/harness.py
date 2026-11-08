#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R08 的确定性验证器层（harness）。

把「实现门禁」做成可独立运行、返回 exit code 的确定性校验，而非写进正文的
叙述。每个 validator 读输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，
`ok=false` 时返回码非 0。这是 R04 蛙挑刺做硬门禁复核的可调用入口。

除 14 个实现门禁外，另含：
- plan：复用 experience/plan_schema.json（实现计划契约口径）。
- runlog：读 ../workspace/runlog.jsonl 最近 n 条（经 agents/core/workspace.py）。

用法：
    python harness.py slice      --input slice.json
    python harness.py mvp        --input mvp.json
    python harness.py plan       --input plan.json
    python harness.py runlog --n 5
    python harness.py verify --mvp mvp.json --qa qa.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import _common as c  # noqa: E402
from skills import (s01_slice, s02_scaffold, s03_landing, s04_saas,  # noqa: E402
                    s05_prototype, s06_design, s07_qa)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "slice": (s01_slice, "_validate_slice"),
    "mvp": (s01_slice, "_validate_mvp"),
    "scaffold": (s02_scaffold, "_validate_scaffold"),
    "spec": (s02_scaffold, "_validate_spec"),
    "landing": (s03_landing, "_validate_landing"),
    "form": (s03_landing, "_validate_form"),
    "saas": (s04_saas, "_validate_saas"),
    "email": (s04_saas, "_validate_email"),
    "prototype": (s05_prototype, "_validate_prototype"),
    "screen": (s05_prototype, "_validate_screen"),
    "design": (s06_design, "_validate_design"),
    "token": (s06_design, "_validate_token"),
    "qa": (s07_qa, "_validate_qa"),
    "handoff": (s07_qa, "_validate_handoff"),
}

_GATE_HELP = {
    "slice": "产品切片门禁", "mvp": "MVP 设计门禁",
    "scaffold": "仓库脚手架门禁", "spec": "工程 Spec 门禁",
    "landing": "落地页门禁", "form": "表单门禁",
    "saas": "SaaS 脚手架门禁", "email": "邮件脚手架门禁",
    "prototype": "跨平台原型门禁", "screen": "单屏门禁",
    "design": "设计系统门禁", "token": "Token 门禁",
    "qa": "质量验证门禁", "handoff": "交接门禁",
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


def verify(mvp: str, qa: str) -> dict:
    parts = {"mvp": run_validator("mvp", mvp),
             "qa": run_validator("qa", qa)}
    ok = all(v["ok"] for v in parts.values())
    return {"ok": ok, "parts": parts, "verdict": "PASS" if ok else "FAIL"}


# --------------------------------------------------------------------------- #
# plan：复用 plan_schema.json
# --------------------------------------------------------------------------- #
def validate_plan(path: str) -> dict:
    with open(os.path.join(_HERE, "experience", "plan_schema.json"),
              encoding="utf-8") as f:
        schema = json.load(f)
    data = c.load_json(path)
    checks = []
    for k in schema["required_fields"]:
        checks.append(c.ck(k in data, f"计划含必填字段 {k}", f"plan:{k}",
                           "CRITICAL" if k not in data else "OK"))
    step = data.get("implementation_step")
    if step not in schema["implementation_step_enum"]:
        checks.append(c.ck(False,
                           f"implementation_step={step!r} 不在枚举 "
                           f"{schema['implementation_step_enum']}",
                           "plan:implementation_step", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"implementation_step={step}",
                           "plan:implementation_step"))
    for key, field in (("deliverables", "deliverables_required"),
                       ("acceptance_criteria", "acceptance_criteria_required"),
                       ("stop_condition", "stop_condition_required")):
        node = data.get(key)
        if isinstance(node, dict):
            missing = [f for f in schema[field] if f not in node]
            if missing:
                checks.append(c.ck(False, f"{key} 缺子字段：{missing}",
                                   f"plan:{key}", "CRITICAL"))
            else:
                checks.append(c.ck(True, f"{key} 子字段齐备", f"plan:{key}"))
        else:
            checks.append(c.ck(False, f"{key} 缺失或非对象", f"plan:{key}", "CRITICAL"))
    ok = all(ch.get("ok") for ch in checks)
    return c.result(checks, ok=ok,
                    grade="PASS" if ok else "FAIL",
                    next="实现计划合规，可执行" if ok else "计划不合规：补齐字段再执行")


# --------------------------------------------------------------------------- #
# runlog：读 ../workspace/runlog.jsonl
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
    p = argparse.ArgumentParser(prog="harness.py", description="R08 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name, help_txt in _GATE_HELP.items():
        pa = sp.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    v = sp.add_parser("verify", help="综合门禁（mvp+qa）")
    v.add_argument("--mvp", required=True)
    v.add_argument("--qa", required=True)
    pl = sp.add_parser("plan", help="实现计划门禁（plan_schema）")
    pl.add_argument("--input", required=True)
    rl = sp.add_parser("runlog", help="读取最近 n 条 runlog")
    rl.add_argument("--n", type=int, default=5)

    args = p.parse_args(argv)
    if args.cmd == "verify":
        out = verify(args.mvp, args.qa)
    elif args.cmd == "plan":
        out = validate_plan(args.input)
    elif args.cmd == "runlog":
        out = validate_runlog(args.n)
    else:
        out = run_validator(args.cmd, args.input)

    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
