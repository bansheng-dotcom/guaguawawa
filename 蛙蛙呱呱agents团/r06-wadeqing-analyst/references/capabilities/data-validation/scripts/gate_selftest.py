#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据校验门禁自检：验证 harness semantic 与包装后的 agent.py quality audit。

两条已知局限（本脚本刻意覆盖以证明其存在）：
  1. `harness.py semantic` 只校验枚举，不校验非空 → 用非法枚举做反例；
  2. `agent.py quality audit` 原生恒 exit 0 → 必须经共享 `scripts/gate_wrap.py` 才有退出码。

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
CAPS = os.path.dirname(PACK)
REFERENCES = os.path.dirname(CAPS)
ROLE = os.path.dirname(REFERENCES)
ROOT = os.path.dirname(ROLE)
HARNESS = os.path.join(ROLE, "harness.py")
WRAP = os.path.join(ROOT, "scripts", "gate_wrap.py")

# (fixture, 模式, 期望退出码, 证明什么)
CASES = [
    ("tests/semantic-pass.json", "semantic", 0, "正例：实体/维度/度量/指标类型全在白名单 → 通过"),
    ("../../../examples/semantic_model.json", "semantic", 0, "正例：官方语义模型夹具 → 通过"),
    ("tests/semantic-bad.json", "semantic", 1, "反例①：自创枚举 sum_of / timex / simplex → 必须拦"),
    ("tests/semantic-empty.json", "semantic", 1, "反例①b：entities/measures 全空（2026-11 补非空校验）→ 必须拦"),
    ("tests/dirty.csv", "quality", 1, "反例②：脏 CSV（缺失 25% + 重复行 + 日期/金额非法）→ 包装后必须拦"),
    ("../../../workspace/parking_profit.csv", "quality", 0, "正例：干净 CSV → 包装后通过"),
]


def run_semantic(path: str):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, HARNESS, "semantic", "--input", path],
                       cwd=ROLE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return int(p.returncode), (p.stdout or ""), (p.stderr or "")


def run_quality(path: str):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, WRAP, "--cwd", ROLE, "--input", path,
                        "--", "agent.py", "quality", "audit"],
                       cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return int(p.returncode), (p.stdout or ""), (p.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="数据校验门禁自检")
    ap.add_argument("--self-test", action="store_true", help="（默认行为）跑内置正/反例自检")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    for p in (HARNESS, WRAP):
        if not os.path.isfile(p):
            print(f"[selftest] 环境错误：找不到 {p}", file=sys.stderr)
            return 2

    print(f"数据校验门禁自检 · 角色根目录 {ROLE}")
    print("提示：quality audit 原生恒 exit 0，本脚本经共享 gate_wrap.py 包装")
    print("=" * 70)
    failures = []
    for rel, mode, expect, why in CASES:
        path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
        if not os.path.isfile(path):
            print(f"  [MISS] {mode:<9} {rel}")
            failures.append((rel, "missing", expect, why))
            continue
        code, out, err = (run_semantic(path) if mode == "semantic" else run_quality(path))
        ok = code == expect
        label = "semantic" if mode == "semantic" else "quality*"
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<9} exit={code} (期望 {expect})  {os.path.basename(rel)}")
        print(f"         {why}")
        if args.verbose or not ok:
            tail = (out or err).strip().splitlines()
            if tail:
                print(f"         > {tail[0][:150]}")
        if not ok:
            failures.append((rel, code, expect, why))

    print("=" * 70)
    if failures:
        print(f"[selftest] FAIL  {len(failures)}/{len(CASES)} 不符合预期")
        for rel, got, expect, why in failures:
            print(f"  - {rel}: 实际 exit={got}，期望 {expect}（{why}）")
        return 1
    neg = sum(1 for _r, _m, e, _w in CASES if e != 0)
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 {neg} 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
