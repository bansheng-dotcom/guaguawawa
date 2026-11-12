# -*- coding: utf-8 -*-
"""真实任务巡检：20 角色各跑一次自带 demo，取真实 result 走内核出报告。

用途：契约级测试用的是合成 fixture；这里用每个角色真实的技能输出，
暴露"真实结果能否满足 spec"的问题。

用法：python scripts/run_real_tasks.py [--roles r05,r06]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import report_bridge, report_renderer  # noqa: E402
from core.report_kernel import layers, spec as kspec  # noqa: E402
from scripts.report_spec import ROLE_MAP  # noqa: E402

MARK = "__AGENT_RESULT__ "
OUT = ROOT / "projects" / "real_check"


def run_demo(role: str, timeout: int = 180) -> dict | None:
    p = subprocess.run([sys.executable, "guagua.py", "call", role, "demo"],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    out = p.stdout or ""
    lines = [l for l in out.splitlines() if l.startswith(MARK)]
    if not lines:
        # 兜底：部分角色 demo 直接打印 JSON（无 marker），取最后一个完整对象
        m = re.search(r"(?m)^\{", out)
        if m:
            try:
                return json.loads(out[m.start():])
            except json.JSONDecodeError:
                return None
        return None
    try:
        return json.loads(lines[-1][len(MARK):])
    except json.JSONDecodeError:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default=None)
    args = ap.parse_args(argv)
    roles = args.roles.split(",") if args.roles else sorted(ROLE_MAP)

    OUT.mkdir(parents=True, exist_ok=True)
    rows, fails = [], 0
    for role in roles:
        try:
            res = run_demo(role)
        except subprocess.TimeoutExpired:
            rows.append((role, "TIMEOUT", "", ""))
            fails += 1
            continue
        if res is None:
            rows.append((role, "NO_RESULT", "", ""))
            fails += 1
            continue

        s = kspec.load(role)
        contract, fid = layers.build_contract(
            role, role, "真实任务演示", res, s, "demo", "demo", "真实输出巡检")
        verrs = report_renderer.validate_contract(contract)
        serrs = layers.spec_compliance(contract, s)

        html = OUT / f"{role}.html"
        try:
            report_bridge.render_html(contract, str(html))
        except Exception as e:  # noqa: BLE001
            verrs.append(f"render: {e}")

        ok = not verrs and not serrs
        if not ok:
            fails += 1
        rows.append((role, "PASS" if ok else "FAIL",
                     f"{len(verrs)}" if verrs else "",
                     "；".join(serrs)[:70]))

    print(f"{'角色':<5}{'结果':<8}{'契约错':<6}规格问题")
    for r in rows:
        print(f"{r[0]:<5}{r[1]:<8}{r[2]:<6}{r[3]}")
    print(f"\n合计 {len(rows)}，失败 {fails}")
    (OUT / "summary.json").write_text(
        json.dumps([{"role": r[0], "status": r[1], "contract_errs": r[2], "spec": r[3]} for r in rows],
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
