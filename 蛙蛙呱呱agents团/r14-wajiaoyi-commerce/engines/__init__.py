# -*- coding: utf-8 -*-
"""engines - R14 蛙交易 · 交易与收入履约官 十维演进解耦核心引擎包。

严格贯彻《Universal Agent 10-Stage Evolution SOP v12.0》要求：
- L01: CommerceRuntimeEngine (真实商品价格阶梯、税费折算、计量聚合与交易健康探针沙箱)
- L02: IntentCompiler (交易履约复合意图解构与 Kahn 拓扑 DAG 编排)
- L03: ReflexiveHealer (交易红线审判与反思自愈引擎)
- L04: SpecLedger (COMMERCE_SPEC 规格账本动态加载与 8 维硬门禁引擎)
- L05: SlopGuard (交易假大空套话清洗与可行动性事实注入引擎)
- L06: ScenarioMatrix (三维交易与结算策略看板裂变引擎)
- L07: CommerceAssetBundle (下游机器可消费资产包与 SARIF/Vega 规范导出)
- L08: CommerceDiffPatchEngine (RFC 6902 交易与订单差量补丁热修引擎)
- L09: CommerceSessionMemory (跨轮会话记忆池、交易槽位代词消歧与快照回滚)
- L10: CommerceTelemetryWatchdog, WatchdogBreaker, TelemetryTracer (三态看门狗熔断、抖动重试与全链路遥测)
"""
from __future__ import annotations

from .runtime_engine import CommerceRuntimeEngine
from .intent_compiler import IntentCompiler
from .reflexive_healer import ReflexiveHealer
from .spec_ledger import SpecLedger
from .slop_guard import SlopGuard
from .scenario_matrix import ScenarioMatrix
from .asset_bundle import CommerceAssetBundle
from .diff_patch_engine import CommerceDiffPatchEngine
from .session_memory import CommerceSessionMemory
from .telemetry_watchdog import CommerceTelemetryWatchdog, WatchdogBreaker, TelemetryTracer

__all__ = [
    "CommerceRuntimeEngine",
    "IntentCompiler",
    "ReflexiveHealer",
    "SpecLedger",
    "SlopGuard",
    "ScenarioMatrix",
    "CommerceAssetBundle",
    "CommerceDiffPatchEngine",
    "CommerceSessionMemory",
    "CommerceTelemetryWatchdog",
    "WatchdogBreaker",
    "TelemetryTracer",
]
