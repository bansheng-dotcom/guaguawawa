# -*- coding: utf-8 -*-
"""R01~R20 结构扫描 + 真实 manifest 试跑（Stage 1 现状体检工具）。

用法：
    python agents/scripts/upgrade/survey_roles.py            # 打印表格
    python agents/scripts/upgrade/survey_roles.py --json     # 输出 JSON
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(AGENTS)


def role_dirs():
    out = []
    for name in sorted(os.listdir(AGENTS)):
        p = os.path.join(AGENTS, name)
        if os.path.isdir(p) and len(name) > 3 and name[0] == "r" and name[1:3].isdigit() and name[4 - 1] == "-":
            out.append(p)
    return out


def manifest_of(role_dir: str):
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run([sys.executable, "agent.py", "manifest"], cwd=role_dir,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=120)
    marker = "__AGENT_RESULT__ "
    man = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith(marker):
            try:
                man = json.loads(line[len(marker):])
            except json.JSONDecodeError:
                man = None
    return proc.returncode, man, (proc.stderr or "").strip()


def main() -> int:
    rows = []
    for d in role_dirs():
        rc, man, err = manifest_of(d)
        skills = []
        if man:
            for s in man.get("skills", []):
                if isinstance(s, dict):
                    actions = s.get("actions")
                    if isinstance(actions, list) and actions and isinstance(actions[0], dict):
                        actions = [a.get("action") for a in actions]
                    skills.append({"skill": s.get("skill") or s.get("name"),
                                   "actions": actions})
                elif isinstance(s, (list, tuple)):
                    skills.append({"skill": s[0], "actions": None})
        ex_dir = os.path.join(d, "examples")
        rows.append({
            "role": os.path.basename(d)[:3],
            "dir": os.path.basename(d),
            "manifest_rc": rc,
            "name": (man or {}).get("name"),
            "skills": skills,
            "examples": sorted(os.listdir(ex_dir)) if os.path.isdir(ex_dir) else [],
            "has_tests": os.path.isdir(os.path.join(d, "tests")),
            "has_configs": os.path.isdir(os.path.join(d, "configs")),
            "stderr_tail": err.splitlines()[-1] if err else "",
        })
    if "--json" in sys.argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    for r in rows:
        print(f"{r['role']} {r['dir']}")
        print(f"   rc={r['manifest_rc']} name={r['name']} tests={r['has_tests']} configs={r['has_configs']}")
        print("   skills=" + ", ".join(
            f"{s['skill']}({', '.join(map(str, s['actions'] or []))})" for s in r["skills"]))
        print("   examples=" + ", ".join(r["examples"]))
        if r["stderr_tail"]:
            print("   ERR=" + r["stderr_tail"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
