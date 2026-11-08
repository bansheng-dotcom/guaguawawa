# -*- coding: utf-8 -*-
"""Verify the HTML report is driven by the result JSON, not by hard-coded numbers."""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("render_r06l_report", os.path.join(HERE, "render_r06l_report.py"))
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class ReportRenderTests(unittest.TestCase):
    def _render(self, result):
        with tempfile.TemporaryDirectory() as tmp:
            result_path = os.path.join(tmp, "r.json")
            output_path = os.path.join(tmp, "out.html")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
            renderer.render(__import__("pathlib").Path(result_path),
                            __import__("pathlib").Path(renderer.DEFAULT_TEMPLATE),
                            __import__("pathlib").Path(output_path))
            with open(output_path, encoding="utf-8") as f:
                return f.read()

    def _base_result(self):
        with open(os.path.join(HERE, "abtest_result.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_render_matches_current_json(self):
        html = self._render(self._base_result())
        self.assertIn("31,234", html)
        self.assertNotIn("8,158", html)
        self.assertNotIn("TOKEN", html)

    def test_decision_and_numbers_change_with_the_json(self):
        result = self._base_result()
        result["decision"] = "no_ship"
        result["power"]["required_n_per_group"] = 654321
        result["primary_metric"]["lift_pct"] = 4.2
        html = self._render(result)
        self.assertIn("no_ship", html)
        self.assertIn("654,321", html)
        self.assertNotIn("31,234", html)

    def test_missing_template_token_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = os.path.join(tmp, "t.html")
            with open(template, "w", encoding="utf-8") as f:
                f.write("<html><body>no tokens here</body></html>")
            with self.assertRaises(ValueError) as cm:
                renderer.render(__import__("pathlib").Path(os.path.join(HERE, "abtest_result.json")),
                                __import__("pathlib").Path(template),
                                __import__("pathlib").Path(os.path.join(tmp, "o.html")))
            self.assertIn("missing required tokens", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
