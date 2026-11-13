#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""订单生命周期门禁自检：验证 7 道 harness 门禁对正/反例的退出码。

用法：
    python references/capabilities/order-lifecycle/scripts/gate_selftest.py [--verbose]

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
HARNESS = os.path.join(ROLE, "harness.py")

# (fixture, 门禁, 期望退出码, 证明什么)
CASES = [
    ("tests/order-pass.json", "order", 0,
     "正例：三态自洽 + 总额>0 → 通过"),
    ("../../../examples/order.json", "order", 0,
     "正例：官方夹具 → 通过"),
    ("../../../examples/order_dirty.json", "order", 1,
     "反例①：已全额退款却 completed + 总额 0 → 三态矛盾必须拦"),
    ("../../../examples/cart.json", "cart", 0,
     "正例：行项目与金额一致 → 通过"),
    ("../../../examples/cart_dirty.json", "cart", 1,
     "反例②：购物车行项目/金额不一致 → 必须拦"),
    ("../../../examples/state.json", "state", 0,
     "正例：终态实体无后续动作 → 通过"),
    ("../../../examples/state_dirty.json", "state", 1,
     "反例③：终态仍有后续动作 → 必须拦"),
    ("../../../examples/transition.json", "transition", 0,
     "正例：合法迁移 → 通过"),
    ("../../../examples/transition_dirty.json", "transition", 1,
     "反例④：试图从终态 refunded 迁出 → 必须拦"),
    ("../../../examples/refund.json", "refund", 0,
     "正例：退款四项满足 → 通过"),
    ("../../../examples/refund_dirty.json", "refund", 1,
     "反例⑤：缺 payment_intent + 比例 1.912 → 必须拦"),
]


def run(gate: str, path: str) -> tuple:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, HARNESS, gate, "--input", path],
        cwd=ROLE, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return int(proc.returncode), (proc.stdout or ""), (proc.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="订单生命周期门禁自检")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="（默认行为）跑内置正/反例自检；保留此开关以与其它技能包命令统一")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not os.path.isfile(HARNESS):
        print(f"[selftest] 环境错误：找不到 {HARNESS}", file=sys.stderr)
        return 2

    print(f"订单生命周期门禁自检 · 角色根目录 {ROLE}")
    print("=" * 68)
    failures = []
    for rel, gate, expect, why in CASES:
        path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
        if not os.path.isfile(path):
            print(f"  [MISS] {gate:<11} {rel}")
            failures.append((rel, "missing", expect, why))
            continue
        code, out, err = run(gate, path)
        ok = code == expect
        print(f"  [{'PASS' if ok else 'FAIL'}] {gate:<11} exit={code} (期望 {expect})  {os.path.basename(rel)}")
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
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 5 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
