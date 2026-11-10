# -*- coding: utf-8 -*-
"""图像生成引擎抽象基类与通用数据结构。

规范所有外置生图软件（ComfyUI, SD-WebUI, Fooocus 等）
以及云端 API（FLUX, Midjourney, DALL-E 3, 通义万相, 智谱 CogView 等）的接入契约。
"""
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImageGenTask:
    """标准生图任务输入参数包。"""
    prompt: str                                   # 正向提示词（英文/中文）
    negative_prompt: str = ""                     # 负向提示词
    width: int = 1024                             # 宽度
    height: int = 1024                            # 高度
    steps: int = 25                               # 采样步数
    cfg_scale: float = 7.0                        # 提示词引导系数 (CFG)
    seed: int = -1                                # 随机种子 (-1 为随机)
    sampler_name: str = "Euler a"                 # 采样器
    batch_size: int = 1                           # 出图数量
    style: str = "cyberpunk"                      # 风格标记
    model_name: Optional[str] = None              # 指定底模
    loras: List[Dict[str, Any]] = field(default_factory=list)  # LoRA 列表: [{"name": "xxx", "strength": 0.8}]
    extra_params: Dict[str, Any] = field(default_factory=dict) # 针对特定引擎的专有参数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "width": self.width,
            "height": self.height,
            "steps": self.steps,
            "cfg_scale": self.cfg_scale,
            "seed": self.seed,
            "sampler_name": self.sampler_name,
            "batch_size": self.batch_size,
            "style": self.style,
            "model_name": self.model_name,
            "loras": self.loras,
            "extra_params": self.extra_params,
        }


@dataclass
class EngineProbeResult:
    """引擎健康度与在线探测结果。"""
    engine_name: str
    online: bool
    endpoint: str
    latency_ms: float = 0.0
    models: List[str] = field(default_factory=list)
    version: str = ""
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine_name,
            "online": self.online,
            "endpoint": self.endpoint,
            "latency_ms": round(self.latency_ms, 2),
            "models": self.models[:10],
            "version": self.version,
            "details": self.details,
        }


@dataclass
class EngineGenResult:
    """生图执行产物。"""
    ok: bool
    engine_name: str
    image_paths: List[str] = field(default_factory=list)
    seed_used: int = -1
    elapsed_seconds: float = 0.0
    prompt_used: str = ""
    error: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "engine": self.engine_name,
            "image_paths": self.image_paths,
            "seed_used": self.seed_used,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "prompt_used": self.prompt_used,
            "error": self.error,
            "raw_response": self.raw_response,
        }


class BaseImageEngine(ABC):
    """生图驱动引擎抽象基类。"""

    def __init__(self, name: str, endpoint: str, enabled: bool = True):
        self.name = name
        self.endpoint = endpoint.rstrip("/")
        self.enabled = enabled

    @abstractmethod
    def probe(self, timeout: float = 2.0) -> EngineProbeResult:
        """探测引擎是否在线、响应延迟及可用模型。"""
        pass

    @abstractmethod
    def generate(self, task: ImageGenTask, output_dir: str) -> EngineGenResult:
        """执行文生图，并将高清图片下载/保存到 output_dir。"""
        pass
