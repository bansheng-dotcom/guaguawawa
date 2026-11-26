# -*- coding: utf-8 -*-
"""core.cards —— 拆卡 / 发卡 / 收卡（P4 第五阶段：已物理归位，shim 已退场）。

7 个卡模块在本包内；拆卡线其余成员已分散到 core/claims、core/sources 等包，
这里只给同一入口，不复制实现：

    from core.cards import card_issue
    from core.cards import dispatch

不 import 任何子模块直到被访问（懒加载），避免卡模块之间的循环依赖。
"""
from __future__ import annotations

import importlib

__all__ = [
    "card_plan", "card_issue", "card_probe", "card_bundle", "card_upgrade",
    "dispatch", "report_dispatch",
]

#: 拆卡线里仍平铺在 core/ 的成员：保持 `core.cards.X` 与 `core.X` 同一对象。
_FLAT = {
    "grid_attach": "core.grid_attach",
    "cells_claims": "core.claims.cells_claims",
    "collection_contract": "core.sources.collection_contract",
    "collab": "core.collab",
    "parallel_research": "core.parallel_research",
    "research_protocol": "core.sources.research_protocol",
    "research_intake": "core.sources.research_intake",
}


def __getattr__(name):
    if name in __all__:
        return importlib.import_module("core.cards." + name)
    if name in _FLAT:
        return importlib.import_module(_FLAT[name])
    raise AttributeError(
        "core.cards 没有 %r；可用：%s"
        % (name, ", ".join(sorted(list(__all__) + list(_FLAT)))))


def __dir__():
    return sorted(list(__all__) + list(_FLAT))
