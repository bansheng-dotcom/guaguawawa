# -*- coding: utf-8 -*-
"""R18 十维演进解耦核心引擎包（SOP v13.0 §七 Golden Standard）。

按演进阶梯逐层解耦，每层一个独立可测模块，主流程 agent.py / skills/ 不反向依赖。
导出采用 PEP 562 惰性属性：包导入时不预加载任何子模块（避免 `python -m engines.x`
触发 runpy 重复导入告警），`from engines import DataEngRuntimeEngine` 时才加载对应层；
尚未落地的层不会阻塞其余层，`available_layers()` 用于演进执行器做物理工件盘点。
"""
from __future__ import annotations

import importlib

# 导出类名 -> 所属模块（按十层元模型顺序）
_EXPORTS = {
    "DataEngRuntimeEngine": "runtime_engine",                 # L01 工具实体层
    "DataEngIntentCompiler": "intent_compiler",               # L02 意图解构层
    "DataEngReflexiveHealer": "reflexive_healer",             # L03 自愈反思层
    "DataEngSpecLedger": "spec_ledger",                       # L04 领域账本层
    "DataEngSlopGuard": "slop_guard",                         # L05 质感去劣化
    "DataEngScenarioMatrix": "scenario_matrix",               # L06 横向决策层
    "DataEngAssetBundle": "asset_bundle",                     # L07 伴生消费层
    "DataEngDiffPatchEngine": "diff_patch_engine",            # L08 局部差量层
    "DataEngSessionMemory": "session_memory",                 # L09 会话记忆层
    "DataEngTelemetryWatchdog": "telemetry_watchdog",         # L10 工业容灾层
    "CircuitBreaker": "telemetry_watchdog",                   # L10 三态熔断器（可独立复用）
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(f"{__name__}.{module_name}")
    return getattr(module, name)


def __dir__():
    return sorted(__all__)


def available_layers():
    """返回当前已落地（可真实导入）的引擎类清单（只统计十层引擎，不含工具类）。"""
    landed = []
    for cls_name, module_name in _EXPORTS.items():
        if not cls_name.startswith("DataEng"):
            continue
        try:
            importlib.import_module(f"{__name__}.{module_name}")
        except ImportError:
            continue
        landed.append(cls_name)
    return sorted(landed)
