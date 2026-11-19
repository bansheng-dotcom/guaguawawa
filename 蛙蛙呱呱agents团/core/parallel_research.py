# -*- coding: utf-8 -*-
"""core.parallel_research —— 16 张角色卡并行调研。

职责边界：
- 本模块只负责「发提示词 + 并行调外部执行器 + 收集 claims」；
- 执行器由 `--worker-cmd`（或环境变量 `GUAGUA_WORKER_CMD`）提供，
  不内置任何模型，也不伪造调研结果；
- 不传 worker 时只生成 `PROMPT.md` 与 `research_plan.json`（plan 模式）。

worker 命令占位符：
  {role} {card_dir} {prompt} {claims}
也可读同名环境变量：GUAGUA_ROLE / GUAGUA_CARD_DIR /
GUAGUA_PROMPT / GUAGUA_CLAIMS。
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional


def _cards(base: Path) -> List[Path]:
    return sorted(d for d in (base / "cards").glob("*")
                  if d.is_dir() and (d / "TASK.md").is_file()
                  and not d.name.startswith("_"))


def prepare(out_dir: str, only: Optional[List[str]] = None) -> Dict[str, Any]:
    """给每张卡写一份自包含 PROMPT.md，返回并行计划。"""
    base = Path(out_dir)
    brief_md = base / "brief.md"
    roles = []
    for d in _cards(base):
        if only and d.name not in only:
            continue
        task = (d / "TASK.md").read_text(encoding="utf-8")
        parts = [task.rstrip(), "", "---", "",
                 "## 完整研究契约（必读）", "",
                 brief_md.read_text(encoding="utf-8") if brief_md.is_file() else "",
                 "", "## 交回路径", "",
                 f"- 只写这一个文件：`{(d / 'claims.json').resolve()}`",
                 f"- 格式：`{(d / 'claims.template.json').resolve()}`",
                 "- 缺 url / date / quote（≥12 字）的来源整张卡会被拒收。"]
        (d / "PROMPT.md").write_text("\n".join(parts), encoding="utf-8")
        roles.append({"role": d.name, "card_dir": str(d.resolve()),
                      "prompt": str((d / "PROMPT.md").resolve()),
                      "claims": str((d / "claims.json").resolve())})
    plan = {"ok": True, "mode": "plan", "roles": roles, "count": len(roles)}
    (base / "research_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def _command(worker_cmd: str, item: Dict[str, str]) -> List[str]:
    cmd = worker_cmd.format(**item)
    toks = shlex.split(cmd, posix=False)
    # Windows 下 posix=False 会保留外层引号，直接传给 CreateProcess 会找不到文件
    return [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "'\"" else t
            for t in toks]


def _one(worker_cmd: str, item: Dict[str, str], timeout: int) -> Dict[str, Any]:
    t0 = time.time()
    env = dict(os.environ)
    env.update({"GUAGUA_ROLE": item["role"], "GUAGUA_CARD_DIR": item["card_dir"],
                "GUAGUA_PROMPT": item["prompt"], "GUAGUA_CLAIMS": item["claims"],
                "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    try:
        proc = subprocess.run(_command(worker_cmd, item), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=env)
        rc, err = proc.returncode, (proc.stderr or "")[-400:]
    except subprocess.TimeoutExpired:
        rc, err = 124, f"timeout {timeout}s"
    except Exception as e:  # noqa: BLE001
        rc, err = 125, f"{type(e).__name__}: {e}"
    return {"role": item["role"], "exit_code": rc,
            "claims_exists": Path(item["claims"]).is_file(),
            "elapsed_s": round(time.time() - t0, 1), "stderr": err}


def run(out_dir: str, worker_cmd: Optional[str], workers: int = 8,
        timeout: int = 1800, only: Optional[List[str]] = None) -> Dict[str, Any]:
    """并行执行所有角色卡；无 worker 时返回 plan。"""
    base = Path(out_dir)
    plan = prepare(out_dir, only)
    if not worker_cmd:
        plan["hint"] = ("未配置执行器：设 GUAGUA_WORKER_CMD 或传 --worker-cmd，"
                        "占位符 {prompt} / {claims}")
        return plan

    items = plan["roles"]
    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futs = {ex.submit(_one, worker_cmd, it, timeout): it["role"] for it in items}
        for fut in as_completed(futs):
            rows.append(fut.result())
    rows.sort(key=lambda r: r["role"])
    ok = all(r["exit_code"] == 0 and r["claims_exists"] for r in rows)
    res = {"ok": ok, "mode": "worker", "count": len(rows), "workers": workers,
           "roles": rows, "worker_cmd": worker_cmd}
    (base / "research_run.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res
