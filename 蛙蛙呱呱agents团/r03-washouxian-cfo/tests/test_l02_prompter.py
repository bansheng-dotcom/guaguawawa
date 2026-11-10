# -*- coding: utf-8 -*-
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.prompter import FinancialPrompter

class TestL02Prompter(unittest.TestCase):
    def test_decompose_runway(self):
        prompt = "当前账户余额 $1,500,000，每月净烧钱 $120,000，测算现金跑道能支撑几个月？"
        res = FinancialPrompter.decompose_intent(prompt)
        self.assertEqual(res["detected_skill"], "cfo")
        self.assertEqual(res["detected_action"], "runway")
        self.assertIn(1500000.0, res["extracted_amounts"])
        self.assertEqual(res["compiled_spec"]["target_route"], "cfo.runway")

    def test_decompose_aml_kyc(self):
        prompt = "排查近期累计 $50,000 的大额可疑分拆洗钱与 AML 申报要求"
        res = FinancialPrompter.decompose_intent(prompt)
        self.assertEqual(res["detected_skill"], "risk")
        self.assertEqual(res["detected_action"], "aml")
        self.assertIn("AML", res["detected_entities"])
        self.assertTrue(res["compiled_spec"]["requires_audit"])
        self.assertIn("dag", res["compiled_spec"])
        self.assertGreaterEqual(len(res["compiled_spec"]["dag"]), 3)

if __name__ == "__main__":
    unittest.main()
