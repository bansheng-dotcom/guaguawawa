# -*- coding: utf-8 -*-
"""演进执行器与遥测的「反假绿」回归测试。

覆盖独立审计提出的缺口：
- 步骤 1/2 不能退回恒 true（引擎缺失 / 标杆 token 不符必须 FAIL）；
- evolve 子命令的门禁失败必须以非零退出（否则 runner 的步骤 4 探针会假绿）；
- 遥测父 span 状态必须与子门禁一致，且链路审计能发现悬空父引用/跨 trace 引用。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (HERE, os.path.dirname(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import auto_evolve_runner as runner  # noqa: E402
from engines import telemetry_watchdog as tw  # noqa: E402
from engines.telemetry_watchdog import TelemetryTracer  # noqa: E402

TMP = os.path.join(HERE, "workspace", "tmp")
os.makedirs(TMP, exist_ok=True)


class TestRunnerGates(unittest.TestCase):
    def test_audit_gate_rejects_missing_engine(self):
        stage = {"engine_module": "module_that_does_not_exist_r07",
                 "verify_cmd": [sys.executable, "-c", "print(1)"],
                 "audit": "审查要点占位文本足够长"}
        out = runner._audit_gate(stage)
        self.assertFalse(out["ok"])
        self.assertFalse(out["checks"]["engine_file_exists"])

    def test_audit_gate_accepts_real_engine(self):
        for stage in runner.EVOLUTION_STAGES:
            self.assertTrue(runner._audit_gate(stage)["ok"], stage["engine_module"])

    def test_benchmark_gate_rejects_wrong_tokens(self):
        stage = dict(runner.EVOLUTION_STAGES[6])
        stage["bench_tokens"] = ["token-not-present-anywhere-xyz"]
        self.assertFalse(runner._benchmark_gate(stage)["ok"])
        stage["bench_tokens"] = []
        self.assertFalse(runner._benchmark_gate(stage)["ok"], "空 token 必须判失败")

    def test_benchmark_tokens_declared_and_hit(self):
        for stage in runner.EVOLUTION_STAGES:
            self.assertTrue(stage.get("bench_tokens"), stage["engine_module"])
            self.assertTrue(runner._benchmark_gate(stage)["ok"], stage["engine_module"])

    def test_cli_gate_aware_exit_codes(self):
        clean = subprocess.run(
            [sys.executable, "agent.py", "evolve", "bundle",
             "--input", os.path.join(HERE, "examples", "prd.json"),
             "--out-dir", os.path.join(TMP, "cli_clean")],
            cwd=HERE, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(clean.returncode, 0, clean.stderr[-500:])
        dirty = subprocess.run(
            [sys.executable, "agent.py", "evolve", "bundle",
             "--input", os.path.join(HERE, "examples", "prd_dirty.json"),
             "--out-dir", os.path.join(TMP, "cli_dirty")],
            cwd=HERE, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(dirty.returncode, 1, "门禁未过必须非零退出")
        payload = json.loads([ln for ln in dirty.stdout.splitlines()
                              if ln.startswith("__AGENT_RESULT__ ")][0]
                             [len("__AGENT_RESULT__ "):])
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["exported"])
        self.assertFalse(payload["gate_ok"])

    def test_telemetry_parent_span_reflects_gate_failure(self):
        path = os.path.join(TMP, "runner_telemetry_fail.jsonl")
        if os.path.exists(path):
            os.remove(path)
        failing = {"ok": False,
                   "gates": {"legacy_run_tests": {"ok": False, "rc": 1},
                             "evolution_pytest": {"ok": True, "rc": 0}}}
        patched = (lambda *a, **k: TelemetryTracer(path=path))
        with mock.patch.object(tw, "TelemetryTracer", patched):
            runner._emit_round_telemetry(
                {"round": 9, "layer": "L09", "batch": 3, "ok": False,
                 "completed_at": "t"}, failing)
        with open(path, encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        parent = next(r for r in records if r["name"] == "evolve.round.9")
        self.assertEqual(parent["status"], "ERROR", "父 span 不得在门禁失败时写 OK")
        gates = {r["name"]: r["status"] for r in records if r["name"].startswith("gate.")}
        self.assertEqual(gates["gate.legacy_run_tests"], "ERROR")
        self.assertEqual(gates["gate.evolution_pytest"], "OK")


class TestTelemetryChainAudit(unittest.TestCase):
    def _write(self, records):
        path = os.path.join(TMP, "chain_audit.jsonl")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return path

    @staticmethod
    def _rec(span_id, trace_id, parent=None, status="OK"):
        import hashlib
        return {"schema": "pm.telemetry/v1", "service": "t", "trace_id": trace_id,
                "span_id": span_id, "parent_span_id": parent, "name": "s",
                "status": status, "duration_ms": 1.0,
                "sha256": hashlib.sha256(span_id.encode()).hexdigest(),
                "ts": 1.0}

    def test_dangling_and_cross_trace_detected(self):
        path = self._write([
            self._rec("a" * 16, "t1" * 16, None),
            self._rec("b" * 16, "t2" * 16, "a" * 16),   # 跨 trace 引用
            self._rec("c" * 16, "t3" * 16, "f" * 16),   # 悬空父引用
        ])
        out = TelemetryTracer(path=path).verify_chain()
        self.assertFalse(out["ok"])
        self.assertEqual(out["cross_trace_parents"], ["a" * 16])
        self.assertEqual(out["dangling_parents"], ["f" * 16])

    def test_duplicate_span_detected(self):
        path = self._write([
            self._rec("d" * 16, "t1" * 16),
            self._rec("d" * 16, "t1" * 16),
        ])
        out = TelemetryTracer(path=path).verify_chain()
        self.assertFalse(out["ok"])
        self.assertTrue(out["duplicate_spans"])

    def test_attributes_and_error_redacted(self):
        path = os.path.join(TMP, "redaction.jsonl")
        if os.path.exists(path):
            os.remove(path)
        tracer = TelemetryTracer(path=path)
        tracer.log("probe", attributes={"password": "hunter2-plaintext"},
                   error="RuntimeError: hunter2-plaintext")
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("hunter2-plaintext", raw)
        self.assertIn("password_sha256", json.loads(raw)["attributes"])


if __name__ == "__main__":
    unittest.main()
