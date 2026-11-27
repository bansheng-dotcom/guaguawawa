# -*- coding: utf-8 -*-
"""L10 工业容灾层（共享实现）：三态熔断 + 全抖动退避 + Trace/Span 遥测。

收敛来源：r12-wayingliu-growth（行为更稳健：getattr 兜底、metadata 可选）。
角色适配器：
  - r11: ContentTelemetryWatchdog
  - r12: GrowthTelemetryWatchdog
两者均为本类的别名，不再保留整份副本。
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

from core.base.workspace import role_workspace


class TelemetryWatchdog:
    """通用看门狗：CLOSED / OPEN / HALF_OPEN 三态 + 结构化遥测。"""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_sec: float = 3.0,
        telemetry_file: Optional[str] = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_state_change = time.time()
        self._lock = threading.Lock()

        if not telemetry_file:
            here = os.path.dirname(os.path.abspath(__file__))
            agent_root = os.path.dirname(here)
            telemetry_file = os.path.join(role_workspace(agent_root), "telemetry.jsonl")
        self.telemetry_file = telemetry_file
        os.makedirs(os.path.dirname(self.telemetry_file), exist_ok=True)

    def get_state(self) -> str:
        with self._lock:
            now = time.time()
            if self.state == "OPEN" and (now - self.last_state_change >= self.reset_timeout_sec):
                self.state = "HALF_OPEN"
                self.last_state_change = now
            return self.state

    def record_success(self) -> None:
        with self._lock:
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                self.last_state_change = time.time()
            elif self.state == "CLOSED":
                self.failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = time.time()

    def execute_with_guard(self, func: Callable, *args, **kwargs) -> Any:
        """带熔断器防护的执行守护。"""
        if self.get_state() == "OPEN":
            raise RuntimeError("[CircuitBreaker-OPEN] 熔断器处于开启状态，快速失败保护系统！")
        t0 = time.perf_counter()
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        try:
            res = func(*args, **kwargs)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.record_success()
            self.record_telemetry(trace_id, getattr(func, "__name__", "anonymous_action"),
                                  latency_ms, "SUCCESS", {})
            return res
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.record_failure()
            self.record_telemetry(trace_id, getattr(func, "__name__", "anonymous_action"),
                                  latency_ms, "FAILED", {"error": str(exc)})
            raise

    def retry_with_backoff(
        self,
        func: Callable,
        *args,
        max_retries: int = 3,
        base_delay: float = 0.05,
        max_delay: float = 0.5,
        **kwargs,
    ) -> Any:
        """全抖动指数退避重试（Full Jitter Exponential Backoff）。"""
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                return self.execute_with_guard(func, *args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt == max_retries:
                    break
                ceiling = min(max_delay, base_delay * (2 ** attempt))
                time.sleep(random.uniform(0, ceiling))
        raise last_exc or RuntimeError("重试超限失败")

    def record_telemetry(
        self,
        trace_id: str,
        span_name: str,
        latency_ms: float,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """结构化遥测日志落盘至 telemetry.jsonl。"""
        entry = {
            "trace_id": trace_id,
            "span_name": span_name,
            "latency_ms": round(latency_ms, 2),
            "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "metadata": metadata or {},
        }
        with open(self.telemetry_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# 角色兼容别名：不保留整份副本，只保留名字。
ContentTelemetryWatchdog = TelemetryWatchdog
GrowthTelemetryWatchdog = TelemetryWatchdog
