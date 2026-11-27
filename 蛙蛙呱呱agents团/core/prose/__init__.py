# -*- coding: utf-8 -*-
"""core.prose —— 报告正文契约与生成（P5-7 五合一，2026-11-27）。

    from core.prose import prose_contract   # 11 字段契约 + 文笔门禁
    from core.prose import prose_render     # 受约束合成 + 多候选淘汰

原 `prose_spec / prose_style / prose_candidates / report_prose_gen`
已合并为上面两个模块，产物语义不变。

不 import 任何子模块直到被访问（懒加载）。
"""
from __future__ import annotations

import importlib

__all__ = ["prose_contract", "prose_render"]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.prose." + name)
    raise AttributeError(
        "core.prose 没有 %r；可用：%s" % (name, ", ".join(sorted(__all__))))


def __dir__():
    return sorted(__all__)
