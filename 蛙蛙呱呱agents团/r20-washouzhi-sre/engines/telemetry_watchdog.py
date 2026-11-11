# -*- coding: utf-8 -*-
"""L10 工业容灾层 —— 三态熔断 + 全抖动退避 + 全链路遥测。

SOP v13.0 L10 体检病灶（R20 真实断点）：
    探测/备份/恢复调用一旦抖动就抛栈崩溃，或 `except: pass` 静默吞异常；
    没有超时熔断，一个卡死的恢复任务能拖垮整条值班链；
    无 TraceID/SpanID/耗时/SHA256 遥测，排障只能人肉翻日志。

对标开源标杆（Stars > 1k）：
    * temporalio/temporal (>12k) —— 长任务工作流与超时语义
    * open-telemetry/opentelemetry-python (>2k) —— Trace/Span 模型
    * jd/tenacity (>6k) —— 指数退避与重试策略

落地的最低 3 项架构升级：
    1. CLOSED/OPEN/HALF_OPEN 三态熔断器与恢复窗口；
    2. 指数退避 + Full Jitter 重试（可注入 RNG，确定性可测）；
    3. telemetry.jsonl 全链路遥测（TraceID/SpanID/SHA256/耗时/状态）。

用法：
    python agent.py evolve watchdog --out workspace/rounds/L10_telemetry.json
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"


class WatchdogBreaker:
    """三态熔断器（可注入时钟，确定性测试）。"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0,
                 half_open_max: int = 2, clock: Optional[Callable[[], float]] = None):
        self.failure_threshold = int(failure_threshold)
        self.recovery_timeout = float(recovery_timeout)
        self.half_open_max = int(half_open_max)
        self._clock = clock or time.monotonic
        self.state = CLOSED
        self.failures = 0
        self.opened_at: Optional[float] = None
        self.half_open_calls = 0
        self.transitions: List[Dict[str, Any]] = []

    def _set(self, state: str, reason: str) -> None:
        self.state = state
        self.transitions.append({"state": state, "reason": reason,
                                 "at": round(self._clock(), 3)})

    def allow(self) -> bool:
        if self.state == OPEN:
            if self.opened_at is not None and \
                    (self._clock() - self.opened_at) >= self.recovery_timeout:
                self.half_open_calls = 0
                self._set(HALF_OPEN, "recovery_timeout_elapsed")
            else:
                return False
        if self.state == HALF_OPEN:
            if self.half_open_calls >= self.half_open_max:
                return False
            self.half_open_calls += 1
        return True

    def record_success(self) -> None:
        self.failures = 0
        if self.state in (HALF_OPEN, OPEN):
            self._set(CLOSED, "probe_success")
        self.half_open_calls = 0

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == HALF_OPEN:
            self.opened_at = self._clock()
            self._set(OPEN, "half_open_probe_failed")
            return
        if self.failures >= self.failure_threshold:
            self.opened_at = self._clock()
            self._set(OPEN, "failure_threshold_reached")


