# -*- coding: utf-8 -*-
import unittest
import sys
import os
import tempfile
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.telemetry import WatchdogCircuitBreaker, ProductionTelemetry, WatchdogTimeoutException

class TestL10Telemetry(unittest.TestCase):
    def test_watchdog_pass(self):
        def quick_task():
            return "done"
        res = WatchdogCircuitBreaker.execute_with_guard(quick_task, timeout_s=1.0)
        self.assertEqual(res, "done")

    def test_watchdog_timeout(self):
        def slow_task():
            time.sleep(0.1)
            return "slow"
        with self.assertRaises(WatchdogTimeoutException):
            WatchdogCircuitBreaker.execute_with_guard(slow_task, timeout_s=0.05)

    def test_telemetry_recording(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, "test_telemetry.jsonl")
            telemetry = ProductionTelemetry(log_path=log_file)
            trace_id = telemetry.record_trace("cfo.runway", {"balance": 100000}, "SUCCESS", 15.5)
            self.assertTrue(os.path.exists(log_file))
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn(trace_id, content)
                self.assertIn("cfo.runway", content)

if __name__ == "__main__":
    unittest.main()
