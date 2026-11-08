# -*- coding: utf-8 -*-
"""共享回归测试的 pytest 夹具（修掉 pytest 在仓库根收集时 import 失败）。

历史故障（Stage 1 体检记录）：
    在仓库根执行 `python -m pytest agents/tests/regression` 时，
    test_foundation.py 抛 `ModuleNotFoundError: No module named 'core'`。
    根因：`core` / `shared` 是 `agents/` 下的包，pytest 只把 rootdir 加进
    sys.path，不会自动加 `agents/`。
    修复：用 `__file__` 推导绝对路径把 `agents/` 与仓库根同时注入 sys.path
    （META-001 关键教训 #1：禁止相对路径推导）。
"""
from __future__ import annotations

import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(os.path.dirname(TESTS_DIR))      # agents/
REPO = os.path.dirname(AGENTS)                             # 仓库根

for _p in (AGENTS, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
