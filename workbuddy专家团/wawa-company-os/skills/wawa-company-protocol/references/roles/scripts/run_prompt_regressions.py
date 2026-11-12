# -*- coding: utf-8 -*-
"""P1.0 模糊指令回归集 runner。

模式：
    --mode keyword   改动前基线：调用角色 _route()，统计静默默认
    --mode compile   改动后：调用 agent.py clarify，校验澄清/路由是否符合预期

用法：
    python scripts/run_prompt_regressions.py --mode keyword
    python scripts/run_prompt_regressions.py --mode compile
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "tests", "prompt_regressions", "fixtures.json")
FIXTURE_DIR = os.path.join(ROOT, "tests", "prompt_regressions", "roles")
OUT_DIR = os.path.join(ROOT, "workspace", "baseline")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def load_fixtures() -> dict:
    """P1 的 r06/r11 夹具保留在 fixtures.json，P2 起每角色一份 roles/<rXX>.json。"""
    data = {}
    if os.path.exists(FIXTURES):
        data.update(json.load(open(FIXTURES, encoding="utf-8")))
    if os.path.isdir(FIXTURE_DIR):
        for name in sorted(os.listdir(FIXTURE_DIR)):
            if not name.endswith(".json"):
                continue
            payload = json.load(open(os.path.join(FIXTURE_DIR, name), encoding="utf-8"))
            for role, spec in payload.items():
                if role in data:
                    raise SystemExit(f"夹具重复定义: {role}（{name}）")
                data[role] = spec
    return data


def _run(cmd, cwd):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=120)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["keyword", "compile"], required=True)
    ap.add_argument("--role", default=None, help="只跑某个角色，如 r07")
    args = ap.parse_args()

    fixtures = load_fixtures()
    if args.role:
        fixtures = {args.role: fixtures[args.role]}
    results, totals = [], {"cases": 0, "route": 0, "clarify": 0,
                           "silent_default": 0, "expect_match": 0, "bare_clarify": 0}
    confidences = set()

    for role, spec in fixtures.items():
        role_dir = os.path.join(ROOT, spec["role_dir"])
        for case in spec["cases"]:
            intent = case["intent"]
            totals["cases"] += 1
            if args.mode == "keyword":
                rc, out, err = _run([sys.executable, os.path.join(ROOT, "scripts", "probe_route.py"),
                                     "--role-dir", role_dir, "--intent", intent], ROOT)
                data = json.loads(out.strip().splitlines()[-1]) if rc == 0 and out.strip() else {}
                actual = "%s.%s" % (data.get("route", {}).get("skill"), data.get("route", {}).get("action"))
                kind = "route"
                silent = bool(data.get("silent_default"))
                match = None
            else:
                rc, out, err = _run([sys.executable, "agent.py", "clarify", "--intent", intent], role_dir)
                data = json.loads(out.strip().splitlines()[-1]) if rc in (0, 2) and out.strip() else {}
                if data.get("needs_clarification"):
                    kind, actual = "clarify", "clarify"
                else:
                    r = data.get("route") or {}
                    kind, actual = "route", "%s.%s" % (r.get("skill"), r.get("action"))
                silent = False
                match = kind == case["expect"] and (
                    case.get("expect_action") is None or actual == case["expect_action"])

            totals[kind] = totals.get(kind, 0) + 1
            totals["silent_default"] += int(silent)
            if args.mode == "compile":
                bare = kind == "clarify" and not data.get("questions") \
                    and not data.get("assumptions")
                totals["bare_clarify"] += int(bare)
                if data.get("confidence") is not None:
                    confidences.add(data["confidence"])
            if match:
                totals["expect_match"] += 1
            results.append({
                "id": case["id"], "role": role, "intent": intent,
                "expect": case["expect"], "expect_action": case.get("expect_action"),
                "actual": actual, "kind": kind, "silent_default": silent,
                "expect_match": match, "rc": rc,
                "questions": [q.get("field") for q in data.get("questions", [])],
                "assumptions": [a.get("field") for a in data.get("assumptions", [])],
                "confidence": data.get("confidence"),
            })

    payload = {"mode": args.mode, "summary": dict(
        totals, confidence_values=sorted(confidences)), "results": results}
    os.makedirs(OUT_DIR, exist_ok=True)
    suffix = f"_{args.role}" if args.role else ""
    out_path = os.path.join(OUT_DIR, f"prompt_regressions_{args.mode}{suffix}.json")
    json.dump(payload, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    for r in results:
        print("{id} {kind:<8} {actual:<20} expect={expect:<8} silent={silent} match={m}".format(
            id=r["id"], kind=r["kind"], actual=r["actual"], expect=r["expect"],
            silent=r["silent_default"], m=r["expect_match"]))
    print(json.dumps(totals, ensure_ascii=False))
    print(f"written: {out_path}")
    if args.mode == "compile":
        # CI 三条硬门槛：静默默认=0；澄清必须带问题或假设；置信度可复算且非常量。
        gates = {
            "all_expect_match": totals["expect_match"] == totals["cases"],
            "silent_default_zero": totals["silent_default"] == 0,
            "clarify_has_question_or_assumption": totals["bare_clarify"] == 0,
            "confidence_not_constant": len(confidences) > 1,
        }
        print(json.dumps({"gates": gates}, ensure_ascii=False))
        return 0 if all(gates.values()) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
