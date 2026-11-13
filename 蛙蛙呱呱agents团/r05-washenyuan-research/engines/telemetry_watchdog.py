# -*- coding: utf-8 -*-
"""L10 工业容灾层：三态熔断、真实超时看门狗、全抖动指数退避与 Trace/Span 遥测。

对标标杆:
- temporalio/temporal (14k⭐) / jd/tenacity (6.5k⭐) /
  open-telemetry/opentelemetry-python (2.1k⭐)
吸收的机制:
- Temporal 的状态机式容灾：CircuitBreaker 的 CLOSED/OPEN/HALF_OPEN 三态机，
  连续失败达阈值即 OPEN 快速失败，冷却到期懒切换 HALF_OPEN 只放一次试探，
  成功即 CLOSED 恢复；失败则重新 OPEN（不会无限打挂上游）；
- Tenacity 的指数退避 + full jitter：delay = min(base * 2**(n-1), max)，
  jitter=True 时再乘 uniform(0.5, 1.0)，打散重试风暴并记录真实 last_delays；
- Temporal 的长任务看门狗：ThreadPoolExecutor + future.result(timeout) 实现
  真超时（不阻塞到被调函数结束），超时抛 TaskTimeout 并 shutdown(wait=False)；
- OpenTelemetry 的 Trace/Span 上下文：trace_id/span_id/parent_span_id + 耗时 +
  状态 + payload 摘要，逐行 JSONL 落盘，health() 汇总成功率与最近活跃时间。

纯标准库实现（concurrent.futures/contextlib/hashlib/json/random/threading/time/uuid），
Windows 路径安全。
"""
from __future__ import annotations
import concurrent.futures
import contextlib
import datetime
import hashlib
import json
import os
import random
import threading
import time
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional


class CircuitOpenError(Exception):
    """熔断器处于 OPEN 状态，本次调用被快速失败（未触达上游）。"""


class TaskTimeout(Exception):
    """看门狗硬超时：任务超过 timeout_sec 仍未返回，已放弃等待。"""


class RetryExhausted(Exception):
    """重试策略用完所有尝试次数仍未成功。"""


class CircuitBreaker:
    """CLOSED / OPEN / HALF_OPEN 三态熔断器。"""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 3, cooldown_sec: float = 30.0):
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_sec = float(cooldown_sec)
        self._state: str = self.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        """当前状态；OPEN 且冷却到期时惰性切换为 HALF_OPEN（放行一次试探）。"""
        if self._state == self.OPEN:
            if (time.monotonic() - self._opened_at) >= self.cooldown_sec:
                self._state = self.HALF_OPEN
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failures

    def reset(self) -> None:
        """人工复位到 CLOSED（发布回滚后的运维入口）。"""
        self._state = self.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """受熔断保护的调用：OPEN 直接抛 CircuitOpenError，成功即恢复。"""
        if self.state == self.OPEN:
            remaining = max(0.0, self.cooldown_sec - (time.monotonic() - self._opened_at))
            raise CircuitOpenError(
                f"熔断器 OPEN，快速失败（剩余冷却 {remaining:.3f}s）")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = self.OPEN
                self._opened_at = time.monotonic()
            raise
        self._failures = 0
        if self._state == self.HALF_OPEN:
            self._state = self.CLOSED
        return result


class RetryPolicy:
    """带指数退避与 full jitter 的重试策略（记录真实等待序列）。"""

    def __init__(self, max_attempts: int = 3, base_delay: float = 0.05,
                 max_delay: float = 2.0, jitter: bool = True,
                 sleep: Callable[[float], Any] = time.sleep):
        self.max_attempts = max(1, int(max_attempts))
        self.base_delay = float(base_delay)
        self.max_delay = float(max_delay)
        self.jitter = bool(jitter)
        self.sleep = sleep
        self.last_delays: List[float] = []

    def _delay_for(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        if self.jitter:
            delay *= random.uniform(0.5, 1.0)
        return delay

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """执行 fn，失败按退避重试；全部失败抛 RetryExhausted。"""
        self.last_delays = []
        last_error: Optional[BaseException] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                delay = self._delay_for(attempt)
                self.last_delays.append(delay)
                self.sleep(delay)
        raise RetryExhausted(
            f"重试 {self.max_attempts} 次仍失败：{type(last_error).__name__}: {last_error}"
        ) from last_error


class WatchdogRunner:
    """真超时看门狗：独立线程执行 + future.result(timeout)，超时不阻塞到结束。"""

    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = float(timeout_sec)

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """在受控线程中执行；超过 timeout_sec 抛 TaskTimeout 并放弃等待。"""
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="r05-watchdog")
        future = executor.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=self.timeout_sec)
        except concurrent.futures.TimeoutError as exc:
            raise TaskTimeout(
                f"任务超过 {self.timeout_sec}s 硬超时，已放弃等待") from exc
        finally:
            # 关键：超时路径绝不能 wait=True，否则看门狗自身被慢函数拖死。
            executor.shutdown(wait=False)


class TelemetryTracer:
    """Trace/Span 遥测：上下文管理器产出 record，退出时追加一行 JSONL。"""

    def __init__(self, log_path: str):
        self.log_path = os.path.abspath(log_path)
        self._trace_id = uuid.uuid4().hex[:16]
        self._span_stack: List[str] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    @staticmethod
    def _digest(action: str, payload: Any) -> str:
        canonical = json.dumps({"action": action, "payload": payload},
                               ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def _append(self, record: Dict[str, Any]) -> None:
        directory = os.path.dirname(self.log_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    # ------------------------------------------------------------------
    # Span 上下文
    # ------------------------------------------------------------------
    @contextlib.contextmanager
    def span(self, action: str,
             payload: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
        """开启一个 Span：成功 SUCCESS、异常 FAILED（记录 error 后原样抛出）。"""
        parent_span_id = self._span_stack[-1] if self._span_stack else None
        span_id = uuid.uuid4().hex[:16]
        record: Dict[str, Any] = {
            "trace_id": self._trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "action": action,
            "timestamp": datetime.datetime.now().isoformat(timespec="milliseconds"),
            "duration_ms": 0.0,
            "status": "SUCCESS",
            "sha256_16": self._digest(action, payload),
            "details": {"payload": payload},
        }
        started = time.perf_counter()
        self._span_stack.append(span_id)
        try:
            yield record
        except BaseException as exc:
            record["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            record["status"] = "FAILED"
            record["details"] = dict(record.get("details") or {})
            record["details"]["error"] = f"{type(exc).__name__}: {exc}"
            self._append(record)
            raise
        else:
            record["duration_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
            record["status"] = "SUCCESS"
            self._append(record)
        finally:
            if self._span_stack and self._span_stack[-1] == span_id:
                self._span_stack.pop()
            elif span_id in self._span_stack:
                self._span_stack.remove(span_id)

    # ------------------------------------------------------------------
    # 健康汇总
    # ------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        """读取 JSONL 遥测，汇总 total/success/failed/success_rate/last_span_at。"""
        total = 0
        success = 0
        failed = 0
        last_span_at: Optional[str] = None
        if not os.path.exists(self.log_path):
            return {"total": 0, "success": 0, "failed": 0,
                    "success_rate": 0.0, "last_span_at": None}
        with open(self.log_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                total += 1
                status = str(record.get("status", "")).upper()
                if status == "SUCCESS":
                    success += 1
                else:
                    failed += 1
                last_span_at = record.get("timestamp") or last_span_at
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total, 4) if total else 0.0,
            "last_span_at": last_span_at,
        }
