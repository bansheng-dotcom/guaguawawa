# -*- coding: utf-8 -*-
"""R04 verify_loop：7 技能 × 15 动作闭环矩阵。

每个动作：
1. 以子进程真实运行 `python agent.py <skill> <action> ...`（同外部调用方式）；
2. contracts.validate_output：输出必须符合登记契约；
3. review.review_packet（T7 对抗评审）：评审产出本身必须过五检查；
4. result.ok 必须等于该夹具的预期 ok。
全绿退出码 0。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(_HERE), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import _common as c                    # noqa: E402
import contracts                                    # noqa: E402
import review as review_lib                         # noqa: E402

_EXAMPLES = os.path.join(_HERE, "examples")

# (skill, action, 输入夹具, 额外 CLI 参数, 预期 ok)
MATRIX: List[Dict[str, Any]] = [
    {"skill": "artifact", "action": "inventory",
     "input": os.path.join(_EXAMPLES, "artifact_inventory.json"),
     "extra": [], "expect_ok": True},
    {"skill": "artifact", "action": "verify",
     "input": os.path.join(_EXAMPLES, "artifact_verify.json"),
     "extra": [], "expect_ok": True},
    {"skill": "gate", "action": "run",
     "input": os.path.join(_EXAMPLES, "gate_run.json"),
     "extra": [], "expect_ok": True},
    {"skill": "gate", "action": "audit",
     "input": os.path.join(_EXAMPLES, "gate_audit.json"),
     "extra": [], "expect_ok": True},
    {"skill": "criteria", "action": "review",
     "input": os.path.join(_EXAMPLES, "criteria_review.json"),
     "extra": [], "expect_ok": True},
    {"skill": "criteria", "action": "delta",
     "input": os.path.join(_EXAMPLES, "criteria_delta.json"),
     "extra": ["--state", os.path.join(_EXAMPLES, "criteria_delta_state.json")],
     "expect_ok": True},
    {"skill": "quality", "action": "critique",
     "input": os.path.join(_EXAMPLES, "quality_critique.json"),
     "extra": [], "expect_ok": True},
    {"skill": "quality", "action": "converge",
     "input": os.path.join(_EXAMPLES, "quality_converge.json"),
     "extra": ["--compare", os.path.join(_EXAMPLES, "quality_converge_v2.json")],
     "expect_ok": True},
    {"skill": "facts", "action": "check",
     "input": os.path.join(_EXAMPLES, "facts_check.json"),
     "extra": [], "expect_ok": True},
    {"skill": "facts", "action": "trace",
     "input": os.path.join(_EXAMPLES, "facts_trace.json"),
     "extra": ["--text", os.path.join(_EXAMPLES, "facts_trace_source.txt")],
     "expect_ok": True},
    {"skill": "strengths", "action": "mark",
     "input": os.path.join(_EXAMPLES, "strengths_mark.json"),
     "extra": [], "expect_ok": True},
    {"skill": "strengths", "action": "recheck",
     "input": os.path.join(_EXAMPLES, "strengths_recheck.json"),
     "extra": ["--new", os.path.join(_EXAMPLES, "strengths_recheck_new.json")],
     "expect_ok": True},
    {"skill": "human", "action": "package",
     "input": os.path.join(_EXAMPLES, "human_package.json"),
     "extra": [], "expect_ok": True},
    {"skill": "human", "action": "ingest",
     "input": os.path.join(_EXAMPLES, "human_ingest.json"),
     "extra": [], "expect_ok": True},
    {"skill": "human", "action": "ack",
     "input": os.path.join(_EXAMPLES, "human_ack.json"),
     "extra": [], "expect_ok": True},
]


def _run_cli(skill: str, action: str, input_path: str, extra: List[str]) -> Dict[str, Any]:
    cmd = [sys.executable, os.path.join(_HERE, "agent.py"), skill, action,
           "--input", input_path] + list(extra)
    cp = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=_HERE)
    for line in (cp.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return {"exit_code": cp.returncode,
                    "result": json.loads(line[len("__AGENT_RESULT__ "):])}
    return {"exit_code": cp.returncode, "result": None,
            "stdout": cp.stdout, "stderr": cp.stderr}


def run_matrix() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    for spec in MATRIX:
        skill, action = spec["skill"], spec["action"]
        r = _run_cli(skill, action, spec["input"], spec["extra"])
        row: Dict[str, Any] = {"skill": skill, "action": action}
        result = r.get("result")
        if result is None:
            row.update({"ok": False, "stage": "run",
                        "error": (r.get("stderr") or r.get("stdout") or "")[:200]})
            rows.append(row)
            checks.append(c.ck(False, f"{skill}/{action} 运行失败（无 __AGENT_RESULT__）",
                               f"loop:{skill}:{action}", "CRITICAL"))
            continue
        # 1) 契约校验（输入 & 输出）
        input_data = c.load_json(spec["input"])
        iv = contracts.validate_input(skill, action, input_data)
        ov = contracts.validate_output(skill, action, result)
        # 2) T7 对抗评审
        rp = review_lib.review_packet({"skill": skill, "action": action,
                                       "result": result})
        # 3) ok 语义
        ok_expected = bool(result.get("ok")) == spec["expect_ok"]
        exit_ok = (r["exit_code"] == 0) == spec["expect_ok"]
        passed = iv["ok"] and ov["ok"] and rp["ok"] and ok_expected and exit_ok
        row.update({"ok": passed,
                    "contract_input": iv["ok"], "contract_output": ov["ok"],
                    "review": rp["ok"], "review_category": rp.get("failure_category"),
                    "result_ok": result.get("ok"), "expect_ok": spec["expect_ok"],
                    "exit_code": r["exit_code"]})
        rows.append(row)
        if not iv["ok"]:
            checks.append(c.ck(False, f"{skill}/{action} 输入契约不过：{iv['errors']}",
                               f"loop:{skill}:{action}", "CRITICAL"))
        if not ov["ok"]:
            checks.append(c.ck(False, f"{skill}/{action} 输出契约不过：{ov['errors']}",
                               f"loop:{skill}:{action}", "CRITICAL"))
        if not rp["ok"]:
            checks.append(c.ck(False, f"{skill}/{action} 对抗评审不过：{rp.get('failure_category')}",
                               f"loop:{skill}:{action}", "CRITICAL"))
        if not ok_expected or not exit_ok:
            checks.append(c.ck(False, f"{skill}/{action} ok 语义不符"
                               f"（result.ok={result.get('ok')} expect={spec['expect_ok']}"
                               f" exit={r['exit_code']}）",
                               f"loop:{skill}:{action}", "CRITICAL"))
        if passed:
            checks.append(c.ck(True, f"{skill}/{action} 闭环通过", f"loop:{skill}:{action}"))
    ok_all = bool(rows) and all(x["ok"] for x in rows)
    out = c.result(checks,
                   matrix=rows,
                   total=len(rows),
                   passed=sum(1 for x in rows if x.get("ok")),
                   failed=sum(1 for x in rows if not x.get("ok")),
                   verdict="PASS" if ok_all else "FAIL",
                   next="闭环矩阵全绿" if ok_all else "闭环矩阵存在红项：逐条修复后重跑")
    out["ok"] = out["ok"] and ok_all
    return out


def _cli() -> int:
    out = run_matrix()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
