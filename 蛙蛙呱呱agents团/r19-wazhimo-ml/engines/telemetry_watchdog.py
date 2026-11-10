# -*- coding: utf-8 -*-
"""L10 工业容灾层 —— 三态看门狗熔断 + 全抖动退避 + 全链路遥测。

SOP v13.0 L10 体检病灶（R19 真实断点）：
    1. 评估/检索/模型仓库等外部依赖抖动时直接抛栈崩溃，或写成 `except: pass`
       静默吞异常，坏数据照样往下游流；
    2. 没有超时熔断：一个卡死的评估任务会拖垮整条发布链；
    3. 没有 TraceID/SpanID/耗时/健康态遥测，线上事故无法定位是哪个环节烂了。

对标开源标杆（Stars > 1k）：
    * temporalio/temporal (>12k)                  —— 长任务看门狗与重试语义
    * open-telemetry/opentelemetry-python (>2k)   —— Trace/Span 遥测规范
    * jd/tenacity (>6k)                           —— 指数退避与 full jitter

落地的最低 3 项架构升级：
    1. CLOSED / OPEN / HALF_OPEN 三态熔断器（阈值 + 恢复窗口）；
    2. 指数退避 + Full Jitter 重试（可注入 RNG，测试确定）；
    3. `workspace/telemetry.jsonl` 全链路遥测（TraceID/SpanID/SHA256/耗时/状态）。

用法：
    python -m engines.telemetry_watchdog --probe --out workspace/rounds/L10_telemetry.json
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import random
import sys
import time
import traceback
import uuid
from collections import deque
from typing import Any, Callable, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"


def _sha(obj: Any) -> str:
    raw = obj if isinstance(obj, (bytes, bytearray)) else str(obj).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class WatchdogBreaker:
    """三态熔断器：CLOSED → (失败达阈值) → OPEN → (恢复窗口到期) → HALF_OPEN。"""

    def __init__(self, failure_threshold: int = 2, recovery_timeout_sec: float = 0.1,
                 clock: Optional[Callable[[], float]] = None):
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout_sec = float(recovery_timeout_sec)
        self._clock = clock or time.monotonic
        self.state = CLOSED
        self.failures = 0
        self.opened_at: Optional[float] = None
        self.transitions: List[Dict[str, Any]] = []

    def _transition(self, new_state: str, reason: str) -> None:
        if new_state != self.state:
            self.transitions.append({"from": self.state, "to": new_state,
                                     "reason": reason,
                                     "ts": round(self._clock(), 4)})
            self.state = new_state

    def can_execute(self) -> bool:
        if self.state == CLOSED:
            return True
        if self.state == OPEN:
            if self.opened_at is not None and \
                    (self._clock() - self.opened_at) >= self.recovery_timeout_sec:
                self._transition(HALF_OPEN, "恢复窗口到期，放行半开探测")
                return True
            return False
        return True  # HALF_OPEN 放行一次探测

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None
        self._transition(CLOSED, "探测成功，恢复闭合")

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == HALF_OPEN:
            self.opened_at = self._clock()
            self._transition(OPEN, "半开探测失败，重新打开")
            return
        if self.failures >= self.failure_threshold and self.state != OPEN:
            self.opened_at = self._clock()
            self._transition(OPEN, f"连续失败 {self.failures} 次达阈值 {self.failure_threshold}")


class SlidingWindowBreaker:
    """[Cycle 2] 滑动窗口失败率熔断：按时间窗统计，而非连续计数。"""

    def __init__(self, window_sec: float = 60.0, failure_rate_threshold: float = 0.5,
                 min_samples: int = 5, recovery_timeout_sec: float = 1.0,
                 half_open_max_probes: int = 1,
                 clock: Optional[Callable[[], float]] = None):
        self.window_sec = float(window_sec)
        self.failure_rate_threshold = float(failure_rate_threshold)
        self.min_samples = max(1, int(min_samples))
        self.recovery_timeout_sec = float(recovery_timeout_sec)
        self.half_open_max_probes = max(1, int(half_open_max_probes))
        self._clock = clock or time.monotonic
        self._events: deque = deque()
        self.state = CLOSED
        self.opened_at: Optional[float] = None
        self.probes = 0
        self.transitions: List[Dict[str, Any]] = []

    def _transition(self, new_state: str, reason: str) -> None:
        if new_state != self.state:
            self.transitions.append({"from": self.state, "to": new_state,
                                     "reason": reason, "ts": round(self._clock(), 4)})
            self.state = new_state

    def _prune(self, now: float) -> None:
        while self._events and self._events[0][0] <= now - self.window_sec:
            self._events.popleft()

    def metrics(self) -> Dict[str, Any]:
        now = self._clock()
        self._prune(now)
        total = len(self._events)
        failures = sum(1 for _, ok in self._events if not ok)
        return {"samples": total, "failures": failures,
                "failure_rate": round(failures / total, 4) if total else 0.0,
                "window_sec": self.window_sec, "state": self.state}

    def can_execute(self) -> bool:
        now = self._clock()
        self._prune(now)
        if self.state == CLOSED:
            return True
        if self.state == OPEN:
            if self.opened_at is not None and \
                    (now - self.opened_at) >= self.recovery_timeout_sec:
                self.probes = 0
                self._transition(HALF_OPEN, "滑动窗口恢复期到期，进入半开")
                return True
            return False
        if self.probes < self.half_open_max_probes:
            self.probes += 1
            return True
        return False

    def record_success(self) -> None:
        now = self._clock()
        self._events.append((now, True))
        if self.state == HALF_OPEN:
            self.probes = 0
            self._transition(CLOSED, "半开探测成功，恢复闭合")

    def record_failure(self) -> None:
        now = self._clock()
        self._events.append((now, False))
        if self.state == HALF_OPEN:
            self.opened_at = now
            self._transition(OPEN, "半开探测失败，重新打开")
            return
        self._prune(now)
        total = len(self._events)
        failures = sum(1 for _, ok in self._events if not ok)
        rate = failures / total if total else 0.0
        if self.state == CLOSED and total >= self.min_samples \
                and rate >= self.failure_rate_threshold:
            self.opened_at = now
            self._transition(OPEN, f"窗口失败率 {rate:.2%} ≥ 阈值 "
                                   f"{self.failure_rate_threshold:.0%}（样本 {total}）")


class TelemetryTracer:
    """把每次执行写成一行 JSONL 遥测。"""

    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    def log(self, trace_id: str, span_id: str, name: str, duration_ms: float,
            status: str, attempt: int = 1, sha256: str = "", error: str = "") -> Dict[str, Any]:
        rec = {"ts": datetime.datetime.now().isoformat(timespec="milliseconds"),
               "trace_id": trace_id, "span_id": span_id, "name": name,
               "duration_ms": round(float(duration_ms), 3), "status": status,
               "attempt": int(attempt), "sha256": sha256, "error": error[:500]}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec


class R19TelemetryWatchdog:
    """弹性执行器：熔断 + 全抖动退避重试 + 遥测。"""

    ENGINE = "R19TelemetryWatchdog"
    LAYER = "L10"
    CAPABILITIES = [
        "CLOSED/OPEN/HALF_OPEN 三态熔断器与恢复窗口",
        "指数退避 + Full Jitter 重试 (可注入 RNG，确定性可测)",
        "telemetry.jsonl 全链路遥测 (TraceID/SpanID/SHA256/耗时/状态)",
        "[C2] 滑动窗口失败率熔断 + 半开探测配额",
        "[C2] 遥测聚合 (p50/p95/p99、错误率、分 span 统计)",
        "[C2] Trace 重建 (按 trace_id 还原 span 序列与总耗时)",
    ]

    def __init__(self, workspace_dir: Optional[str] = None,
                 log_path: Optional[str] = None):
        ws = workspace_dir or os.path.join(_ROLE, "workspace")
        self.log_path = log_path or os.path.join(ws, "telemetry.jsonl")
        self.tracer = TelemetryTracer(self.log_path)
        self.breaker = WatchdogBreaker()

    # ------------------------------------------------------------------ #
    def probe_health(self) -> Dict[str, Any]:
        trace_id = uuid.uuid4().hex
        t0 = time.monotonic()
        ok = True
        try:
            self.tracer.log(trace_id, uuid.uuid4().hex, "watchdog.probe",
                            (time.monotonic() - t0) * 1000, "OK", 1,
                            _sha({"layer": self.LAYER, "ts": trace_id}))
        except OSError as exc:  # pragma: no cover - 磁盘异常
            ok = False
            self.tracer_error = str(exc)
        return {"ok": ok, "engine": self.ENGINE, "layer": self.LAYER,
                "status": "healthy" if ok else "degraded",
                "log_path": self.log_path,
                "log_exists": os.path.exists(self.log_path),
                "breaker_state": self.breaker.state,
                "trace_id": trace_id,
                "capabilities": list(self.CAPABILITIES),
                "checks": [
                    {"ok": ok, "msg": "遥测写入成功", "dim": "L10.telemetry",
                     "sev": "OK" if ok else "CRITICAL"},
                    {"ok": self.breaker.state == CLOSED, "msg": "熔断器初始闭合",
                     "dim": "L10.breaker", "sev": "OK"},
                ],
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds")}

    # ------------------------------------------------------------------ #
    @staticmethod
    def backoff_delay(attempt: int, base_delay: float = 0.05,
                      cap: float = 2.0, rng: Optional[random.Random] = None) -> float:
        """指数退避 + Full Jitter：delay ∈ [0, min(cap, base * 2^(attempt-1))]。"""
        r = rng or random
        ceil = min(cap, base_delay * (2 ** max(0, int(attempt) - 1)))
        return round(r.uniform(0, ceil), 6)

    def execute_with_resilience(self, name: str, fn: Callable[[], Any],
                               max_attempts: int = 3, base_delay: float = 0.01,
                               cap: float = 0.2,
                               rng: Optional[random.Random] = None,
                               breaker: Optional[WatchdogBreaker] = None) -> Dict[str, Any]:
        br = breaker or self.breaker
        trace_id = uuid.uuid4().hex
        attempts = 0
        last_error = ""
        trace: List[Dict[str, Any]] = []
        for attempt in range(1, max(1, int(max_attempts)) + 1):
            if not br.can_execute():
                trace.append({"attempt": attempt, "status": "CIRCUIT_OPEN"})
                return {"ok": False, "attempts": attempts, "trace_id": trace_id,
                        "error": "circuit_open", "breaker_state": br.state,
                        "trace": trace, "engine": self.ENGINE}
            attempts = attempt
            span_id = uuid.uuid4().hex
            t0 = time.monotonic()
            try:
                result = fn()
                dur = (time.monotonic() - t0) * 1000
                self.tracer.log(trace_id, span_id, name, dur, "OK", attempt, _sha(result))
                br.record_success()
                trace.append({"attempt": attempt, "status": "OK",
                              "duration_ms": round(dur, 3)})
                return {"ok": True, "attempts": attempts, "result": result,
                        "trace_id": trace_id, "breaker_state": br.state,
                        "trace": trace, "engine": self.ENGINE}
            except Exception as exc:  # noqa: BLE001 - 这里是容灾边界，必须兜住
                last_error = f"{type(exc).__name__}: {exc}"
                dur = (time.monotonic() - t0) * 1000
                self.tracer.log(trace_id, span_id, name, dur, "ERROR", attempt,
                                _sha(last_error), last_error)
                br.record_failure()
                trace.append({"attempt": attempt, "status": "ERROR",
                              "error": last_error, "duration_ms": round(dur, 3)})
                if attempt < max_attempts:
                    time.sleep(self.backoff_delay(attempt, base_delay, cap, rng))
        return {"ok": False, "attempts": attempts, "trace_id": trace_id,
                "error": last_error, "breaker_state": br.state,
                "trace": trace, "engine": self.ENGINE,
                "next": "重试耗尽，交由上游降级或人工介入（不静默吞异常）"}

    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    # [Cycle 2] 遥测聚合 + Trace 重建
    # ------------------------------------------------------------------ #
    @staticmethod
    def _percentile(values: List[float], pct: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return round(ordered[0], 3)
        idx = (len(ordered) - 1) * pct
        lo, hi = int(idx), min(len(ordered) - 1, int(idx) + 1)
        frac = idx - lo
        return round(ordered[lo] * (1 - frac) + ordered[hi] * frac, 3)

    def aggregate_telemetry(self, rows: Optional[List[Dict[str, Any]]] = None,
                            n: int = 200) -> Dict[str, Any]:
        rows = rows if rows is not None else self.read_telemetry(n)
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for rec in rows:
            groups.setdefault(str(rec.get("name", "unknown")), []).append(rec)
        by_name: Dict[str, Dict[str, Any]] = {}
        for name, items in groups.items():
            durations = [float(r.get("duration_ms", 0) or 0) for r in items]
            errors = sum(1 for r in items if str(r.get("status", "")).upper() != "OK")
            by_name[name] = {
                "count": len(items), "errors": errors,
                "error_rate": round(errors / len(items), 4) if items else 0.0,
                "p50": self._percentile(durations, 0.50),
                "p95": self._percentile(durations, 0.95),
                "p99": self._percentile(durations, 0.99),
                "max": round(max(durations), 3) if durations else 0.0,
            }
        all_durations = [float(r.get("duration_ms", 0) or 0) for r in rows]
        all_errors = sum(1 for r in rows if str(r.get("status", "")).upper() != "OK")
        return {"ok": True, "total_spans": len(rows), "span_names": sorted(by_name),
                "by_name": by_name,
                "overall": {"error_rate": round(all_errors / len(rows), 4) if rows else 0.0,
                            "p50": self._percentile(all_durations, 0.50),
                            "p95": self._percentile(all_durations, 0.95),
                            "p99": self._percentile(all_durations, 0.99)},
                "window_rows": n}

    def reconstruct_traces(self, rows: Optional[List[Dict[str, Any]]] = None,
                           n: int = 200) -> Dict[str, Any]:
        rows = rows if rows is not None else self.read_telemetry(n)
        traces: Dict[str, List[Dict[str, Any]]] = {}
        for rec in rows:
            traces.setdefault(str(rec.get("trace_id", "unknown")), []).append(rec)
        built = []
        for trace_id, spans in traces.items():
            spans = sorted(spans, key=lambda r: str(r.get("ts", "")))
            total = round(sum(float(s.get("duration_ms", 0) or 0) for s in spans), 3)
            errors = [s for s in spans if str(s.get("status", "")).upper() != "OK"]
            built.append({"trace_id": trace_id, "span_count": len(spans),
                          "total_duration_ms": total,
                          "attempts": sum(int(s.get("attempt", 1) or 1) for s in spans),
                          "error_count": len(errors),
                          "complete": bool(spans),
                          "span_sequence": [s.get("name") for s in spans],
                          "status": "OK" if not errors else "DEGRADED"})
        built.sort(key=lambda t: (-t["total_duration_ms"], t["trace_id"]))
        return {"ok": bool(built), "trace_count": len(built),
                "traces": built[:50],
                "slowest": built[0]["trace_id"] if built else None}

    def read_telemetry(self, n: int = 5) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_path):
            return []
        rows: List[Dict[str, Any]] = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
        return rows[-n:]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L10 看门狗熔断与遥测")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    wd = R19TelemetryWatchdog()
    out = wd.probe_health()
    ok_once = wd.execute_with_resilience("probe.healthcheck", lambda: {"status": "ok"},
                                         rng=random.Random(7))
    # 演示退避：注入确定性 RNG
    delays = [wd.backoff_delay(a, 0.05, 2.0, random.Random(7)) for a in range(1, 5)]
    out.update({"ok": bool(out["ok"] and ok_once["ok"]),
                "resilience_demo": {k: v for k, v in ok_once.items() if k != "result"},
                "backoff_delays": delays})
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "status": out["status"],
                      "log": out["log_path"], "delays": delays,
                      "out": args.out}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
