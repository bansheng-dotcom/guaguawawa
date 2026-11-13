#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模型评测门禁自检：验证 harness.py 的 evaluation_dataset / evaluation_scorer / release_regression。

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
HARNESS = os.path.join(ROLE, "harness.py")

CASES = [
    ("../../../examples/evaluation_dataset.json", "evaluation_dataset", 0, "正例：输入与期望成对 → 通过"),
    ("../../../examples/evaluation_dataset_dirty.json", "evaluation_dataset", 1, "反例①：缺 inputs / expectations → 必须拦"),
    ("../../../examples/evaluation_scorer.json", "evaluation_scorer", 0, "正例：评分器三件齐全 → 通过"),
    ("../../../examples/evaluation_scorer_dirty.json", "evaluation_scorer", 1, "反例②：缺 type/target/criteria → 必须拦"),
    ("../../../examples/release_regression.json", "release_regression", 0, "正例：旧绿集 + 归因层次齐备 → 通过"),
    ("../../../examples/release_regression_dirty.json", "release_regression", 1, "反例③：缺旧绿集 / 归因层次 → 必须拦"),
]


def run(gate: str, path: str):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, HARNESS, gate, "--input", path],
                       cwd=ROLE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return int(p.returncode), (p.stdout or ""), (p.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="模型评测门禁自检")
    ap.add_argument("--self-test", action="store_true", help="（默认行为）跑内置正/反例自检")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not os.path.isfile(HARNESS):
        print(f"[selftest] 环境错误：找不到 {HARNESS}", file=sys.stderr)
        return 2

    print(f"模型评测门禁自检 · 角色根目录 {ROLE}")
    print("=" * 74)
    failures = []
    for rel, gate, expect, why in CASES:
        path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
        if not os.path.isfile(path):
            print(f"  [MISS] {gate:<22} {rel}")
            failures.append((rel, "missing", expect, why))
            continue
        code, out, err = run(gate, path)
        ok = code == expect
        print(f"  [{'PASS' if ok else 'FAIL'}] {gate:<22} exit={code} (期望 {expect})  {os.path.basename(rel)}")
        print(f"         {why}")
        if args.verbose or not ok:
            tail = (out or err).strip().splitlines()
            if tail:
                print(f"         > {tail[0][:150]}")
        if not ok:
            failures.append((rel, code, expect, why))

    print("=" * 74)
    if failures:
        print(f"[selftest] FAIL  {len(failures)}/{len(CASES)} 不符合预期")
        for rel, got, expect, why in failures:
            print(f"  - {rel}: 实际 exit={got}，期望 {expect}（{why}）")
        return 1
    neg = sum(1 for _r, _g, e, _w in CASES if e != 0)
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 {neg} 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
