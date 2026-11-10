# -*- coding: utf-8 -*-
"""r17-wazhiwang-automation 核心计算引擎包。
严格遵循 Universal Agent 10-Stage Evolution SOP v13.0 标准规范。
"""
from __future__ import annotations

from .runtime_engine import AutomationRuntimeEngine
from .intent_compiler import AutomationIntentCompiler
from .reflexive_healer import AutomationReflexiveHealer
from .spec_ledger import AutomationSpecLedger, SpecLedger
from .slop_guard import AutomationSlopGuard, SlopGuard
from .scenario_matrix import AutomationScenarioMatrix, ScenarioMatrix
from .asset_bundle import AutomationAssetBundle, AssetBundle
from .diff_patch_engine import AutomationDiffPatchEngine, DiffPatchEngine
from .session_memory import AutomationSessionMemory, SessionMemory
from .telemetry_watchdog import AutomationTelemetryWatchdog, WatchdogBreaker, TelemetryTracer

# 别名设置以兼容各层次调用
RuntimeEngine = AutomationRuntimeEngine
IntentCompiler = AutomationIntentCompiler
ReflexiveHealer = AutomationReflexiveHealer

__all__ = [
    "AutomationRuntimeEngine",
    "RuntimeEngine",
    "AutomationIntentCompiler",
    "IntentCompiler",
    "AutomationReflexiveHealer",
    "ReflexiveHealer",
    "AutomationSpecLedger",
    "SpecLedger",
    "AutomationSlopGuard",
    "SlopGuard",
    "AutomationScenarioMatrix",
    "ScenarioMatrix",
    "AutomationAssetBundle",
    "AssetBundle",
    "AutomationDiffPatchEngine",
    "DiffPatchEngine",
    "AutomationSessionMemory",
    "SessionMemory",
    "AutomationTelemetryWatchdog",
    "WatchdogBreaker",
    "TelemetryTracer",
]
