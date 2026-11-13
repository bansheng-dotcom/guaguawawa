# -*- coding: utf-8 -*-
"""engines/telemetry_watchdog.py - L10 工业容灾层 (Watchdog / Circuit Breaker / Telemetry).

对标开源标杆（Stars > 1k）：
- temporalio/temporal —— 长任务编排与超时治理；
- open-telemetry/opentelemetry-python —— TraceID/SpanID 全链路遥测；
- jd/tenacity —— 指数退避 + 全抖动重试（Exponential Backoff with Full Jitter）。

解决 R07 历史断点：外部依赖抖动/超时即整条链路瘫痪，无三态熔断、无退避重试、
无遥测可观测性，出故障只能靠人肉复现。

核心能力：
1. `CircuitBreaker`：CLOSED / OPEN / HALF_OPEN 三态熔断（可注入时钟，确定性可测）；
2. `retry_with_backoff`：指数退避 + 全抖动（sleep 与 rng 可注入，测试零等待）；
3. `Watchdog`：线程级软超时 + **子进程级硬隔离**（超时直接 kill，不污染主进程）；
4. `TelemetryTracer`：JSONL 全链路遥测（TraceID/SpanID/ParentSpanID/SHA256/耗时/状态）。
"""
from __future__ import annotations

import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import random
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = ["CircuitOpenError", "CircuitBreaker", "retry_with_backoff",
           "Watchdog", "TelemetryTracer", "TELEMETRY_SCHEMA"]

TELEMETRY_SCHEMA = "pm.telemetry/v1"
_REQUIRED_KEYS = ("schema", "trace_id", "span_id", "name", "status",
                  "duration_ms", "sha256", "ts")

CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(RuntimeError):
    """熔断器处于 OPEN 时拒绝调用。"""


