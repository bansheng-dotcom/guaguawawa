"""运行器：让一个 Agent 以子进程方式调用另一个 Agent。

这是「编排器-子代理」模式的落地：编排器(r01)通过 subprocess 调用执行角色
的 agent.py，读取其标准输出(JSON)作为交接结果。Agent 之间不共享内存，
只通过进程边界 + 共享工作区协作，从而保持上下文隔离(Anthropic 反复强调
的点)。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from . import registry


def agents_root() -> str:
    """core/ 的父目录，即 agents/。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def role_dir(role_id: str) -> str:
    return os.path.join(agents_root(), registry.by_id(role_id)["dir"])


def agent_py(role_id: str) -> str:
    return os.path.join(role_dir(role_id), "agent.py")


def _load_path() -> str:
    """把 agents/ 追加到 sys.path，使子进程能 import core。"""
    return os.path.abspath(os.path.join(agents_root(), ".."))


def invoke(role_id: str, argv: List[str], cwd: Optional[str] = None,
           timeout: int = 300) -> Dict[str, Any]:
    """调用某角色的 agent.py，返回 {exit_code, stdout, stderr, json}。

    JSON 约定：agent.py 对任何子命令输出一行 `__AGENT_RESULT__ {json}`；
    若没有该标记，则整段 stdout 原样当作文本结果返回。
    """
    cmd = [sys.executable, agent_py(role_id), *argv]
    env = dict(os.environ)
    env["PYTHONPATH"] = _load_path() + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        cmd, cwd=cwd or agents_root(), capture_output=True,
        text=True, encoding="utf-8", timeout=timeout, env=env,
    )
    out = proc.stdout or ""
    result: Dict[str, Any] = {
        "exit_code": proc.returncode,
        "stdout": out,
        "stderr": proc.stderr or "",
    }
    marker = "__AGENT_RESULT__ "
    if marker in out:
        line = next(l for l in out.splitlines() if l.startswith(marker))
        try:
            result["json"] = json.loads(line[len(marker):])
        except json.JSONDecodeError:
            result["json"] = {"raw": line[len(marker):]}
    return result