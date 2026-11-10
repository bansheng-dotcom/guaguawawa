# -*- coding: utf-8 -*-
"""R05 会话记忆池回归测试：快照不得复制 history（O(n²) 回归），回滚按长度截断。"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for _p in (HERE, AGENTS, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from engines.session_memory import ResearchSessionStore  # noqa: E402


def _store(tmp_path, name="session_state.json"):
    return ResearchSessionStore(str(tmp_path / name))


def test_eighty_turns_stay_under_100kb(tmp_path):
    """80 轮之后文件必须 <100 KB；快照恒定不超过保留上限。"""
    store = _store(tmp_path)
    for i in range(80):
        store.record_turn(f"第{i}轮研究", {"report": "分析结论" * 60}, topic=f"市场{i}")

    path = store.storage_path
    size = os.path.getsize(path)
    assert size < 100 * 1024, f"80 轮膨胀到 {size / 1024:.1f} KB"

    data = json.loads(open(path, encoding="utf-8").read())
    assert len(data["snapshots"]) <= 50
    assert len(data["history"]) == 80
    for snap in data["snapshots"]:
        state = snap["state"]
        assert "history" not in state, "快照禁止整份复制 history"
        assert "snapshots" not in state, "快照禁止嵌套 snapshots"
        assert isinstance(state.get("history_len"), int)


def test_snapshot_count_is_capped(tmp_path):
    """连续 300 轮：快照条数恒定为保留上限，文件不随轮次平方增长。"""
    store = _store(tmp_path)
    for i in range(300):
        store.record_turn(f"第{i}轮", {"report": "结论" * 40}, topic=f"t{i}")
    data = json.loads(open(store.storage_path, encoding="utf-8").read())
    assert len(data["snapshots"]) == 50
    assert len(data["history"]) == 300
    assert os.path.getsize(store.storage_path) < 1024 * 1024


def test_rollback_restores_history_length(tmp_path):
    """回滚后历史长度必须回到快照时刻，且业务态同步回退。"""
    store = _store(tmp_path)
    store.record_turn("第一轮", {"tam": 120.0}, topic="海外SaaS市场")
    store.record_turn("第二轮", {"tam": 130.0}, topic="欧洲市场")
    assert len(store.state["history"]) == 2

    assert store.rollback(1) is True
    assert len(store.state["history"]) == 1
    assert store.state["current_focus"] == "海外SaaS市场"
    assert len(store.state["snapshots"]) == 1, "回滚不得删除快照列表"


def test_rollback_without_snapshot_returns_false(tmp_path):
    store = _store(tmp_path)
    assert store.rollback(1) is False


def test_oversize_file_is_quarantined_not_parsed(tmp_path, monkeypatch):
    """体积熔断：超过硬上限的记忆池不解析，隔离为 .bak 后回落默认态。"""
    from core import memory_guard as mg

    path = tmp_path / "session_state.json"
    path.write_text(json.dumps({"slots": {"a": "x" * 500}, "snapshots": []}), encoding="utf-8")
    monkeypatch.setattr(mg, "HARD_LIMIT_BYTES", 10)
    store = ResearchSessionStore(str(path))

    assert store.last_guard_notice and store.last_guard_notice["action"] == "quarantined"
    assert not path.exists()
    assert store.state["snapshots"] == [] and store.state["history"] == []
