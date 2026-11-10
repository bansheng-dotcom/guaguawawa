# -*- coding: utf-8 -*-
"""L10 工业容灾层 —— 三态熔断 + 指数退避全抖动 + 全链路遥测。

病灶（体检结论）：升级前 R18 遇到外部依赖抖动/超时只有两种结局——直接抛栈雪崩，
或静默吞异常把失败当成功；没有熔断、没有重试预算、没有 TraceID/SpanID/耗时/健康态
遥测，生产事故无法定位（SOP 明确禁止 `except: pass` 式伪容灾）。

对标标杆（Stars > 1k）：
- `temporalio/temporal`（> 12k）：工作流级超时/重试/看门狗；
- `open-telemetry/opentelemetry-python`（> 2k）：TraceID/SpanID 全链路追踪；
- `jd/tenacity`（> 6k）：指数退避 + 全抖动重试策略。

本引擎落地：
1. `CircuitBreaker`：CLOSED / OPEN / HALF_OPEN 三态，阈值 + 恢复窗口；
2. `execute_with_resilience`：指数退避 + Full Jitter（可注入随机源，便于确定性测试）；
3. `watchdog`：超时硬熔断（守护线程隔离），超时即 TIMEOUT 并留痕；
4. `workspace/telemetry.jsonl`：每跳一行，含 TraceID/SpanID/SHA256/耗时/状态/熔断态。
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional


class CircuitBreaker:
    """三态熔断器：CLOSED →（连续失败达阈值）OPEN →（恢复窗口到）HALF_OPEN。"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 0.2,
                 name: str = "default", clock: Callable[[], float] = time.monotonic):
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout = max(0.0, float(recovery_timeout))
        self.name = name
        self.clock = clock
        self.state = "CLOSED"
        self.failures = 0
        self.opened_at: Optional[float] = None

    def allow(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.opened_at is not None and self.clock() - self.opened_at >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN：放一个探针

    def record_success(self) -> None:
        self.state = "CLOSED"
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == "HALF_OPEN" or self.failures >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = self.clock()

    def snapshot(self) -> Dict[str, Any]:
        return {"name": self.name, "state": self.state, "failures": self.failures,
                "threshold": self.failure_threshold,
                "recovery_timeout_s": self.recovery_timeout}


class DataEngTelemetryWatchdog:
    """L10 工业容灾看门狗。"""

    def __init__(self, workspace_dir: Optional[str] = None, breaker: Optional[CircuitBreaker] = None,
                 telemetry_name: str = "telemetry.jsonl"):
        here = os.path.dirname(os.path.abspath(__file__))
        self.workspace_dir = workspace_dir or os.path.join(os.path.dirname(here), "workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.telemetry_path = os.path.join(self.workspace_dir, telemetry_name)
        self.breaker = breaker or CircuitBreaker()

    # ------------------------------------------------------------------ #
    # 遥测
    # ------------------------------------------------------------------ #
    def _record(self, **fields: Any) -> Dict[str, Any]:
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
               "circuit_state": self.breaker.state}
        row.update(fields)
        with open(self.telemetry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    @staticmethod
    def _digest(value: Any) -> str:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def read_telemetry(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not os.path.exists(self.telemetry_path):
            return []
        rows: List[Dict[str, Any]] = []
        with open(self.telemetry_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
        return rows[-limit:]

    # ------------------------------------------------------------------ #
    # 重试 + 退避 + 熔断
    # ------------------------------------------------------------------ #
    def execute_with_resilience(self, fn: Callable[[], Any], retries: int = 3,
                                base_delay: float = 0.01, max_delay: float = 0.2,
                                rng: Optional[random.Random] = None,
                                name: str = "task") -> Dict[str, Any]:
        rng = rng or random.Random(20261110)
        trace_id = uuid.uuid4().hex[:16]
        attempts = 0
        last_error = ""
        for attempt in range(1, max(1, retries) + 1):
            attempts = attempt
            span_id = uuid.uuid4().hex[:8]
            if not self.breaker.allow():
                self._record(trace_id=trace_id, span_id=span_id, name=name,
                             attempt=attempt, status="CIRCUIT_OPEN",
                             duration_ms=0, sha256=self._digest(last_error),
                             error=last_error, backoff_ms=0)
                return {"ok": False, "status": "CIRCUIT_OPEN", "attempts": attempts,
                        "trace_id": trace_id, "error": last_error,
                        "circuit": self.breaker.snapshot()}
            t0 = time.monotonic()
            try:
                result = fn()
                duration_ms = int((time.monotonic() - t0) * 1000)
                self.breaker.record_success()
                self._record(trace_id=trace_id, span_id=span_id, name=name,
                             attempt=attempt, status="OK", duration_ms=duration_ms,
                             sha256=self._digest(result), error="", backoff_ms=0)
                return {"ok": True, "status": "OK", "attempts": attempts,
                        "result": result, "trace_id": trace_id,
                        "duration_ms": duration_ms, "circuit": self.breaker.snapshot()}
            except Exception as exc:  # noqa: BLE001 - 容灾层必须接住并留痕
                last_error = f"{type(exc).__name__}: {exc}"
                duration_ms = int((time.monotonic() - t0) * 1000)
                self.breaker.record_failure()
                backoff_ms = 0
                if attempt < retries:
                    ceiling = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    backoff_ms = int(rng.uniform(0, ceiling) * 1000)
                self._record(trace_id=trace_id, span_id=span_id, name=name,
                             attempt=attempt, status="FAILED", duration_ms=duration_ms,
                             sha256=self._digest(last_error), error=last_error,
                             backoff_ms=backoff_ms)
                if backoff_ms:
                    time.sleep(backoff_ms / 1000.0)
        return {"ok": False, "status": "FAILED", "attempts": attempts,
                "trace_id": trace_id, "error": last_error,
                "circuit": self.breaker.snapshot()}

    # ------------------------------------------------------------------ #
    # 超时看门狗
    # ------------------------------------------------------------------ #
    def watchdog(self, fn: Callable[[], Any], timeout_s: float = 0.1,
                 name: str = "watchdog") -> Dict[str, Any]:
        trace_id = uuid.uuid4().hex[:16]
        span_id = uuid.uuid4().hex[:8]
        box: Dict[str, Any] = {}

        def runner() -> None:
            t0 = time.monotonic()
            try:
                box["result"] = fn()
                box["duration_ms"] = int((time.monotonic() - t0) * 1000)
            except Exception as exc:  # noqa: BLE001
                box["error"] = f"{type(exc).__name__}: {exc}"

        thread = threading.Thread(target=runner, name=name, daemon=True)
        t0 = time.monotonic()
        thread.start()
        thread.join(max(0.0, float(timeout_s)))
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        if thread.is_alive():
            self._record(trace_id=trace_id, span_id=span_id, name=name, attempt=1,
                         status="TIMEOUT", duration_ms=elapsed_ms,
                         sha256=self._digest(timeout_s), error=f"timeout>{timeout_s}s",
                         backoff_ms=0)
            return {"ok": False, "status": "TIMEOUT", "trace_id": trace_id,
                    "timeout_s": timeout_s, "duration_ms": elapsed_ms}
        if "error" in box:
            self._record(trace_id=trace_id, span_id=span_id, name=name, attempt=1,
                         status="FAILED", duration_ms=elapsed_ms,
                         sha256=self._digest(box["error"]), error=box["error"],
                         backoff_ms=0)
            return {"ok": False, "status": "FAILED", "trace_id": trace_id,
                    "error": box["error"], "duration_ms": elapsed_ms}
        self._record(trace_id=trace_id, span_id=span_id, name=name, attempt=1,
                     status="OK", duration_ms=elapsed_ms,
                     sha256=self._digest(box.get("result")), error="", backoff_ms=0)
        return {"ok": True, "status": "OK", "result": box.get("result"),
                "trace_id": trace_id, "duration_ms": elapsed_ms}

    # ------------------------------------------------------------------ #
    # 健康汇总
    # ------------------------------------------------------------------ #
    def health(self) -> Dict[str, Any]:
        rows = self.read_telemetry()
        counts: Dict[str, int] = {}
        for row in rows:
            counts[row.get("status", "?")] = counts.get(row.get("status", "?"), 0) + 1
        return {"ok": True, "telemetry_path": self.telemetry_path,
                "records": len(rows), "counts": counts,
                "circuit": self.breaker.snapshot()}


# --------------------------------------------------------------------------- #
# CLI：python -m engines.telemetry_watchdog --probe --out ...
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L10 工业容灾看门狗")
    ap.add_argument("--probe", action="store_true", help="跑熔断/重试/超时探针")
    ap.add_argument("--out", default="", help="探针结果 JSON")
    args = ap.parse_args(argv)

    # 重试探针用独立熔断器：避免「3 次重试里前 2 次失败」把熔断器提前打开
    retry_wd = DataEngTelemetryWatchdog(
        breaker=CircuitBreaker(failure_threshold=5, recovery_timeout=0.01),
        telemetry_name="telemetry.jsonl")
    state = {"n": 0}

    def flaky() -> str:
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError(f"upstream jitter #{state['n']}")
        return "pipeline_ok"

    retry = retry_wd.execute_with_resilience(flaky, retries=3, base_delay=0.001,
                                             name="flaky")

    wd = DataEngTelemetryWatchdog(breaker=CircuitBreaker(failure_threshold=2,
                                                         recovery_timeout=0.01))
    def hard_fail() -> str:
        raise TimeoutError("upstream timeout")

    failed = wd.execute_with_resilience(hard_fail, retries=2, base_delay=0.001, name="hard")
    rejected = wd.execute_with_resilience(hard_fail, retries=1, name="rejected")

    slow = wd.watchdog(lambda: (time.sleep(0.15), "late")[1], timeout_s=0.02, name="slow")
    fast = wd.watchdog(lambda: 42, timeout_s=0.2, name="fast")

    out = {
        "ok": bool(retry["ok"] and not failed["ok"] and not rejected["ok"]
                   and slow["status"] == "TIMEOUT" and fast["ok"]),
        "retry": {k: retry.get(k) for k in ("ok", "status", "attempts", "trace_id")},
        "hard_failure": {k: failed.get(k) for k in ("ok", "status", "attempts")},
        "circuit_open": {k: rejected.get(k) for k in ("ok", "status")},
        "watchdog_timeout": {k: slow.get(k) for k in ("ok", "status", "timeout_s")},
        "watchdog_ok": {k: fast.get(k) for k in ("ok", "status", "result")},
        "health": wd.health(),
    }
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print("__AGENT_RESULT__ " + json.dumps(
        {"ok": out["ok"], "retry": out["retry"], "timeout": out["watchdog_timeout"]["status"],
         "records": out["health"]["records"], "telemetry": out["health"]["telemetry_path"]},
        ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
