# -*- coding: utf-8 -*-
"""第 5 段 Debug：复现 → 假设 → 插桩 → 根因 → 最小修复 → 回归。

没有证据链的“根因”只是猜测：每个假设必须有检验方式与结果，
插桩点必须能区分假设，修复必须最小且带回归用例。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    dbg = brief.get("debug") or {}
    fix = dbg.get("fix") or {}
    art: Dict[str, Any] = {
        "artifact": "debug",
        "stage": "debug",
        "project": brief.get("project", ""),
        "bug": dbg.get("bug", ""),
        "repro": dbg.get("repro") or [],
        "hypotheses": [
            {"id": h.get("id", ""), "claim": h.get("claim", ""),
             "test": h.get("test", ""), "result": h.get("result", ""),
             "evidence": h.get("evidence", "")}
            for h in dbg.get("hypotheses") or []
        ],
        "instrumentation": dbg.get("instrumentation") or [],
        "root_cause": dbg.get("root_cause", ""),
        "fix": {"summary": fix.get("summary", ""), "minimal": bool(fix.get("minimal")),
                "files": fix.get("files") or []},
        "regression": dbg.get("regression") or [],
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """调试门禁：复现≥3、假设≥2 且有结果与证据、插桩≥2、根因、最小修复、回归≥2。"""
    hyps = art.get("hypotheses") or []
    fix = art.get("fix") or {}
    confirmed = [h for h in hyps if h.get("result") in ("reproduced", "confirmed")]
    checks = [
        ck(len(art.get("repro") or []) >= 3,
           "≥3 步稳定复现步骤", "debug:repro", "CRITICAL"),
        ck(len(hyps) >= 2 and all(nonempty_str(h.get("claim")) and
                                  nonempty_str(h.get("test")) and
                                  nonempty_str(h.get("result")) for h in hyps) and
           bool(confirmed),
           "≥2 个假设，各有检验与结果，至少一个被证实", "debug:hypotheses", "CRITICAL"),
        ck(len(art.get("instrumentation") or []) >= 2,
           "≥2 个能区分假设的插桩点", "debug:instrumentation", "CRITICAL"),
        ck(nonempty_str(art.get("root_cause")) and
           art.get("root_cause") != "unknown",
           "根因明确且非 unknown", "debug:root_cause", "CRITICAL"),
        ck(nonempty_str(fix.get("summary")) and fix.get("minimal") and
           len(fix.get("files") or []) >= 1,
           "最小修复（标注改动文件）", "debug:minimal_fix", "CRITICAL"),
        ck(all(nonempty_str(h.get("evidence")) for h in hyps),
           "假设到证据链完整", "debug:evidence_chain", "CRITICAL"),
        ck(len(art.get("regression") or []) >= 2,
           "≥2 条回归用例", "debug:regression", "CRITICAL"),
    ]
    return gate(checks, "debug")


def render(art: Dict[str, Any]) -> str:
    hy_rows = [[h.get("id"), h.get("claim"), h.get("test"), h.get("result"),
                h.get("evidence")] for h in art.get("hypotheses") or []]
    summary = (f"**缺陷**：{art.get('bug', '')}\n\n"
               f"**根因**：{art.get('root_cause', '')}\n\n"
               f"**修复**：{(art.get('fix') or {}).get('summary', '')}")
    tables = [
        "## 复现步骤", "",
        "\n".join(f"{i + 1}. {s}" for i, s in enumerate(art.get("repro") or [])),
        "", "## 假设与证据", "",
        md_table(["ID", "假设", "检验", "结果", "证据"], hy_rows),
        "", "## 插桩点", "", "\n".join(f"- {x}" for x in art.get("instrumentation") or []),
        "", "## 回归", "", "\n".join(f"- {x}" for x in art.get("regression") or []),
    ]
    return render_stage(art, summary, tables)
