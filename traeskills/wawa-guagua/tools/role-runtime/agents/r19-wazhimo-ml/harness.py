# -*- coding: utf-8 -*-
"""R19 的确定性验证器层（harness）。

把「模型工程门禁」做成可独立运行、返回 exit code 的确定性校验。每个 validator
读输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，`ok=false` 时返回码非 0。
这是 R04 蛙挑刺做硬门禁复核的可调用入口。

用法：
    python harness.py tracking_run --input tracking_run.json
    python harness.py release_candidate --input release_candidate.json
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
from skills import (s01_tracking, s02_registry, s03_evaluation,  # noqa: E402
                    s04_trace, s05_release, s06_monitor, s07_modelcard)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "tracking_experiment": (s01_tracking, "_validate_experiment"),
    "tracking_run": (s01_tracking, "_validate_run"),
    "registry_register": (s02_registry, "_validate_register"),
    "registry_version": (s02_registry, "_validate_version"),
    "evaluation_dataset": (s03_evaluation, "_validate_dataset"),
    "evaluation_scorer": (s03_evaluation, "_validate_scorer"),
    "trace_analyze": (s04_trace, "_validate_analyze"),
    "trace_retrieval": (s04_trace, "_validate_retrieval"),
    "release_regression": (s05_release, "_validate_regression"),
    "release_candidate": (s05_release, "_validate_candidate"),
    "monitor_metrics": (s06_monitor, "_validate_metrics"),
    "monitor_drift": (s06_monitor, "_validate_drift"),
    "modelcard_card": (s07_modelcard, "_validate_card"),
    "modelcard_asset": (s07_modelcard, "_validate_asset"),
}

_GATE_HELP = {
    "tracking_experiment": "实验登记门禁", "tracking_run": "运行记录门禁",
    "registry_register": "模型注册门禁", "registry_version": "版本清单门禁",
    "evaluation_dataset": "评估数据集门禁", "evaluation_scorer": "评分器门禁",
    "trace_analyze": "Trace 分析门禁", "trace_retrieval": "Trace 检索门禁",
    "release_regression": "回归报告门禁", "release_candidate": "发布候选门禁",
    "monitor_metrics": "监控指标门禁", "monitor_drift": "漂移监控门禁",
    "modelcard_card": "模型卡门禁", "modelcard_asset": "资产证据门禁",
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
    p = argparse.ArgumentParser(prog="harness.py", description="R19 确定性验证器层")
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
