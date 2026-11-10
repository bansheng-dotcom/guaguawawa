# -*- coding: utf-8 -*-
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.slop_guard import FinancialSlopGuard

class TestL05SlopGuard(unittest.TestCase):
    def test_audit_slop(self):
        text = "对于公司近期的现金流缺口，我们要高度重视，逐步落实，尽快推进。"
        score, detected = FinancialSlopGuard.audit_text(text)
        self.assertLess(score, 6.0)
        self.assertIn("高度重视", detected)
        self.assertIn("尽快推进", detected)

    def test_polish_slop(self):
        text = "我们要高度重视合规审查，逐步落实整改。"
        polished = FinancialSlopGuard.polish(text, default_dri="Risk_DRI", default_amount=25000.0)
        self.assertNotIn("高度重视", polished)
        self.assertNotIn("逐步落实", polished)
        self.assertIn("Risk_DRI", polished)

if __name__ == "__main__":
    unittest.main()
