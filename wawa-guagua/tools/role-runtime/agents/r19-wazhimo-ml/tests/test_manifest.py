# -*- coding: utf-8 -*-
"""manifest 契约测试：角色可被编排器发现，且声明了能力状态。"""
import json
import subprocess
import sys
import os


def _manifest(role_dir: str) -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run([sys.executable, "agent.py", "manifest"], cwd=role_dir,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr[-800:]
    marker = "__AGENT_RESULT__ "
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            return json.loads(line[len(marker):])
    return json.loads(proc.stdout.strip())


def test_manifest_shape(role_dir):
    man = _manifest(role_dir)
    assert man.get("role") == "r19"
    assert man.get("skills"), "manifest 必须声明技能清单"
    assert "capability_status" in man, "必须声明能力状态（real/blocked/simulated）"


def test_manifest_skills_have_names(role_dir):
    man = _manifest(role_dir)
    for s in man["skills"]:
        if isinstance(s, dict):
            assert s.get("skill") or s.get("name")
        else:
            assert s and s[0]
