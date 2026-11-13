#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评审门禁自检：验证 harness.py verdict 与 review.py 是否真的会拦住错误。

为什么需要它：
    两个判定器都已存在（根目录 `harness.py` / `review.py`），但"存在"不等于"有效"。
    尤其 review.py 对**空 result** 会返回 ok=true（无字段 → 无检查），
    这是一种"对错误答案也通过"的假绿。本脚本用显式 fixture 把它锁住。

用法：
    python references/capabilities/review-anti-collusion/scripts/gate_selftest.py
    python references/capabilities/review-anti-collusion/scripts/gate_selftest.py --verbose

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
REVIEW = os.path.join(ROLE, "review.py")

# (相对本包的 fixture, 判定器, 门禁/参数, 期望退出码, 这段用例在证明什么)
CASES = [
    ("tests/packet-pass.json", "review", [], 0,
     "正例：身份不同 + 有证据 + 无修复声明 + 无模糊措辞 → 通过"),
    ("tests/packet-self-review.json", "review", [], 1,
     "反例①：reviewer==producer → 身份红线必须拦住"),
    ("tests/packet-applied-fixes.json", "review", [], 1,
     "反例②：含 applied_fixes（已改好声明）→ 只记录不修复红线必须拦住"),
    ("tests/packet-no-evidence.json", "review", [], 1,
     "反例③：PASS 但证据链全空 → 证据门禁必须拦住"),
    ("../../../examples/review_result_clean.json", "harness", ["verdict"], 0,
     "正例：flat 结果结构完整 → harness verdict 通过"),
    ("../../../examples/review_result_dirty.json", "harness", ["verdict"], 1,
     "反例④：PASS 无证据链 → harness verdict 必须拦住"),
]


def run(kind: str, gate: list, path: str) -> tuple:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if kind == "harness":
        cmd = [sys.executable, HARNESS] + gate + ["--input", path]
    else:
        cmd = [sys.executable, REVIEW, "--packet", path]
    proc = subprocess.run(cmd, cwd=ROLE, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return int(proc.returncode), (proc.stdout or ""), (proc.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="评审门禁自检")
    ap.add_argument("--verbose", action="store_true", help="打印判定器原始输出")
    ap.add_argument("--self-test", action="store_true",
                    help="（默认行为）跑内置正/反例自检；保留此开关以与其它技能包命令统一")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    for p in (HARNESS, REVIEW):
        if not os.path.isfile(p):
            print(f"[selftest] 环境错误：找不到 {p}", file=sys.stderr)
            return 2

    print(f"评审门禁自检 · 角色根目录 {ROLE}")
    print("=" * 66)
    failures = []
    for rel, kind, gate, expect, why in CASES:
        path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
        if not os.path.isfile(path):
            print(f"  [MISS] {rel}")
            failures.append((rel, "missing", expect, why))
            continue
        code, out, err = run(kind, gate, path)
        ok = code == expect
        label = f"{kind} {' '.join(gate)}".strip()
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<14} exit={code} (期望 {expect})  {os.path.basename(rel)}")
        print(f"         {why}")
        if args.verbose or not ok:
            tail = (out or err).strip().splitlines()
            if tail:
                print(f"         > {tail[0][:150]}")
        if not ok:
            failures.append((rel, code, expect, why))

    print("=" * 66)
    if failures:
        print(f"[selftest] FAIL  {len(failures)}/{len(CASES)} 不符合预期")
        for rel, got, expect, why in failures:
            print(f"  - {rel}: 实际 exit={got}，期望 {expect}（{why}）")
        print("\n门禁可能已失效，或 fixture 已过期。先确认 harness.py / review.py 未被改动。")
        return 1
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 4 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
