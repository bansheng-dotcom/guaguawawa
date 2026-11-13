#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""决策闸门自检：用正/反例 fixture 验证 harness.py 的门禁是否真的会拦住错误。

为什么需要它：
    判定逻辑在角色根目录的 `harness.py`（本包刻意不重复实现）。
    但"门禁存在"不等于"门禁有效"——上游改了 harness 的检查项，这里必须能立刻发现。
    本脚本只做一件事：**断言每个 fixture 的预期退出码**。

用法：
    python references/capabilities/decision-gate/scripts/gate_selftest.py
    python references/capabilities/decision-gate/scripts/gate_selftest.py --verbose

退出码：
    0  全部 fixture 符合预期
    1  有 fixture 不符合预期（门禁失效或 fixture 过期）
    2  环境问题（找不到 harness.py / fixture 缺失）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(_HERE)                     # .../decision-gate
CAPS = os.path.dirname(PACK)                      # .../capabilities
REFERENCES = os.path.dirname(CAPS)                # .../references
ROLE = os.path.dirname(REFERENCES)                # <role 根目录>
HARNESS = os.path.join(ROLE, "harness.py")

# (fixture 相对本包的路径, harness 门禁名, 期望退出码, 这段用例在证明什么)
CASES = [
    ("templates/decision-card.example.json", "card", 0,
     "合格决策卡应通过（15 项全 OK）"),
    ("tests/pass.json", "card", 0,
     "不可逆但回滚/标准齐备的卡应通过"),
    ("tests/fail-missing-rollback.json", "card", 1,
     "不可逆缺回滚计划 + 只有 1 个选项 → 必须被拦"),
    ("tests/fail-vague-thresholds.json", "card", 1,
     "阈值写「更快」+ owner 写「团队」+ deadline 写「尽快」→ 必须被拦"),
]


def run_gate(gate: str, path: str) -> tuple:
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
    ap = argparse.ArgumentParser(description="决策闸门自检")
    ap.add_argument("--verbose", action="store_true", help="打印门禁原始输出")
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

    print(f"决策闸门自检 · 角色根目录 {ROLE}")
    print("=" * 64)
    failures = []
    for rel, gate, expect, why in CASES:
        path = os.path.join(PACK, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            print(f"  [MISS] {rel}  文件不存在")
            failures.append((rel, "missing", expect, None))
            continue
        code, out, err = run_gate(gate, path)
        ok = code == expect
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {gate:<4} exit={code} (期望 {expect})  {rel}")
        print(f"         {why}")
        if args.verbose or not ok:
            tail = (out or err).strip().splitlines()
            if tail:
                print(f"         > {tail[0][:160]}")
        if not ok:
            failures.append((rel, code, expect, why))

    print("=" * 64)
    if failures:
        print(f"[selftest] FAIL  {len(failures)}/{len(CASES)} 不符合预期")
        for rel, got, expect, why in failures:
            print(f"  - {rel}: 实际 exit={got}，期望 {expect}（{why}）")
        print("\n门禁可能已失效，或 fixture 已过期。先确认 harness.py 未被人改动。")
        return 1
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 2 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
