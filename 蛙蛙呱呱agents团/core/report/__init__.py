# -*- coding: utf-8 -*-
"""core.report —— 报告产线（P4 第六阶段：已物理归位，shim 已退场）。

20 个平铺报告模块在本包内；`report_kernel/`、`report_theme/` 本来就是真包，
保持原地不动（迁进来只会制造两份模块身份）。

    from core.report import report_flow
    from core.report import report_cli

不 import 任何子模块直到被访问（懒加载）。
"""
from __future__ import annotations

import importlib

__all__ = [
    "report_assembly", "report_bridge", "report_clarify", "report_cli",
    "report_contract", "report_editorial", "report_exchange", "report_flow",
    "report_ir", "report_layout", "report_line", "report_marks",
    "report_model", "report_quality", "report_renderer",
    "report_roles", "report_structure", "report_thesis", "flow_report",
]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.report." + name)
    raise AttributeError(
        "core.report 没有 %r；可用：%s" % (name, ", ".join(sorted(__all__))))


def __dir__():
    return sorted(__all__)
