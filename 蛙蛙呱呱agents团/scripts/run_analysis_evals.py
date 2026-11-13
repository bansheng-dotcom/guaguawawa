# -*- coding: utf-8 -*-
"""分析评测集执行器：每技能 3 个 case（正常/脏数据/边界）的 CI 入口。

case 结构：
{
  "skill": "chi2",
  "args": ["--input", "{AGENTS}/tests/fixtures/analysis_orders.csv", ...],
  "expect": {"chi2.p_exact": {"not_null": true}, "chi2.significant_at_0.05": false}
}
expect 规则：标量=相等；{"not_null":true}；{"in":[...]}；{"gt":x}/{"lt":x}。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1]
EVALS = AGENTS / "evals" / "analysis"


def _run(skill: str, args: list) -> dict:
    argv = [sys.executable, "guagua.py", "call", "r06", skill, *[str(a).replace("{AGENTS}", str(AGENTS)) for a in args]]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    p = subprocess.run(argv, cwd=str(AGENTS), capture_output=True, text=True,
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
    return {"ok": False, "error": out[-300:]}


def _get(d, path):
    cur = d
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _check(got, rule) -> bool:
    if isinstance(rule, dict):
        if "not_null" in rule:
            return got is not None
        if "in" in rule:
            return got in rule["in"]
        if "gt" in rule:
            return got is not None and got > rule["gt"]
        if "lt" in rule:
            return got is not None and got < rule["lt"]
        return False
    return got == rule


def main() -> int:
    cases = sorted(EVALS.glob("*/*.json"))
    if not cases:
        print("没有 case：evals/analysis/<skill>/case_*.json")
        return 1
    failed, passed = [], 0
    for c in cases:
        spec = json.loads(c.read_text(encoding="utf-8"))
        res = _run(spec["skill"], spec.get("args", []))
        bad = []
        for path, rule in (spec.get("expect") or {}).items():
            got = _get(res, path)
            if not _check(got, rule):
                bad.append(f"{path}: got={got!r} want={rule!r}")
        if bad:
            failed.append((c.name, bad))
            print(f"[FAIL] {c.parent.name}/{c.name} — {bad[:2]}")
        else:
            passed += 1
            print(f"[PASS] {c.parent.name}/{c.name}")
    print(f"\n{passed}/{len(cases)} 通过")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
