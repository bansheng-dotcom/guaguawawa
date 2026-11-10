# -*- coding: utf-8 -*-
"""engines - R11 蛙点题 · 内容主笔与文案运营 十维演进解耦核心引擎包。

严格遵循《SOP_AGENT_EVOLUTION_UNIVERSAL.md v9.0》：
- L01: CopyRuntimeEngine (真实文案沙箱、排版字数精算、敏感词排查与健康探针)
- L02: IntentDAGCompiler (复杂文案运营意图解构与 Kahn 拓扑 DAG 编排)
- L03: CopyReflexiveHealer (广告法极限词拦截、未授权发布阻断与闭环自愈)
- L04: CopySpecLedger (COPY_SPEC.md 领域业务账本动态加载与校验)
- L05: CopySlopGuard (AI 味与假大空套话物理清洗、Actionability 量化打分)
- L06: ScenarioMatrix (三维风格版本裂变与全链路 ROI 权衡矩阵)
- L07: ContentAssetBundle (下游机器消费资产包与 OASIS SARIF v2.1.0 导出)
- L08: ContentDiffPatchEngine (RFC 6902 JSON Patch 增量热修与段落级差量应用)
- L09: ContentSessionMemory (多轮会话记忆池、代词消歧与快照树回滚)
- L10: ContentTelemetryWatchdog (三态熔断看门狗、指数退避重试与全链路遥测)
"""
from __future__ import annotations

from .copy_runtime_engine import CopyRuntimeEngine
from .intent_compiler import IntentDAGCompiler
from .copy_reflexive_healer import CopyReflexiveHealer
from .copy_spec_ledger import CopySpecLedger
from .copy_slop_guard import CopySlopGuard
from .scenario_matrix import ScenarioMatrix
from .asset_bundle import ContentAssetBundle
from .diff_patch_engine import ContentDiffPatchEngine
from .session_memory import ContentSessionMemory
from .telemetry_watchdog import ContentTelemetryWatchdog

__all__ = [
    "CopyRuntimeEngine",
    "IntentDAGCompiler",
    "CopyReflexiveHealer",
    "CopySpecLedger",
    "CopySlopGuard",
    "ScenarioMatrix",
    "ContentAssetBundle",
    "ContentDiffPatchEngine",
    "ContentSessionMemory",
    "ContentTelemetryWatchdog",
]
