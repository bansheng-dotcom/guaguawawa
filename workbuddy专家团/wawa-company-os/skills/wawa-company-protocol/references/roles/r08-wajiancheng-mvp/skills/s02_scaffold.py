# -*- coding: utf-8 -*-
"""S02 Spec 转仓库 —— 能力域 2。

整合自 makerskills（spec-to-repo / scaffold）。把 PRD/设计翻译成可跑起来的
仓库脚手架骨架：stack 白名单、目录树含入口、文件清单带用途、可执行命令、
鉴权方式合法。

动作：
  scaffold  校验仓库脚手架（stack/tree/files/run_commands/auth/env_vars）
  spec      校验工程 Spec（trigger/stack/delivery/auth）
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from . import _common as c

NAME = "scaffold"
DESC = "Spec转仓库：scaffold/spec"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    s = act.add_parser("scaffold", help="校验仓库脚手架骨架")
    s.add_argument("--input", required=True)
    spc = act.add_parser("spec", help="校验工程 Spec")
    spc.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "scaffold":
        return _validate_scaffold(data)
    if args.action == "spec":
        return _validate_spec(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _validate_scaffold(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    stack_types = th["scaffold"]["stack_types"]
    auth_types = th["scaffold"]["auth_types"]
    entry_markers = th["scaffold"]["entry_markers"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    stack = str(data.get("stack", "")).strip().lower()
    ok_stack = stack in stack_types
    checks.append(_ck(ok_stack,
                      f"stack ∈ {stack_types}"
                      if ok_stack else f"stack 非法/缺失: {stack!r}",
                      "scaffold.stack"))

    tree = data.get("tree")
    ok_tree = isinstance(tree, list) and len(tree) >= 1
    checks.append(_ck(ok_tree,
                      f"tree ≥1（实际 {len(tree) if isinstance(tree, list) else 0}）",
                      "scaffold.tree"))

    has_entry = False
    if isinstance(tree, list):
        entries: List[str] = []
        for node in tree:
            if isinstance(node, str):
                entries.append(node.lower())
            elif isinstance(node, dict):
                entries.append(json.dumps(node, ensure_ascii=False).lower())
        has_entry = any(any(m in e for m in entry_markers) for e in entries)
    checks.append(_ck(has_entry, "tree 含入口（main/index/app）", "scaffold.entry"))

    files = data.get("files")
    ok_files = isinstance(files, list) and len(files) >= 1
    checks.append(_ck(ok_files,
                      f"files ≥1（实际 {len(files) if isinstance(files, list) else 0}）",
                      "scaffold.files"))
    file_ok = ok_files
    if isinstance(files, list):
        for i, f in enumerate(files):
            if not isinstance(f, dict):
                checks.append(_ck(False, f"file[{i}] 非对象", "scaffold.file"))
                file_ok = False
                continue
            for k in ("path", "purpose"):
                if not str(f.get(k, "")).strip():
                    checks.append(_ck(False, f"file[{i}] 缺 {k}",
                                      f"scaffold.file.{k}"))
                    file_ok = False

    run_commands = data.get("run_commands")
    ok_run = isinstance(run_commands, list) and len(run_commands) >= 1
    checks.append(_ck(ok_run,
                      f"run_commands ≥1（实际 {len(run_commands) if isinstance(run_commands, list) else 0}）",
                      "scaffold.run_commands"))

    auth = str(data.get("auth", "none") or "none").strip().lower()
    ok_auth = auth in auth_types
    checks.append(_ck(ok_auth, f"auth={auth}", "scaffold.auth"))

    env_vars = data.get("env_vars")
    env_ok = True
    if env_vars is not None:
        if not isinstance(env_vars, list):
            checks.append(_ck(False, "env_vars 应为数组", "scaffold.env_vars"))
            env_ok = False
        else:
            for i, e in enumerate(env_vars):
                if not isinstance(e, dict):
                    checks.append(_ck(False, f"env_var[{i}] 非对象",
                                      "scaffold.env_vars"))
                    env_ok = False
                    continue
                for k in ("name", "description"):
                    if not str(e.get(k, "")).strip():
                        checks.append(_ck(False, f"env_var[{i}] 缺 {k}",
                                          "scaffold.env_vars"))
                        env_ok = False

    ok = (ok_stack and ok_tree and has_entry and file_ok
          and ok_run and ok_auth and env_ok)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    file_count=len(files) if isinstance(files, list) else 0,
                    stack=stack)


# --------------------------------------------------------------------------- #
def _validate_spec(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    stack_types = th["scaffold"]["stack_types"]
    auth_types = th["scaffold"]["auth_types"]

    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    trigger = str(data.get("trigger", "")).strip()
    ok_t = bool(trigger)
    checks.append(_ck(ok_t, "trigger 非空", "spec.trigger"))

    stack = str(data.get("stack", "")).strip().lower()
    ok_s = stack in stack_types
    checks.append(_ck(ok_s,
                      f"stack ∈ {stack_types}"
                      if ok_s else f"stack 非法/缺失: {stack!r}",
                      "spec.stack"))

    delivery = str(data.get("delivery", "")).strip()
    ok_d = bool(delivery)
    checks.append(_ck(ok_d, "delivery 非空", "spec.delivery"))

    auth = str(data.get("auth", "none") or "none").strip().lower()
    ok_a = auth in auth_types
    checks.append(_ck(ok_a, f"auth={auth}", "spec.auth"))

    ok = ok_t and ok_s and ok_d and ok_a
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL", stack=stack)