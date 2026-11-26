# -*- coding: utf-8 -*-
"""platform 域测试（合并自 4 个文件）。

源文件：
    test_cli_aliases.py —— v11 唯一入口：`report "指令" --dir … --out …`。
    test_mcp_client.py —— MCP 适配器测试：不联网，起本地 stdio 桩服务器。
    test_memory_guard.py —— 记忆池体积护栏测试（core/memory_guard.py）。
    test_paths_project.py —— 项目边界：三个根 + 写入守卫 + 项目骨架。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


import pytest
from core.report import report_cli
import json
from shared.mcp.client import MCPClient, doctor, load_registry
import os
from core import memory_guard as mg
from core.base import paths, project



# ====================================================================
# 合并自 test_cli_aliases.py：v11 唯一入口：`report "指令" --dir … --out …`。
# ====================================================================
# -*- coding: utf-8 -*-


EXPECTED = {"run-line", "check", "charts", "capabilities", "plan",
            "gaps", "research-plan"}


def test_only_one_entry(capsys):
    with pytest.raises(SystemExit):
        report_cli.main(["--help"])
    cap = capsys.readouterr()
    out = cap.out + cap.err
    assert "run-line" in out
    # 用「子命令集合」判定，不用子串：research-plan 里含 research 是正常的，
    # 但 research 本身作为子命令必须已经消失。
    for gone in ("build", "decide", "produce", "pack", "research", "run"):
        with pytest.raises(SystemExit):
            report_cli.main([gone, "--help"])
        capsys.readouterr()


def test_old_names_are_gone(capsys):
    """六个旧名字都必须已删除（argparse 直接报错退出）。"""
    for name in ("build", "decide", "produce", "pack", "research", "run"):
        with pytest.raises(SystemExit):
            report_cli.main([name, "--help"])
        capsys.readouterr()


def test_instruction_first_is_rewritten(capsys, monkeypatch):
    """`report "指令" …` 会被改写成 `run-line --intent "指令" …`。"""
    seen = {}

    def fake_run(args):
        seen["intent"] = args.intent
        seen["dir"] = args.dir
        return 0

    monkeypatch.setattr(report_cli, "cmd_run_line", fake_run)
    rc = report_cli.main(["内蒙古水果诊断", "--dir", "x", "--out", "y"])
    assert rc == 0
    assert seen == {"intent": "内蒙古水果诊断", "dir": "x"}


# ====================================================================
# 合并自 test_mcp_client.py：MCP 适配器测试：不联网，起本地 stdio 桩服务器。
# ====================================================================
# -*- coding: utf-8 -*-


def test_registry_slots_are_reserved() -> None:
    reg = load_registry()
    assert len(reg["servers"]) >= 8
    assert all(s["enabled"] is False for s in reg["servers"].values())
    assert all(s["owner_role"] for s in reg["servers"].values())


def test_client_handshake_list_and_call() -> None:
    entry = {"transport": "stdio", "command": sys.executable,
             "args": [str(ROOT / "tests" / "fixtures" / "mock_mcp_server.py")],
             "enabled": True, "owner_role": "r05"}
    c = MCPClient.from_entry(entry, "mock")
    try:
        c.initialize()
        tools = c.list_tools()
        assert tools and tools[0]["name"] == "echo_price"
        res = c.call_tool("echo_price", {"item": "苹果"})
        text = res["content"][0]["text"]
        assert json.loads(text)["item"] == "苹果"
    finally:
        c.close()


def test_doctor_reports_reserved() -> None:
    r = doctor({"transport": "stdio", "enabled": False, "owner_role": "r05"}, "x")
    assert r["status"] == "reserved"


# ====================================================================
# 合并自 test_memory_guard.py：记忆池体积护栏测试（core/memory_guard.py）。
# ====================================================================
# -*- coding: utf-8 -*-


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


# ====================================================================
# 合并自 test_paths_project.py：项目边界：三个根 + 写入守卫 + 项目骨架。
# ====================================================================
# -*- coding: utf-8 -*-


def test_default_project_root_is_outside_team(monkeypatch):
    monkeypatch.delenv(paths.ENV_PROJECT, raising=False)
    monkeypatch.delenv(paths.ENV_PROJECTS, raising=False)
    root = paths.project_root(None)
    assert root == paths.REPO_ROOT / "projects"
    assert not paths.is_within(root, paths.TEAM_ROOT)


def test_explicit_and_env_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.ENV_PROJECT, str(tmp_path / "from-env"))
    assert paths.project_root(None) == (tmp_path / "from-env").resolve()
    assert paths.project_root(str(tmp_path / "explicit")) == \
        (tmp_path / "explicit").resolve()


def test_assert_writable_rejects_team(tmp_path):
    with pytest.raises(paths.BoundaryError):
        paths.assert_writable(paths.TEAM_ROOT / "projects" / "x")
    with pytest.raises(paths.BoundaryError):
        paths.assert_writable(paths.TEAM_ROOT / "report.html")
    # 项目外的普通目录（tmp）允许
    assert paths.assert_writable(tmp_path / "ok") == (tmp_path / "ok").resolve()


def test_runtime_requires_explicit_flag():
    runtime = paths.runtime_root() / "tmp_probe"
    with pytest.raises(paths.BoundaryError):
        paths.assert_writable(runtime)
    assert paths.assert_writable(runtime, allow_runtime=True) == runtime.resolve()


def test_assert_writable_team_flag_is_explicit(tmp_path, monkeypatch):
    target = paths.TEAM_ROOT / "tests" / "_boundary_probe"
    with pytest.raises(paths.BoundaryError):
        paths.assert_writable(target)
    monkeypatch.setenv(paths.ENV_ALLOW_TEAM_WRITE, "1")
    assert paths.assert_writable(target) == target.resolve()


def test_project_init_creates_skeleton(tmp_path):
    p = tmp_path / "demo"
    res = project.init(p, industry="测试行业", name="演示")
    assert res["ok"] and res["created"]
    for sub in project.SUBDIRS:
        assert (p / sub).is_dir(), f"缺目录 {sub}"
    meta = project.load(p)
    assert meta.industry == "测试行业"
    assert meta.name == "演示"

    again = project.init(p)
    assert not again["created"], "已存在时不得覆盖 project.yaml"


def test_project_init_rejects_team_path():
    with pytest.raises(paths.BoundaryError):
        project.init(paths.TEAM_ROOT / "should-not-exist")


def test_project_load_missing_is_safe(tmp_path):
    meta = project.load(tmp_path / "nope")
    assert meta.root == (tmp_path / "nope").resolve()
    assert meta.industry is None


def test_project_rel():
    root = Path(os.path.abspath("d:/tmp/proj"))
    assert paths.project_rel(root / "cards" / "r06", root) == "cards/r06"
