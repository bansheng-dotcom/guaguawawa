# -*- coding: utf-8 -*-
import unittest
import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.asset_bundle import FinancialAssetBundle

class TestL07AssetBundle(unittest.TestCase):
    def test_bundle_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_data = {
                "entity": "r03",
                "chart_data": [
                    {"label": "2026Q1", "value": 150.0},
                    {"label": "2026Q2", "value": 220.0}
                ]
            }
            files = FinancialAssetBundle.bundle(tmp_dir, "financial_spec", test_data)
            self.assertTrue(os.path.exists(files["ast"]))
            self.assertTrue(os.path.exists(files["vega"]))
            with open(files["ast"], "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.assertEqual(loaded["entity"], "r03")

if __name__ == "__main__":
    unittest.main()
