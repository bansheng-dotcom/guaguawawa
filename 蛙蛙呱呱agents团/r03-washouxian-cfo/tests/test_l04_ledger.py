# -*- coding: utf-8 -*-
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.ledger import FinancialLedgerParser

class TestL04Ledger(unittest.TestCase):
    def test_ledger_parsing(self):
        spec = FinancialLedgerParser.load_spec(force_reload=True)
        self.assertGreater(spec["RUNWAY_ALERT_MONTHS"], 0)
        self.assertEqual(spec["FINANCIAL_RECORD_RETENTION_YEARS"], 7)
        self.assertIn("保本", spec["LICENSED_GUARANTEE_WORDS"])

if __name__ == "__main__":
    unittest.main()
