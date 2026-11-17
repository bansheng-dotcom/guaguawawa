# -*- coding: utf-8 -*-
"""core/capability_graph —— 角色 × 问题 × 能力 × 证据状态（升级 P2）。

回答一个问题：**现有的 20 个角色，到底能回答哪些问题、以什么状态回答？**

状态：
    real       可产出可复核的报告证据（本地确定性计算 / 台账 / 门禁）
    simulated  可产出草案/计划/定性判断，但不能当硬证据
    blocked    不进报告（enters=false）或没有可进报告技能
    missing    没有任何角色能回答（能力缺口）

用法：
    python -m core.capability_graph --json workspace/report_upgrade/capability_graph.json
    python -m core.capability_graph --summary
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core import question_library, report_roles

# 只做草案/定性判断、不能当硬证据的角色（P2 的显式声明；P4 可调整）
SIMULATED_ROLES = {"r11", "r14"}


def _role_status(role: str, meta: Dict[str, Any]) -> str:
    if not meta.get("enters") or int(meta.get("eligible") or 0) <= 0:
        return "blocked"
    if role in SIMULATED_ROLES:
        return "simulated"
    return "real"


def build() -> Dict[str, Any]:
    cat = report_roles.classify()
    roles_meta = cat["roles"]
    questions = question_library.QUESTIONS

    roles: Dict[str, Dict[str, Any]] = {}
    for role, meta in sorted(roles_meta.items()):
        status = _role_status(role, meta)
        roles[role] = {
            "id": role,
            "name": meta.get("name", ""),
            "title": meta.get("title", ""),
            "enters": bool(meta.get("enters")),
            "skills": int(meta.get("skills") or 0),
            "eligible": int(meta.get("eligible") or 0),
            "actions": int(meta.get("actions") or 0),
            "eligible_actions": int(meta.get("eligible_actions") or 0),
            "status": status,
            "thin": int(meta.get("eligible") or 0) <= 2,
            "contributes": meta.get("contributes", ""),
            "questions": [q["id"] for q in questions if q["role"] == role],
        }

    caps: Dict[str, Dict[str, Any]] = {}
    for q in questions:
        cap = q["capability"]
        c = caps.setdefault(cap, {
            "key": cap,
            "group": q["group"],
            "dimension": q["dimension"],
            "questions": [],
            "providers": [],
        })
        if q["id"] not in c["questions"]:
            c["questions"].append(q["id"])
        for role in q.get("providers") or []:
            if role not in [p["role"] for p in c["providers"]]:
                c["providers"].append({
                    "role": role,
                    "status": roles.get(role, {}).get("status", "missing"),
                    "eligible": roles.get(role, {}).get("eligible", 0),
                    "enters": roles.get(role, {}).get("enters", False),
                })

    for cap, c in caps.items():
        stats = {p["status"] for p in c["providers"]}
        if "real" in stats:
            c["status"] = "real"
        elif "simulated" in stats:
            c["status"] = "simulated"
        elif "blocked" in stats:
            c["status"] = "blocked"
        else:
            c["status"] = "missing"
        c["real_providers"] = [p["role"] for p in c["providers"] if p["status"] == "real"]
        c["simulated_providers"] = [p["role"] for p in c["providers"] if p["status"] == "simulated"]
        c["blocked_providers"] = [p["role"] for p in c["providers"] if p["status"] == "blocked"]

    counts = {
        "roles": len(roles),
        "report_roles": sum(1 for r in roles.values() if r["status"] != "blocked"),
        "blocked_roles": sorted(r["id"] for r in roles.values() if r["status"] == "blocked"),
        "simulated_roles": sorted(r["id"] for r in roles.values() if r["status"] == "simulated"),
        "thin_roles": sorted(r["id"] for r in roles.values() if r["thin"]),
        "questions": len(questions),
        "capabilities": len(caps),
        "real": sum(1 for c in caps.values() if c["status"] == "real"),
        "simulated": sum(1 for c in caps.values() if c["status"] == "simulated"),
        "blocked": sum(1 for c in caps.values() if c["status"] == "blocked"),
        "missing": sum(1 for c in caps.values() if c["status"] == "missing"),
        "without_v9_dimension": sorted(c["key"] for c in caps.values() if not c["dimension"]),
    }

    return {
        "schema": "dsh.capability_graph/v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "source": {
            "roles": "core/report_roles.py",
            "questions": "core/question_library.py",
            "matrix": "docs/ROLE_CAPABILITY_MATRIX.md",
        },
        "roles": roles,
        "capabilities": caps,
        "questions": questions,
        "counts": counts,
    }


def write(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(build(), ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="capability_graph",
                                 description="角色能力图：角色 × 问题 × 能力 × 状态")
    ap.add_argument("--json", default=None, help="输出 JSON 路径")
    ap.add_argument("--summary", action="store_true", help="只打印摘要")
    a = ap.parse_args(argv)
    g = build()
    if a.json:
        p = write(a.json)
        print(f"wrote {p}")
    if a.summary or not a.json:
        print(json.dumps(g["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
