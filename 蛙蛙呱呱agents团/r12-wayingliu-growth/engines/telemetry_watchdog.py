# -*- coding: utf-8 -*-
"""engines/telemetry_watchdog.py - L10 工业容灾层 (Watchdog Circuit Breaker & Telemetry).

对标标杆: Temporal / Tenacity / OpenTelemetry (Stars > 25k)
核心功能:
1. 三态看门狗熔断器 (CLOSED / OPEN / HALF_OPEN)
2. 带全抖动的指数退避重试机制 (Exponential Backoff with Full Jitter)
3. 全链路结构化遥测追踪落盘至 workspace/telemetry.jsonl
"""
from __future__ import annotations

import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional


class GrowthTelemetryWatchdog:
    """增长运营工业级看门狗熔断与全链路遥测追踪器。"""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_sec: float = 3.0,
        telemetry_file: Optional[str] = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
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
        current_state = self.get_state()
        if current_state == "OPEN":
            raise RuntimeError(f"[CircuitBreaker-OPEN] 增长看门狗熔断器处于开启状态，快速失败保护系统！")

        t0 = time.perf_counter()
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        try:
            res = func(*args, **kwargs)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.record_success()
            self.record_telemetry(trace_id, getattr(func, "__name__", "anonymous_action"), latency_ms, "SUCCESS", {})
            return res
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self.record_failure()
            self.record_telemetry(trace_id, getattr(func, "__name__", "anonymous_action"), latency_ms, "FAILED", {"error": str(e)})
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
        """全抖动指数退避重试 (Full Jitter Exponential Backoff)。"""
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                return self.execute_with_guard(func, *args, **kwargs)
            except Exception as e:
                last_exc = e
                if attempt == max_retries:
                    break
                # AWS 全抖动: sleep = random_between(0, min(cap, base * 2 ** attempt))
                ceiling = min(max_delay, base_delay * (2 ** attempt))
                jittered_delay = random.uniform(0, ceiling)
                time.sleep(jittered_delay)
        raise last_exc or RuntimeError("重试超限失败")

    def record_telemetry(
        self,
        trace_id: str,
        span_name: str,
        latency_ms: float,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """结构化遥测日志追踪落盘至 telemetry.jsonl。"""
        metadata = metadata or {}
        entry = {
            "trace_id": trace_id,
            "span_name": span_name,
            "latency_ms": round(latency_ms, 2),
            "status": status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "metadata": metadata,
        }
        with open(self.telemetry_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
