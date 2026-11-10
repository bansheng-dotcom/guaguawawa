# -*- coding: utf-8 -*-
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.patch_editor import FinancialPatchEditor

class TestL08PatchEditor(unittest.TestCase):
    def test_patch_percentage_reduction(self):
        budget = {
            "expenses": {
                "marketing": 50000.0,
                "office_rent": 20000.0,
                "salaries": 100000.0
            }
        }
        patched = FinancialPatchEditor.apply_patch(budget, "把 office_rent 削减 20%")
        self.assertEqual(patched["expenses"]["office_rent"], 16000.0)
        # 验证其他项目绝对未被修改
        self.assertEqual(patched["expenses"]["marketing"], 50000.0)
        self.assertEqual(patched["expenses"]["salaries"], 100000.0)

    def test_patch_exact_value(self):
        config = {"dsr": {"sla_days": 30, "priority": "high"}}
        patched = FinancialPatchEditor.apply_patch(config, "将 sla_days 改为 14")
        self.assertEqual(patched["dsr"]["sla_days"], 14.0)
        self.assertEqual(patched["dsr"]["priority"], "high")

if __name__ == "__main__":
    unittest.main()
