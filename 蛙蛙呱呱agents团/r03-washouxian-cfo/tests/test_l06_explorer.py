# -*- coding: utf-8 -*-
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.explorer import MultiScenarioExplorer

class TestL06Explorer(unittest.TestCase):
    def test_scenario_裂变(self):
        res = MultiScenarioExplorer.explore_scenarios(base_runway_months=12.0, base_burn_rate=100000.0, cash_balance=1200000.0)
        self.assertIn("conservative", res["scenarios"])
        self.assertIn("baseline", res["scenarios"])
        self.assertIn("aggressive", res["scenarios"])
        # 保守型跑道应大于基准型
        self.assertGreater(res["scenarios"]["conservative"]["runway_months"], res["scenarios"]["baseline"]["runway_months"])
        self.assertIn("| 策略情景 |", res["comparison_board_md"])

if __name__ == "__main__":
    unittest.main()
