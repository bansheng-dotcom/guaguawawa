# -*- coding: utf-8 -*-
"""Validate the R06L experiment profile templates and their sample-size outputs."""
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.path.join(HERE, "experiment_profiles.json")

spec = importlib.util.spec_from_file_location("stitch_result", os.path.join(HERE, "stitch_result.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with open(PROFILES, encoding="utf-8") as f:
    CONFIG = json.load(f)


class ProfileTemplateTests(unittest.TestCase):
    def test_every_profile_has_required_fields(self):
        for name, profile in CONFIG["profiles"].items():
            with self.subTest(profile=name):
                for field in ("display_name", "primary_metric", "analysis_method", "baseline", "mde",
                              "alpha", "power", "impact_min_pct", "guardrails", "minimum_runtime_days"):
                    self.assertIn(field, profile, f"{name} missing {field}")
                self.assertTrue(0 < profile["alpha"] < 1)
                self.assertTrue(0.5 <= profile["power"] < 1)
                self.assertGreaterEqual(profile["impact_min_pct"], 0)
                self.assertIn(profile["mde"]["mode"], ("relative", "absolute"))
                self.assertGreater(len(profile["guardrails"]), 0)

    def test_binary_profiles_have_computable_mde(self):
        for name, profile in CONFIG["profiles"].items():
            if profile["analysis_method"] != "binary_rate":
                continue
            with self.subTest(profile=name):
                self.assertIsNotNone(profile["mde"]["default"])
                baseline = profile["baseline"].get("fallback")
                self.assertIsNotNone(baseline, f"{name} needs a planning fallback baseline")
                self.assertGreater(baseline, 0)

    def test_sample_size_is_monotonic_in_mde_and_power(self):
        base = module.required_n_proportion(0.05, 0.005, 0.05, 0.8)
        bigger_mde = module.required_n_proportion(0.05, 0.01, 0.05, 0.8)
        higher_power = module.required_n_proportion(0.05, 0.005, 0.05, 0.9)
        stricter_alpha = module.required_n_proportion(0.05, 0.005, 0.01, 0.8)
        # A larger detectable effect is cheaper to find; more power / stricter alpha cost more.
        self.assertLess(bigger_mde, base)
        self.assertGreater(higher_power, base)
        self.assertGreater(stricter_alpha, base)

    def test_higher_baseline_needs_smaller_sample_for_same_relative_mde(self):
        low = module.required_n_proportion(0.02, 0.02 * 0.10, 0.05, 0.8)
        high = module.required_n_proportion(0.20, 0.20 * 0.10, 0.05, 0.8)
        self.assertLess(high, low)

    def test_sample_size_matches_reference_power_value(self):
        # Baseline 5%, absolute MDE 1pp, alpha 0.05, power 0.80 -> 8,158 per arm.
        self.assertEqual(module.required_n_proportion(0.05, 0.01, 0.05, 0.80), 8158)

    def test_profile_load_rejects_invalid_parameters(self):
        with self.assertRaises(ValueError):
            module.load_profile(PROFILES, "ecommerce_conversion", {"alpha": 1.5})
        with self.assertRaises(ValueError):
            module.load_profile(PROFILES, "ecommerce_conversion", {"power": 0.2})
        with self.assertRaises(ValueError):
            module.load_profile(PROFILES, "no_such_profile")

    def test_relative_mde_resolves_to_absolute_and_sample_size(self):
        profile = module.load_profile(PROFILES, "ecommerce_conversion")
        params = module.resolve_experiment_parameters(profile, 0.05)
        self.assertAlmostEqual(params["mde_absolute"], 0.05 * 0.10, places=6)
        self.assertAlmostEqual(params["mde_relative"], 0.10, places=6)
        self.assertEqual(params["required_n_per_group"],
                         module.required_n_proportion(0.05, 0.005, 0.05, 0.8))

    def test_continuous_profile_is_rejected_by_binary_pipeline(self):
        profile = module.load_profile(PROFILES, "ecommerce_revenue")
        with self.assertRaises(ValueError):
            module.analyze(os.path.join(HERE, "orders.csv"), {**profile, "profile_name": "ecommerce_revenue"})

    def test_different_profiles_produce_different_sample_sizes(self):
        conv = module.load_profile(PROFILES, "ecommerce_conversion")
        lead = module.load_profile(PROFILES, "lead_generation")
        conv_n = module.resolve_experiment_parameters(conv, 0.05)["required_n_per_group"]
        lead_n = module.resolve_experiment_parameters(lead, 0.10)["required_n_per_group"]
        self.assertNotEqual(conv_n, lead_n)


if __name__ == "__main__":
    unittest.main(verbosity=2)
