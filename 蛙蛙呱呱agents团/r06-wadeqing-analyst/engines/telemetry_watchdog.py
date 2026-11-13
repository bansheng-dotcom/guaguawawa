# -*- coding: utf-8 -*-
"""L10 工业容灾层 (Watchdog Circuit Breaker & OpenTelemetry Telemetry Layer)
对标开源: Temporal / OpenTelemetry / Tenacity / Resilience4j
核心工业级容灾能力:
1. 看门狗熔断器 (Watchdog Circuit Breaker)：
   - 支持 CLOSED / OPEN / HALF_OPEN 三态状态机转移；
   - 支持超时强熔断守护 (Timeout Hard Kill / Enforcement) 与超时主动熔断；
   - 支持动态熔断阈值自适应 (Dynamic Failure Ratio / Threshold) 与连续成功恢复计数；
   - 具备熔断指标统计（总调用数、失败数、熔断拒绝数、恢复数等）。
2. 全抖动指数退避重试 (Exponential Backoff with Full Jitter / Decorrelated Jitter)：
   - 对标 AWS/Temporal 全抖动算法与最大延迟限流顶板 (cap)；
   - 支持可配置可重试异常清单 (retryable_exceptions)。
3. 高频链路遥测 Span 追踪 (Distributed Tracing & Telemetry)：
   - 结构化 telemetry.jsonl 追踪；
   - 支持上下文 Trace/Span 继承 (Parent Span ID, Context Manager `start_span`)；
   - 自动检测并打标异常耗时离群点告警 (Latency Outlier Alerting)；
   - Payload SHA256 签名与审计摘要。
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import statistics
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from typing import Any, Callable, Deque, Dict, Generator, List, Optional, Tuple, Type


class TimeoutException(RuntimeError):
    """任务执行超时异常。"""
    pass


class AnalysisWatchdogBreaker:
    """看门狗与熔断器，防止耗时分析或死锁阻塞系统，对标 Resilience4j 与 Temporal Activity Watchdog。"""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_sec: float = 5.0,
        half_open_success_threshold: int = 2,
        window_size: int = 10,
        failure_ratio_threshold: float = 0.5,
        min_calls_in_window: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.half_open_success_threshold = half_open_success_threshold
        self.window_size = window_size
        self.failure_ratio_threshold = failure_ratio_threshold
        self.min_calls_in_window = min_calls_in_window

        self.failure_count = 0
        self.consecutive_success_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()
        self._outcomes: Deque[bool] = deque(maxlen=window_size)

        # 统计计数
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,
            "timeout_calls": 0,
            "tripped_count": 0,
        }
        self._lock = threading.Lock()

    def window_stats(self) -> Dict[str, Any]:
        """滑窗失败率统计，用于自适应熔断判定。"""
        with self._lock:
            outcomes = list(self._outcomes)
        failures = sum(1 for ok in outcomes if not ok)
        ratio = (failures / len(outcomes)) if outcomes else 0.0
        return {
            "window_size": self.window_size,
            "observed": len(outcomes),
            "failures": failures,
            "failure_ratio": round(ratio, 4),
            "threshold": self.failure_ratio_threshold,
            "state": self.state,
        }

    def get_state(self) -> str:
        with self._lock:
            self._evaluate_state_transition(time.time())
            return self.state

    def _evaluate_state_transition(self, now: float) -> None:
        if self.state == "OPEN":
            if now - self.last_state_change >= self.reset_timeout_sec:
                self.state = "HALF_OPEN"
                self.consecutive_success_count = 0
                self.last_state_change = now

    def execute_with_guard(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        timeout_sec: float = 0.0,
    ) -> Any:
        """在熔断器与看门狗超时监控保护下执行目标函数。"""
        kwargs = kwargs or {}
        now = time.time()

        with self._lock:
            self.metrics["total_calls"] += 1
            self._evaluate_state_transition(now)

            if self.state == "OPEN":
                self.metrics["rejected_calls"] += 1
                raise RuntimeError("CircuitBreaker is OPEN: operation rejected for self-protection")

        # 若设置了正超时时间，则利用独立线程执行监护超时（看门狗硬超时杀手）
        if timeout_sec and timeout_sec > 0:
            result_container: List[Any] = []
            exc_container: List[Exception] = []

            def _worker():
                try:
                    res = func(*args, **kwargs)
                    result_container.append(res)
                except Exception as e:
                    exc_container.append(e)

            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()
            thread.join(timeout=timeout_sec)

            if thread.is_alive():
                # 超时判定
                with self._lock:
                    self.metrics["failed_calls"] += 1
                    self.metrics["timeout_calls"] += 1
                    self.failure_count += 1
                    if self.failure_count >= self.failure_threshold:
                        self.state = "OPEN"
                        self.metrics["tripped_count"] += 1
                        self.last_state_change = time.time()
                raise TimeoutException(f"Task exceeded hard watchdog limit of {timeout_sec}s")

            if exc_container:
                self._record_failure(exc_container[0])
                raise exc_container[0]

            self._record_success()
            return result_container[0] if result_container else None

        # 无超时约束或普通保护调用
        try:
            res = func(*args, **kwargs)
            self._record_success()
            return res
        except Exception as exc:
            self._record_failure(exc)
            raise exc

    def _record_success(self) -> None:
        with self._lock:
            self.metrics["successful_calls"] += 1
            self._outcomes.append(True)
            if self.state == "HALF_OPEN":
                self.consecutive_success_count += 1
                if self.consecutive_success_count >= self.half_open_success_threshold:
                    self.state = "CLOSED"
                    self.failure_count = 0
                    self.consecutive_success_count = 0
                    self._outcomes.clear()
                    self.last_state_change = time.time()
            elif self.state == "CLOSED":
                self.failure_count = 0

    def _record_failure(self, exc: Exception) -> None:
        with self._lock:
            self.metrics["failed_calls"] += 1
            self.failure_count += 1
            self._outcomes.append(False)
            observed = len(self._outcomes)
            ratio = sum(1 for ok in self._outcomes if not ok) / observed if observed else 0.0
            ratio_tripped = (observed >= self.min_calls_in_window
                             and ratio >= self.failure_ratio_threshold)
            if self.state == "HALF_OPEN" or ratio_tripped or self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.metrics["tripped_count"] += 1
                self.last_state_change = time.time()

    def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 0.05,
        max_delay: float = 2.0,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> Any:
        """带 Full Jitter (高斯/随机均匀全抖动) 的指数退避重试 (对标 AWS/Temporal)。"""
        last_exc = None
        for attempt in range(max_retries):
            try:
                return func()
            except retryable_exceptions as exc:
                last_exc = exc
                if attempt == max_retries - 1:
                    break
                # Full Jitter: min(max_delay, base_delay * 2^attempt) 的 [0, delay] 均匀抖动
                exp_delay = min(max_delay, base_delay * (2 ** attempt))
                jitter_delay = random.uniform(0.0, exp_delay)
                time.sleep(jitter_delay)
            except Exception as non_retryable:
                raise non_retryable

        raise RuntimeError(f"Exceeded max retries ({max_retries}): {last_exc}")

    def reset(self) -> None:
        """手动重置熔断器至初始关闭状态。"""
        with self._lock:
            self.state = "CLOSED"
            self.failure_count = 0
            self.consecutive_success_count = 0
            self._outcomes.clear()
            self.last_state_change = time.time()

    # ------------------------------------------------------------------ #
    # 进程级隔离执行（真·硬超时强杀，不依赖线程）
    # ------------------------------------------------------------------ #
    def run_isolated(self, argv: List[str], timeout_sec: float = 10.0,
                     cwd: Optional[str] = None) -> Dict[str, Any]:
        """在独立子进程中执行任务；超时立即 kill，主进程不被拖垮。"""
        t0 = time.perf_counter()
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        with self._lock:
            self.metrics["total_calls"] += 1
        try:
            proc = subprocess.run(
                argv, cwd=cwd, capture_output=True, text=True,
                encoding="utf-8", errors="replace", env=env, timeout=timeout_sec,
            )
            duration = round((time.perf_counter() - t0) * 1000.0, 3)
            status = "OK" if proc.returncode == 0 else "FAILED"
            with self._lock:
                self.metrics["successful_calls" if proc.returncode == 0 else "failed_calls"] += 1
                self._outcomes.append(proc.returncode == 0)
            return {
                "status": status,
                "returncode": proc.returncode,
                "duration_ms": duration,
                "stdout_tail": (proc.stdout or "").strip()[-500:],
                "stderr_tail": (proc.stderr or "").strip()[-500:],
                "isolated": True,
            }
        except subprocess.TimeoutExpired as exc:
            duration = round((time.perf_counter() - t0) * 1000.0, 3)
            with self._lock:
                self.metrics["failed_calls"] += 1
                self.metrics["timeout_calls"] += 1
                self._outcomes.append(False)
            return {
                "status": "TIMEOUT",
                "returncode": None,
                "duration_ms": duration,
                "stdout_tail": (exc.stdout or "")[-500:] if isinstance(exc.stdout, str) else "",
                "stderr_tail": f"killed after {timeout_sec}s hard limit",
                "isolated": True,
            }

    def execute_with_budget(self, func: Callable, budget_sec: float,
                            args: tuple = (), kwargs: dict = None) -> Dict[str, Any]:
        """按剩余预算执行，返回剩余时间用于下游预算传播。"""
        started = time.perf_counter()
        result = self.execute_with_guard(func, args=args, kwargs=kwargs or {}, timeout_sec=budget_sec)
        elapsed = time.perf_counter() - started
        return {
            "result": result,
            "budget_sec": budget_sec,
            "remaining_sec": round(max(0.0, budget_sec - elapsed), 4),
            "elapsed_sec": round(elapsed, 4),
        }


class AnalysisTelemetryTracer:
    """工业级遥测追踪器，输出结构化 OpenTelemetry 规范兼容的 telemetry.jsonl 日志。"""

    def __init__(self, log_path: str = None, latency_alert_threshold_ms: float = 100.0,
                 sample_rate: float = 1.0):
        if not log_path:
            here = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(role_workspace(os.path.dirname(here)), "telemetry.jsonl")
        self.log_path = log_path
        self.latency_alert_threshold_ms = latency_alert_threshold_ms
        self.sample_rate = max(0.0, min(1.0, float(sample_rate)))
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # W3C traceparent
    # ------------------------------------------------------------------ #
    @staticmethod
    def new_traceparent(trace_id: Optional[str] = None,
                        span_id: Optional[str] = None) -> str:
        """生成 W3C Trace Context 标准 traceparent 头。"""
        trace = (trace_id or uuid.uuid4().hex).ljust(32, "0")[:32]
        span = (span_id or uuid.uuid4().hex[:16]).ljust(16, "0")[:16]
        return f"00-{trace}-{span}-01"

    @staticmethod
    def parse_traceparent(header: str) -> Dict[str, str]:
        """解析 traceparent；非法格式抛出 ValueError。"""
        parts = (header or "").split("-")
        if len(parts) != 4 or len(parts[1]) != 32 or len(parts[2]) != 16:
            raise ValueError(f"Invalid traceparent: {header}")
        return {"version": parts[0], "trace_id": parts[1],
                "parent_span_id": parts[2], "flags": parts[3]}

    def record_span(
        self,
        action_name: str,
        duration_ms: float,
        status: str,
        details: Dict[str, Any] = None,
        trace_id: str = None,
        parent_span_id: str = None,
        traceparent: str = None,
    ) -> Dict[str, Any]:
        """记录单一 Span 追踪日志，自动计算 Payload SHA256，并在耗时过长时注入离群告警。"""
        details = details or {}
        if traceparent:
            try:
                ctx = self.parse_traceparent(traceparent)
                trace_id = trace_id or ctx["trace_id"]
                parent_span_id = parent_span_id or ctx["parent_span_id"]
            except ValueError:
                pass
        trace_id = (trace_id or uuid.uuid4().hex).ljust(32, "0")[:32]
        span_id = uuid.uuid4().hex[:16]
        active_traceparent = f"00-{trace_id}-{span_id}-01"

        try:
            payload_str = json.dumps(details, sort_keys=True, ensure_ascii=False)
        except Exception:
            payload_str = str(details)
        sha256_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:12]

        is_outlier = duration_ms >= self.latency_alert_threshold_ms
        alert = "LATENCY_OUTLIER" if is_outlier else None
        sampled = self.sample_rate >= 1.0 or random.random() < self.sample_rate

        record = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "traceparent": active_traceparent,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "action": action_name,
            "duration_ms": round(duration_ms, 3),
            "status": status,
            "payload_sha256": sha256_hash,
            "latency_alert": alert,
            "sampled": sampled,
            "details": details,
        }

        if sampled:
            with self._lock:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    @contextlib.contextmanager
    def start_span(
        self,
        action_name: str,
        details: Dict[str, Any] = None,
        trace_id: str = None,
        parent_span_id: str = None,
        traceparent: str = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """上下文管理器方式自动追踪执行耗时并记录 Span。"""
        details = details or {}
        active_trace = trace_id or uuid.uuid4().hex
        active_span = uuid.uuid4().hex[:16]
        active_traceparent = self.new_traceparent(active_trace, active_span)
        context_data = {
            "trace_id": active_trace,
            "span_id": active_span,
            "parent_span_id": parent_span_id,
            "traceparent": traceparent or active_traceparent,
            "details": details,
        }

        t0 = time.perf_counter()
        status = "SUCCESS"
        try:
            yield context_data
        except Exception as exc:
            status = "FAILED"
            details["error"] = str(exc)
            raise exc
        finally:
            cost_ms = (time.perf_counter() - t0) * 1000
            self.record_span(
                action_name=action_name,
                duration_ms=cost_ms,
                status=status,
                details=details,
                trace_id=active_trace,
                parent_span_id=parent_span_id,
                traceparent=traceparent,
            )

    def aggregate_metrics(self) -> Dict[str, Any]:
        """聚合遥测日志：调用量、失败率与 p50/p95/p99 延迟分位。"""
        spans = self.get_recent_spans(limit=100000)
        durations = sorted(float(s.get("duration_ms", 0.0)) for s in spans)
        failed = sum(1 for s in spans if s.get("status") == "FAILED")
        outliers = sum(1 for s in spans if s.get("latency_alert"))

        def _pct(q: float) -> float:
            if not durations:
                return 0.0
            idx = min(len(durations) - 1, max(0, int(round((len(durations) - 1) * q))))
            return round(durations[idx], 3)

        return {
            "span_count": len(spans),
            "failed": failed,
            "error_rate": round(failed / len(spans), 4) if spans else 0.0,
            "latency_outliers": outliers,
            "p50_ms": _pct(0.50),
            "p95_ms": _pct(0.95),
            "p99_ms": _pct(0.99),
            "sample_rate": self.sample_rate,
        }

    def get_recent_spans(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近落盘的 Span 记录。"""
        if not os.path.exists(self.log_path):
            return []
        spans = []
        with self._lock:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            spans.append(json.loads(line))
                        except Exception:
                            pass
        return spans[-limit:]
