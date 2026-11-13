#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R01 的确定性验证器层（harness）。

把「CEO 门禁」做成可独立运行、返回 exit code 的确定性校验，而非写进正文的
叙述。每个 validator 读输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，
`ok=false` 时返回码非 0。这是 R04 蛙挑刺做硬门禁复核的可调用入口。

用法：
    python harness.py brief        --input brief.json
    python harness.py card        --input decision_card.json
    python harness.py crosseval   --input redteam.json
    python harness.py freeze      --input freeze.json
    python harness.py verify      --brief brief.json --card decision_card.json
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from skills import _common as c  # noqa: E402
from skills import (s01_intent, s02_decompose, s03_decide,  # noqa: E402
                    s04_redteam, s05_companyos, s06_decisionlog,
                    s07_boardroom)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "brief": (s01_intent, "_validate_brief"),
    "clarify": (s01_intent, "_clarify"),
    "triage": (s01_intent, "_triage"),
    "taskcard": (s02_decompose, "_validate_taskcard"),
    "wave": (s02_decompose, "_wave"),
    "route": (s02_decompose, "_route"),
    "reversibility": (s03_decide, "_reversibility"),
    "card": (s03_decide, "_card"),
    "escalate": (s03_decide, "_escalate"),
    "devil": (s04_redteam, "_devil"),
    "crosseval": (s04_redteam, "_crosseval"),
    "grove": (s04_redteam, "_grove"),
    "os": (s05_companyos, "_os"),
    "scorecard": (s05_companyos, "_scorecard"),
    "ids": (s05_companyos, "_ids"),
    "freeze": (s05_companyos, "_freeze"),
    "entry": (s06_decisionlog, "_entry"),
    "conflict": (s06_decisionlog, "_conflict"),
    "retro": (s06_decisionlog, "_retro"),
    "memo": (s07_boardroom, "_memo"),
    "coach": (s07_boardroom, "_coach"),
}


def _grade(checks) -> str:
    if not checks:
        return "EMPTY"
    if all(x.get("ok") for x in checks):
        return "PASS"
    if any(x.get("sev") in ("BLOCKER", "CRITICAL") and not x.get("ok")
           for x in checks):
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
    out = getattr(mod, fn)(data)
    checks = out.get("checks", [])
    out["grade"] = _grade(checks)
    out["gate"] = cmd
    return out


def verify(brief: str, card: str) -> dict:
    parts = {"brief": run_validator("brief", brief),
             "card": run_validator("card", card)}
    ok = all(v["ok"] for v in parts.values())
    return {"ok": ok, "parts": parts, "verdict": "PASS" if ok else "FAIL"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.py", description="R01 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name in _VALIDATORS:
        pa = sp.add_parser(name, help=f"{name} 门禁")
        pa.add_argument("--input", required=True)

    v = sp.add_parser("verify", help="综合门禁（brief+card）")
    v.add_argument("--brief", required=True)
    v.add_argument("--card", required=True)

    args = p.parse_args(argv)
    if args.cmd == "verify":
        out = verify(args.brief, args.card)
    else:
        out = run_validator(args.cmd, args.input)

    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
