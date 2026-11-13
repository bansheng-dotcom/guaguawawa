# -*- coding: utf-8 -*-
"""最小可用编排层：按 pipeline.json 顺序执行 data → skill → assert → report。

不做 DAG 调度，只做「顺序执行 + 失败即停 + 每步留痕」，先把 49 条人工命令收敛成一条。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

AGENTS_ROOT = Path(__file__).resolve().parents[1]


def _run_skill(step: Dict[str, Any]) -> Dict[str, Any]:
    args = [str(x).replace("{AGENTS}", str(AGENTS_ROOT)) for x in step.get("args", [])]
    argv = [sys.executable, "guagua.py", "call", "r06", step["skill"], *args]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    p = subprocess.run(argv, cwd=str(AGENTS_ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if "__AGENT_RESULT__" in line:
            try:
                return json.loads(line.split("__AGENT_RESULT__", 1)[1].strip())
            except json.JSONDecodeError:
                pass
    for line in reversed(out.splitlines()):
        if line.strip().startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"ok": False, "error": (out or "无输出")[-300:]}


def _get(d: Any, path: str):
    cur = d
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur.get(part)
        if cur is None:
            return None
    return cur


def run(pipeline_path: str) -> Dict[str, Any]:
    spec = json.loads(Path(pipeline_path).read_text(encoding="utf-8"))
    out_dir = Path(spec.get("out_dir") or (Path(pipeline_path).parent / "out"))
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx: Dict[str, Any] = {}
    log = []

    for step in spec.get("steps", []):
        sid, typ = step.get("id", ""), step.get("type")
        if typ == "skill":
            res = _run_skill(step)
            ctx[sid] = res
            (out_dir / f"{sid}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            ok = res.get("ok", True) and not res.get("error")
            log.append({"id": sid, "type": typ, "ok": ok,
                        "conclusion": res.get("conclusion"), "status": res.get("status")})
            if not ok:
                return {"ok": False, "failed": sid, "log": log}
        elif typ == "data":
            rows = 0
            p = Path(str(step["path"]).replace("{AGENTS}", str(AGENTS_ROOT)))
            if p.exists():
                rows = max(0, len(p.read_text(encoding="utf-8-sig").splitlines()) - 1)
            log.append({"id": sid, "type": typ, "ok": p.exists(), "rows": rows})
            if not p.exists():
                return {"ok": False, "failed": sid, "log": log}
        elif typ == "assert":
            got = _get(ctx, step["path"])
            want = step.get("equals")
            ok = (got is not None) if want is None else (got == want)
            log.append({"id": sid, "type": typ, "ok": ok, "got": got, "want": want})
            if not ok:
                return {"ok": False, "failed": sid, "log": log}
        elif typ == "report":
            lines = [f"# {spec.get('proposition', '分析流水线')}", ""]
            for item in log:
                if item.get("conclusion"):
                    lines += [f"## {item['id']}", f"- 状态：{item.get('status')}", f"- 结论：{item['conclusion']}", ""]
            out_md = out_dir / (step.get("path") or "report.md")
            out_md.write_text("\n".join(lines), encoding="utf-8")
            log.append({"id": sid, "type": typ, "ok": True, "path": str(out_md)})
        else:
            return {"ok": False, "failed": sid, "error": f"未知步骤类型 {typ}", "log": log}

    (out_dir / "pipeline_log.json").write_text(
        json.dumps({"ran_at": datetime.now().isoformat(timespec="seconds"), "log": log},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "log": log, "out_dir": str(out_dir)}
