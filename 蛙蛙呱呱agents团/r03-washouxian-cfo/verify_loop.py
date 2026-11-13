# -*- coding: utf-8 -*-
"""R03 蛙守线 verify_loop：逐动作「跑到绿」循环。

对 24 个动作各执行一轮：夹具 → 契约校验 → CLI 执行 → 结构校验 →
评审门（输出可评审化）。任何一步红即报 FAIL 并继续，最后汇总。
可独立运行：python verify_loop.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from skills import _common as c  # noqa: E402
import contracts  # noqa: E402

TOOL = os.path.join(HERE, "agent.py")
EX = os.path.join(HERE, "examples")
RESULT_MARK = "__AGENT_RESULT__ "

ACTIONS = [
    ("financial", "rollforward"), ("financial", "recon"),
    ("financial", "variance"),
    ("cfo", "runway"), ("cfo", "unitecon"), ("cfo", "healthcheck"),
    ("tax", "iso"), ("tax", "rmd"), ("tax", "safeharbor"),
    ("contract", "scan"), ("contract", "policy"), ("contract", "redline"),
    ("privacy", "map"), ("privacy", "dsr"), ("privacy", "minimize"),
    ("aigov", "frameworks"), ("aigov", "aiclassify"),
    ("aigov", "disclose"),
    ("audit", "retention"), ("audit", "mockaudit"), ("audit", "evidence"),
    ("risk", "kyc"), ("risk", "aml"), ("risk", "adreview"),
]


def _cli(skill, action, input_path):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, TOOL, skill, action,
                        "--input", input_path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env,
                       timeout=120)
    for line in (p.stdout or "").splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
    return None


def verify_once(skill: str, action: str) -> tuple:
    """返回 (ok, notes)。四步：契约/执行/结构/评审门。"""
    fx = os.path.join(EX, f"{skill}_{action}.json")
    if not os.path.exists(fx):
        return False, [f"夹具缺失 {fx}"]
    notes = []
    # 1) 契约
    with open(fx, encoding="utf-8") as f:
        data = json.load(f)
    errs = c.validate_schema(data, contracts.CONTRACTS[skill][action])
    if errs:
        return False, [f"契约违规 {errs[:2]}"]
    notes.append("契约 OK")
    # 2) CLI 执行
    out = _cli(skill, action, fx)
    if out is None:
        return False, ["CLI 崩溃"]
    notes.append("CLI OK")
    # 3) 结构：ok + checks[{ok,msg,dim,sev}]
    if "ok" not in out or not isinstance(out.get("checks"), list):
        return False, ["输出结构缺失"]
    for ch in out["checks"]:
        for k in ("ok", "msg", "dim", "sev"):
            if k not in ch:
                return False, [f"检查项缺 {k}"]
    notes.append(f"结构 OK（{len(out['checks'])} 检查项）")
    # 4) 评审门：输出可评审化（含量化事实 + next）
    text = json.dumps(out, ensure_ascii=False)
    if not any(ch.isdigit() for ch in text):
        return False, ["输出缺量化事实"]
    if not out.get("next"):
        return False, ["输出缺 next 行动位"]
    notes.append("评审门 OK")
    return True, notes


def run_loop(max_rounds: int = 3) -> bool:
    """循环到全绿或轮次耗尽；每轮只重跑上轮红项。"""
    pending = list(ACTIONS)
    for rnd in range(1, max_rounds + 1):
        failed = []
        for skill, action in pending:
            ok, notes = verify_once(skill, action)
            mark = "PASS" if ok else "FAIL"
            print(f"  {mark} {skill}.{action} — {'; '.join(notes)}")
            if not ok:
                failed.append((skill, action))
        if not failed:
            print(f"verify_loop 全绿（{len(ACTIONS)} 动作×契约×评审）"
                  f" @ round {rnd}")
            return True
        pending = failed
    print(f"verify_loop 仍有 {len(pending)} 动作红：{pending}")
    return False


if __name__ == "__main__":
    sys.exit(0 if run_loop() else 1)
