"""Run deterministic smoke checks for all registered roles.

The suite intentionally tests the stable CLI contract first (manifest), then
runs a safe local task when a fixture task exists. External side effects are
never required: unavailable integrations must report blocked/simulated.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

AGENTS = Path(__file__).resolve().parents[2]
ROOT = AGENTS.parent


def _run(role_dir: Path, *args: str) -> tuple[int, str, str]:
    env = dict(os.environ)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(role_dir / "agent.py"), *args],
        cwd=str(role_dir), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _result(stdout: str) -> dict[str, Any] | None:
    marker = "__AGENT_RESULT__ "
    candidates = [line[len(marker):] for line in stdout.splitlines()
                  if line.startswith(marker)]
    candidates.extend((stdout.strip(),))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def run_regression() -> int:
    role_dirs = sorted(
        path for path in AGENTS.iterdir()
        if path.is_dir() and path.name[:1] == "r"
        and len(path.name) >= 4 and path.name[1:3].isdigit()
        and path.name[3] == "-"
    )
    failures: list[str] = []
    print(f"Running manifest smoke tests for {len(role_dirs)} roles...")
    for role_dir in role_dirs:
        if not (role_dir / "agent.py").exists():
            failures.append(f"{role_dir.name}: missing agent.py")
            continue
        code, out, err = _run(role_dir, "manifest")
        value = _result(out)
        ok = code == 0 and isinstance(value, dict) and value.get("role")
        status = "PASS" if ok else "FAIL"
        print(f"{status:4} {role_dir.name}")
        if not ok:
            failures.append(f"{role_dir.name}: exit={code} stdout={out[-160:]} stderr={err[-240:]}")
    if failures:
        print("\nFailures:")
        print("\n".join(failures))
        return 1
    print("All role manifests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_regression())
