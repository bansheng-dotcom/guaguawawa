# -*- coding: utf-8 -*-
"""core.data —— 数据层（P4 第二阶段：已物理归位，shim 已退场）。

    from core.data import fact_table, dataset, data_model

不 import 任何子模块直到被访问（懒加载），避免循环依赖。
"""
from __future__ import annotations

import importlib

__all__ = [
    "analysis_desk", "analysis_pipeline", "analysis_unit",
    "dataset", "dataset_gates", "dataset_query",
    "data_contract", "data_model", "data_profile", "data_shape",
    "data_standard", "evidence_pack", "fact_table",
]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.data." + name)
    raise AttributeError(
        "core.data 没有 %r；可用：%s" % (name, ", ".join(sorted(__all__))))


def __dir__():
    return sorted(__all__)
