# -*- coding: utf-8 -*-
"""engines/telemetry_watchdog.py - [L10] 工业容灾层：三态看门狗熔断、抖动重试与全链路遥测引擎。

对标开源标杆：
- Temporal 故障隔离与工作流看门狗 (Stars > 25k)
- Tenacity 带抖动指数退避重试 (Stars > 6k)
- OpenTelemetry 结构化链路遥测规范 (Stars > 15k)

核心职责：
1. CLOSED / OPEN / HALF_OPEN 三态看门狗断路熔断器；
2. 带随机全抖动的指数退避重试 (Exponential Backoff with Full Jitter)；
3. 结构化全链路遥测追踪日志记录，落盘至 `workspace/telemetry.jsonl`。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import time
from typing import Any, Callable, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
DEFAULT_TELEMETRY_FILE = os.path.join(role_workspace(_PARENT), "telemetry.jsonl")


class WatchdogBreaker:
    """三态看门狗断路熔断器。"""

    def __init__(self, failure_threshold: int = 3, recovery_time_sec: float = 2.0):
        self.state = "CLOSED"  # CLOSED / OPEN / HALF_OPEN
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = recovery_time_sec
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        now = time.time()

        if self.state == "OPEN":
            if self.last_failure_time and (now - self.last_failure_time >= self.recovery_time_sec):
                self.state = "HALF_OPEN"
            else:
                raise RuntimeError("[CIRCUIT BREAKER OPEN] 服务熔断处于打开状态，快速失败！")

        try:
            res = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return res
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise e


class TelemetryTracer:
    """全链路遥测追踪器。"""

    def __init__(self, log_file: str = DEFAULT_TELEMETRY_FILE):
        self.log_file = log_file

    def record_span(
        self, span_name: str, duration_ms: float, status: str = "OK", metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """记录一条结构化遥测跨度事件。"""
        now = datetime.datetime.now()
        trace_id = hashlib.sha256(f"{span_name}_{now.isoformat()}_{random.random()}".encode()).hexdigest()[:16]
        span_id = hashlib.sha256(f"{span_name}_{random.random()}".encode()).hexdigest()[:8]

        entry = {
            "timestamp": now.isoformat(),
            "trace_id": trace_id,
            "span_id": span_id,
            "span_name": span_name,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "metadata": metadata or {},
        }

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return entry


class CsmTelemetryWatchdog:
    """客户成功综合工业容灾与看门狗调度器。"""

    def __init__(self):
        self.breaker = WatchdogBreaker()
        self.tracer = TelemetryTracer()

    def execute_with_resilience(
        self, span_name: str, func: Callable, max_retries: int = 3, *args, **kwargs
    ) -> Any:
        """带熔断与退避抖动重试的执行包装器。"""
        start = time.time()
        attempt = 0
        last_exc = None

        while attempt < max_retries:
            attempt += 1
            try:
                result = self.breaker.call(func, *args, **kwargs)
                duration = (time.time() - start) * 1000.0
                self.tracer.record_span(span_name, duration, "OK", {"attempts": attempt})
                return result
            except Exception as e:
                last_exc = e
                # 指数退避加随机抖动
                sleep_sec = min(0.1 * (2 ** (attempt - 1)) + random.uniform(0.01, 0.05), 1.0)
                time.sleep(sleep_sec)

        duration = (time.time() - start) * 1000.0
        self.tracer.record_span(span_name, duration, "ERROR", {"attempts": attempt, "error": str(last_exc)})
        raise last_exc
