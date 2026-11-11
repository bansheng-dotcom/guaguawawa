#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交接与验收门禁自检。

关键注意：r02 的 `harness.py` **没有 __main__ 块**（纯库），
直接 `python harness.py ...` 不会执行判定且退出码为 0（假绿）。
因此本脚本一律通过 `agent.py harness <action>` 调用。

用法：python scripts/gate_selftest.py [--self-test] [--verbose]
退出码：0 全符合预期 / 1 有 fixture 不符合 / 2 环境问题
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(_HERE)
REFERENCES = os.path.dirname(os.path.dirname(PACK))
ROLE = os.path.dirname(REFERENCES)
AGENT = os.path.join(ROLE, "agent.py")

CASES = [
    ("tests/handoff-pass.json", "package", 0, "正例：字段齐全 + 复现命令 + 下游字段 + 验收标准 → 通过"),
    ("../../../examples/handoff.json", "package", 0, "正例：官方夹具 → 通过"),
    ("tests/handoff-missing.json", "package", 1, "反例①：缺复现命令 / 下游字段 / 验收标准 → 必须拦"),
    ("tests/accept-pass.json", "accept", 0, "正例：每个验收项都带证据 → 通过"),
    ("../../../examples/acceptance.json", "accept", 0, "正例：官方夹具 → 通过"),
    ("tests/accept-no-evidence.json", "accept", 1, "反例②：passed=true 但无 evidence（口头通过）→ 必须拦"),
    ("../../../examples/audittrail.json", "trace", 0, "正例：审计轨迹时间单调且字段齐全 → 通过"),
]


def run(action: str, path: str):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, AGENT, "harness", action, "--input", path],
                       cwd=ROLE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return int(p.returncode), (p.stdout or ""), (p.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="交接与验收门禁自检")
    ap.add_argument("--self-test", action="store_true", help="（默认行为）跑内置正/反例自检")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not os.path.isfile(AGENT):
        print(f"[selftest] 环境错误：找不到 {AGENT}", file=sys.stderr)
        return 2

    print(f"交接与验收门禁自检 · 角色根目录 {ROLE}")
    print("提示：走 agent.py harness（harness.py 无 __main__，直跑会假绿）")
    print("=" * 68)
    failures = []
    for rel, action, expect, why in CASES:
        path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
        if not os.path.isfile(path):
            print(f"  [MISS] {action:<8} {rel}")
            failures.append((rel, "missing", expect, why))
            continue
        code, out, err = run(action, path)
        ok = code == expect
        print(f"  [{'PASS' if ok else 'FAIL'}] {action:<8} exit={code} (期望 {expect})  {os.path.basename(rel)}")
        print(f"         {why}")
        if args.verbose or not ok:
            tail = (out or err).strip().splitlines()
            if tail:
                print(f"         > {tail[0][:150]}")
        if not ok:
            failures.append((rel, code, expect, why))

    print("=" * 68)
    if failures:
        print(f"[selftest] FAIL  {len(failures)}/{len(CASES)} 不符合预期")
        for rel, got, expect, why in failures:
            print(f"  - {rel}: 实际 exit={got}，期望 {expect}（{why}）")
        return 1
    neg = sum(1 for _r, _a, e, _w in CASES if e != 0)
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 {neg} 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