class CircuitBreaker:
    """三态熔断器：连续失败达阈值即 OPEN，冷却后 HALF_OPEN 试探，成功则 CLOSED。"""

    def __init__(self, name: str = "r07-breaker", failure_threshold: int = 3,
                 recovery_timeout: float = 30.0, half_open_max_calls: int = 1,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self.name = name
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout = float(recovery_timeout)
        self.half_open_max_calls = max(1, int(half_open_max_calls))
        self._clock = clock or time.monotonic
        self._state = CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._half_open_calls = 0
        self._transitions: List[Dict[str, Any]] = []

    @property
    def state(self) -> str:
        self._maybe_half_open()
        return self._state

    def _transition(self, new_state: str, reason: str) -> None:
        if new_state == self._state:
            return
        self._transitions.append({
            "from": self._state, "to": new_state, "reason": reason,
            "at": round(self._clock(), 6),
        })
        self._state = new_state
        if new_state == OPEN:
            self._opened_at = self._clock()
        if new_state == HALF_OPEN:
            self._half_open_calls = 0

    def _maybe_half_open(self) -> None:
        if (self._state == OPEN
                and self._clock() - self._opened_at >= self.recovery_timeout):
            self._transition(HALF_OPEN, "recovery_timeout_elapsed")

    def record_success(self) -> None:
        self._failures = 0
        self._transition(CLOSED, "success")
        self._half_open_calls = 0

    def record_failure(self) -> None:
        self._failures += 1
        if self._state == HALF_OPEN:
            self._transition(OPEN, "half_open_trial_failed")
        elif self._failures >= self.failure_threshold:
            self._transition(OPEN, f"failure_threshold({self.failure_threshold})_reached")

    def call(self, fn: Callable[[], Any]) -> Any:
        self._maybe_half_open()
        if self._state == OPEN:
            raise CircuitOpenError(
                f"[{self.name}] 熔断 OPEN，拒绝调用（{(self.recovery_timeout - (self._clock() - self._opened_at)):.2f}s 后进入半开）")
        if self._state == HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError(f"[{self.name}] 半开态试探额度已用尽，拒绝调用")
            self._half_open_calls += 1
        try:
            value = fn()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return value

    def stats(self) -> Dict[str, Any]:
        return {"name": self.name, "state": self.state, "failures": self._failures,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "transitions": list(self._transitions)}


def retry_with_backoff(fn: Callable[[], Any], attempts: int = 4,
                       base_delay: float = 0.05, max_delay: float = 1.0,
                       jitter: bool = True,
                       rng: Optional[random.Random] = None,
                       sleep: Optional[Callable[[float], None]] = None,
                       retry_on: Tuple[type, ...] = (Exception,)) -> Dict[str, Any]:
    """指数退避 + 全抖动重试：delay_i = U(0, min(max, base * 2**i))。"""
    rng = rng or random.Random(20261110)
    sleep = sleep or time.sleep
    delays: List[float] = []
    last_error: Optional[str] = None
    attempt_used = 0
    for attempt in range(1, max(1, attempts) + 1):
        attempt_used = attempt
        try:
            return {"ok": True, "attempts": attempt, "value": fn(),
                    "delays": delays, "last_error": None}
        except retry_on as exc:  # noqa: BLE001 - 重试需捕获调用方声明的异常族
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt == attempts:
                break
            ceiling = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay = rng.uniform(0.0, ceiling) if jitter else ceiling
            delays.append(round(delay, 6))
            sleep(delay)
    return {"ok": False, "attempts": attempt_used, "value": None,
            "delays": delays, "last_error": last_error}


class Watchdog:
    """长任务看门狗：线程软超时 + 子进程硬隔离（超时 kill，不留僵尸）。"""

    def __init__(self, default_timeout: float = 2.0,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self.default_timeout = float(default_timeout)
        self._clock = clock or time.monotonic

    def run(self, fn: Callable[[], Any],
            timeout: Optional[float] = None) -> Dict[str, Any]:
        budget = float(timeout if timeout is not None else self.default_timeout)
        started = self._clock()
        box: Dict[str, Any] = {}

        def _target() -> None:
            try:
                box["value"] = fn()
            except Exception as exc:  # noqa: BLE001 - 隔离态必须吞掉并上报
                box["error"] = f"{type(exc).__name__}: {exc}"

        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        worker.join(budget)
        elapsed_ms = round((self._clock() - started) * 1000.0, 3)
        if worker.is_alive():
            return {"ok": False, "status": "TIMEOUT", "duration_ms": elapsed_ms,
                    "budget_ms": round(budget * 1000.0, 3), "value": None,
                    "error": "watchdog timeout", "process_isolated": False}
        if "error" in box:
            return {"ok": False, "status": "ERROR", "duration_ms": elapsed_ms,
                    "budget_ms": round(budget * 1000.0, 3), "value": None,
                    "error": box["error"], "process_isolated": False}
        return {"ok": True, "status": "SUCCESS", "duration_ms": elapsed_ms,
                "budget_ms": round(budget * 1000.0, 3), "value": box.get("value"),
                "error": None, "process_isolated": False}

    def run_isolated(self, code: str, timeout: Optional[float] = None,
                     env_extra: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """在独立子进程中执行代码；超时直接 kill（真隔离，主进程不被拖垮）。"""
        budget = float(timeout if timeout is not None else self.default_timeout)
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        if env_extra:
            env.update(env_extra)
        started = self._clock()
        try:
            proc = subprocess.run([sys.executable, "-c", code], env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  timeout=budget, cwd=os.path.dirname(
                                      os.path.dirname(os.path.abspath(__file__))))
        except subprocess.TimeoutExpired:
            elapsed_ms = round((self._clock() - started) * 1000.0, 3)
            return {"ok": False, "status": "TIMEOUT", "duration_ms": elapsed_ms,
                    "budget_ms": round(budget * 1000.0, 3),
                    "process_isolated": True, "killed": True,
                    "stdout": "", "error": "process hard-killed after timeout"}
        elapsed_ms = round((self._clock() - started) * 1000.0, 3)
        out = (proc.stdout or b"").decode("utf-8", "replace").strip()
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        return {"ok": proc.returncode == 0, "status": "SUCCESS" if proc.returncode == 0 else "ERROR",
                "duration_ms": elapsed_ms, "budget_ms": round(budget * 1000.0, 3),
                "process_isolated": True, "killed": False,
                "stdout": out[-500:], "error": err[-500:] or None}


_SAFE_ATTR_KEYS = {"round", "batch", "layer", "gate", "kind", "step",
                   "stage", "state", "status", "role", "attempt", "level"}


def _safe_attributes(attributes: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """attributes 脱敏：只允许白名单元数据键，其余键的值一律落 SHA256 指纹。"""
    out: Dict[str, Any] = {}
    for key, value in (attributes or {}).items():
        key_s = str(key)
        if key_s in _SAFE_ATTR_KEYS and (
                isinstance(value, (int, float, bool)) or value is None
                or (isinstance(value, str) and len(value) <= 24)):
            out[key_s] = value
            continue
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        out[f"{key_s}_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return out


class TelemetryTracer:
    """全链路遥测：把 operation 写成 JSONL span，供离线审计与链路重建。"""

    def __init__(self, path: Optional[str] = None, service: str = "r07-wademing-pm",
                 clock: Optional[Callable[[], float]] = None) -> None:
        here = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(role_workspace(os.path.dirname(here)),
                                         "telemetry.jsonl")
        self.service = service
        self._clock = clock or time.time
        self._lock = threading.Lock()
        self._seq = 0
        self._salt = os.urandom(8).hex()
        self._stack: List[Dict[str, str]] = []
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _new_ids(self) -> Tuple[str, str]:
        with self._lock:
            self._seq += 1
            seq = self._seq
        # trace/span id 必须全局唯一：混入进程级随机盐，避免跨进程/跨轮次撞号
        trace_id = hashlib.sha256(f"{self.service}:trace:{seq}:{self._salt}".encode()).hexdigest()[:32]
        span_id = hashlib.sha256(f"{self.service}:span:{seq}:{self._salt}".encode()).hexdigest()[:16]
        return trace_id, span_id

    def _append(self, record: Dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock:
            with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(line)

    def _emit(self, trace_id: str, span_id: str, parent_span_id: Optional[str],
              name: str, status: str, payload: Any, duration_ms: float,
              attributes: Optional[Dict[str, Any]], error: Optional[str]) -> Dict[str, Any]:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str) \
            if payload is not None else ""
        record = {
            "schema": TELEMETRY_SCHEMA,
            "service": self.service,
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "status": status,
            "duration_ms": round(float(duration_ms), 3),
            "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "bytes": len(raw.encode("utf-8")),
            "attributes": _safe_attributes(attributes),
            "error": ({"class": error.split(":", 1)[0],
                       "sha256": hashlib.sha256(error.encode("utf-8")).hexdigest()[:16]}
                      if error else None),
            "ts": round(self._clock(), 6),
        }
        self._append(record)
        return record

    def log(self, name: str, status: str = "OK", payload: Any = None,
            duration_ms: float = 0.0, attributes: Optional[Dict[str, Any]] = None,
            error: Optional[str] = None) -> Dict[str, Any]:
        trace_id, span_id = self._new_ids()
        parent = self._stack[-1]["span_id"] if self._stack else None
        if parent:
            trace_id = self._stack[-1]["trace_id"]
        return self._emit(trace_id, span_id, parent, name, status, payload,
                          duration_ms, attributes, error)

    @contextmanager
    def span(self, name: str, payload: Any = None,
             attributes: Optional[Dict[str, Any]] = None):
        """with tracer.span("x") as span: ... → 自动记录耗时/状态/父子关系。"""
        started = self._clock()
        trace_id, span_id = self._new_ids()
        parent = self._stack[-1]["span_id"] if self._stack else None
        if parent:
            trace_id = self._stack[-1]["trace_id"]
        entry = {"name": name, "trace_id": trace_id, "span_id": span_id}
        self._stack.append(entry)
        holder: Dict[str, Any] = {"name": name, "span_id": span_id,
                                  "trace_id": trace_id}
        try:
            yield holder
        except Exception as exc:  # noqa: BLE001
            self._stack.pop()
            self._emit(trace_id, span_id, parent, name, "ERROR", payload,
                       (self._clock() - started) * 1000.0, attributes,
                       f"{type(exc).__name__}: {exc}")
            raise
        else:
            self._stack.pop()
            self._emit(trace_id, span_id, parent, name, "OK", payload,
                       (self._clock() - started) * 1000.0, attributes, None)

    # -- 审计 ---------------------------------------------------------- #
    def verify_chain(self, last_n: Optional[int] = None) -> Dict[str, Any]:
        """离线审计：全文件结构合法性 + （可选）最近 N 条 span 的链路一致性。"""
        if not os.path.isfile(self.path):
            return {"ok": False, "error": "telemetry.jsonl 不存在", "lines": 0}
        total = 0
        bad = 0
        records: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    rec = json.loads(line)
                except ValueError:
                    bad += 1
                    continue
                if any(k not in rec for k in _REQUIRED_KEYS):
                    bad += 1
                    continue
                if len(rec["sha256"]) != 64 or len(rec["span_id"]) != 16:
                    bad += 1
                records.append(rec)
        window = records[-int(last_n):] if last_n else records
        statuses: Dict[str, int] = {}
        spans: List[str] = []
        parents: List[Optional[str]] = []
        span_trace: Dict[str, str] = {}
        for rec in window:
            statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1
            spans.append(rec["span_id"])
            parents.append(rec.get("parent_span_id"))
            span_trace[rec["span_id"]] = rec["trace_id"]
        # 引用完整性：父 span 必须存在且同一 trace
        dangling = [p for p in parents if p and p not in set(spans)]
        cross_trace = []
        for rec in window:
            parent = rec.get("parent_span_id")
            if parent and parent in span_trace and span_trace[parent] != rec["trace_id"]:
                cross_trace.append(parent)
        duplicates = len(spans) != len(set(spans))
        return {"ok": bad == 0 and total > 0 and not dangling and not duplicates
                and not cross_trace,
                "lines": total, "window": len(window), "bad_lines": bad,
                "statuses": statuses,
                "traces": sorted({r["trace_id"] for r in window}),
                "dangling_parents": dangling, "cross_trace_parents": cross_trace,
                "duplicate_spans": duplicates,
                "unique_spans": len(set(spans)), "path": self.path}


def self_test(telemetry_path: Optional[str] = None,
              tmp_dir: Optional[str] = None) -> Dict[str, Any]:
    """L10 确定性自检：熔断三态 / 退避重试 / 超时隔离 / 遥测链路。"""
    here = os.path.dirname(os.path.abspath(__file__))
    agent_dir = os.path.dirname(here)
    tmp_dir = tmp_dir or os.path.join(role_workspace(agent_dir), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    telemetry_path = telemetry_path or os.path.join(role_workspace(agent_dir), "telemetry.jsonl")
    # 遥测是 append-only 审计日志：探针不清空历史，只校验「最近 4 条」自洽
    os.makedirs(os.path.dirname(telemetry_path), exist_ok=True)
    tracer = TelemetryTracer(path=telemetry_path)
    steps: List[Dict[str, Any]] = []

    def rec(name: str, ok: bool, detail: Any = "") -> None:
        steps.append({"step": name, "ok": bool(ok), "detail": detail})

    # ① 指数退避 + 全抖动重试（前两次失败，第三次成功）
    tries = {"n": 0}

    def flaky() -> str:
        tries["n"] += 1
        if tries["n"] < 3:
            raise TimeoutError("upstream timeout")
        return "ok-after-retry"

    retry = retry_with_backoff(flaky, attempts=4, base_delay=0.04, max_delay=0.2,
                               rng=random.Random(7), sleep=lambda _s: None)
    rec("指数退避重试", retry["ok"] and retry["attempts"] == 3
        and len(retry["delays"]) == 2
        and all(d <= 0.2 for d in retry["delays"]), retry)

    # ② 三态熔断（注入时钟，零等待）
    now = {"t": 1000.0}
    breaker = CircuitBreaker("r07-upstream", failure_threshold=3,
                             recovery_timeout=5.0, clock=lambda: now["t"])

    def boom() -> None:
        raise ConnectionError("upstream reset")

    for _ in range(3):
        try:
            breaker.call(boom)
        except ConnectionError:
            pass
    rec("熔断 OPEN", breaker.state == OPEN, breaker.stats()["transitions"])
    blocked = False
    try:
        breaker.call(lambda: "x")
    except CircuitOpenError:
        blocked = True
    rec("OPEN 态硬拒绝", blocked, "CircuitOpenError raised")
    now["t"] += 6.0
    rec("冷却进入 HALF_OPEN", breaker.state == HALF_OPEN, breaker.stats()["transitions"])
    value = breaker.call(lambda: "recovered")
    rec("半开试探成功 → CLOSED", value == "recovered" and breaker.state == CLOSED,
        breaker.stats()["transitions"])

    # ③ 线程看门狗：成功 / 软超时
    wd = Watchdog(default_timeout=0.5)
    fast = wd.run(lambda: 42, timeout=0.3)
    slow = wd.run(lambda: time.sleep(0.4) or "late", timeout=0.1)
    rec("看门狗软超时", fast["ok"] and slow["status"] == "TIMEOUT",
        {"fast": fast["status"], "slow": slow["status"]})

    # ④ 子进程硬隔离：超时必须 kill，主进程不受影响
    isolated = wd.run_isolated("import time; time.sleep(3)", timeout=0.4)
    rec("子进程硬隔离 kill", isolated["status"] == "TIMEOUT"
        and isolated["process_isolated"] and isolated["killed"],
        {"status": isolated["status"], "killed": isolated["killed"]})

    # ⑤ 全链路遥测：status 由本轮探针真实结论推导，禁止写死 "pass"
    marker = f"R07_SECRET_MARKER_{os.urandom(4).hex()}"
    with tracer.span("watchdog.self_test", payload={"layer": "L10"}) as outer:
        outer["layer"] = "L10"
        tracer.log("retry.backoff",
                   status="OK" if retry["ok"] and retry["attempts"] == 3 else "ERROR",
                   payload={"attempts": retry["attempts"], "delays": retry["delays"]},
                   attributes={"round": 10})
        tracer.log("breaker.state", status="OK" if breaker.state == CLOSED else "ERROR",
                   payload={"state": breaker.state,
                            "transitions": len(breaker.stats()["transitions"])})
        tracer.log("watchdog.isolated",
                   status="OK" if isolated["killed"] else "ERROR",
                   payload={"status": isolated["status"], "secret": marker})
    chain = tracer.verify_chain(last_n=4)
    rec("遥测 JSONL 链路完整", chain["ok"] and chain["window"] == 4,
        {"lines": chain["lines"], "window": chain["window"],
         "statuses": chain["statuses"], "traces": chain.get("traces"),
         "dangling": chain.get("dangling_parents")})
    rec("同 Trace 父子 span 一致",
        len(chain.get("traces", [])) == 1 and not chain.get("dangling_parents"),
        {"traces": chain.get("traces"), "unique_spans": chain.get("unique_spans")})

    # ⑥ 敏感载荷不得明文落盘：payload / attributes / error 三通道都只留指纹
    leaked_secret = f"SECRET_{os.urandom(4).hex()}"
    tracer.log("redaction.probe", payload={"secret": leaked_secret},
               attributes={"secret": leaked_secret},
               error=f"RuntimeError: {leaked_secret}")
    with open(telemetry_path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    rec("敏感载荷仅落指纹", leaked_secret not in raw and marker not in raw,
        {"path": telemetry_path, "probe_leaked": leaked_secret in raw,
         "marker_leaked": marker in raw})

    ok = all(s["ok"] for s in steps)
    return {"ok": ok, "layer": "L10", "engine": "TelemetryWatchdog",
            "steps": steps, "telemetry_path": telemetry_path,
            "breaker": breaker.stats(), "telemetry": chain}
