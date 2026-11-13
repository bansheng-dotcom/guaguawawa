# -*- coding: utf-8 -*-
"""记忆池体积护栏测试（core/memory_guard.py）。

覆盖三条防线：
1. trim_snapshots 对 list / dict 两种快照结构都只保留最近 N 条；
2. load_json_guarded 对 >100 MB 文件拒绝解析并隔离为 .bak，回落默认值；
3. gc() 对软超限文件裁剪、对硬超限文件隔离，且 dry-run 不落盘。
"""
from __future__ import annotations

import json
import os

import pytest

from core import memory_guard as mg


def _write(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def test_trim_snapshots_list():
    state = {"snapshots": [{"id": i} for i in range(10)]}
    assert mg.trim_snapshots(state, keep_last=3) == 7
    assert [s["id"] for s in state["snapshots"]] == [7, 8, 9]


def test_trim_snapshots_dict():
    state = {"snapshots": {f"v{i}": {"i": i} for i in range(6)}}
    assert mg.trim_snapshots(state, keep_last=2) == 4
    assert list(state["snapshots"]) == ["v4", "v5"]


def test_trim_snapshots_noop_when_small():
    state = {"snapshots": [{"id": 1}]}
    assert mg.trim_snapshots(state, keep_last=50) == 0


def test_load_json_guarded_normal(tmp_path):
    path = tmp_path / "session_state.json"
    _write(path, {"slots": {"a": 1}})
    data, notice = mg.load_json_guarded(str(path), dict)
    assert data["slots"]["a"] == 1
    assert notice is None


def test_load_json_guarded_missing(tmp_path):
    data, notice = mg.load_json_guarded(str(tmp_path / "nope.json"), dict)
    assert data == {} and notice is None


def test_load_json_guarded_quarantines_oversize(tmp_path, monkeypatch):
    path = tmp_path / "session_state.json"
    _write(path, {"slots": {"a": 1}})
    monkeypatch.setattr(mg, "HARD_LIMIT_BYTES", 10)  # 强制触发硬上限
    data, notice = mg.load_json_guarded(str(path), dict)
    assert data == {}
    assert notice and notice["action"] == "quarantined"
    assert not path.exists()
    assert os.path.exists(notice["quarantine_path"])
    assert notice["quarantine_path"].endswith(".bak")


def test_load_json_guarded_corrupt(tmp_path):
    path = tmp_path / "session_state.json"
    path.write_text("{not json", encoding="utf-8")
    data, notice = mg.load_json_guarded(str(path), dict)
    assert data == {}
    assert notice and notice["action"] == "reset"


def test_gc_trims_soft_oversize(tmp_path, monkeypatch):
    path = tmp_path / "session_state.json"
    _write(path, {"slots": {"a": 1},
                  "snapshots": [{"id": i, "pad": "x" * 50} for i in range(200)]})
    monkeypatch.setattr(mg, "SOFT_LIMIT_BYTES", 1024)
    report = mg.guard_file(str(path), keep_last=5)
    assert report["action"] == "trimmed"
    assert report["snapshots_after"] == 5
    with open(path, encoding="utf-8") as fh:
        assert len(json.load(fh)["snapshots"]) == 5


def test_gc_quarantines_hard_oversize(tmp_path, monkeypatch):
    path = tmp_path / "session_state.json"
    _write(path, {"snapshots": []})
    monkeypatch.setattr(mg, "HARD_LIMIT_BYTES", 5)
    report = mg.guard_file(str(path))
    assert report["action"] == "quarantine"
    assert report["quarantine_path"].endswith(".bak")
    assert not path.exists()


def test_gc_dry_run_leaves_files_untouched(tmp_path, monkeypatch):
    path = tmp_path / "session_state.json"
    payload = {"slots": {}, "snapshots": [{"id": i} for i in range(120)]}
    _write(path, payload)
    monkeypatch.setattr(mg, "SOFT_LIMIT_BYTES", 512)  # 文件已超软限
    before = path.stat().st_size
    summary = mg.gc(str(tmp_path), keep_last=5, dry_run=True)
    assert summary["scanned"] == 1
    assert summary["trimmed"] and summary["trimmed"][0]["snapshots_after"] == 5
    assert path.stat().st_size == before
    with open(path, encoding="utf-8") as fh:
        assert len(json.load(fh)["snapshots"]) == 120


def test_iter_memory_files_skips_quarantine(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "session_state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a" / "session_state.json.oversize-20260101-000000.bak").write_text("{}", encoding="utf-8")
    found = mg.iter_memory_files(str(tmp_path))
    assert [os.path.basename(p) for p in found] == ["session_state.json"]


def test_guard_file_missing(tmp_path):
    report = mg.guard_file(str(tmp_path / "absent.json"))
    assert report["action"] == "missing"


def test_doctor_memory_sentinel_thresholds():
    """doctor 的体积哨兵：软限 WARN、硬限 FAIL、正常无告警。"""
    import guagua

    ok = {"biggest": ("x", 1000), "soft": 2 * 1024 * 1024, "hard": 100 * 1024 * 1024}
    assert guagua._memory_health(ok) is None

    warn = {"biggest": ("x", 3 * 1024 * 1024), "soft": 2 * 1024 * 1024, "hard": 100 * 1024 * 1024}
    assert guagua._memory_health(warn).startswith("[WARN]")

    fail = {"biggest": ("x", 101 * 1024 * 1024), "soft": 2 * 1024 * 1024, "hard": 100 * 1024 * 1024}
    assert guagua._memory_health(fail).startswith("[FAIL]")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
