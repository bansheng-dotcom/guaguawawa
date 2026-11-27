# -*- coding: utf-8 -*-
"""一人公司 · 20 角色智能体专家团（仓库根包）。

本文件只做一件事：把仓库父目录注入 `sys.path`，供从任意 cwd 启动角色时复用。

历史（Stage 1 体检 → 2026-11-27 收敛）：
    曾有 `agents/` 兼容别名包，让角色里的 `from agents.shared.xxx import ...`
    在「任意 cwd / 任意入口」下都能解析。
    2026-11-27 起 20 个角色统一 `from shared.xxx import ...`，别名包已删除；
    直接用仓库根即可，不再需要多层 `agents.shared` 路径。
"""
from __future__ import annotations

import os
import sys

# 仓库根（本文件所在目录的父目录）——即 agents 包的父目录，供子模块互相导入时复用。
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

__all__ = ["REPO_ROOT"]
