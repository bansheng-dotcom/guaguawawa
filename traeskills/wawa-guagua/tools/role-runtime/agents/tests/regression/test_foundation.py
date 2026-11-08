"""Deterministic tests for shared safety and artifact primitives."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from core.approvals import ApprovalStore, needs_approval, risk
from core.artifact_registry import ArtifactRegistry, sha256_file
from core.protocol import Event, Port, Task
from core.workspace import Workspace


class FoundationTests(unittest.TestCase):
    def test_artifact_registry_hashes_and_indexes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = root / "report.txt"
            payload.write_text("证据", encoding="utf-8")
            registry = ArtifactRegistry(str(root / "registry"))
            record = registry.register("run/r06/report", path=str(payload), producer="r06", schema_version="1.0")
            self.assertEqual(record["sha256"], sha256_file(str(payload)))
            self.assertEqual(registry.get("run/r06/report")["producer"], "r06")
            self.assertEqual(json.loads((root / "registry" / "artifacts.json").read_text(encoding="utf-8"))[0]["artifact_ref"], "run/r06/report")

    def test_high_risk_requires_approval_and_resume(self):
        self.assertTrue(needs_approval("send payment"))
        self.assertTrue(needs_approval("发起退款"))
        with tempfile.TemporaryDirectory() as td:
            store = ApprovalStore(td)
            card = store.create("publish", details={"text": "release"}, checkpoint="step-7")
            self.assertEqual(card["status"], "pending")
            with self.assertRaises(RuntimeError):
                store.resume(card["id"])
            store.approve(card["id"], actor="founder")
            self.assertEqual(store.resume(card["id"]), "step-7")

    def test_workspace_atomic_utf8_task_and_events(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Workspace(td)
            task = Task(task_id="cn01", title="中文客户任务", owner="r13", intent="复核商机")
            ws.create_task(task)
            ws.update_task("cn01", {"status": "done"}, event_type="task_finished")
            self.assertEqual(ws.read_task("cn01").title, "中文客户任务")
            self.assertEqual(len(ws.events()), 2)
            events = ws.events(agent="r13")
            self.assertEqual(events[-1]["type"], "task_finished")
            self.assertEqual(ws.list_tasks(status="done")[0].task_id, "cn01")


if __name__ == "__main__":
    unittest.main()
