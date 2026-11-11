#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""品牌一致性门禁自检（以 DESIGN.md 令牌为基准）。

用法：python scripts/gate_selftest.py [--self-test] [--verbose]
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
DESIGN = os.path.join(ROLE, "DESIGN.md")

CASES = [
    ("tests/brand-pass.json", 0, "正例：用色全在令牌内 + 高对比度 → 通过"),
    ("tests/brand-fail.json", 1, "反例：令牌外颜色 + 灰字白底 → 必须拦"),
]


def run(rel: str):
    path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
    if not os.path.isfile(path):
        return None, "", f"fixture 缺失: {rel}"
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, AGENT, "brandcheck", "check",
                        "--input", path, "--design", DESIGN],
                       cwd=ROLE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return int(p.returncode), (p.stdout or ""), (p.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="品牌一致性门禁自检")
    ap.add_argument("--self-test", action="store_true", help="（默认行为）跑内置正/反例自检")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print(f"品牌一致性门禁自检 · 角色根目录 {ROLE}")
    print("=" * 66)
    failures = []
    for rel, expect, why in CASES:
        code, out, err = run(rel)
        ok = code == expect
        print(f"  [{'PASS' if ok else 'FAIL'}] exit={code} (期望 {expect})  {os.path.basename(rel)}")
        print(f"         {why}")
        if args.verbose or not ok:
            tail = (out or err).strip().splitlines()
            if tail:
                print(f"         > {tail[0][:150]}")
        if not ok:
            failures.append((rel, code, expect, why))
    print("=" * 66)
    if failures:
        print(f"[selftest] FAIL  {len(failures)}/{len(CASES)}")
        return 1
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 1 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
