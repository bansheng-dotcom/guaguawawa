# -*- coding: utf-8 -*-
"""第 3 段 Feature：用户故事 → 端到端垂直切片（UI/服务/状态/认证）。

垂直切片必须一条路打通到底，且带可运行命令与回滚清单；
只画架构图、只给伪代码不算交付。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    feat = brief.get("feature") or {}
    acceptance = [{"id": a.get("id", ""), "given_when_then": a.get("given_when_then", "")}
                  for a in feat.get("acceptance") or []]
    art: Dict[str, Any] = {
        "artifact": "feature",
        "stage": "feature",
        "project": brief.get("project", ""),
        "story": feat.get("story", ""),
        "slice": {
            "ui": feat.get("ui") or [],
            "service": feat.get("service") or [],
            "state": feat.get("state") or [],
            "auth": feat.get("auth") or [],
        },
        "acceptance": acceptance,
        "acceptance_ids": [a["id"] for a in acceptance],
        "runnable": feat.get("runnable") or {},
        "rollback": feat.get("rollback") or [],
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """切片门禁：四层齐全、验收可执行、可运行、可回滚。"""
    sl = art.get("slice") or {}
    acc = art.get("acceptance") or []
    ids = [a.get("id") for a in acc]
    runnable = art.get("runnable") or {}
    checks = [
        ck(nonempty_str(art.get("story")),
           "用户故事以角色/动作/价值描述", "feature:story", "CRITICAL"),
        ck(all(bool(sl.get(k)) for k in ("ui", "service", "state", "auth")),
           "UI/服务/状态/认证四层都有落点", "feature:slice", "CRITICAL"),
        ck(len(acc) >= 3 and len(ids) == len(set(ids)) and
           all(nonempty_str(a.get("given_when_then")) for a in acc),
           "≥3 条带 id 的 Given/When/Then 验收", "feature:acceptance", "CRITICAL"),
        ck(nonempty_str(runnable.get("command")) and nonempty_str(runnable.get("expected")),
           "给出可运行命令与预期输出", "feature:runnable", "CRITICAL"),
        ck(len(art.get("rollback") or []) >= 2,
           "≥2 步回滚清单", "feature:rollback", "CRITICAL"),
    ]
    return gate(checks, "feature")


def render(art: Dict[str, Any]) -> str:
    sl = art.get("slice") or {}
    acc_rows = [[a.get("id"), a.get("given_when_then")] for a in art.get("acceptance") or []]
    summary = f"**用户故事**：{art.get('story', '')}\n\n" \
              f"**可运行**：`{(art.get('runnable') or {}).get('command', '')}` → " \
              f"{(art.get('runnable') or {}).get('expected', '')}"
    tables = [
        "## 垂直切片", "",
        md_table(["层", "落点"],
                 [["UI", "、".join(sl.get("ui") or [])],
                  ["服务", "、".join(sl.get("service") or [])],
                  ["状态", "、".join(sl.get("state") or [])],
                  ["认证", "、".join(sl.get("auth") or [])]]),
        "", "## 验收场景", "", md_table(["ID", "Given / When / Then"], acc_rows),
        "", "## 回滚清单", "",
        "\n".join(f"- {x}" for x in art.get("rollback") or []),
    ]
    return render_stage(art, summary, tables)
