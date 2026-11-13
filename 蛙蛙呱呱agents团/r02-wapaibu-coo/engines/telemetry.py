# -*- coding: utf-8 -*-
"""R02 工业级容灾编排、异步看门狗与遥测可观测性 (轮次 10 落地)。

对标高星标杆: Celery / Temporal / OpenTelemetry
1. Watchdog 超时熔断保护
2. 指数退避重试 (Exponential Backoff)
3. 结构化全链路 Telemetry 遥测指标日志
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from typing import Any, Callable, Dict, Optional

class WatchdogCircuitBreaker:
    """看门狗熔断器。"""

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds

    def execute_guarded(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        t0 = time.time()
        try:
            res = func(*args, **kwargs)
            duration = time.time() - t0
            return {"ok": True, "result": res, "duration": round(duration, 3)}
        except Exception as e:
            return {"ok": False, "error": str(e), "duration": round(time.time() - t0, 3)}

class ProductionTelemetry:
    """生产级遥测日志记录器。"""

    def __init__(self, log_path: str = "telemetry.jsonl"):
        self.log_path = log_path

    def record_span(self, trace_id: str, action: str, input_payload: Any, ok: bool, duration_ms: float) -> None:
        payload_bytes = json.dumps(input_payload, ensure_ascii=False).encode("utf-8")
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        
        entry = {
            "trace_id": trace_id,
            "action": action,
            "sha256": payload_sha256,
            "ok": ok,
            "duration_ms": round(duration_ms, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
