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
import random
import time
from typing import Any, Callable, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
DEFAULT_TELEMETRY_FILE = os.path.join(_PARENT, "workspace", "telemetry.jsonl")


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
                raise RuntimeError("[CIRCUIT BREAKER OPEN] 支付/交易网关服务熔断处于打开状态，快速失败！")

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
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return entry


class CommerceTelemetryWatchdog:
    """交易工业级看门狗与容灾重试中枢。"""

    def __init__(self, log_file: str = DEFAULT_TELEMETRY_FILE):
        self.breaker = WatchdogBreaker()
        self.tracer = TelemetryTracer(log_file)

    def execute_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 0.05,
        max_delay: float = 0.5,
    ) -> Any:
        """带 Full Jitter 的指数退避重试执行器。"""
        last_exc = None
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exc = e
                if attempt == max_retries - 1:
                    break
                # Full Jitter: sleep = Uniform(0, min(max_delay, base_delay * 2^attempt))
                backoff = min(max_delay, base_delay * (2 ** attempt))
                sleep_time = random.uniform(0, backoff)
                time.sleep(sleep_time)

        raise last_exc or RuntimeError("Execution failed after retries")

    def call_protected(
        self,
        span_name: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """受看门狗与遥测双重保护的调用入口。"""
        t0 = time.time()
        status = "OK"
        try:
            res = self.breaker.call(func, *args, **kwargs)
            return res
        except Exception as e:
            status = f"ERROR: {type(e).__name__}"
            raise e
        finally:
            dur = (time.time() - t0) * 1000.0
            self.tracer.record_span(span_name, dur, status=status)
