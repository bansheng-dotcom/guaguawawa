#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""20 角色端到端验收：逐个执行 `<role>/run_tests.py`，任一非 0 即失败。

为什么不是直接 `pytest r*/tests`：
    20 个角色目录都叫 `tests`，其中 7 个带 `__init__.py`、13 个没有，
    一次性收集会抛 ImportPathMismatchError。所以按角色隔离子进程执行，
    与各角色 README「python run_tests.py」的口径一致。

用法：
    python scripts/check_role_tests.py                 # 全部 20 个
    python scripts/check_role_tests.py --role r06 r14  # 指定角色
    python scripts/check_role_tests.py --json          # 机器可读
    python scripts/check_role_tests.py --timeout 900   # 单角色超时秒数
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLE_RE = re.compile(r"^r\d\d-")


def role_dirs():
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name)
        if os.path.isdir(path) and ROLE_RE.match(name):
            yield name, path


def run_role(name: str, path: str, timeout: int) -> dict:
    script = os.path.join(path, "run_tests.py")
    if not os.path.isfile(script):
        return {"role": name, "ok": False, "reason": "缺 run_tests.py"}
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))
    try:
        proc = subprocess.run([sys.executable, "run_tests.py"], cwd=path,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"role": name, "ok": False, "reason": f"超时 >{timeout}s"}
    out = (proc.stdout or "") + (proc.stderr or "")
    fails = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL")]
    summary = ""
    for ln in reversed(out.splitlines()):
        s = ln.strip()
        if ("通过" in s and "失败" in s) or "ALL GREEN" in s or "全绿" in s or "FAILED" in s:
            summary = s
            break
    return {"role": name, "ok": proc.returncode == 0,
            "returncode": proc.returncode, "summary": summary,
            "failures": fails[:5]}


def main() -> int:
    ap = argparse.ArgumentParser(prog="check_role_tests")
    ap.add_argument("--role", nargs="*", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    results = []
    for name, path in role_dirs():
        if args.role and name[:3] not in args.role and name not in args.role:
            continue
        r = run_role(name, path, args.timeout)
        results.append(r)
        if not args.json:
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"{mark:4} {name}  {r.get('summary') or r.get('reason', '')}")
            for f in r.get("failures") or []:
                print("       ", f)

    bad = [r for r in results if not r["ok"]]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0 if not bad else 1
    print(f"--- {len(results) - len(bad)}/{len(results)} 角色端到端验收通过")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
