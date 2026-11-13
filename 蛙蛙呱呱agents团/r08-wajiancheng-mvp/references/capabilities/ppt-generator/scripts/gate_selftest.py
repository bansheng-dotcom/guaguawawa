#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单文件 HTML 幻灯片门禁自检。

用法：python scripts/gate_selftest.py [--self-test] [--verbose]
退出码：0 全符合预期 / 1 有 fixture 不符合 / 2 环境问题
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.dirname(_HERE)
REFERENCES = os.path.dirname(os.path.dirname(PACK))
ROLE = os.path.dirname(REFERENCES)
AGENT = os.path.join(ROLE, "agent.py")

CASES = [
    ("tests/deck-pass.json", "deck", "plan", 0,
     "正例：6 页 + 封面首 + 收尾末 → 通过"),
    ("tests/deck-fail.json", "deck", "plan", 1,
     "反例：2 页 + 标题空 + 封面不在首 → 必须拦"),
]


def run(sub: str, act: str, rel: str):
    path = os.path.normpath(os.path.join(PACK, rel.replace("/", os.sep)))
    if not os.path.isfile(path):
        return None, "", f"fixture 缺失: {rel}"
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, AGENT, sub, act, "--input", path]
    if "":
        out = os.path.join(PACK, "tests", "_out.xlsx")
        if os.path.exists(out):
            os.remove(out)
        cmd += ["--out", out]
    p = subprocess.run(cmd, cwd=ROLE, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return int(p.returncode), (p.stdout or ""), (p.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="单文件 HTML 幻灯片门禁自检")
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

    print(f"单文件 HTML 幻灯片门禁自检 · 角色根目录 {ROLE}")
    print("=" * 68)
    failures = []
    try:
        for rel, sub, act, expect, why in CASES:
            code, out, err = run(sub, act, rel)
            ok = code == expect
            print(f"  [{'PASS' if ok else 'FAIL'}] {sub}.{act:<10} exit={code} (期望 {expect})  {os.path.basename(rel)}")
            print(f"         {why}")
            if args.verbose or not ok:
                tail = (out or err).strip().splitlines()
                if tail:
                    print(f"         > {tail[0][:150]}")
            if not ok:
                failures.append((rel, code, expect, why))
    finally:
        tmp = os.path.join(PACK, "tests", "_out.xlsx")
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass

    print("=" * 68)
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
