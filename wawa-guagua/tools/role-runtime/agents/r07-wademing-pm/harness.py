#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R07 的确定性验证器层（harness）。

把「产品门禁」做成可独立运行、返回 exit code 的确定性校验，而非写进正文的
叙述。每个 validator 读输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，
`ok=false` 时返回码非 0。这是 R04 蛙挑刺做硬门禁复核的可调用入口。

用法：
    python harness.py prd        --input prd.json
    python harness.py story      --input story.json --kind user
    python harness.py demand     --input demand.json
    python harness.py decision   --input decision.json
    python harness.py northstar  --input metrics.json
    python harness.py techbrief  --input brief.json
    python harness.py experience --input card.json
    python harness.py verify     --prd prd.json --decision decision.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from skills import _common as c  # noqa: E402
from skills import (s01_discover, s02_ost, s03_prd, s06_metrics,  # noqa: E402
                    s07_techbrief, s08_decision)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "jobstory": (s01_discover, "_validate_jobstory"),
    "discover": (s01_discover, "_validate_discover"),
    "interview": (s01_discover, "_validate_interview"),
    "ost": (s02_ost, "_validate_ost"),
    "poc": (s02_ost, "_score_poc"),
    "assumption": (s02_ost, "_prioritize_assumptions"),
    "prd": (s03_prd, "_validate_prd"),
    "acceptance": (s03_prd, "_validate_acceptance"),
    "northstar": (s06_metrics, "_northstar"),
    "metrics": (s06_metrics, "_metrics"),
    "okr": (s06_metrics, "_okr"),
    "techbrief": (s07_techbrief, "_techbrief"),
    "uibrief": (s07_techbrief, "_uibrief"),
    "codetoprd": (s07_techbrief, "_codetoprd"),
    "releasegate": (s07_techbrief, "_releasegate"),
    "decision": (s08_decision, "_decision"),
    "demand": (s08_decision, "_demand"),
    "experience": (s08_decision, "_experience"),
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


def verify(prd: str, decision: str) -> dict:
    parts = {"prd": run_validator("prd", prd),
             "decision": run_validator("decision", decision)}
    ok = all(v["ok"] for v in parts.values())
    return {"ok": ok, "parts": parts, "verdict": "PASS" if ok else "FAIL"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.py", description="R07 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name, help_txt in {
        "jobstory": "JTBD Job story 门禁", "discover": "发现计划门禁",
        "interview": "访谈脚本门禁", "ost": "机会树门禁", "poc": "POC 打分门禁",
        "assumption": "假设优先级门禁", "prd": "PRD 八门禁", "acceptance": "验收门禁",
        "northstar": "北极星门禁", "metrics": "指标分层门禁", "okr": "OKR 门禁",
        "techbrief": "技术翻译门禁", "uibrief": "UI Brief 门禁",
        "codetoprd": "代码反推需求门禁", "releasegate": "发布门禁",
        "decision": "决策汇报门禁", "demand": "需求卡门禁", "experience": "经验卡门禁",
    }.items():
        pa = sp.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)

    v = sp.add_parser("verify", help="综合门禁（prd+decision）")
    v.add_argument("--prd", required=True)
    v.add_argument("--decision", required=True)

    args = p.parse_args(argv)
    if args.cmd == "verify":
        out = verify(args.prd, args.decision)
    else:
        out = run_validator(args.cmd, args.input)

    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())