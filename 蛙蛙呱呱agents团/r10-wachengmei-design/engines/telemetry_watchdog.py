# -*- coding: utf-8 -*-
"""engines/telemetry_watchdog.py - R10 视觉设计官 · L10 工业容灾与全链路可观测层 (Watchdog & Telemetry).

对标 Temporal / Tenacity / OpenTelemetry (Stars > 25k)：
1. 看门狗三态熔断器 (CLOSED / OPEN / HALF_OPEN) 防雪崩；
2. 带全抖动的指数退避重试机制 (Exponential Backoff with Full Jitter)；
3. 全链路遥测追踪写入 workspace/telemetry.jsonl，记录 TraceID、耗时与健康状态。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(HERE)
DEFAULT_TELEMETRY_LOG = os.path.join(role_workspace(AGENT_DIR), "telemetry.jsonl")


class WatchdogBreaker:
    """三态看门狗熔断器。"""

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 5.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        now = time.time()
        # 冷却期超时，尝试半开
        if self.state == self.STATE_OPEN and (now - self.last_state_change > self.cooldown_seconds):
            self.state = self.STATE_HALF_OPEN

        if self.state == self.STATE_OPEN:
            raise RuntimeError("熔断器处于 OPEN 状态，保护性拒绝执行！")

        try:
            res = func(*args, **kwargs)
            if self.state == self.STATE_HALF_OPEN:
                self.state = self.STATE_CLOSED
                self.failure_count = 0
            return res
        except Exception:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = self.STATE_OPEN
                self.last_state_change = time.time()
            raise

    def execute_with_retry(self, func: Callable, max_retries: int = 3, base_delay: float = 0.05) -> Any:
        """指数退避带随机抖动重试。"""
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                return self.call(func)
            except Exception as e:
                last_exc = e
                if attempt == max_retries:
                    raise
                # 指数退避 + Jitter
                sleep_time = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.005, 0.02)
                time.sleep(sleep_time)
        raise last_exc


class TelemetryTracer:
    """全链路可观测遥测日志收集器。"""

    def __init__(self, log_path: str = DEFAULT_TELEMETRY_LOG):
        self.log_path = log_path

    def record_span(self, name: str, duration_ms: float, status: str = "SUCCESS", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """记录单次遥测跨度并追加到 telemetry.jsonl。"""
        span = {
            "trace_id": uuid.uuid4().hex[:16],
            "span_id": uuid.uuid4().hex[:8],
            "name": name,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "timestamp": datetime.datetime.now().isoformat(),
            "details": details or {},
        }
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(span, ensure_ascii=False) + "\n")
        return span
