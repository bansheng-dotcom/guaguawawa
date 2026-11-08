# -*- coding: utf-8 -*-
"""跑一遍每个角色的代表性技能动作，采集真实 result 字段（Stage 1 证据）。

用法：
    python agents/scripts/upgrade/probe_results.py                # 人类可读
    python agents/scripts/upgrade/probe_results.py --json         # 机器可读
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(AGENTS)

# 每角色一个代表性的 (skill, action, example 文件名)，均已存在于 examples/
PROBES = {
    "r01": ("intent", "brief", "brief.json"),
    "r02": ("schedule", "wbs", "wbs.json"),
    "r03": ("cfo", "runway", "cfo_runway.json"),
    "r04": ("artifact", "verify", "artifact_verify.json"),
    "r05": ("sizing", "size", "sizing_size.json"),
    "r06": ("explore", "trend", None),
    "r07": ("prd", "prd", "prd.json"),
    "r08": ("slice", "slice", "slice.json"),
    "r09": ("testing", "suites", "testing_suites.json"),
    "r10": ("logo", "logo", "logo.json"),
    "r11": ("copy", "article", "article.json"),
    "r12": ("diagnose", "diagnose", "diagnose.json"),
    "r13": ("health", "health", "health.json"),
    "r14": ("order", "order", "order.json"),
    "r15": ("inventory", "inventory", "inventory.json"),
    "r16": ("people", "employee", "employee.json"),
    "r17": ("integration", "workflow", "workflow.json"),
    "r18": ("quality", "check", "quality_check.json"),
    "r19": ("tracking", "run", "tracking_run.json"),
    "r20": ("monitor", "monitor", "monitor.json"),
}


def role_dir(role_id: str) -> str:
    for name in sorted(os.listdir(AGENTS)):
        if name.startswith(role_id + "-"):
            return os.path.join(AGENTS, name)
    raise KeyError(role_id)


def run(role_id: str, skill: str, action: str, example: str | None):
    d = role_dir(role_id)
    argv = [sys.executable, "agent.py", skill, action]
    if example:
        argv += ["--input", os.path.join("examples", example)]
    env = dict(os.environ, PYTHONPATH=ROOT + os.pathsep + AGENTS,
               PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run(argv, cwd=d, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=120)
    marker = "__AGENT_RESULT__ "
    payload = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith(marker):
            try:
                payload = json.loads(line[len(marker):])
            except json.JSONDecodeError:
                payload = None
    return proc.returncode, payload, (proc.stderr or "").strip()


def main() -> int:
    out = {}
    for rid, (skill, action, example) in PROBES.items():
        if not example and rid != "r06":
            continue
        rc, payload, err = run(rid, skill, action, example)
        keys = {}
        if isinstance(payload, dict):
            for k, v in payload.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    keys[k] = v if not isinstance(v, str) or len(v) <= 60 else v[:60] + "…"
                elif isinstance(v, list):
                    keys[k] = f"list[{len(v)}]"
                elif isinstance(v, dict):
                    keys[k] = f"dict({','.join(list(v)[:6])})"
        out[rid] = {"rc": rc, "skill": skill, "action": action,
                    "fields": keys, "err": err.splitlines()[-1] if err else ""}
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    for rid, info in out.items():
        print(f"== {rid} {info['skill']}/{info['action']} rc={info['rc']}")
        for k, v in info["fields"].items():
            print(f"   {k} = {v}")
        if info["err"]:
            print("   ERR=" + info["err"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
