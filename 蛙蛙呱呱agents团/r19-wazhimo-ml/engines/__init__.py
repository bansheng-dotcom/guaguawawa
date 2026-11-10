# -*- coding: utf-8 -*-
"""r19-wazhimo-ml 十维演进解耦核心引擎包 (SOP v13.0)。

L01 runtime_engine     真实评估精算沙箱（指标/分位/守恒/资产取证）
L02 intent_compiler    复合诉求 → 5 阶段 Kahn 交付 DAG
L03 reflexive_healer   Reflexion 自纠闭环 + 五条红线刚性审判
L04 spec_ledger        ML_SPEC.md 单一信任源 + 8 维发布硬门禁
L05 slop_guard         质感去劣化（假大空清洗/量化证据/DRI/行动力）
L06 scenario_matrix    三维发布方案裂变 + MCDA 权衡矩阵
L07 asset_bundle       伴生消费（Bundle / SARIF 2.1.0 / Vega-Lite）
L08 diff_patch_engine  RFC 6902 差量热修 + 指标增量重算
L09 session_memory     持久化记忆池 + 代词消歧 + 快照回滚
L10 telemetry_watchdog 三态熔断 + 全抖动退避 + 全链路遥测

说明：采用懒加载（PEP 562），避免 `python -m engines.xxx` 探针触发
「module found in sys.modules before execution」告警，同时保持
`from engines import R19RuntimeEngine` 的调用契约不变。
"""
from __future__ import annotations

import importlib
from typing import Dict, Tuple

_LAZY: Dict[str, Tuple[str, str]] = {
    # L01
    "R19RuntimeEngine": (".runtime_engine", "R19RuntimeEngine"),
    "RuntimeEngine": (".runtime_engine", "R19RuntimeEngine"),
    "MetricSandboxError": (".runtime_engine", "MetricSandboxError"),
    # L02
    "R19IntentCompiler": (".intent_compiler", "R19IntentCompiler"),
    "IntentCompiler": (".intent_compiler", "R19IntentCompiler"),
    # L03
    "R19ReflexiveHealer": (".reflexive_healer", "R19ReflexiveHealer"),
    "ReflexiveHealer": (".reflexive_healer", "R19ReflexiveHealer"),
    "RedlineViolation": (".reflexive_healer", "RedlineViolation"),
    "REDLINES": (".reflexive_healer", "REDLINES"),
    # L04
    "R19SpecLedger": (".spec_ledger", "R19SpecLedger"),
    "SpecLedger": (".spec_ledger", "R19SpecLedger"),
    # L05
    "MLSlopGuard": (".slop_guard", "MLSlopGuard"),
    "SlopGuard": (".slop_guard", "MLSlopGuard"),
    # L06
    "R19ScenarioMatrix": (".scenario_matrix", "R19ScenarioMatrix"),
    "ScenarioMatrix": (".scenario_matrix", "R19ScenarioMatrix"),
    # L07
    "R19AssetBundle": (".asset_bundle", "R19AssetBundle"),
    "AssetBundle": (".asset_bundle", "R19AssetBundle"),
    # L08
    "R19DiffPatchEngine": (".diff_patch_engine", "R19DiffPatchEngine"),
    "DiffPatchEngine": (".diff_patch_engine", "R19DiffPatchEngine"),
    "PatchError": (".diff_patch_engine", "PatchError"),
    "recompute_derived": (".diff_patch_engine", "recompute_derived"),
    # L09
    "R19SessionMemory": (".session_memory", "R19SessionMemory"),
    "SessionMemory": (".session_memory", "R19SessionMemory"),
    # L10
    "R19TelemetryWatchdog": (".telemetry_watchdog", "R19TelemetryWatchdog"),
    "TelemetryWatchdog": (".telemetry_watchdog", "R19TelemetryWatchdog"),
    "WatchdogBreaker": (".telemetry_watchdog", "WatchdogBreaker"),
    "SlidingWindowBreaker": (".telemetry_watchdog", "SlidingWindowBreaker"),
    "TelemetryTracer": (".telemetry_watchdog", "TelemetryTracer"),
    "CLOSED": (".telemetry_watchdog", "CLOSED"),
    "OPEN": (".telemetry_watchdog", "OPEN"),
    "HALF_OPEN": (".telemetry_watchdog", "HALF_OPEN"),
}

__all__ = sorted(_LAZY)


def __getattr__(name: str):
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = target
    mod = importlib.import_module(module_name, __name__)
    value = getattr(mod, attr)
    globals()[name] = value
    return value


def __dir__():
    return sorted(list(globals()) + __all__)
