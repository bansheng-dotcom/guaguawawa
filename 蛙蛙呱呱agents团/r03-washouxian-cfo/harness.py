# -*- coding: utf-8 -*-
"""R03 蛙守线 harness：子进程运行 agent.py（隔离崩溃），
读取 skills/_common.emit 的 `__AGENT_RESULT__` 行。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional

AGENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent.py")
RESULT_MARK = "__AGENT_RESULT__ "


def run_agent(skill: str, action: str, input_path: str,
              timeout: int = 120) -> Optional[Dict[str, Any]]:
    """返回 dict（含 ok 等字段）；崩溃/超时返回 None。"""
    cmd = [sys.executable, AGENT, skill, action, "--input", input_path]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    for line in (p.stdout or "").splitlines():
        if line.startswith(RESULT_MARK):
            try:
                return json.loads(line[len(RESULT_MARK):])
            except ValueError:
                return None
    return None


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("skill")
    ap.add_argument("action")
    ap.add_argument("--input", required=True)
    a = ap.parse_args()
    out = run_agent(a.skill, a.action, a.input)
    print(json.dumps(out, ensure_ascii=False, indent=2) if out else "CRASH")
