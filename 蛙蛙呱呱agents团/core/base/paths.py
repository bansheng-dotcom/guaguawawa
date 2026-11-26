# -*- coding: utf-8 -*-
"""三个根，一条边界。

    TEAM_ROOT     专家团（工具）：角色、技能、core、scripts、门禁、通用知识
    PROJECT_ROOT  项目（资产）：数据、知识快照、brief、卡、claims、报告
    RUNTIME_ROOT  运行临时物：事件流、锁、trace、临时下载

硬规则：**项目资产只能写 PROJECT_ROOT；写团内一律拒绝。**
唯一例外是显式自测开关（`GUAGUA_ALLOW_TEAM_WRITE=1` 或 `allow_team=True`），
出现在测试里必须写清为什么，正常产线不允许打开。

为什么要有这个文件：`--out/--dir` 以前没有限制，用户可以把项目数据、
报告直接写进专家团；一旦写进去，工具仓库就变成项目仓库，无法独立升级、
分发、复用，下一个项目还会读到上一个项目的语义形成漂移。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

#: 专家团根目录（本文件位于 <TEAM_ROOT>/core/platform/paths.py）
TEAM_ROOT: Path = Path(__file__).resolve().parent.parent.parent
#: 仓库根（专家团的上一级），项目默认落在这里的 projects/
REPO_ROOT: Path = TEAM_ROOT.parent

ENV_WORKSPACE = "GUAGUA_WORKSPACE"
ENV_PROJECT = "GUAGUA_PROJECT"
ENV_PROJECTS = "GUAGUA_PROJECTS"
ENV_ALLOW_TEAM_WRITE = "GUAGUA_ALLOW_TEAM_WRITE"

_TRUTHY = {"1", "true", "yes", "on"}


class BoundaryError(ValueError):
    """越界写入。CLI 捕获后统一返回退出码 2。"""

    exit_code = 2


def team_root() -> Path:
    return TEAM_ROOT


def runtime_root() -> Path:
    """运行临时物根：默认 <仓库根>/workspace，可用 GUAGUA_WORKSPACE 覆盖。"""
    env = os.environ.get(ENV_WORKSPACE)
    if env:
        return Path(env).expanduser().resolve()
    return (REPO_ROOT / "workspace").resolve()


def projects_root() -> Path:
    """项目默认根：<仓库根>/projects，可用 GUAGUA_PROJECTS 覆盖。"""
    env = os.environ.get(ENV_PROJECTS)
    if env:
        return Path(env).expanduser().resolve()
    return (REPO_ROOT / "projects").resolve()


def project_root(explicit: Optional[str] = None) -> Path:
    """解析项目根：显式参数 > GUAGUA_PROJECT > 默认 projects 根。"""
    raw = explicit or os.environ.get(ENV_PROJECT)
    if raw:
        return Path(raw).expanduser().resolve()
    return projects_root()


def _norm(p: Path) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def is_within(child: Path | str, parent: Path | str) -> bool:
    """child 是否位于 parent 之内（含相等）。Windows 下大小写不敏感。"""
    c, p = _norm(Path(child)), _norm(Path(parent))
    if c == p:
        return True
    try:
        return os.path.commonpath([c, p]) == p
    except ValueError:          # 不同盘符
        return False


def _team_write_allowed(explicit: bool) -> bool:
    if explicit:
        return True
    return str(os.environ.get(ENV_ALLOW_TEAM_WRITE) or "").strip().lower() in _TRUTHY


def assert_writable(path: Path | str, *, allow_runtime: bool = False,
                    allow_team: bool = False) -> Path:
    """写入守卫：解析成绝对路径后检查边界，越界抛 BoundaryError。

    Args:
        path: 准备写入的文件或目录
        allow_runtime: 允许写 RUNTIME_ROOT（事件/锁/trace 这类临时物才传 True）
        allow_team: 允许写 TEAM_ROOT（仅测试夹具；产线不要打开）

    返回解析后的绝对路径，方便调用方直接使用。
    """
    resolved = Path(path).expanduser().resolve()
    if is_within(resolved, TEAM_ROOT) and not _team_write_allowed(allow_team):
        raise BoundaryError(
            f"拒绝写入专家团目录：{resolved}\n"
            f"  项目资产请写到 --project 指向的项目根，或默认 {projects_root()}\n"
            f"  运行临时物请写到 {runtime_root()}（并显式 allow_runtime=True）")
    if is_within(resolved, runtime_root()) and not allow_runtime:
        raise BoundaryError(
            f"拒绝把项目产物写进运行临时物目录：{resolved}\n"
            f"  {runtime_root()} 只放事件/锁/trace，会随清理丢失；"
            f"请用 --out 指向项目目录")
    return resolved


def write_artifact(path: Path | str, *, project: Path | str | None = None,
                   allow_team: bool = False) -> Path:
    """产物落盘唯一入口：解析路径 → 过写入守卫 → 建父目录 → 返回可写路径。

    `core/**`、`shared/**`、`r*/**` 不允许直接 open(...,"w") / write_text 落产物；
    统一走这里，越界（写团内 / 写运行临时物）直接抛 BoundaryError。

    Args:
        path: 目标路径；给相对路径时必须同时给 project
        project: 项目根；相对路径会拼到它下面
        allow_team: 仅测试夹具可置 True，产线不要打开
    """
    p = Path(path).expanduser()
    if project is not None and not p.is_absolute():
        p = Path(project).expanduser() / p
    resolved = assert_writable(p, allow_team=allow_team)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def project_rel(path: Path | str, project: Path | str) -> str:
    """把项目内路径转成 posix 相对路径；不在项目内则返回绝对路径字符串。"""
    p = Path(path).expanduser().resolve()
    root = Path(project).expanduser().resolve()
    if is_within(p, root):
        return Path(os.path.relpath(p, root)).as_posix()
    return p.as_posix()
