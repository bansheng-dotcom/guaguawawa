#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRD 门禁自检：验证 prdguard（执行层）与 harness prd（战略层）真的会拦住错误。

用法：
    python references/capabilities/prd-authoring/scripts/gate_selftest.py [--verbose]

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
AGENT = os.path.join(ROLE, "agent.py")
HARNESS = os.path.join(ROLE, "harness.py")

# (fixture, 判定器, 额外参数, 期望退出码, 证明什么)
CASES = [
    ("tests/spec-pass.json", "prdguard", ["check"], 0,
     "正例：契约四要素 + P0 四段 + source 枚举 + 不做≥2 + 边界≥1 → 12 项全过"),
    ("tests/spec-fail.json", "prdguard", ["check"], 1,
     "反例①：P0 缺四段 + source 不在枚举 + 不做仅 1 条 + 无边界 → 必须拦"),
    ("../../../examples/prd.json", "harness", ["prd"], 0,
     "正例：战略层结构完整 → harness prd 通过"),
    ("../../../examples/prd_dirty.json", "harness", ["prd"], 1,
     "反例②：战略层缺字段 → harness prd 必须拦"),
    ("../../../../configs/r07.yaml", "prdguard", ["check"], 1,
     "反例③：喂非 PRD 文件（yaml 配置）→ 必须拒绝，不许假绿"),
]


def run(kind: str, extra: list, path: str) -> tuple:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if kind == "harness":
        cmd = [sys.executable, HARNESS] + extra + ["--input", path]
    else:
        cmd = [sys.executable, AGENT, "prdguard"] + extra + ["--input", path]
    proc = subprocess.run(cmd, cwd=ROLE, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return int(proc.returncode), (proc.stdout or ""), (proc.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PRD 门禁自检")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--self-test", action="store_true",
                    help="（默认行为）跑内置正/反例自检；保留此开关以与其它技能包命令统一")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    for p in (AGENT, HARNESS):
        if not os.path.isfile(p):
            print(f"[selftest] 环境错误：找不到 {p}", file=sys.stderr)
            return 2

    print(f"PRD 门禁自检 · 角色根目录 {ROLE}")
    print("=" * 66)
    failures = []
    for rel, kind, extra, expect, why in CASES:
        path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
        if not os.path.isfile(path):
            print(f"  [MISS] {rel}")
            failures.append((rel, "missing", expect, why))
            continue
        code, out, err = run(kind, extra, path)
        ok = code == expect
        label = f"{kind} {' '.join(extra)}".strip()
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<18} exit={code} (期望 {expect})  {os.path.basename(rel)}")
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
        return 1
    print(f"[selftest] PASS  {len(CASES)}/{len(CASES)} 符合预期（含 3 个反例被正确拦下）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
