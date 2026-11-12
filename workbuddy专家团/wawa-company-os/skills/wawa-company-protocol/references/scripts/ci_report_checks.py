# -*- coding: utf-8 -*-
"""CI 闸门：规格校验 + 契约测试 + 退出条件。

退出条件（与 SOP 一致）：
  1. 20/20 角色有 spec 且校验通过；
  2. 契约测试 60/60 通过（20 角色 × 3 fixture）；
  3. configs/legacy_roles.txt 为空（迁移完成）；
  4. 代码里不再 import reportkit（单轨）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "configs" / "legacy_roles.txt"


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    fails = []

    rc, out = run([sys.executable, "scripts/report_spec.py", "check"])
    print(f"[1] spec check rc={rc}")
    print("\n".join(out.strip().splitlines()[-2:]))
    if rc:
        fails.append("spec")

    rc, out = run([sys.executable, "scripts/contract_test.py", "--all", "--mode", "spec"])
    print(f"[2] contract(spec) rc={rc} :: {out.strip().splitlines()[-1]}")
    if rc:
        fails.append("contract-spec")

    rc, out = run([sys.executable, "scripts/contract_test.py", "--all", "--mode", "preserve"])
    print(f"[3] contract(preserve) rc={rc} :: {out.strip().splitlines()[-1]}")
    if rc:
        fails.append("contract-preserve")

    names = [x.strip().lstrip("﻿") for x in LEGACY.read_text(encoding="utf-8").splitlines()
             if x.strip() and not x.strip().lstrip("﻿").startswith("#")]
    print(f"[4] legacy list: {len(names)} 个 -> {names or '空'}")
    if names:
        fails.append("legacy-not-empty")

    import re
    pat = re.compile(r"^\s*(?:from|import)\s+reportkit", re.M)
    bad = []
    for p in ROOT.rglob("*.py"):
        if p.name == "ci_report_checks.py":
            continue
        if pat.search(p.read_text(encoding="utf-8", errors="replace")):
            bad.append(p)
    print(f"[5] import reportkit: {len(bad)} 处")
    if bad:
        fails.append("dual-track")

    rc, out = run([sys.executable, "scripts/check_report_layout.py", "--all"])
    print(f"[6] report layout rc={rc} :: {out.strip().splitlines()[-1] if out.strip() else ''}")
    if rc:
        fails.append("layout")

    print(f"\n=== {'FAIL: ' + ','.join(fails) if fails else 'ALL PASS'} ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
