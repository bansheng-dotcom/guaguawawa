# -*- coding: utf-8 -*-
"""engines/__init__.py - R10 视觉设计官 · 十维演进解耦核心引擎包。"""
from __future__ import annotations

from .base import BaseImageEngine, EngineGenResult, EngineProbeResult, ImageGenTask
from .comfyui import ComfyUIEngine
from .sdwebui import SDWebUIEngine
from .cloud_apis import (FooocusEngine, FluxCloudEngine, DalleEngine,
                        MidjourneyEngine, DashScopeWanxEngine, CogViewEngine)
from .manager import EngineManager, get_engine_manager
from .prompter import DesignPrompter, get_design_prompter
from .vlm_critic import VLMCritic, get_vlm_critic
from .inpaint import InpaintEditEngine
from .explorer import StylescapeExplorer
from .layout_spec import LayoutSpecEngine, LayerSpec
from .slop_guard import SlopGuard, SlopAuditReport

# 十维元模型核心引擎层 (L01~L10)
from .runtime_engine import VisualRuntimeEngine
from .intent_compiler import VisualIntentCompiler
from .reflexive_healer import VisualReflexiveHealer
from .spec_ledger import DesignSpecLedger
from .scenario_matrix import VisualScenarioMatrix
from .asset_bundle import VisualAssetBundle
from .diff_patch_engine import VisualDiffPatchEngine
from .session_memory import VisualSessionMemory
from .telemetry_watchdog import WatchdogBreaker, TelemetryTracer

__all__ = [
    # 基础引擎与设备接管
    "BaseImageEngine",
    "EngineGenResult",
    "EngineProbeResult",
    "ImageGenTask",
    "ComfyUIEngine",
    "SDWebUIEngine",
    "FooocusEngine",
    "FluxCloudEngine",
    "DalleEngine",
    "MidjourneyEngine",
    "DashScopeWanxEngine",
    "CogViewEngine",
    "DesignPrompter",
    "get_design_prompter",
    "VLMCritic",
    "get_vlm_critic",
    "EngineManager",
    "get_engine_manager",
    "InpaintEditEngine",
    "StylescapeExplorer",
    "LayoutSpecEngine",
    "LayerSpec",
    "SlopGuard",
    "SlopAuditReport",

    # 十维演进元模型体系 (L01~L10)
    "VisualRuntimeEngine",      # L01
    "VisualIntentCompiler",     # L02
    "VisualReflexiveHealer",    # L03
    "DesignSpecLedger",         # L04
    "VisualScenarioMatrix",     # L06
    "VisualAssetBundle",        # L07
    "VisualDiffPatchEngine",    # L08
    "VisualSessionMemory",      # L09
    "WatchdogBreaker",          # L10
    "TelemetryTracer",          # L10
]
