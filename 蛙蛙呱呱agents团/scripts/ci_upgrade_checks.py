# -*- coding: utf-8 -*-
"""升级门禁 CI：方法包 / 测试 / MCP / 评测回归 / 角色入口。

退出码非 0 = 有门禁失败。可挂 pre-commit 或 GitHub Actions。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(name: str, cmd: list[str], timeout: int = 300) -> tuple[str, int, str]:
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return name, p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    checks = [
        ("roles", [PY, "guagua.py", "check"]),
        ("method", [PY, "scripts/audit_method.py", "--all"]),
        ("tests", [PY, "-m", "pytest", "tests/test_mcp_client.py", "tests/test_consulting_workbook.py", "tests/test_method_gate.py", "tests/test_methods_core.py", "tests/test_methods_deep.py", "tests/test_methods_deep_advanced.py", "tests/test_methods_business.py", "-q"]),
        ("mcp", [PY, "scripts/mcp_doctor.py", "doctor", "--all"]),
        ("eval", [PY, "scripts/run_consult_eval.py", "--compare", "evals/consulting/baseline.json"]),
        ("depth", [PY, "scripts/audit_method_depth.py"]),
    ]
    results = []
    for name, cmd in checks:
        n, rc, out = run(name, cmd)
        tail = out.strip().splitlines()[-1] if out.strip() else ""
        print(f"[{'OK' if rc == 0 else 'FAIL'}] {n:<8} {tail[:90]}")
        results.append({"name": n, "rc": rc, "tail": tail})
    out = ROOT / "workspace" / "ci_upgrade_report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [r for r in results if r["rc"] != 0]
    print(f"\n{len(results)} 项，失败 {len(bad)} 项；报告：{out}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
