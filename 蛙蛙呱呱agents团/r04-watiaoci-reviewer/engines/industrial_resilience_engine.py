# -*- coding: utf-8 -*-
"""L10 工业容灾层：Watchdog 长任务看门狗、指数退避重试与 OpenTelemetry 遥测追踪。
对标开源项目：OpenTelemetry (Stars > 10k), Temporal (Stars > 12k), Tenacity (Stars > 6k)。
解决病灶：审查遇到子进程假死、网络或文件系统锁挂起时直接无限等待；缺乏工业级熔断降级与链路追踪日志 (telemetry.jsonl)。
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import random
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from core.workspace import role_workspace


class TelemetryLogger:
    """全链路遥测追踪器，规范写入 telemetry.jsonl。"""

    def __init__(self, log_path: str | None = None) -> None:
        self.log_path = log_path or os.path.join(
            role_workspace(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "telemetry.jsonl",
        )
        os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)

    def log_span(self, trace_id: str, span_name: str, duration_ms: float, status: str, payload_summary: Dict[str, Any]) -> None:
        record = {
            "trace_id": trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "span_name": span_name,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "payload_sha256": hashlib.sha256(json.dumps(payload_summary, sort_keys=True).encode("utf-8")).hexdigest(),
            "meta": payload_summary,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


class IndustrialResilienceEngine:
    """长任务熔断看门狗与退避重试器。"""

    @classmethod
    def retry_with_exponential_backoff(
        cls,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ) -> Callable:
        """带 Jitter 的指数退避重试装饰器。"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                delay = initial_delay
                last_exc = None
                for attempt in range(1, max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exc = e
                        if attempt == max_retries:
                            break
                        sleep_time = delay * (1.0 + random.uniform(-0.1, 0.1) if jitter else 1.0)
                        time.sleep(max(0.01, sleep_time))
                        delay *= backoff_factor
                raise last_exc  # 重试耗尽，向上抛出
            return wrapper
        return decorator

    @classmethod
    def run_with_watchdog(cls, target_func: Callable, args: tuple = (), timeout_seconds: float = 5.0) -> Dict[str, Any]:
        """带超时硬防线保护的看门狗执行器。"""
        trace_id = uuid.uuid4().hex
        logger = TelemetryLogger()
        start_time = time.perf_counter()

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(target_func, *args)
            try:
                result = future.result(timeout=timeout_seconds)
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.log_span(trace_id, getattr(target_func, "__name__", "task"), duration_ms, "SUCCESS", {"status": "ok"})
                return {
                    "ok": True,
                    "result": result,
                    "duration_ms": duration_ms,
                    "trace_id": trace_id,
                }
            except concurrent.futures.TimeoutError:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.log_span(trace_id, getattr(target_func, "__name__", "task"), duration_ms, "TIMEOUT", {"error": "TimeoutError"})
                return {
                    "ok": False,
                    "error": f"Task timed out after {timeout_seconds} seconds (Watchdog tripped)",
                    "duration_ms": duration_ms,
                    "trace_id": trace_id,
                }
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.log_span(trace_id, getattr(target_func, "__name__", "task"), duration_ms, "ERROR", {"error": str(e)})
                return {
                    "ok": False,
                    "error": str(e),
                    "duration_ms": duration_ms,
                    "trace_id": trace_id,
                }
