# -*- coding: utf-8 -*-
"""r20-washouzhi-sre 十维演进解耦核心引擎包 (SOP v13.0)。

L01 runtime_engine      SRE 可靠性精算沙箱（SLI/错误预算/MTTR/RPO-RTO）
L02 intent_compiler     复合故障诉求 → 5 阶段 Kahn 恢复 DAG
L03 reflexive_healer    告警归一 + Reflexion 自愈 + 五条可靠性红线
L04 spec_ledger         SRE_SPEC.md 单一信任源 + 8 维发布硬门禁
L05 slop_guard          SRE 假大空清洗 + 量化证据 + DRI + 行动力
L06 scenario_matrix     三维处置方案裂变 + MCDA 权衡矩阵
L07 asset_bundle        Bundle / OASIS SARIF 2.1.0 / Vega-Lite
L08 diff_patch_engine   RFC 6902 差量热修 + 配置不变量复核
L09 session_memory      持久化记忆池 + 代词消歧 + 快照回滚
L10 telemetry_watchdog  三态熔断 + 全抖动退避 + 全链路遥测

采用 PEP 562 懒加载，避免 `python -m engines.xxx` 探针触发
「module found in sys.modules before execution」告警，同时保持
`from engines import R20RuntimeEngine` 的调用契约稳定。
"""
from __future__ import annotations

import importlib
from typing import Dict, Tuple

_LAZY: Dict[str, Tuple[str, str]] = {
    # L01
    "R20RuntimeEngine": (".runtime_engine", "R20RuntimeEngine"),
    "RuntimeEngine": (".runtime_engine", "R20RuntimeEngine"),
    "ReliabilitySandboxError": (".runtime_engine", "ReliabilitySandboxError"),
    # L02
    "R20IntentCompiler": (".intent_compiler", "R20IntentCompiler"),
    "IntentCompiler": (".intent_compiler", "R20IntentCompiler"),
    # L03
    "R20ReflexiveHealer": (".reflexive_healer", "R20ReflexiveHealer"),
    "ReflexiveHealer": (".reflexive_healer", "R20ReflexiveHealer"),
    "RedlineViolation": (".reflexive_healer", "RedlineViolation"),
    "REDLINES": (".reflexive_healer", "REDLINES"),
    # L04
    "R20SpecLedger": (".spec_ledger", "R20SpecLedger"),
    "SpecLedger": (".spec_ledger", "R20SpecLedger"),
    # L05
    "SreSlopGuard": (".slop_guard", "SreSlopGuard"),
    "SlopGuard": (".slop_guard", "SreSlopGuard"),
    # L06
    "R20ScenarioMatrix": (".scenario_matrix", "R20ScenarioMatrix"),
    "ScenarioMatrix": (".scenario_matrix", "R20ScenarioMatrix"),
    # L07
    "R20AssetBundle": (".asset_bundle", "R20AssetBundle"),
    "AssetBundle": (".asset_bundle", "R20AssetBundle"),
    # L08
    "R20DiffPatchEngine": (".diff_patch_engine", "R20DiffPatchEngine"),
    "DiffPatchEngine": (".diff_patch_engine", "R20DiffPatchEngine"),
    "PatchError": (".diff_patch_engine", "PatchError"),
    # L09
    "R20SessionMemory": (".session_memory", "R20SessionMemory"),
    "SessionMemory": (".session_memory", "R20SessionMemory"),
    # L10
    "R20TelemetryWatchdog": (".telemetry_watchdog", "R20TelemetryWatchdog"),
    "TelemetryWatchdog": (".telemetry_watchdog", "R20TelemetryWatchdog"),
    "WatchdogBreaker": (".telemetry_watchdog", "WatchdogBreaker"),
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
