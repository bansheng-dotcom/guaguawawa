#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""委托到团队级一致性检查器（唯一实现在团队根 `scripts/check_threshold_consistency.py`）。

为什么是委托而不是复制：
    检查器的实现必须只有一份，否则「检查规则」自己就会分叉——
    这正是本卡要防的病。本文件只做路径解析与转发。

用法与团队级脚本完全一致：
    python scripts/check_threshold_consistency.py
    python scripts/check_threshold_consistency.py --json
    python scripts/check_threshold_consistency.py --self-test
"""
from __future__ import annotations

import os
import runpy
import sys

TARGET = os.path.join("scripts", "check_threshold_consistency.py")


def find_target(start: str) -> str:
    """向上找团队根的检查器；**跳过自身**，否则会 runpy 递归到自己。"""
    me = os.path.abspath(__file__)
    cur = os.path.abspath(start)
    for _ in range(10):
        cand = os.path.join(cur, TARGET)
        if os.path.isfile(cand) and os.path.abspath(cand) != me:
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return ""


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    target = find_target(here)
    if not target:
        print(f"[delegate] 找不到团队级脚本 {TARGET}（应从团队根运行）", file=sys.stderr)
        return 2
    sys.argv[0] = target
    runpy.run_path(target, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
