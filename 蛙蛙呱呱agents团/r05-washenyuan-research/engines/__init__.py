# -*- coding: utf-8 -*-
"""engines 模块统一导出入口。"""
from engines.base import BaseResearchEngine, EngineProbeResult, ExecutionResult
from engines.manager import ResearchEngineManager, NativeResearchEngine
from engines.prompter import ResearchPrompter
from engines.critic import ResearchCritic
from engines.ledger import ResearchLedgerParser
from engines.slop_guard import ResearchSlopGuard
from engines.scenario_matrix import ScenarioMatrixExplorer
from engines.asset_bundle import ResearchAssetBundle
from engines.patch_editor import ResearchPatchEditor
from engines.memory import SessionMemoryPool
from engines.telemetry import WatchdogCircuitBreaker, ProductionTelemetry
# Round 1 / Stage 1 执行基石阶段新增实体（L01 运行时算子沙箱 / L02 意图编译器 /
# L03 深层自愈器），保持 engines 包单一导出入口，下游 CLI 与轮次探针统一消费。
from engines.runtime_engine import EvidenceTierValidator, ResearchRuntimeEngine
from engines.intent_compiler import DagCycleError, ResearchIntentCompiler
from engines.reflexive_healer import RedlineBlocked, ReflexiveResearchHealer
# Round 2 / Stage 2 专业深度阶段新增实体（L04 机器可读 SSOT 账本）
from engines.spec_ledger import ResearchSpecLedger
# Round 3 / Stage 3 工业交付阶段新增实体（L08 差量引擎 / L09 会话存储 /
# L10 三态容灾），旧模块 patch_editor / memory / telemetry 契约保持不变。
from engines.diff_patch_engine import (PatchError, PatchTestFailed,
                                       ResearchDiffPatchEngine)
from engines.session_memory import ResearchSessionStore
from engines.telemetry_watchdog import (CircuitBreaker, CircuitOpenError,
                                        RetryExhausted, RetryPolicy, TaskTimeout,
                                        TelemetryTracer, WatchdogRunner)

__all__ = [
    "BaseResearchEngine",
    "EngineProbeResult",
    "ExecutionResult",
    "ResearchEngineManager",
    "NativeResearchEngine",
    "ResearchPrompter",
    "ResearchCritic",
    "ResearchLedgerParser",
    "ResearchSlopGuard",
    "ScenarioMatrixExplorer",
    "ResearchAssetBundle",
    "ResearchPatchEditor",
    "SessionMemoryPool",
    "WatchdogCircuitBreaker",
    "ProductionTelemetry",
    "ResearchRuntimeEngine",
    "EvidenceTierValidator",
    "ResearchIntentCompiler",
    "DagCycleError",
    "ReflexiveResearchHealer",
    "RedlineBlocked",
    "ResearchDiffPatchEngine",
    "PatchError",
    "PatchTestFailed",
    "ResearchSessionStore",
    "ResearchSpecLedger",
    "CircuitBreaker",
    "CircuitOpenError",
    "RetryPolicy",
    "RetryExhausted",
    "TaskTimeout",
    "WatchdogRunner",
    "TelemetryTracer"
]
