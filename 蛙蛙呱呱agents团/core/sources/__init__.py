# -*- coding: utf-8 -*-
"""core.sources —— 来源与覆盖（P4 第二阶段：已物理归位，shim 已退场）。

    from core.sources import source_verify, coverage_plan, supply_plan

不 import 任何子模块直到被访问（懒加载），避免循环依赖。
"""
from __future__ import annotations

import importlib

__all__ = [
    "source_verify", "source_freshness", "source_match", "source_profile",
    "collection_contract", "collection_gen", "collection_spec",
    "coverage_plan", "coverage_confirm", "coverage_policy", "coverage_wire",
    "supply_plan", "research_intake", "research_protocol",
]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.sources." + name)
    raise AttributeError(
        "core.sources 没有 %r；可用：%s" % (name, ", ".join(sorted(__all__))))


def __dir__():
    return sorted(__all__)
