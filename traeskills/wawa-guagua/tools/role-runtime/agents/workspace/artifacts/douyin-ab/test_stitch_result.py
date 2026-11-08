"""Focused tests for R06L stitched A/B analysis."""
import csv
import importlib.util
import os
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "stitch_result.py")
spec = importlib.util.spec_from_file_location("stitch_result", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StitchPipelineTests(unittest.TestCase):
    def test_current_simulated_data_uses_proportion_test_and_passes(self):
        result = module.analyze(os.path.join(os.path.dirname(__file__), "orders.csv"))
        self.assertEqual(result["decision"], "ship")
        self.assertEqual(result["primary_metric"]["test"]["method"],
                         "pooled two-proportion z test, two-sided normal approximation")
        self.assertGreater(result["primary_metric"]["lift_pct"], 3)
        self.assertTrue(result["srm"]["balanced"])
        self.assertTrue(result["power"]["met"])
        self.assertEqual(result["data_quality"]["rows"], 16400)

    def test_profile_changes_sample_size_and_thresholds(self):
        path = os.path.join(os.path.dirname(__file__), "orders.csv")
        with open(os.path.join(os.path.dirname(__file__), "experiment_profiles.json"), encoding="utf-8") as f:
            config = __import__("json").load(f)
        profile = module.load_profile(os.path.join(os.path.dirname(__file__), "experiment_profiles.json"), "content_engagement")
        result = module.analyze(path, {**config["profiles"]["content_engagement"], **profile, "profile_name": "content_engagement"})
        self.assertEqual(result["experiment_profile"]["name"], "content_engagement")
        self.assertEqual(result["power"]["alpha"], 0.05)
        self.assertGreater(result["power"]["required_n_per_group"], 0)
        self.assertEqual(result["primary_metric"]["impact_min_pct"], 8.0)

    def test_continuous_profile_is_not_misapplied_to_binary_data(self):
        path = os.path.join(os.path.dirname(__file__), "orders.csv")
        profile = module.load_profile(os.path.join(os.path.dirname(__file__), "experiment_profiles.json"), "ecommerce_revenue")
        with self.assertRaises(ValueError) as cm:
            module.analyze(path, {**profile, "profile_name": "ecommerce_revenue"})
        self.assertIn("only implements binary_rate", str(cm.exception))

    def test_duplicate_user_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["user_id", "group", "converted", "amount", "date"])
                w.writeheader()
                w.writerows([
                    {"user_id": "x", "group": "control", "converted": 0, "amount": 0, "date": "2026-01-01"},
                    {"user_id": "x", "group": "treatment", "converted": 1, "amount": 10, "date": "2026-01-01"},
                ])
            with self.assertRaises(ValueError) as cm:
                module.analyze(path)
            self.assertIn("duplicate user_id", str(cm.exception))

    def test_non_binary_conversion_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["user_id", "group", "converted", "amount", "date"])
                w.writeheader()
                w.writerows([
                    {"user_id": "a", "group": "control", "converted": 2, "amount": 0, "date": "2026-01-01"},
                    {"user_id": "b", "group": "treatment", "converted": 0, "amount": 0, "date": "2026-01-01"},
                ])
            with self.assertRaises(ValueError) as cm:
                module.analyze(path)
            self.assertIn("converted must be 0 or 1", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
