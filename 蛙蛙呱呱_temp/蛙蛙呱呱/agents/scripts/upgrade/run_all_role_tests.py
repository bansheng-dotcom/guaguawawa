# -*- coding: utf-8 -*-
"""全角色 pytest 回归（Stage 5 闭环验证）：每个角色 tests/ 独立真实执行。

用 `__file__` 推导绝对路径定位 tests（META-001 关键教训 #1），
并在子进程中设置 PYTHONIOENCODING/PYTHONUTF8（教训 #2）。

用法：
    python agents/scripts/upgrade/run_all_role_tests.py
    python agents/scripts/upgrade/run_all_role_tests.py --role r14 r20
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP = {"r06-wadeqing-analyst"}


def role_dirs():
    for name in sorted(os.listdir(AGENTS)):
        p = os.path.join(AGENTS, name)
        if (os.path.isdir(p) and len(name) > 3 and name[0] == "r"
                and name[1:3].isdigit() and name[3] == "-" and name not in SKIP):
            yield name[:3], p


def run(role: str, path: str) -> dict:
    tests = os.path.join(path, "tests")
    if not os.path.isdir(tests):
        return {"role": role, "ok": False, "reason": "no tests/"}
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               PYTHONPATH=os.path.dirname(AGENTS))
    proc = subprocess.run([sys.executable, "-m", "pytest", tests, "-q",
                           "--no-header", "-p", "no:cacheprovider"],
                          cwd=path, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=300)
    tail = [ln for ln in (proc.stdout or "").strip().splitlines() if ln.strip()]
    summary = tail[-1] if tail else ""
    passed = failed = 0
    for ln in tail:
        if " passed" in ln:
            parts = ln.replace("=", " ").split()
            for i, tok in enumerate(parts):
                if tok == "passed":
                    try:
                        passed = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass
                if tok == "failed":
                    try:
                        failed = int(parts[i - 1])
                    except (ValueError, IndexError):
                        pass
    return {"role": role, "ok": proc.returncode == 0, "passed": passed,
            "failed": failed, "summary": summary,
            "stderr": (proc.stderr or "").strip().splitlines()[-3:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", nargs="*", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = []
    for role, path in role_dirs():
        if args.role and role not in args.role:
            continue
        r = run(role, path)
        results.append(r)
        if not args.json:
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"{mark:4} {role}  passed={r.get('passed')} failed={r.get('failed')}"
                  f"  {r.get('summary') or r.get('reason', '')}")
            for line in r.get("stderr") or []:
                print("       !", line)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0
    bad = [r for r in results if not r["ok"]]
    total_pass = sum(r.get("passed") or 0 for r in results)
    print(f"--- {len(results) - len(bad)}/{len(results)} 角色测试全绿，"
          f"合计 {total_pass} 条断言用例通过")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
