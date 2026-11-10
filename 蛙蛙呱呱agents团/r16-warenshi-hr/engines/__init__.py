# -*- coding: utf-8 -*-
"""r16-warenshi-hr 核心计算引擎包。
严格遵循 Universal Agent 10-Stage Evolution SOP v13.0 标准规范。
"""
from __future__ import annotations

from .runtime_engine import HRRuntimeEngine
from .intent_compiler import HRIntentCompiler
from .reflexive_healer import HRReflexiveHealer
from .spec_ledger import HRSpecLedger, SpecLedger
from .slop_guard import HRSlopGuard, SlopGuard
from .scenario_matrix import HRScenarioMatrix, ScenarioMatrix
from .asset_bundle import HRAssetBundle
from .diff_patch_engine import HRDiffPatchEngine, DiffPatchEngine
from .session_memory import HRSessionMemory, SessionMemory
from .telemetry_watchdog import HRTelemetryWatchdog, WatchdogBreaker, TelemetryTracer

# 别名设置以兼容各层次调用
AssetBundle = HRAssetBundle
RuntimeEngine = HRRuntimeEngine
IntentCompiler = HRIntentCompiler
ReflexiveHealer = HRReflexiveHealer

__all__ = [
    "HRRuntimeEngine",
    "RuntimeEngine",
    "HRIntentCompiler",
    "IntentCompiler",
    "HRReflexiveHealer",
    "ReflexiveHealer",
    "HRSpecLedger",
    "SpecLedger",
    "HRSlopGuard",
    "SlopGuard",
    "HRScenarioMatrix",
    "ScenarioMatrix",
    "HRAssetBundle",
    "AssetBundle",
    "HRDiffPatchEngine",
    "DiffPatchEngine",
    "HRSessionMemory",
    "SessionMemory",
    "HRTelemetryWatchdog",
    "WatchdogBreaker",
    "TelemetryTracer",
]
