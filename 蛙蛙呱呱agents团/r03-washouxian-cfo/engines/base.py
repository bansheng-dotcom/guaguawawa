# -*- coding: utf-8 -*-
"""R03 蛙守线 CFO 引擎底层接口规范与数据契约。

对标 GitHub 开源标杆:
- DuckDB / FinOps / Temporal / OpenTelemetry
- 提供财务与合规底座的 probe / execute / audit 核心契约。
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

class BaseFinancialEngine(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def probe(self) -> EngineProbeResult:
        """检查引擎底座、算子库及合规规则健康状态。"""
        pass

    @abstractmethod
    def execute(self, action: str, payload: Dict[str, Any]) -> ExecutionResult:
        """执行财务精算、合规排查或风控审计动作。"""
        pass
