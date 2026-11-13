# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 决策编排引擎底层接口规范与数据契约。

对标 GitHub 开源标杆:
- Temporal (14k+ stars) / Celery (25k+ stars) / CrewAI (20k+ stars)
- 提供标准 probe / execute / degrade 机制。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time

@dataclass
class EngineProbeResult:
    engine_name: str
    available: bool
    status_code: int = 200
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionResult:
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    engine: str = "base"

class BaseDecisionEngine(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def probe(self) -> EngineProbeResult:
        """检查引擎及后端依赖健康状态。"""
        pass

    @abstractmethod
    def execute(self, action: str, payload: Dict[str, Any]) -> ExecutionResult:
        """执行战略决策或全局编排动作。"""
        pass
