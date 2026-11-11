#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Web 应用门禁自检：验证 agent.py 的 spec / fullstack 三道门禁。

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

# (fixture, 子命令, 动作, 期望退出码, 证明什么)
CASES = [
    ("../../../examples/spec_spec.json", "spec", "spec", 0,
     "正例：每个模块 inputs/outputs 成对 → 契约门禁通过"),
    ("../../../examples/spec_spec_dirty.json", "spec", "spec", 1,
     "反例①：契约缺段/结构不合法 → 必须拦"),
    ("../../../examples/fullstack_feature.json", "fullstack", "feature", 0,
     "正例：端到端切片四段齐全 → 通过"),
    ("../../../examples/fullstack_feature_dirty.json", "fullstack", "feature", 1,
     "反例②：切片链路不闭合 → 必须拦"),
    ("../../../examples/fullstack_auth.json", "fullstack", "auth", 0,
     "正例：放行规则完整 + 服务端校验 → 通过"),
    ("../../../examples/fullstack_auth_dirty.json", "fullstack", "auth", 1,
     "反例③：鉴权规则不完整（只藏前端）→ 必须拦"),
]


def run(sub: str, act: str, path: str):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, AGENT, sub, act, "--input", path],
                       cwd=ROLE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return int(p.returncode), (p.stdout or ""), (p.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Web 应用门禁自检")
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

    print(f"Web 应用门禁自检 · 角色根目录 {ROLE}")
    print("=" * 70)
    failures = []
    for rel, sub, act, expect, why in CASES:
        path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
        if not os.path.isfile(path):
            print(f"  [MISS] {sub}.{act:<8} {rel}")
            failures.append((rel, "missing", expect, why))
            continue
        code, out, err = run(sub, act, path)
        ok = code == expect
        label = f"{sub}.{act}"
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<14} exit={code} (期望 {expect})  {os.path.basename(rel)}")
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
    neg = sum(1 for _r, _s, _a, e, _w in CASES if e != 0)
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 {neg} 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
