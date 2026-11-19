# -*- coding: utf-8 -*-
"""core/roster —— 完整专家名册：从 20 个角色目录生成，不手写（v12.2）。

问题：
    `core/registry.py::ROLES` 只有身份（id/name/title/dir/capabilities），
    没有技能。技能在各自 `prompt_profile.json` 的 actions 里，在 `skills/` 目录里。
    名册不暴露技能，调度就回答不了「谁会干这件事」——技能调用自然调不到。

做法：
    名册**不手写**，每次从磁盘生成：
        ROLES（身份）+ prompt_profile.json（技能动作）+ skills/（技能包）
    → {role: {id, name, title, dir, enters_report, actions[], skills[], entry}}

    这样加一个技能、改一个 action，名册自动跟着变，不存在「名册与角色不同步」。

用途：
    * `guagua.py report brief` 按名册给每个角色发任务卡；
    * `find_action("市场规模")` 反查谁能干；
    * 报告出厂的「谁答的」可追溯。

用法：
    python -m core.roster                # 20 行总览
    python -m core.roster --who 市场规模  # 反查
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


def _load_profile(dirname: str) -> Dict[str, Any]:
    p = ROOT / dirname / "prompt_profile.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def _skills(dirname: str) -> List[str]:
    """角色技能 = skills/ 下的模块（s01_research.py → research）。"""
    d = ROOT / dirname / "skills"
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("s[0-9]*_*.py")):
        out.append(f.stem.split("_", 1)[-1])
    return out


def build() -> Dict[str, Any]:
    from core.registry import ROLES

    roles: Dict[str, Any] = {}
    for r in ROLES:
        rid = str(r["id"])
        dirname = str(r.get("dir") or "")
        prof = _load_profile(dirname)
        actions = []
        for a in prof.get("actions") or []:
            actions.append({
                "skill": str(a.get("skill") or ""),
                "action": str(a.get("action") or ""),
                "label": str(a.get("label") or ""),
                "when": list(a.get("when") or []),
                "requires": list(a.get("requires") or []),
            })
        roles[rid] = {
            "id": rid,
            "name": r.get("name"),
            "title": r.get("title"),
            "dir": dirname,
            "status": r.get("status"),
            "capabilities": list(r.get("capabilities") or []),
            "enters_report": bool(r.get("enters_report", True)),
            "actions": actions,
            "skills": _skills(dirname),
            "entry": f"python guagua.py call {rid}",
        }
    return {
        "schema": "dsh.roster/v1",
        "count": len(roles),
        "roles": roles,
        "totals": {
            "actions": sum(len(v["actions"]) for v in roles.values()),
            "skills": sum(len(v["skills"]) for v in roles.values()),
            "report_roles": sum(1 for v in roles.values() if v["enters_report"]),
        },
    }


def find_action(roster: Dict[str, Any], keyword: str) -> List[Dict[str, Any]]:
    """反查：谁能干这件事（按 action 的 when/label 命中关键词）。"""
    kw = str(keyword or "").strip()
    if not kw:
        return []
    out = []
    for rid, r in roster["roles"].items():
        if not r["enters_report"]:
            continue
        hits = []
        for a in r["actions"]:
            text = a["label"] + " " + " ".join(a["when"])
            if kw in text:
                hits.append(a)
        if hits:
            out.append({"role": rid, "name": r["name"], "title": r["title"],
                        "matched": hits})
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="roster", description="完整专家名册（生成式）")
    ap.add_argument("--who", default=None, help="反查谁有这个技能")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    roster = build()
    if a.who:
        res = find_action(roster, a.who)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res else 1
    if a.json:
        Path(a.json).write_text(json.dumps(roster, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    t = roster["totals"]
    print(f"专家 {roster['count']} 人｜可进报告 {t['report_roles']}｜"
          f"技能动作 {t['actions']} 个｜技能包 {t['skills']} 个")
    for rid, r in roster["roles"].items():
        flag = "进报告" if r["enters_report"] else "不出报告"
        print(f"  {rid} {r['name']:6} {r['title'][:18]:20} "
              f"动作{len(r['actions']):3} 技能包{len(r['skills']):3} {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
