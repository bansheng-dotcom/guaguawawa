"""Deterministic tests for shared safety and artifact primitives."""
from __future__ import annotations
import tempfile
import unittest

from core.protocol import Event, Port, Task
from core.workspace import Workspace


class FoundationTests(unittest.TestCase):
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
