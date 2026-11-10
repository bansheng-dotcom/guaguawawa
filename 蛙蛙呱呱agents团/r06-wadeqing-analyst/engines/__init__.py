# -*- coding: utf-8 -*-
"""R06 蛙得清 · 数据分析引擎集群 (Engines Package)
依据 SOP_AGENT_EVOLUTION_UNIVERSAL.md 规范：
十座工程与认知大山 (L01~L10) 模块化解耦实现。
"""
from .analysis_engine import (
    AnalysisEngineManager,
    DuckDBSQLSandbox,
    NativeAnalysisEngine,
    AnalyticalQueryResult,
)
from .intent_decompiler import AnalysisIntentDecompiler
from .reflexive_healer import AnalysisReflexiveHealer
from .metrics_spec_ledger import MetricsSpecLedgerParser
from .data_slop_guard import DataSlopGuard
from .scenario_matrix import ScenarioComparativeMatrix
from .asset_bundle import AnalysisAssetBundle
from .diff_patch_engine import AnalysisDiffPatchEngine
from .session_memory import AnalysisSessionMemoryPool
from .telemetry_watchdog import (
    AnalysisWatchdogBreaker,
    AnalysisTelemetryTracer,
    TimeoutException,
)

__all__ = [
    "AnalysisEngineManager",
    "DuckDBSQLSandbox",
    "NativeAnalysisEngine",
    "AnalyticalQueryResult",
    "AnalysisIntentDecompiler",
    "AnalysisReflexiveHealer",
    "MetricsSpecLedgerParser",
    "DataSlopGuard",
    "ScenarioComparativeMatrix",
    "AnalysisAssetBundle",
    "AnalysisDiffPatchEngine",
    "AnalysisSessionMemoryPool",
    "AnalysisWatchdogBreaker",
    "AnalysisTelemetryTracer",
    "TimeoutException",
]
