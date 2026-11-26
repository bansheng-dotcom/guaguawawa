# -*- coding: utf-8 -*-
"""core.prose —— 报告正文契约与文笔门禁（P4 第七阶段：已物理归位，shim 已退场）。

3 个模块在本包内；正文生成 `report_prose_gen` 已随报告产线落在 `core/report/`，
这里只做同一入口映射，不复制实现：

    from core.prose import prose_spec
    from core.prose import report_prose_gen

不 import 任何子模块直到被访问（懒加载）。
"""
from __future__ import annotations

import importlib

__all__ = ["prose_spec", "prose_candidates", "prose_style"]

#: 正文生成仍在 core/report/：保持 `core.prose.report_prose_gen` 与 `core.report.report_prose_gen` 同一对象。
_ALIAS = {"report_prose_gen": "core.report.report_prose_gen"}


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.prose." + name)
    if name in _ALIAS:
        return importlib.import_module(_ALIAS[name])
    raise AttributeError(
        "core.prose 没有 %r；可用：%s"
        % (name, ", ".join(sorted(list(__all__) + list(_ALIAS)))))


def __dir__():
    return sorted(list(__all__) + list(_ALIAS))
