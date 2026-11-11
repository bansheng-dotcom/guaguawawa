# -*- coding: utf-8 -*-
"""engines/telemetry_watchdog.py - [L10] 工业容灾层：三态看门狗熔断、指数抖动重试与全链路遥测追踪。

对标开源标杆：
- Temporal / OpenTelemetry / Tenacity (Stars > 25k)
- 工业级看门狗熔断器 (CLOSED -> OPEN -> HALF_OPEN)
- 指数退避带全抖动 (Full Jitter) 重试
- JSON Lines 全链路遥测追踪落盘 (workspace/telemetry.jsonl)

核心职责：
1. 三态熔断器 WatchdogBreaker：短时间内连续失败达到阈值立即切入 OPEN 状态，阻断雪崩；
2. 指数退避全抖动重试器：实现优雅退避重试，防止惊群效应；
3. 全链路遥测 TelemetryTracer：记录每次执行的 trace_id、span_id、耗时、状态与 SHA256 审计指纹。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WS = os.path.join(role_workspace(_HERE))
TELEMETRY_LOG = os.path.join(_WS, "telemetry.jsonl")


class WatchdogBreaker:
    """工业级三态熔断看门狗 (CLOSED / OPEN / HALF_OPEN)。"""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 3, recovery_timeout_sec: float = 2.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_success(self) -> None:
        """记录成功调用：重置计数并恢复为 CLOSED。"""
        self.failure_count = 0
        self.state = self.CLOSED
        self.last_state_change = time.time()

    def record_failure(self) -> None:
        """记录失败调用：达到阈值直接触发熔断 (OPEN)。"""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            self.last_state_change = time.time()

    def can_execute(self) -> bool:
        """判断当前是否允许执行。OPEN 状态若超期则转为 HALF_OPEN 试探。"""
        now = time.time()
        if self.state == self.CLOSED:
            return True
        elif self.state == self.OPEN:
            if now - self.last_state_change > self.recovery_timeout_sec:
                self.state = self.HALF_OPEN
                self.last_state_change = now
                return True
            return False
        elif self.state == self.HALF_OPEN:
            return True
        return False


class TelemetryTracer:
    """全链路遥测追踪日志记录器 (落盘至 workspace/telemetry.jsonl)。"""

    def __init__(self, log_path: str = TELEMETRY_LOG):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_event(self, trace_id: str, action: str, status: str, elapsed_ms: int, payload_snippet: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """记录一条结构化遥测事件。"""
        entry = {
            "trace_id": trace_id,
            "span_id": f"span_{random.randint(1000, 9999)}",
            "timestamp": datetime.datetime.now().isoformat(),
            "role": "r17-wazhiwang-automation",
            "action": action,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "sha256": hashlib.sha256(json.dumps(payload_snippet or {}, sort_keys=True).encode("utf-8")).hexdigest()[:16],
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


class AutomationTelemetryWatchdog:
    """自动化容灾管理总成。"""

    def __init__(self, log_path: str = TELEMETRY_LOG):
        self.breaker = WatchdogBreaker()
        self.tracer = TelemetryTracer(log_path)

    def execute_with_resilience(
        self,
        func: Callable[[], Any],
        action_name: str = "workflow_action",
        max_retries: int = 3,
        base_delay_sec: float = 0.05,
    ) -> Any:
        """带熔断与指数退避带全抖动 (Full Jitter) 的高可用执行封装。"""
        trace_id = f"trace_r17_{int(time.time()*1000)}"
        t0 = time.time()

        if not self.breaker.can_execute():
            self.tracer.log_event(trace_id, action_name, "BREAKER_OPEN_REJECTED", 0)
            raise RuntimeError(f"熔断器当前处于 OPEN 状态，拒绝执行高风险请求: {action_name}")

        attempt = 0
        last_err = None

        while attempt <= max_retries:
            attempt += 1
            try:
                res = func()
                elapsed = int((time.time() - t0) * 1000)
                self.breaker.record_success()
                self.tracer.log_event(trace_id, action_name, "SUCCESS", elapsed)
                return res
            except Exception as e:
                last_err = e
                self.breaker.record_failure()
                if attempt <= max_retries:
                    # Full Jitter: Uniform(0, min(cap, base * 2^(attempt-1)))
                    cap = 1.0
                    sleep_time = random.uniform(0, min(cap, base_delay_sec * (2 ** (attempt - 1))))
                    time.sleep(sleep_time)

        elapsed = int((time.time() - t0) * 1000)
        self.tracer.log_event(trace_id, action_name, "FAILED_EXHAUSTED", elapsed, {"error": str(last_err)})
        raise RuntimeError(f"在 {max_retries} 次重试后执行依然失败: {last_err}") from last_err
