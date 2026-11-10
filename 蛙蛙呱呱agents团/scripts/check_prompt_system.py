#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2.2 统一门禁：一条命令跑完提示词系统的全部 CI 检查。

四道门禁：
    1. 目录一致性：现场重扫的技能/动作集合必须与 docs/actions_catalog.json 完全一致；
    2. profile 完整性：20 个角色全部有 prompt_profile.json 且通过校验；
    3. 模糊指令回归：200 条夹具全部符合预期，静默默认 = 0；
    4. 内核门槛：澄清必须带问题或假设、置信度非常量（由回归 runner 断言）。

用法：
    python scripts/check_prompt_system.py
    python scripts/check_prompt_system.py --skip-catalog   # 本地快速迭代
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "docs", "actions_catalog.json")
CHECK_OUT = os.path.join(ROOT, "workspace", "baseline", "actions_catalog_check.json")


def run(cmd, timeout=1800):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def signature(path):
    data = json.load(open(path, encoding="utf-8"))
    return {
        role["role"]: sorted((s["name"], a["name"])
                             for s in role["skills"] for a in s["actions"])
        for role in data["roles"]
    }


def check_catalog():
    rc, out, err = run([sys.executable, "scripts/export_actions_catalog.py",
                        "--all", "--out", CHECK_OUT])
    if rc != 0:
        return False, "重新导出失败：%s" % (err.strip()[-300:] or out.strip()[-300:])
    live, frozen = signature(CHECK_OUT), signature(CATALOG)
    diffs = []
    for role in sorted(set(live) | set(frozen)):
        a, b = live.get(role, []), frozen.get(role, [])
        if a != b:
            only_live = [x for x in a if x not in b]
            only_frozen = [x for x in b if x not in a]
            diffs.append("%s 新增=%s 缺失=%s" % (role, only_live[:5], only_frozen[:5]))
    if diffs:
        return False, "目录与代码不一致：\n  " + "\n  ".join(diffs)
    total = sum(len(v) for v in live.values())
    return True, "%d 个角色 / %d 个动作与目录一致" % (len(live), total)


def check_profiles():
    rc, out, err = run([sys.executable, "scripts/validate_profiles.py", "--require-all"])
    tail = (out.strip().splitlines() or [""])[-1]
    return rc == 0, tail if rc == 0 else out.strip()[-800:] or err[-400:]


def check_regressions():
    rc, out, err = run([sys.executable, "scripts/run_prompt_regressions.py",
                        "--mode", "compile"])
    lines = out.strip().splitlines()
    tail = lines[-2] if len(lines) >= 2 else ""
    gates = lines[-1] if lines else ""
    return rc == 0, (tail + " " + gates).strip() or err[-400:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-catalog", action="store_true")
    args = ap.parse_args()

    checks = []
    if not args.skip_catalog:
        checks.append(("catalog", check_catalog))
    checks += [("profiles", check_profiles), ("regressions", check_regressions)]

    failed = 0
    for name, fn in checks:
        ok, detail = fn()
        print("[%s] %-12s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            failed += 1
    print(json.dumps({"checks": len(checks), "failed": failed}, ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
