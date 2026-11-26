# -*- coding: utf-8 -*-
"""core.claims —— 断言与格子（P4 第四阶段：已物理归位，shim 已退场）。

    from core.claims import claims, cells_unified, cell_claim

不 import 任何子模块直到被访问（懒加载），避免循环依赖。
"""
from __future__ import annotations

import importlib

__all__ = [
    "claims", "claims_v4", "claim_consistency",
    "cell_claim", "cells_claims", "cells_unified",
]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.claims." + name)
    raise AttributeError(
        "core.claims 没有 %r；可用：%s" % (name, ", ".join(sorted(__all__))))


def __dir__():
    return sorted(__all__)
