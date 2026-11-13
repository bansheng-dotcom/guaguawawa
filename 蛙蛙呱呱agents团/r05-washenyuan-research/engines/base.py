# -*- coding: utf-8 -*-
"""R05 蛙深远（战略研究官）底层引擎规范与数据契约。

对标标杆:
- OpenBB-finance/OpenBB / DuckDB / Temporal / OpenTelemetry
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

class BaseResearchEngine(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def probe(self) -> EngineProbeResult:
        """检查引擎底座、证据库及研报驱动健康状态。"""
        pass

    @abstractmethod
    def execute(self, action: str, payload: Dict[str, Any]) -> ExecutionResult:
        """执行研究取证、集中度测算或规模评估动作。"""
        pass
