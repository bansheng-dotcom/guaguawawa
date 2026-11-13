# -*- coding: utf-8 -*-
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.manager import FinancialEngineManager

class TestL01Engine(unittest.TestCase):
    def test_manager_probe(self):
        manager = FinancialEngineManager()
        status = manager.probe_all()
        self.assertEqual(status["status"], "ok")
        self.assertIn("native", status["engines"])
        self.assertIn("compliance", status["engines"])
        self.assertTrue(status["engines"]["native"]["available"])
        self.assertTrue(status["engines"]["compliance"]["available"])

    def test_native_fin_execution(self):
        manager = FinancialEngineManager()
        eng = manager.engines["native"]
        res = eng.execute("runway", {"cash": 1200000, "burn": 100000})
        self.assertTrue(res.ok)
        self.assertEqual(res.data["runway_months"], 12.0)

    def test_compliance_execution(self):
        manager = FinancialEngineManager()
        eng = manager.engines["compliance"]
        res = eng.execute("screen", {"text": "本理财方案稳赚不赔，零风险"})
        self.assertFalse(res.ok)
        self.assertIn("稳赚不赔", res.data["hit_redlines"])

if __name__ == "__main__":
    unittest.main()

