# -*- coding: utf-8 -*-
"""agents.shared —— `shared/` 的兼容别名包（单一事实来源）。

历史故障：
    本目录曾是 `shared/` 的整份拷贝。因为多嵌套了一层 `agents/`，
    各模块里的 `dirname(dirname(__file__))` 会解析到 `agents/` 而不是仓库根，
    导致图表库路径、日志/报告目录、角色目录全部偏移（图表静默降级为表格）。

修复：
    把 `__path__` 指向真正的 `shared/`，`agents.shared.*` 与 `shared.*`
    加载的是同一份源码，仓库内不再存在两份实现。
"""
from __future__ import annotations

import os

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
__path__ = [os.path.join(_REPO, "shared")]
