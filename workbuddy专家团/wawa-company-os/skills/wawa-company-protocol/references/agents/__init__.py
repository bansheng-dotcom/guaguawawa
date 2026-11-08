# -*- coding: utf-8 -*-
"""一人公司 · 20 角色智能体专家团（agents 包）。

本文件存在的唯一目的：把 `agents` 变成**真正的 Python 包**，
从而让 20 个角色目录里的 `from agents.shared.xxx import ...` 在
「任意 cwd / 任意入口」下都能解析。

历史故障（Stage 1 体检记录）：
    r02~r20 在角色目录内直接 `python agent.py manifest` 时抛
        ModuleNotFoundError: No module named 'agents'
    根因：仓库根目录没有 `agents/__init__.py`，`agents` 不是包；
    在 `D:\\一人公司\\agents\\` 下运行时，`import agents` 永远失败，
    必须手工设置 PYTHONPATH=D:\\一人公司 才能跑通。
    修复：补本文件 + 各 agent.py 用 `__file__` 把仓库根注入 sys.path。
"""
from __future__ import annotations

import os
import sys

# 仓库根（D:\一人公司）——即 agents 包的父目录，供子模块互相导入时复用。
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

__all__ = ["REPO_ROOT"]
