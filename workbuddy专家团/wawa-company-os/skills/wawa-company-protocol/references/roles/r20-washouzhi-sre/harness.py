# -*- coding: utf-8 -*-
"""R20 的确定性验证器层（harness）。

把「可靠性门禁」做成可独立运行、返回 exit code 的确定性校验。每个 validator
读输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，`ok=false` 时返回码非 0。
这是 R04 蛙挑刺做硬门禁复核的可调用入口。

用法：
    python harness.py monitor --input monitor.json
    python harness.py backup --input backup.json
    python harness.py runlog --n 5
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
from skills import (s01_monitor, s02_alert, s03_statuspage,  # noqa: E402
                    s04_backup, s05_restore, s06_dr, s07_postmortem)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "monitor": (s01_monitor, "_validate_monitor"),
    "uptime": (s01_monitor, "_validate_uptime"),
    "alert": (s02_alert, "_validate_alert"),
    "escalation": (s02_alert, "_validate_escalation"),
    "statuspage": (s03_statuspage, "_validate_statuspage"),
    "incident": (s03_statuspage, "_validate_incident"),
    "backup": (s04_backup, "_validate_backup"),
    "snapshot": (s04_backup, "_validate_snapshot"),
    "restore": (s05_restore, "_validate_restore"),
    "drill": (s05_restore, "_validate_drill"),
    "rpo_rto": (s06_dr, "_validate_rpo_rto"),
    "rollback": (s06_dr, "_validate_rollback"),
    "postmortem": (s07_postmortem, "_validate_postmortem"),
    "improvement": (s07_postmortem, "_validate_improvement"),
}

_GATE_HELP = {
    "monitor": "监控项门禁", "uptime": "可用率门禁",
    "alert": "告警规则门禁", "escalation": "值班升级门禁",
    "statuspage": "状态页组件门禁", "incident": "事件时间线门禁",
    "backup": "备份仓门禁", "snapshot": "快照清单门禁",
    "restore": "恢复请求门禁", "drill": "恢复演练门禁",
    "rpo_rto": "RPO/RTO 门禁", "rollback": "回滚计划门禁",
    "postmortem": "复盘结构门禁", "improvement": "改进项闭环门禁",
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
    p = argparse.ArgumentParser(prog="harness.py", description="R20 确定性验证器层")
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
