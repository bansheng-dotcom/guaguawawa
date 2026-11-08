"""Static invariants that every role must satisfy.

These checks are intentionally textual: they catch the wiring mistakes that
produced silent runtime failures (missing imports, missing capability status,
renderer forks) without executing side effects.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[2]


def _roles() -> list[Path]:
    return sorted(path for path in AGENTS.iterdir()
                  if path.is_dir() and len(path.name) >= 4
                  and path.name[0] == "r" and path.name[1:3].isdigit()
                  and path.name[3] == "-")


def _source(role: Path) -> str:
    return (role / "agent.py").read_text(encoding="utf-8")


class RoleInvariantTests(unittest.TestCase):
    def test_every_role_has_agent_py(self):
        for role in _roles():
            self.assertTrue((role / "agent.py").exists(), role.name)

    def test_every_role_declares_capability_status(self):
        for role in _roles():
            self.assertIn("capability_status", _source(role),
                          f"{role.name} manifest lacks capability_status")

    def test_report_bridge_calls_are_imported(self):
        for role in _roles():
            source = _source(role)
            if "report_bridge." not in source:
                continue
            self.assertRegex(source, r"import[^\n]*\breport_bridge\b",
                             f"{role.name} calls report_bridge without importing it")

    def test_agent_modules_parse(self):
        for role in _roles():
            ast.parse(_source(role), filename=str(role / "agent.py"))

    def test_no_role_local_renderer_fork(self):
        """The shared renderer + 48-chart lib live in core; role copies are fork risk."""
        for role in _roles():
            for stray in ("report_renderer.py", "chart_lib.py",
                          "chart_renderers_ext.py"):
                self.assertFalse((role / stray).exists(),
                                 f"{role.name}/{stray} duplicates core renderer")

    def test_core_owns_shared_chart_library(self):
        charts = AGENTS / "core" / "charts"
        self.assertTrue((charts / "chart_lib.py").exists())
        self.assertTrue((charts / "chart_renderers_ext.py").exists())

    def test_core_exposes_shared_modules(self):
        core = AGENTS / "core"
        for module in ("artifact_registry.py", "approvals.py", "report_bridge.py",
                       "report_renderer.py", "workspace.py", "registry.py"):
            self.assertTrue((core / module).exists(), module)


if __name__ == "__main__":
    unittest.main()
