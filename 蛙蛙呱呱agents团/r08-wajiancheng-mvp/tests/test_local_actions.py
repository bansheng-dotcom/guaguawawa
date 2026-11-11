import unittest
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from local_actions import inspect_scaffold

class LocalActionCases(unittest.TestCase):
    def test_present_file_real(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "main.py"), "w") as f: f.write("pass")
            result = inspect_scaffold({"files": [{"path": "main.py"}]}, root)
            self.assertTrue(result["ok"]); self.assertEqual(result["capability_status"], "real")
    def test_missing_required_is_failure(self):
        with tempfile.TemporaryDirectory() as root:
            result = inspect_scaffold({"files": [{"path": "absent.py"}]}, root)
            self.assertFalse(result["ok"])

if __name__ == "__main__": unittest.main()
