# -*- coding: utf-8 -*-
"""engines/__init__.py - R07 蛙得明 · 产品经理 核心演进引擎导出包."""
from __future__ import annotations

from .pm_runtime_engine import PMRuntimeEngine, PRDParser, PMCalculationEngine
from .intent_dag_compiler import IntentDAGCompiler, AgileProductDeliveryDAG, ProductIntentNode
from .pm_reflexive_healer import PMReflexiveHealer
from .pm_spec_ledger import PMSpecLedger
from .pm_slop_guard import PMSlopGuard
from .scenario_matrix import ScenarioMatrix
from .asset_bundle import (AssetBundleExporter, PRDASTBuilder, SARIFReporter,
                          VegaChartBuilder)
from .diff_patch_engine import (JSONPointer, PatchError, PatchTestFailed,
                                PRDPatchEngine)
from .session_memory import SessionMemory
from .telemetry_watchdog import (CircuitBreaker, CircuitOpenError, TelemetryTracer,
                                 Watchdog, retry_with_backoff)

__all__ = [
    "PMRuntimeEngine",
    "PRDParser",
    "PMCalculationEngine",
    "IntentDAGCompiler",
    "AgileProductDeliveryDAG",
    "ProductIntentNode",
    "PMReflexiveHealer",
    "PMSpecLedger",
    "PMSlopGuard",
    "ScenarioMatrix",
    "AssetBundleExporter",
    "PRDASTBuilder",
    "SARIFReporter",
    "VegaChartBuilder",
    "PRDPatchEngine",
    "JSONPointer",
    "PatchError",
    "PatchTestFailed",
    "SessionMemory",
    "CircuitBreaker",
    "CircuitOpenError",
    "Watchdog",
    "TelemetryTracer",
    "retry_with_backoff",
]
