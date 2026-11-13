# -*- coding: utf-8 -*-
"""结论层审计：跑评测集里的技能，检查每个结果都有 conclusion（或明确 blocked）。

用法：python scripts/check_conclusions.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1]
EVALS = AGENTS / "evals" / "analysis"


def _run(skill, args):
    argv = [sys.executable, "guagua.py", "call", "r06", skill,
            *[str(a).replace("{AGENTS}", str(AGENTS)) for a in args]]
    p = subprocess.run(argv, cwd=str(AGENTS), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if "__AGENT_RESULT__" in line:
            return json.loads(line.split("__AGENT_RESULT__", 1)[1].strip())
    return {"ok": False, "raw": out[-200:]}


def main() -> int:
    rows, missing = [], []
    for c in sorted(EVALS.glob("*/*.json")):
        spec = json.loads(c.read_text(encoding="utf-8"))
        res = _run(spec["skill"], spec.get("args", []))
        has = bool(res.get("conclusion"))
        status = res.get("status", "?")
        rows.append((c.parent.name, spec["skill"], has, status))
        if not has and status != "blocked":
            missing.append(f"{c.parent.name}: 技能 {spec['skill']} 无 conclusion")
    for r in rows:
        print(f"[{'OK' if r[2] else '--'}] {r[0]:<14} skill={r[1]:<10} status={r[3]}")
    print(f"\n{sum(1 for r in rows if r[2])}/{len(rows)} 有 conclusion")
    if missing:
        print("缺失：")
        for m in missing:
            print(" -", m)
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
