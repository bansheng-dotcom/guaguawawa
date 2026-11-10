# -*- coding: utf-8 -*-
"""engines - R13 蛙客成 · 客户成功与销售运营官 十维演进解耦核心引擎包。

严格贯彻《Universal Agent 10-Stage Evolution SOP v11.0》要求：
- L01: CsmRuntimeEngine (真实 NPS / 四维健康分 / HHI / 流失风险沙箱)
- L02: IntentCompiler (客户成功复合意图解构与 Kahn 拓扑 DAG 编排)
- L03: ReflexiveHealer (客户成功红线审判与反思自愈引擎)
- L04: SpecLedger (CSM_SPEC 规格账本动态加载与校验引擎)
- L05: SlopGuard (假大空套话清洗与可行动性强化引擎)
- L06: ScenarioMatrix (多维挽留方案看板裂变引擎)
- L07: CsmAssetBundle (下游机器可消费资产包与 SARIF/Vega 规范导出)
- L08: CsmDiffPatchEngine (RFC 6902 客户成功差量补丁与热修引擎)
- L09: CsmSessionMemory (跨轮会话记忆池、代词消歧与版本回滚)
- L10: CsmTelemetryWatchdog, WatchdogBreaker, TelemetryTracer (三态看门狗熔断、抖动重试与全链路遥测)
"""
from __future__ import annotations

from .runtime_engine import CsmRuntimeEngine
from .intent_compiler import IntentCompiler
from .reflexive_healer import ReflexiveHealer
from .spec_ledger import SpecLedger
from .slop_guard import SlopGuard
from .scenario_matrix import ScenarioMatrix
from .asset_bundle import CsmAssetBundle
from .diff_patch_engine import CsmDiffPatchEngine
from .session_memory import CsmSessionMemory
from .telemetry_watchdog import CsmTelemetryWatchdog, WatchdogBreaker, TelemetryTracer

__all__ = [
    "CsmRuntimeEngine",
    "IntentCompiler",
    "ReflexiveHealer",
    "SpecLedger",
    "SlopGuard",
    "ScenarioMatrix",
    "CsmAssetBundle",
    "CsmDiffPatchEngine",
    "CsmSessionMemory",
    "CsmTelemetryWatchdog",
    "WatchdogBreaker",
    "TelemetryTracer",
]
