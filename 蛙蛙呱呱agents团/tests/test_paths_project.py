# -*- coding: utf-8 -*-
"""项目边界：三个根 + 写入守卫 + 项目骨架。

这些测试守的是本团最容易回退的一条约束：**项目资产不许写进专家团**。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core import paths, project


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
