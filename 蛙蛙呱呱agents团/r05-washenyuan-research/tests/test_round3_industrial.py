# -*- coding: utf-8 -*-
"""R05 第 3 轮升级验收契约（工业交付阶段 L07~L10）。

本轮契约针对 R05 蛙深远真实体检病灶：
- L07：伴生包只有 research_spec/chart，没有 OASIS SARIF 审计结果与带 SHA256
  的资产清单，下游 CI 无法校验完整性、更无法回放发现；
- L08：patch_editor 只支持 replace/add/remove 三种算子，无 test/copy/move、
  无 JSON Pointer 转义、无 create_patch 差量生成与完整性摘要；
- L09：memory.py 的 rollback 只弹空列表、槽位不落顶层字段，遇到“第二套方案”
  这类数量代词直接失忆；
- L10：telemetry.py 的看门狗只在事后比对耗时（无法真正超时熔断），没有
  CLOSED/OPEN/HALF_OPEN 三态熔断、没有全抖动退避与 Trace/Span 上下文。
"""
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import sys
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
for _p in (_HERE, _ROLE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engines.asset_bundle import ResearchAssetBundle  # noqa: E402
from engines.diff_patch_engine import (ResearchDiffPatchEngine,  # noqa: E402
                                       PatchError, PatchTestFailed)
from engines.session_memory import ResearchSessionStore  # noqa: E402
from engines.telemetry_watchdog import (CircuitBreaker, CircuitOpenError,  # noqa: E402
                                        RetryPolicy, RetryExhausted, TaskTimeout,
                                        TelemetryTracer, WatchdogRunner)

TMP = os.path.join(role_workspace(_ROLE), "tmp")


def _ensure_tmp():
    os.makedirs(TMP, exist_ok=True)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class TestL07AssetBundle(unittest.TestCase):
    """L07 伴生消费层：SARIF 2.1.0 + SHA256 资产清单 + 完整性校验。"""

    DATA = {
        "tam": 120.0, "hhi": 2250, "cr4": 90, "structure": "moderate",
        "claims": [{"id": "c1", "sources": ["S1"]}, {"id": "c2", "sources": []}],
        "tam_top": 120.0, "tam_bottom": 180.0,
    }

    def setUp(self):
        _ensure_tmp()
        self.out = os.path.join(TMP, "bundle_round3")
        self.bundle = ResearchAssetBundle().export_bundle(self.DATA, self.out)

    def test_all_artifacts_written(self):
        for key in ("research_spec", "chart_spec", "sarif", "bundle_manifest"):
            self.assertIn(key, self.bundle)
            self.assertTrue(os.path.exists(self.bundle[key]), key)

    def test_sarif_is_valid_2_1_0(self):
        with open(self.bundle["sarif"], "r", encoding="utf-8") as f:
            sarif = json.load(f)
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertTrue(sarif["$schema"].endswith("sarif-schema-2.1.0.json"))
        run = sarif["runs"][0]
        self.assertEqual(run["tool"]["driver"]["name"], "r05-washenyuan-research")
        self.assertTrue(run["results"])
        rule_ids = {r["ruleId"] for r in run["results"]}
        self.assertIn("R05-EVIDENCE-GAP", rule_ids)
        self.assertIn("R05-TAM-VARIANCE", rule_ids)
        for result in run["results"]:
            self.assertIn(result["level"], ("error", "warning", "note"))
            loc = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            self.assertTrue(loc)

    def test_manifest_hashes_are_verifiable(self):
        with open(self.bundle["bundle_manifest"], "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["producer"], "r05-washenyuan-research")
        self.assertGreaterEqual(len(manifest["artifacts"]), 3)
        for item in manifest["artifacts"]:
            path = os.path.join(self.out, item["path"])
            self.assertTrue(os.path.exists(path), item["path"])
            self.assertEqual(item["sha256"], _sha256(path))
            self.assertEqual(item["bytes"], os.path.getsize(path))

    def test_verify_bundle_detects_tampering(self):
        checker = ResearchAssetBundle()
        ok = checker.verify_bundle(self.bundle["bundle_manifest"])
        self.assertTrue(ok["ok"], ok)
        with open(self.bundle["research_spec"], "a", encoding="utf-8") as f:
            f.write("\n ")
        tampered = checker.verify_bundle(self.bundle["bundle_manifest"])
        self.assertFalse(tampered["ok"])
        self.assertTrue(tampered["mismatches"])


class TestL08DiffPatchEngine(unittest.TestCase):
    """L08 局部差量层：完整 RFC 6902 算子与完整性摘要。"""

    DOC = {"a": {"b": 1}, "arr": [1, 2], "weird/key": {"~x": 1}}

    def test_full_rfc6902_operators(self):
        engine = ResearchDiffPatchEngine()
        out = engine.apply(self.DOC, [
            {"op": "replace", "path": "/a/b", "value": 2},
            {"op": "add", "path": "/arr/-", "value": 3},
            {"op": "add", "path": "/new", "value": {"x": 1}},
            {"op": "copy", "from": "/a", "path": "/a_copy"},
            {"op": "move", "from": "/a_copy", "path": "/moved"},
            {"op": "remove", "path": "/arr/0"},
        ])
        self.assertEqual(out["a"]["b"], 2)
        self.assertEqual(out["arr"], [2, 3])
        self.assertEqual(out["new"], {"x": 1})
        self.assertNotIn("a_copy", out)
        self.assertEqual(out["moved"], {"b": 2})
        self.assertEqual(self.DOC["a"]["b"], 1, "patch 不得原地污染原文档")

    def test_json_pointer_escaping(self):
        out = ResearchDiffPatchEngine().apply(
            self.DOC, [{"op": "replace", "path": "/weird~1key/~0x", "value": 9}])
        self.assertEqual(out["weird/key"]["~x"], 9)

    def test_test_operator_and_errors(self):
        engine = ResearchDiffPatchEngine()
        engine.apply(self.DOC, [{"op": "test", "path": "/a/b", "value": 1}])
        with self.assertRaises(PatchTestFailed):
            engine.apply(self.DOC, [{"op": "test", "path": "/a/b", "value": 5}])
        with self.assertRaises(PatchError):
            engine.apply(self.DOC, [{"op": "replace", "path": "/nope", "value": 1}])
        with self.assertRaises(PatchError):
            engine.apply(self.DOC, [{"op": "bogus", "path": "/a", "value": 1}])

    def test_create_patch_roundtrip(self):
        engine = ResearchDiffPatchEngine()
        target = {"a": {"b": 1, "c": 2}, "arr": [1, 3], "z": None}
        patch = engine.create_patch(self.DOC, target)
        self.assertIsInstance(patch, list)
        self.assertGreaterEqual(len(patch), 2)
        self.assertEqual(engine.apply(self.DOC, patch), target)

    def test_integrity_summary(self):
        engine = ResearchDiffPatchEngine()
        changed = engine.apply_with_integrity(
            self.DOC, [{"op": "replace", "path": "/a/b", "value": 5}])
        self.assertEqual(changed["doc"]["a"]["b"], 5)
        self.assertTrue(changed["changed"])
        self.assertNotEqual(changed["sha256_before"], changed["sha256_after"])
        self.assertEqual(len(changed["applied"]), 1)

        noop = engine.apply_with_integrity(self.DOC, [])
        self.assertFalse(noop["changed"])
        self.assertEqual(noop["sha256_before"], noop["sha256_after"])


class TestL09SessionStore(unittest.TestCase):
    """L09 会话记忆层：槽位双向同步、数量代词消歧、真实回滚。"""

    def setUp(self):
        _ensure_tmp()
        self.path = os.path.join(TMP, "session_round3.json")
        if os.path.exists(self.path):
            os.remove(self.path)
        self.store = ResearchSessionStore(self.path)

    def test_slot_top_level_sync_and_persistence(self):
        self.store.record_turn("调研海外SaaS市场",
                               {"tam": 120.0,
                                "scenarios": [{"name": "A"}, {"name": "B"},
                                              {"name": "C"}]},
                               topic="海外SaaS市场")
        self.store.update_slot("current_market", "海外SaaS")
        self.assertEqual(self.store.state["current_market"], "海外SaaS")
        self.assertEqual(self.store.get_slot("current_market"), "海外SaaS")

        reloaded = ResearchSessionStore(self.path)
        self.assertEqual(reloaded.get_slot("current_market"), "海外SaaS")
        self.assertEqual(reloaded.state.get("current_market"), "海外SaaS")

    def test_pronoun_and_ordinal_disambiguation(self):
        self.store.record_turn("调研海外SaaS市场",
                               {"tam": 120.0,
                                "scenarios": [{"name": "A"}, {"name": "B"},
                                              {"name": "C"}]},
                               topic="海外SaaS市场")
        self.store.update_slot("current_market", "海外SaaS")
        resolved = self.store.resolve_reference("按刚才那个市场继续")
        self.assertIn("海外SaaS", json.dumps(resolved, ensure_ascii=False))

        second = self.store.resolve_reference("按第二套方案调整")
        self.assertIn("B", json.dumps(second, ensure_ascii=False))
        self.assertIsNone(self.store.resolve_reference("完全无关的一句话"))

    def test_rollback_restores_state(self):
        self.store.record_turn("第一轮", {"tam": 120.0}, topic="海外SaaS市场")
        self.store.update_slot("current_market", "海外SaaS")
        self.store.record_turn("第二轮", {"tam": 130.0}, topic="欧洲市场")
        self.assertEqual(self.store.state["current_focus"], "欧洲市场")

        self.assertTrue(self.store.rollback(1))
        self.assertEqual(self.store.get_slot("current_market"), "海外SaaS")
        self.assertNotEqual(self.store.state["current_focus"], "欧洲市场")


class TestL10TelemetryWatchdog(unittest.TestCase):
    """L10 工业容灾层：三态熔断 + 全抖动退避 + Trace/Span 遥测。"""

    def test_circuit_breaker_three_states(self):
        breaker = CircuitBreaker(failure_threshold=2, cooldown_sec=0.06)

        def boom():
            raise ValueError("upstream 503")

        for _ in range(2):
            with self.assertRaises(ValueError):
                breaker.call(boom)
        self.assertEqual(breaker.state, "OPEN")
        with self.assertRaises(CircuitOpenError):
            breaker.call(lambda: 1)

        time.sleep(0.07)
        self.assertEqual(breaker.state, "HALF_OPEN")
        self.assertEqual(breaker.call(lambda: 42), 42)
        self.assertEqual(breaker.state, "CLOSED")

    def test_retry_with_backoff(self):
        policy = RetryPolicy(max_attempts=3, base_delay=0.01, max_delay=0.05,
                             jitter=False, sleep=lambda s: None)
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("transient")
            return "ok"

        self.assertEqual(policy.run(flaky), "ok")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(policy.last_delays, [0.01, 0.02])

        always_fail = RetryPolicy(max_attempts=2, base_delay=0.01,
                                  jitter=False, sleep=lambda s: None)
        with self.assertRaises(RetryExhausted):
            always_fail.run(lambda: (_ for _ in ()).throw(RuntimeError("down")))

    def test_watchdog_real_timeout(self):
        watchdog = WatchdogRunner(timeout_sec=0.05)
        with self.assertRaises(TaskTimeout):
            watchdog.run(time.sleep, 0.3)
        self.assertEqual(watchdog.run(lambda: 7), 7)

    def test_telemetry_tracer_health(self):
        _ensure_tmp()
        log_path = os.path.join(TMP, "telemetry_round3.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        tracer = TelemetryTracer(log_path)
        with tracer.span("research:sizing", {"tam": 120.0}) as span:
            time.sleep(0.001)
        self.assertEqual(span["status"], "SUCCESS")
        self.assertTrue(span["trace_id"])
        self.assertTrue(span["span_id"])
        self.assertGreaterEqual(span["duration_ms"], 0)

        try:
            with tracer.span("research:bundle", {"x": 1}):
                raise RuntimeError("bundle failed")
        except RuntimeError:
            pass

        with open(log_path, "r", encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(records), 2)
        for record in records:
            self.assertTrue(record["sha256_16"])
        health = TelemetryTracer(log_path).health()
        self.assertEqual(health["total"], 2)
        self.assertEqual(health["success"], 1)
        self.assertEqual(health["failed"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
