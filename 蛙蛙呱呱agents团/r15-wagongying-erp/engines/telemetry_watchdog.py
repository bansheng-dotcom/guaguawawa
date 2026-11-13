# -*- coding: utf-8 -*-
"""engines/telemetry_watchdog.py - [L10] 工业容灾层：三态熔断看门狗、抖动重试与全链路遥测追踪。

对标开源标杆：
- Temporal 分布式容灾工作流
- Tenacity 指数退避抖动重试机制 (Exponential Backoff with Full Jitter)
- OpenTelemetry 标准遥测追踪模式 (Stars > 25k)

核心职责：
1. 实现 CLOSED / OPEN / HALF_OPEN 三态看门狗熔断器 (WatchdogBreaker)；
2. 外部 ERP/WMS/供应商 EDI 接口指数退避重试 (Exponential Backoff with Jitter)；
3. 全链路遥测落盘至 workspace/telemetry.jsonl (含 TraceID, SpanID, 耗时, SHA256)；
4. 确保在生产高并发与网络抖动时具备工业级自愈与弹性。
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

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WS = os.path.join(role_workspace(_HERE))
TELEMETRY_LOG = os.path.join(_WS, "telemetry.jsonl")


class WatchdogBreaker:
    """三态看门狗熔断器 (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)。"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout_sec: float = 2.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = 0.0

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout_sec:
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False


class TelemetryTracer:
    """全链路结构化遥测追踪器，追加写入 workspace/telemetry.jsonl。"""

    def __init__(self, log_path: str = TELEMETRY_LOG):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def trace(
        self,
        action: str,
        duration_ms: float,
        status: str,
        payload: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())[:8]
        payload_str = json.dumps(payload or {}, ensure_ascii=False)
        sha256 = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:16]

        record = {
            "trace_id": trace_id,
            "span_id": span_id,
            "role": "r15-wagongying-erp",
            "action": action,
            "timestamp": datetime.datetime.now().isoformat(),
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "payload_sha256": sha256,
            "error": error,
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record


class ERPTelemetryWatchdog:
    """供应链容灾看门狗总调度器。"""

    def __init__(self, log_path: str = TELEMETRY_LOG):
        self.breaker = WatchdogBreaker()
        self.tracer = TelemetryTracer(log_path)

    def execute_with_resilience(
        self,
        action_name: str,
        callable_fn: Callable[[], Any],
        max_retries: int = 3,
        base_backoff_sec: float = 0.05,
    ) -> Dict[str, Any]:
        """带熔断与退避抖动重试的高弹性执行器。"""
        if not self.breaker.can_execute():
            self.tracer.trace(action_name, 0.0, "CIRCUIT_BROKEN", error="熔断器处于 OPEN 状态，拦截快速失败")
            raise RuntimeError(f"看门狗拦截：目标服务熔断器处于 [{self.breaker.state}] 状态，请等待冷却恢复！")

        start_time = time.time()
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                result = callable_fn()
                duration_ms = (time.time() - start_time) * 1000.0
                self.breaker.record_success()
                self.tracer.trace(action_name, duration_ms, "SUCCESS", payload={"attempt": attempt})
                return {"ok": True, "result": result, "attempts": attempt, "duration_ms": duration_ms}
            except Exception as e:
                last_exception = e
                self.breaker.record_failure()
                if attempt < max_retries:
                    # 指数退避加随机全抖动
                    jitter = random.uniform(0.01, 0.05)
                    backoff = (base_backoff_sec * (2 ** (attempt - 1))) + jitter
                    time.sleep(backoff)

        duration_ms = (time.time() - start_time) * 1000.0
        self.tracer.trace(action_name, duration_ms, "FAILED", error=str(last_exception))
        return {"ok": False, "error": str(last_exception), "attempts": max_retries, "duration_ms": duration_ms}

    def probe_health(self) -> Dict[str, Any]:
        """探针检测看门狗与遥测日志可用性。"""
        test_rec = self.tracer.trace("probe_health", 1.2, "HEALTHY", payload={"check": "l10"})
        return {
            "status": "healthy",
            "layer": "L10",
            "circuit_state": self.breaker.state,
            "log_path": self.tracer.log_path,
            "sample_trace_id": test_rec["trace_id"],
        }
