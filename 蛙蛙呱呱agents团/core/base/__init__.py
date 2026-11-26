# -*- coding: utf-8 -*-
"""core.base —— 地基模块（P4 第一阶段：已物理归位，shim 已退场）。

    from core.base import paths, workspace, project, registry, protocol

不 import 任何子模块直到被访问（懒加载），避免循环依赖。
"""
from __future__ import annotations

import importlib

__all__ = ["paths", "workspace", "project", "registry", "protocol"]


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.base." + name)
    raise AttributeError(
        "core.base 没有 %r；可用：%s" % (name, ", ".join(sorted(__all__))))


def __dir__():
    return sorted(__all__)
