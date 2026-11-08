"""Local per-role execution checks for the roles that expose a `local` command.

Each check runs the role CLI against a committed local fixture and asserts the
declared capability status. External integrations must stay blocked.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[2]
ROOT = AGENTS.parent


def _run(role: str, *args: str) -> dict:
    env = dict(os.environ)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(AGENTS / role / "agent.py"), *args],
        cwd=str(AGENTS / role), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, timeout=90,
    )
    out = proc.stdout or ""
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return json.loads(line[len("__AGENT_RESULT__ "):])
    try:
        return json.loads(out.strip())
    except json.JSONDecodeError:
        raise AssertionError(f"{role} produced no JSON result: {out[-300:]}")


class LocalCapabilityTests(unittest.TestCase):
    def test_r14_local_order_is_real_and_never_charges(self):
        out = _run("r14-wajiaoyi-commerce", "local", "--input",
                   str(AGENTS / "r14-wajiaoyi-commerce" / "examples" / "local_order_check.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["capability_status"], "real")
        self.assertEqual(out["payment"], "not charged")
        self.assertEqual(out["side_effects"], [])

    def test_r14_external_payment_is_blocked(self):
        payload = {"external_payment": True}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "pay.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            out = _run("r14-wajiaoyi-commerce", "local", "--input", str(path))
        self.assertFalse(out["ok"])
        self.assertEqual(out["capability_status"], "blocked")

    def test_r15_local_inventory_conservation(self):
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "r15.json"
            out = _run("r15-wagongying-erp", "local", "--input",
                       str(AGENTS / "r15-wagongying-erp" / "examples" / "bin.json"),
                       "--output", str(out_path))
            self.assertTrue(out_path.exists())
        self.assertTrue(out["ok"])
        self.assertEqual(out["capability_status"], "real")
        self.assertTrue(out["conservation_checked"])

    def test_r16_payroll_validated_but_not_paid(self):
        out = _run("r16-warenshi-hr", "local", "--input",
                   str(AGENTS / "r16-warenshi-hr" / "examples" / "local_payroll_input.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["capability_status"], "real")
        self.assertEqual(out["payroll"], "not paid")
        self.assertIn("[REDACTED_EMAIL]", out["redacted_preview"])

    def test_r17_dry_run_is_simulated_and_never_calls_n8n(self):
        out = _run("r17-wazhiwang-automation", "local", "--input",
                   str(AGENTS / "r17-wazhiwang-automation" / "examples" / "workflow.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["capability_status"], "simulated")
        self.assertEqual(out["external_calls"], 0)

    def test_r18_local_elt_reports_lineage_and_quality(self):
        out = _run("r18-washucang-dataeng", "local", "--input",
                   str(AGENTS / "r18-washucang-dataeng" / "examples" / "local_elt_rows.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["capability_status"], "real")
        self.assertTrue(out["quality"]["schema_consistent"])
        self.assertEqual(out["external_connectors_used"], 0)

    def test_r19_local_evaluation_never_publishes(self):
        out = _run("r19-wazhimo-ml", "local", "--input",
                   str(AGENTS / "r19-wazhimo-ml" / "examples" / "local_evaluation_rows.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["capability_status"], "real")
        self.assertFalse(out["published"])
        self.assertEqual(out["model_card"]["publication_status"], "not_published")

    def test_r09_local_verify_runs_safe_test_and_blocks_dangerous(self):
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            (proj / "test_ok.py").write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    def test_a(self): self.assertEqual(1 + 1, 2)\n",
                encoding="utf-8")
            real = _run("r09-wawenma-engineer", "local-verify", "--project", str(proj),
                        "--kind", "unittest", "--command",
                        "python -m unittest discover -s . -p test_*.py")
            blocked = _run("r09-wawenma-engineer", "local-verify", "--project", str(proj),
                           "--kind", "build", "--command", "rm -rf /")
        self.assertEqual(real["capability_status"], "real")
        self.assertEqual(real["verdict"], "PASS")
        self.assertEqual(blocked["capability_status"], "blocked")

    def test_r20_restore_drill_is_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "backup"
            source.mkdir()
            (source / "asset.txt").write_text("restore-drill", encoding="utf-8")
            spec = Path(td) / "spec.json"
            spec.write_text(json.dumps({"source": source.as_posix()}), encoding="utf-8")
            out = _run("r20-washouzhi-sre", "local", "--input", str(spec),
                       "--output", str(Path(td) / "out.json"))
        self.assertTrue(out["ok"])
        self.assertEqual(out["capability_status"], "real")
        self.assertTrue(out["hashes_verified"])
        self.assertFalse(out["production_modified"])


if __name__ == "__main__":
    unittest.main()
