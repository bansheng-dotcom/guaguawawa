# -*- coding: utf-8 -*-
"""全角色 case 结构门禁批量校验（Stage 4/5 验收工具）。

对 R01~R20（跳过 R06）逐个执行 `python agent.py case validate --case <本角色新增案例>`，
把 11 项结构检查的结果汇总成一张表。

用法：
    python agents/scripts/upgrade/verify_cases.py [--json]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

AGENTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP = {"r06-wadeqing-analyst"}

CASE_IDS = {
    "r01": "budget-rebalance", "r02": "sprint-overload", "r03": "runway-crisis",
    "r04": "artifact-reject", "r05": "market-sizing", "r07": "feature-coldstart",
    "r08": "mvp-launch", "r09": "refactor-capacity", "r10": "brand-refresh",
    "r11": "headline-test", "r12": "channel-attribution", "r13": "churn-warning",
    "r14": "funnel-pricing", "r15": "stockout-risk", "r16": "productivity-review",
    "r17": "workflow-reliability", "r18": "metric-reconcile", "r19": "model-gain",
    "r20": "sla-incident",
}


def role_dir(role_id: str) -> str | None:
    for name in sorted(os.listdir(AGENTS)):
        if name.startswith(role_id + "-") and name not in SKIP:
            return os.path.join(AGENTS, name)
    return None


def check(role_id: str, case_id: str) -> dict:
    d = role_dir(role_id)
    if not d:
        return {"role": role_id, "ok": False, "reason": "角色目录缺失"}
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    variants = [
        ["agent.py", "case", "validate", "--case", case_id],
        ["agent.py", "case", "validate", case_id],
        ["agent.py", "case", case_id],
    ]
    last = ""
    for argv in variants:
        proc = subprocess.run([sys.executable, *argv], cwd=d, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              env=env, timeout=120)
        out = proc.stdout or ""
        idx = out.find("__AGENT_RESULT__ ")
        payload = None
        if idx >= 0:
            try:
                payload = json.loads(out[idx + len("__AGENT_RESULT__ "):].strip().splitlines()[0])
            except json.JSONDecodeError:
                payload = None
        if payload is None and out.strip().startswith("{"):
            try:
                payload = json.loads(out.strip())
            except json.JSONDecodeError:
                payload = None
        if payload is None:
            last = (proc.stderr or out).strip().splitlines()[-1] if (proc.stderr or out) else ""
            continue
        # 三种形态：{ok, checks} / {validate:{ok,errors}} / {error: N}
        if "error" in payload and "ok" not in payload:
            last = str(payload["error"])
            continue
        if isinstance(payload.get("validate"), dict):
            v = payload["validate"]
            errors = v.get("errors") or []
            return {"role": role_id, "case": case_id, "ok": bool(v.get("ok")),
                    "grade": v.get("grade"), "passed": None,
                    "total": None, "failed": errors}
        checks = payload.get("checks") or []
        failed = [c for c in checks if not c.get("ok")]
        return {"role": role_id, "case": case_id, "ok": bool(payload.get("ok")),
                "grade": payload.get("grade"), "passed": len(checks) - len(failed),
                "total": len(checks),
                "failed": [f"{c.get('dim')}: {c.get('msg')}" for c in failed]}
    return {"role": role_id, "case": case_id, "ok": False, "reason": last}


def main() -> int:
    results = [check(r, CASE_IDS[r]) for r in sorted(CASE_IDS)]
    if "--json" in sys.argv:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return 0
    for r in results:
        mark = "PASS" if r.get("ok") else "FAIL"
        extra = f"{r.get('passed')}/{r.get('total')}" if r.get("total") else r.get("reason", "")
        print(f"{mark:4} {r['role']} {r.get('case','')}  {extra}")
        for f in r.get("failed") or []:
            print("       -", f)
    bad = [r for r in results if not r.get("ok")]
    print(f"--- {len(results) - len(bad)}/{len(results)} 角色案例通过结构门禁")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
