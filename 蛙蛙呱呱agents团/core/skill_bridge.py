# -*- coding: utf-8 -*-
"""core/skill_bridge —— 领域方法 ↔ 现有技能的接入层。

解决的问题：领域包里的方法不能另起一套实现。每一条方法必须回答：
- 你落到哪个角色、哪个技能、哪个动作？
- 是「已有技能直接做」（exact）、「同域但要扩字段」（partial），
  还是「现有技能没有，必须新增」（new）？

本模块只做三件事：
    coverage()                 覆盖率：exact / partial / new
    info(role, method)         某条方法的技能落点
    run(role, method, args)    真调用该技能（runner.invoke），返回 result

校验：`scripts/check_skill_integration.py` 会检查 120 条方法是否全部有落点，
且映射到的技能/动作在 `knowledge/skills_inventory.json` 里真实存在。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
INV = ROOT / "knowledge" / "skills_inventory.json"
MAP = ROOT / "knowledge" / "roles" / "skill_map.json"

_CACHE: Dict[str, Any] = {}


def _load() -> Dict[str, Any]:
    if "inv" not in _CACHE:
        _CACHE["inv"] = json.loads(INV.read_text(encoding="utf-8-sig"))
        _CACHE["map"] = json.loads(MAP.read_text(encoding="utf-8-sig"))
    return _CACHE


def inventory() -> Dict[str, Any]:
    return _load()["inv"]


def skill_map() -> Dict[str, Any]:
    return _load()["map"]


def info(role: str, method: str) -> Optional[Dict[str, Any]]:
    return (skill_map().get("roles", {}).get(role) or {}).get(method)


def methods(role: str) -> Dict[str, Any]:
    return skill_map().get("roles", {}).get(role) or {}


def coverage() -> Dict[str, Any]:
    counts: Counter = Counter()
    by_role: Dict[str, Counter] = {}
    missing: List[str] = []
    inv = inventory()
    for role, items in skill_map().get("roles", {}).items():
        by_role[role] = Counter()
        for method, m in items.items():
            fit = m.get("fit", "new")
            counts[fit] += 1
            by_role[role][fit] += 1
            if fit in ("exact", "partial"):
                node = inv.get(m.get("skill_role"), {}).get(m.get("skill"))
                if node is None:
                    missing.append(f"{role}.{method}: 技能 {m.get('skill_role')}.{m.get('skill')} 不存在")
                elif m.get("action") and m["action"] not in node.get("actions", []):
                    missing.append(f"{role}.{method}: 动作 {m['action']} 不存在")
            elif not m.get("note"):
                missing.append(f"{role}.{method}: new 但没有说明")
    total = sum(counts.values())
    return {"total": total, "counts": dict(counts),
            "coverage_rate": round((counts.get("exact", 0) + counts.get("partial", 0))
                                   / max(1, total), 4),
            "by_role": {r: dict(c) for r, c in by_role.items()},
            "missing": missing}


def commands(role: str) -> List[str]:
    return [m["command"] for m in methods(role).values() if m.get("command")]


def run(role: str, method: str, args: List[str],
        timeout: int = 120) -> Dict[str, Any]:
    """真调用该角色技能；new 方法直接返回可读错误，不静默 fallback。"""
    from core import runner
    m = info(role, method)
    if not m:
        return {"ok": False, "error": f"未登记的方法：{role}.{method}"}
    if m.get("fit") == "new" or not m.get("skill"):
        return {"ok": False, "error": f"{role}.{method} 是新增方法：{m.get('note')}",
                "fit": "new"}
    argv = [m["skill"]] + ([m["action"]] if m.get("action") else []) + list(args)
    try:
        r = runner.invoke(m["skill_role"], argv, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": bool((r.get("json") or {}).get("ok", True)),
            "role": m["skill_role"], "skill": m["skill"],
            "action": m["action"], "result": r.get("json") or r.get("stdout")}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="skill_bridge")
    ap.add_argument("action", choices=["coverage", "info", "commands"])
    ap.add_argument("--role", default=None)
    ap.add_argument("--method", default=None)
    a = ap.parse_args(argv)
    if a.action == "coverage":
        c = coverage()
        print(json.dumps(c, ensure_ascii=False, indent=2))
        return 0 if not c["missing"] else 1
    if a.action == "info":
        if not (a.role and a.method):
            print("需要 --role 与 --method")
            return 2
        print(json.dumps(info(a.role, a.method), ensure_ascii=False, indent=2))
        return 0
    if not a.role:
        print("需要 --role")
        return 2
    print("\n".join(commands(a.role)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
