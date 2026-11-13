# -*- coding: utf-8 -*-
"""r15-wagongying-erp 十维演进解耦核心引擎包。
严格遵循 Universal Agent 10-Stage Evolution SOP v12.0 标准规范。
"""
from __future__ import annotations

from .runtime_engine import ERPRuntimeEngine
from .intent_compiler import IntentCompiler
from .reflexive_healer import ReflexiveHealer
from .spec_ledger import SpecLedger
from .slop_guard import SupplySlopGuard, SlopGuard
from .scenario_matrix import SupplyScenarioMatrix, ScenarioMatrix
from .asset_bundle import ERPAssetBundle
from .diff_patch_engine import ERPDiffPatchEngine
from .session_memory import ERPSessionMemory
from .telemetry_watchdog import ERPTelemetryWatchdog, WatchdogBreaker, TelemetryTracer

__all__ = [
    "ERPRuntimeEngine",
    "IntentCompiler",
    "ReflexiveHealer",
    "SpecLedger",
    "SupplySlopGuard",
    "SlopGuard",
    "SupplyScenarioMatrix",
    "ScenarioMatrix",
    "ERPAssetBundle",
    "ERPDiffPatchEngine",
    "ERPSessionMemory",
    "ERPTelemetryWatchdog",
    "WatchdogBreaker",
    "TelemetryTracer",
]
