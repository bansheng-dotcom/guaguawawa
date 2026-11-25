# -*- coding: utf-8 -*-
"""core/skill_graph —— 角色 → 技能 → 动作 的可调度注册表。

为什么需要：报告里的每个数字都应该由某个角色的某个技能真实跑出来，
而不是在写作时算出来。要调度，先得知道「有哪些技能、每个动作要什么参数」。

本模块只做登记与查询，不执行：
  scan()                     扫描 r*/skills/*.py，得到 20 角色 / N 技能 / M 动作
  contract(role, skill, act) 某个动作的必填参数（从 argparse 声明解析）
  find(...)                  按角色/技能/动作查找

执行在 core/report_flow.py。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

TEAM = Path(__file__).resolve().parent.parent
CACHE = TEAM / "configs" / "skill_graph.json"

_NAME = re.compile(r'^NAME\s*=\s*"([^"]+)"', re.M)
_DESC = re.compile(r'^DESC\s*=\s*"([^"]+)"', re.M)
_ACTIONS = re.compile(r"^ACTIONS\s*=\s*\{([\s\S]*?)\n\}", re.M)
_ACTION_KEY = re.compile(r'"([a-z0-9_]+)"\s*:')
_ARG = re.compile(r'add_argument\(\s*"(--[a-z0-9_-]+)"([^)]*)\)')


def _parse_skill(path: Path) -> Optional[Dict[str, Any]]:
    src = path.read_text(encoding="utf-8", errors="replace")
    m = _NAME.search(src)
    if not m:
        return None
    name = m.group(1)
    desc = (_DESC.search(src).group(1) if _DESC.search(src) else "")
    actions: List[str] = []
    am = _ACTIONS.search(src)
    if am:
        actions = _ACTION_KEY.findall(am.group(1))
    # add_parser("动作名") 里声明的子动作
    for act in re.findall(r'add_parser\(\s*"([a-z0-9_]+)"', src):
        if act not in actions:
            actions.append(act)
    required = []
    for flag, rest in _ARG.findall(src):
        if "required=True" in rest and flag != "--input":
            required.append(flag)
    return {"role_path": path.parent.parent.name, "skill": name, "desc": desc,
            "actions": sorted(set(actions)), "required": required,
            "file": str(path.relative_to(TEAM)).replace("\\", "/")}


def scan(write_cache: bool = True) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for d in sorted(TEAM.glob("r[0-9][0-9]-*")):
        role = d.name.split("-")[0]
        sk = d / "skills"
        if not sk.is_dir():
            continue
        for f in sorted(sk.glob("*.py")):
            if f.name.startswith("_"):
                continue
            row = _parse_skill(f)
            if not row:
                continue
            row["role"] = role
            rows.append(row)
    if write_cache:
        try:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                             encoding="utf-8")
        except OSError:
            pass
    return rows


def load() -> List[Dict[str, Any]]:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return scan()


def contract(role: str, skill: str, action: Optional[str] = None) -> Dict[str, Any]:
    for row in load():
        if row["role"] == role and row["skill"] == skill:
            if action and action not in row["actions"]:
                return {"ok": False, "reason": f"{role}.{skill} 没有动作 {action}"}
            return {"ok": True, "required": row["required"], "actions": row["actions"],
                    "desc": row.get("desc", "")}
    return {"ok": False, "reason": f"未登记 {role}.{skill}"}


def stats() -> Dict[str, Any]:
    rows = load()
    return {"roles": len({r["role"] for r in rows}), "skills": len(rows),
            "actions": sum(max(1, len(r["actions"])) for r in rows)}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="skill_graph")
    ap.add_argument("--rescan", action="store_true")
    ap.add_argument("--role", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = scan() if a.rescan else load()
    if a.role:
        rows = [r for r in rows if r["role"] == a.role]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        print(f"角色 {len({r['role'] for r in rows})} / 技能 {len(rows)}")
        for r in rows:
            acts = ", ".join(r["actions"]) or "-"
            print(f"  {r['role']}.{r['skill']:<14} {acts:<40} {r.get('desc', '')[:28]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
