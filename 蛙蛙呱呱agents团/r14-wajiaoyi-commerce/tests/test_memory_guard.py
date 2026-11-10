# -*- coding: utf-8 -*-
"""R14 会话记忆池回归测试：快照体积必须线性、回滚必须按 history_len 截断历史。"""
from __future__ import annotations

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for _p in (HERE, AGENTS, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engines.session_memory import CommerceSessionMemory  # noqa: E402


def test_eighty_snapshots_stay_under_100kb(tmp_path):
    """80 次快照体积必须 <100 KB（历史上 19 次就 966 MB）。"""
    path = tmp_path / "session_state.json"
    mem = CommerceSessionMemory(str(path))
    for i in range(80):
        mem.update_slot("current_order_id", f"ORD_{i:03d}")
        mem.create_snapshot(f"snap_{i}")

    size = path.stat().st_size
    assert size < 100 * 1024, f"80 次快照膨胀到 {size / 1024:.1f} KB"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["snapshots"]) == 80
    for snap in data["snapshots"]:
        assert "snapshots" not in snap["state_dump"], "快照禁止嵌套 snapshots"
        assert "history" not in snap["state_dump"], "快照禁止整份复制 history"
        assert "history_len" in snap["state_dump"]


def test_snapshot_size_grows_linearly(tmp_path):
    """快照体积线性：500 次快照仍应远小于 1 MB。"""
    path = tmp_path / "session_state.json"
    mem = CommerceSessionMemory(str(path))
    for i in range(500):
        mem.update_slot("current_order_id", f"ORD_{i:04d}")
        mem.create_snapshot(f"snap_{i}")
    assert path.stat().st_size < 1024 * 1024


def test_rollback_truncates_history_to_snapshot_moment(tmp_path):
    """回滚后历史长度必须等于拍快照时的 history_len。"""
    path = tmp_path / "session_state.json"
    mem = CommerceSessionMemory(str(path))
    mem.state["history"] = [{"turn": i} for i in range(3)]
    mem.update_slot("current_order_id", "ORD_20261110_888")
    snap_id = mem.create_snapshot("before_more_turns")

    mem.state["history"].extend([{"turn": 3}, {"turn": 4}])
    assert len(mem.state["history"]) == 5

    assert mem.rollback(snap_id) is True
    assert len(mem.state["history"]) == 3
    assert mem.state["slots"]["current_order_id"] == "ORD_20261110_888"
    assert len(mem.state["snapshots"]) == 1, "回滚不得删除快照列表"


def test_rollback_unknown_snapshot_returns_false(tmp_path):
    mem = CommerceSessionMemory(str(tmp_path / "session_state.json"))
    mem.create_snapshot("only")
    assert mem.rollback("snap_not_exists") is False


def test_oversize_file_is_quarantined_not_parsed(tmp_path, monkeypatch):
    """体积熔断：超过硬上限的文件不解析，直接隔离为 .bak，状态回落默认值。"""
    from core import memory_guard as mg

    path = tmp_path / "session_state.json"
    path.write_text(json.dumps({"slots": {"a": "x" * 500}, "snapshots": []}), encoding="utf-8")
    monkeypatch.setattr(mg, "HARD_LIMIT_BYTES", 10)
    mem = CommerceSessionMemory(str(path))

    assert mem.last_guard_notice and mem.last_guard_notice["action"] == "quarantined"
    assert not path.exists()
    assert os.path.exists(mem.last_guard_notice["quarantine_path"])
    assert mem.state["current_order_id"] == "ORD_20261110_001"
    assert mem.state["snapshots"] == []