class TelemetryTracer:
    """JSONL 全链路遥测。"""

    def __init__(self, path: str):
        self.path = path
        self.trace_id = uuid.uuid4().hex

    def span(self, name: str, status: str, duration_ms: float,
             parent_span_id: Optional[str] = None,
             attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "trace_id": self.trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "parent_span_id": parent_span_id,
            "name": name,
            "status": status,
            "duration_ms": round(float(duration_ms), 3),
            "attributes": attributes or {},
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        payload["sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload


class R20TelemetryWatchdog:
    """R20 工业容灾：熔断 / 退避 / 遥测。"""

    ENGINE = "R20TelemetryWatchdog"
    LAYER = "L10"
    CAPABILITIES = [
        "CLOSED/OPEN/HALF_OPEN 三态熔断器与恢复窗口",
        "指数退避 + Full Jitter 重试 (可注入 RNG，确定性可测)",
        "telemetry.jsonl 全链路遥测 (TraceID/SpanID/SHA256/耗时/状态)",
    ]

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or os.path.join(role_workspace(_ROLE))
        self.telemetry_path = os.path.join(self.workspace_dir, "telemetry.jsonl")

    # ------------------------------------------------------------------ #
    # 退避
    # ------------------------------------------------------------------ #
    def compute_backoff(self, attempt: int, base: float = 0.5, cap: float = 30.0,
                        rng: Optional[random.Random] = None) -> float:
        attempt = max(0, int(attempt))
        rng = rng or random.Random(20261110)
        ceiling = min(cap, base * (2 ** attempt))
        return round(rng.uniform(0.0, ceiling), 4)

    # ------------------------------------------------------------------ #
    # 熔断 + 重试 + 遥测
    # ------------------------------------------------------------------ #
    def execute_with_resilience(self, name: str, fn: Callable[[], Any],
                                retries: int = 2,
                                breaker: Optional[WatchdogBreaker] = None,
                                tracer: Optional[TelemetryTracer] = None,
                                sleep: bool = False) -> Dict[str, Any]:
        breaker = breaker or WatchdogBreaker()
        tracer = tracer or TelemetryTracer(self.telemetry_path)
        rng = random.Random(42)
        attempts = 0
        backoffs: List[float] = []
        last_error = None
        parent = None
        for attempt in range(retries + 1):
            if not breaker.allow():
                status = "CIRCUIT_OPEN"
                tracer.span(f"{name}.rejected", status, 0.0, parent,
                            {"state": breaker.state, "attempt": attempt})
                return {"ok": False, "status": status, "attempts": attempts,
                        "breaker_state": breaker.state, "backoffs": backoffs,
                        "error": "circuit open"}
            attempts += 1
            t0 = time.monotonic()
            try:
                result = fn()
                duration = (time.monotonic() - t0) * 1000.0
                breaker.record_success()
                span = tracer.span(f"{name}.call", "OK", duration, parent,
                                   {"attempt": attempt, "breaker": breaker.state})
                return {"ok": True, "status": "OK", "result": result,
                        "attempts": attempts, "breaker_state": breaker.state,
                        "backoffs": backoffs, "span": span}
            except Exception as exc:  # 外部依赖抖动：记录并重试
                duration = (time.monotonic() - t0) * 1000.0
                last_error = f"{type(exc).__name__}: {exc}"
                breaker.record_failure()
                span = tracer.span(f"{name}.call", "ERROR", duration, parent,
                                   {"attempt": attempt, "error": last_error,
                                    "breaker": breaker.state})
                parent = span["span_id"]
                if breaker.state == OPEN:
                    break
                if attempt < retries:
                    wait = self.compute_backoff(attempt, rng=rng)
                    backoffs.append(wait)
                    if sleep:
                        time.sleep(wait)
        tracer.span(f"{name}.exhausted", "ERROR", 0.0, parent,
                    {"attempts": attempts, "error": last_error})
        return {"ok": False, "status": "EXHAUSTED", "attempts": attempts,
                "breaker_state": breaker.state, "backoffs": backoffs,
                "error": last_error}

    # ------------------------------------------------------------------ #
    # 健康探测
    # ------------------------------------------------------------------ #
    def probe_health(self) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        now = [1000.0]
        br = WatchdogBreaker(failure_threshold=2, recovery_timeout=10,
                             clock=lambda: now[0])
        br.record_failure()
        br.record_failure()
        open_ok = br.state == OPEN and not br.allow()
        now[0] += 11
        half_ok = br.allow() and br.state == HALF_OPEN
        br.record_success()
        closed_ok = br.state == CLOSED
        checks.append({"ok": open_ok and half_ok and closed_ok,
                       "msg": "三态熔断 CLOSED→OPEN→HALF_OPEN→CLOSED 正确",
                       "dim": "L10.breaker", "sev": "OK" if (open_ok and half_ok and closed_ok) else "BLOCKER"})

        rng = random.Random(7)
        vals = [self.compute_backoff(i, 0.5, 30.0, rng) for i in range(6)]
        bounds = [0.0 <= vals[0] <= 0.5, 0.0 <= vals[5] <= 30.0]
        checks.append({"ok": all(bounds) and len(set(vals)) > 1,
                       "msg": f"全抖动退避在 [0, ceiling] 内且非恒定 {vals}",
                       "dim": "L10.backoff", "sev": "OK" if all(bounds) else "BLOCKER"})

        demo = self.execute_with_resilience(
            "evolve.healthcheck", lambda: {"status": "ok"})
        tel_ok = bool(demo["ok"]) and os.path.isfile(self.telemetry_path)
        last = {}
        if tel_ok:
            with open(self.telemetry_path, encoding="utf-8") as f:
                lines = [x for x in f.read().splitlines() if x.strip()]
            tel_ok = bool(lines) and all(
                k in json.loads(lines[-1]) for k in
                ("trace_id", "span_id", "sha256", "duration_ms", "status"))
            last = json.loads(lines[-1]) if lines else {}
        checks.append({"ok": tel_ok, "msg": "telemetry.jsonl 落盘且含 TraceID/SpanID/SHA256",
                       "dim": "L10.telemetry", "sev": "OK" if tel_ok else "BLOCKER"})

        ok_all = all(x["ok"] for x in checks)
        return {"ok": ok_all, "engine": self.ENGINE, "layer": self.LAYER,
                "status": "HEALTHY" if ok_all else "DEGRADED",
                "checks": checks, "breaker_transitions": br.transitions,
                "backoff_samples": vals, "telemetry_last": last,
                "telemetry_path": self.telemetry_path,
                "capabilities": list(self.CAPABILITIES),
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds")}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R20 L10 看门狗与遥测")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    wd = R20TelemetryWatchdog()
    out = wd.probe_health()
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "status": out["status"]}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
