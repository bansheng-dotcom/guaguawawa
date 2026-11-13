# -*- coding: utf-8 -*-
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.critic import FinancialCritic, FinancialAutoHealLoop

class TestL03Critic(unittest.TestCase):
    def test_critic_violation(self):
        bad_data = {
            "skill": "cfo", "action": "runway",
            "findings": "本项目保证收益，稳赚不赔，后续逐步优化。",
            "ok": True
        }
        score, flaws = FinancialCritic.evaluate("cfo", "runway", bad_data)
        self.assertLess(score, 7.0)
        self.assertTrue(any("licensed_boundary_violation" in f for f in flaws))
        self.assertTrue(any("vague_unquantified_recommendation" in f for f in flaws))

    def test_auto_heal_loop(self):
        call_count = 0
        def fake_runner(patch):
            nonlocal call_count
            call_count += 1
            if patch.get("strip_guarantee_words"):
                return {
                    "skill": "cfo", "action": "runway",
                    "findings": "根据当前跑道模型，预计维持14个月，由 CFO_Office 牵头控费 $50,000。",
                    "ok": True, "checks": [{"ok": True}]
                }
            return {
                "skill": "cfo", "action": "runway",
                "findings": "稳赚不赔，逐步优化",
                "ok": True
            }

        res = FinancialAutoHealLoop.run_with_heal(fake_runner)
        self.assertEqual(res["verdict"], "PASS")
        self.assertEqual(call_count, 2)
        self.assertEqual(len(res["heal_logs"]), 1)

if __name__ == "__main__":
    unittest.main()
