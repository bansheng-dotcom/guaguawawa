#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 测试基线固化器：串行执行 20 个角色的 run_tests.py + 根级能力测试。

用法：
    python scripts/run_baseline_tests.py

输出：
    workspace/baseline/test_results.json

判据：
    角色 rc=0 且 stdout 含 "ALL GREEN" 视为通过；根级测试 rc=0 视为通过。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "workspace", "baseline", "test_results.json")
PASS_RE = re.compile(r"PASS\s+(\d+)\s*/\s*(\d+)")
CN_PASS_RE = re.compile(r"通过\s+(\d+)\s*(?:项|/)")
FAIL_RE = re.compile(r"失败\s*(\d+)\s*项")


def run_case(name: str, cwd: str, argv: list) -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    started = time.time()
    try:
        p = subprocess.run([sys.executable, *argv], cwd=cwd, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           env=env, timeout=900)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        err = "timeout>900s"
    duration = round(time.time() - started, 1)
    m = PASS_RE.search(out) or CN_PASS_RE.search(out)
    passed = int(m.group(1)) if m else None
    total = int(m.group(2)) if m and m.re.groups > 1 and m.group(2) else None
    fm = FAIL_RE.search(out)
    failed_n = int(fm.group(1)) if fm else None
    ok = (rc == 0 and failed_n in (0, None)
          and "FAILED" not in out and "Traceback" not in err)
    return {
        "name": name, "cwd": os.path.relpath(cwd, ROOT).replace("\\", "/"),
        "cmd": " ".join(argv), "rc": rc, "duration_s": duration,
        "ok": ok, "passed": passed, "total": total, "failed_n": failed_n,
        "all_green": "ALL GREEN" in out or "全绿" in out,
        "stdout_tail": out[-1200:], "stderr_tail": err[-600:],
    }


def main() -> int:
    roles = sorted(d for d in os.listdir(ROOT)
                   if d.startswith("r") and "-" in d and os.path.isdir(os.path.join(ROOT, d)))
    results = []
    for d in roles:
        print(f"[run] {d}", flush=True)
        results.append(run_case(d, os.path.join(ROOT, d), ["run_tests.py"]))
        r = results[-1]
        print(f"      rc={r['rc']} ok={r['ok']} {r['passed']}/{r['total']} {r['duration_s']}s",
              flush=True)

    if os.path.exists(os.path.join(ROOT, "local_capability_tests.py")):
        print("[run] local_capability_tests.py", flush=True)
        results.append(run_case("local_capability_tests", ROOT, ["local_capability_tests.py"]))
        r = results[-1]
        print(f"      rc={r['rc']} ok={r['ok']} {r['duration_s']}s", flush=True)

    payload = {
        "generated_by": "scripts/run_baseline_tests.py",
        "python": sys.version.split()[0],
        "summary": {
            "cases": len(results),
            "ok": sum(1 for r in results if r["ok"]),
            "failed": [r["name"] for r in results if not r["ok"]],
            "total_assertions": sum(r["passed"] or 0 for r in results),
            "duration_s": round(sum(r["duration_s"] for r in results), 1),
        },
        "results": results,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(f"written: {OUT}")
    return 0 if not payload["summary"]["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
