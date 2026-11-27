# -*- coding: utf-8 -*-
"""第 6 段 Release：CI/CD 阶段 + 发布 + 回滚 + 版本锁/幂等。

发布不是“把代码推上去”：测试必须真绿、依赖必须锁版本、
写操作必须幂等、回滚必须演练过、整条链必须可重放。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)

_REQUIRED_STAGES = {"lint", "test", "security", "build", "deploy"}


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    rel = brief.get("release") or {}
    tests = rel.get("tests") or {}
    art: Dict[str, Any] = {
        "artifact": "release",
        "stage": "release",
        "project": brief.get("project", ""),
        "pipeline": [{"stage": p.get("stage", ""), "command": p.get("command", ""),
                      "gate": p.get("gate", "")} for p in rel.get("pipeline") or []],
        "publish": rel.get("publish") or {},
        "version_lock": rel.get("version_lock") or {},
        "idempotency": rel.get("idempotency") or {},
        "rollback": rel.get("rollback") or {},
        "replay": rel.get("replay") or {},
        "tests": {"passed": int(tests.get("passed", 0)),
                  "failed": int(tests.get("failed", 0)),
                  "skipped": int(tests.get("skipped", 0)),
                  "coverage": float(tests.get("coverage", 0.0))},
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """发布门禁：流水线完整、测试真绿、版本锁、幂等、回滚演练、可重放。"""
    pipe = art.get("pipeline") or []
    names = {p.get("stage") for p in pipe}
    t = art.get("tests") or {}
    lock = art.get("version_lock") or {}
    idem = art.get("idempotency") or {}
    rb = art.get("rollback") or {}
    replay = art.get("replay") or {}
    checks = [
        ck(len(pipe) >= 5 and _REQUIRED_STAGES <= names,
           "CI/CD 至少含 lint/test/security/build/deploy", "release:pipeline", "CRITICAL"),
        ck(t.get("failed") == 0 and t.get("skipped") == 0 and
           t.get("passed", 0) > 0 and t.get("coverage", 0) >= 0.8,
           "测试 0 失败 0 跳过、覆盖≥80%（禁止无测试发布）",
           "release:tests_green", "CRITICAL"),
        ck(bool(lock.get("pinned")) and nonempty_str(lock.get("lockfile")),
           "依赖锁定到 lockfile", "release:version_lock", "CRITICAL"),
        ck(bool(idem.get("verified")) and nonempty_str(idem.get("key")),
           "写操作幂等键已验证", "release:idempotent", "CRITICAL"),
        ck(bool(rb.get("tested")) and len(rb.get("steps") or []) >= 2,
           "回滚步骤已演练", "release:rollback_tested", "CRITICAL"),
        ck(bool(replay.get("deterministic")) and nonempty_str(replay.get("command")),
           "发布链可重放且确定", "release:replay", "CRITICAL"),
    ]
    return gate(checks, "release")


def render(art: Dict[str, Any]) -> str:
    pipe_rows = [[p.get("stage"), p.get("command"), p.get("gate")]
                 for p in art.get("pipeline") or []]
    t = art.get("tests") or {}
    pub = art.get("publish") or {}
    rb = art.get("rollback") or {}
    summary = (f"**版本**：{pub.get('version', '')}（{pub.get('strategy', '')}）；"
               f"测试 {t.get('passed')} 通过 / {t.get('failed')} 失败 / "
               f"{t.get('skipped')} 跳过，覆盖 {t.get('coverage')}。")
    tables = [
        "## 流水线", "", md_table(["阶段", "命令", "门禁"], pipe_rows),
        "", "## 发布与回滚", "",
        f"- 制品：{pub.get('artifact', '')}",
        f"- 版本锁：{(art.get('version_lock') or {}).get('lockfile', '')}",
        f"- 幂等键：{(art.get('idempotency') or {}).get('key', '')}",
        f"- 回滚：{'；'.join(rb.get('steps') or [])}（演练={rb.get('tested')}）",
        f"- 重放：`{(art.get('replay') or {}).get('command', '')}`",
    ]
    return render_stage(art, summary, tables)
