# -*- coding: utf-8 -*-
"""R20 蛙值守 · SOP v13.0 自动演进执行器（可断点续跑）。

把 SOP 的三轮演进（每轮一个完整 SOP 周期，每周期 ≥3 维真实架构升级）
固化为可复跑的确定性流水线：

    Round 1 (L01-L03) 工具实体层 / 意图解构层 / 自愈反思层
    Round 2 (L04-L06) 领域账本层 / 质感去劣化层 / 横向决策层
    Round 3 (L07-L10) 伴生消费层 / 局部差量层 / 会话记忆层 / 工业容灾层

每轮执行：
    1. 逐个真实引擎探针（agent.py evolve ...），逐条断言可复算证据；
    2. 双轨回归：历史 run_tests.py + 演进 tests/test_evolution_l01_l10.py；
    3. 零回归硬门禁：任一失败即整轮 FAIL，不推进下一轮；
    4. 写 gate.json / EVOLUTION_STATE 状态文件，支持 --stage / --run-all 续跑。

用法：
    python auto_evolve_runner.py --status
    python auto_evolve_runner.py --stage 1
    python auto_evolve_runner.py --run-all
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SOP_VERSION = "13.0"
ROLE = "r20"
WORKSPACE = os.path.join(HERE, "workspace")
ROUNDS_DIR = os.path.join(WORKSPACE, "rounds")
STATE_PATH = os.path.join(WORKSPACE, "evolution_state.json")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


# --------------------------------------------------------------------------- #
# 轮次定义
# --------------------------------------------------------------------------- #
ROUNDS: Dict[int, Dict[str, Any]] = {
    1: {
        "title": "第一轮 · 工具实体 / 意图解构 / 自愈反思",
        "stages": [
            {"id": "L01", "name": "真实可靠性精算沙箱",
             "argv": ["evolve", "probe", "--out", "{dir}/L01_probe.json"],
             "artifact": "L01_probe.json",
             "assert": lambda d: d.get("status") == "HEALTHY" and d.get("ok")
             and all(c.get("ok") for c in d.get("checks", []))},
            {"id": "L02", "name": "复合故障诉求 → 5 阶段恢复 DAG",
             "argv": ["evolve", "decompile",
                      "--text", "支付服务 P1 故障，30 分钟内恢复，RTO<=2h，RPO<=0.5h，"
                                "影响 3 万用户，先回滚再复盘",
                      "--out", "{dir}/L02_compile.json", "--md", "{dir}/L02_compile.md"],
             "artifact": "L02_compile.json",
             "assert": lambda d: d.get("ok") and len(d.get("stages", [])) == 5
             and d.get("dag", {}).get("is_dag") and d.get("entities", {}).get("severity") == "critical"},
            {"id": "L03", "name": "告警归一 + Reflexion + 五条红线",
             "argv": ["evolve", "heal", "--action", "补齐告警并生成恢复计划",
                      "--artifact", "{dir}/L03_input.json", "--out", "{dir}/L03_heal.json"],
             "artifact": "L03_heal.json",
             "assert": lambda d: d.get("ok") and d.get("converged")
             and d.get("final", {}).get("severity") == "critical"
             and d.get("final", {}).get("status") == "investigating"},
        ],
    },
    2: {
        "title": "第二轮 · 领域账本 / 质感去劣化 / 横向决策",
        "stages": [
            {"id": "L04", "name": "SRE_SPEC 账本 + 8 维发布门禁",
             "argv": ["evolve", "spec", "--artifact", "{dir}/L04_artifact.json",
                      "--export-dir", "{dir}/gates", "--out", "{dir}/L04_spec.json"],
             "artifact": "L04_spec.json",
             "assert": lambda d: d.get("ok") and d.get("spec", {}).get("gates_count") == 8
             and d.get("compliance", {}).get("passed") == 8},
            {"id": "L05", "name": "假大空清洗 + 量化证据 + DRI",
             "argv": ["evolve", "slop", "--text",
                      "整体稳定，运行正常，持续关注，视情况而定，相关细节待定，基本可用",
                      "--out", "{dir}/L05_slop.json"],
             "artifact": "L05_slop.json",
             "assert": lambda d: d.get("ok")
             and d.get("before", {}).get("hit_count", 0) >= 5
             and d.get("after", {}).get("verdict") == "PASS"
             and d.get("after", {}).get("actionability", 0) >= 85},
            {"id": "L06", "name": "三维处置方案 + MCDA 权衡",
             "argv": ["evolve", "scenario", "--service", "支付服务", "--severity", "critical",
                      "--out", "{dir}/L06_scenario.json", "--md", "{dir}/L06_scenario.md"],
             "artifact": "L06_scenario.json",
             "assert": lambda d: d.get("ok") and len(d.get("scenarios", [])) == 3
             and abs(sum(d.get("weights", {}).values()) - 1.0) < 1e-6
             and bool(d.get("recommended"))},
        ],
    },
    3: {
        "title": "第三轮 · 伴生消费 / 局部差量 / 会话记忆 / 工业容灾",
        "stages": [
            {"id": "L07", "name": "Bundle / SARIF 2.1.0 / Vega-Lite",
             "argv": ["evolve", "bundle", "--run-id", "R20-R3",
                      "--out-dir", "{dir}/bundles", "--out", "{dir}/L07_bundle.json"],
             "artifact": "L07_bundle.json",
             "assert": lambda d: d.get("ok") and len(d.get("files", [])) == 3
             and all(len(v) == 64 for v in (d.get("fingerprints") or {}).values())},
            {"id": "L08", "name": "RFC 6902 差量热修 + 不变量复核",
             "argv": ["evolve", "patch", "--out", "{dir}/L08_patch.json"],
             "artifact": "L08_patch.json",
             "assert": lambda d: d.get("ok") and d.get("op_count", 0) >= 1
             and d.get("invariants_after", {}).get("ok")
             and d.get("monitor_invariants", {}).get("ok")},
            {"id": "L09", "name": "持久记忆 + 代词消歧 + 回滚",
             "argv": ["evolve", "memory", "--query",
                      "按刚才第二套方案调整，把上次那个服务的阈值调高0.05",
                      "--out", "{dir}/L09_memory.json"],
             "artifact": "L09_memory.json",
             "assert": lambda d: d.get("ok")
             and len(d.get("disambiguation", {}).get("resolved", [])) >= 3
             and d.get("rollback", {}).get("ok")},
            {"id": "L10", "name": "三态熔断 + 全抖动退避 + 全链路遥测",
             "argv": ["evolve", "watchdog", "--out", "{dir}/L10_telemetry.json"],
             "artifact": "L10_telemetry.json",
             "assert": lambda d: d.get("status") == "HEALTHY" and d.get("ok")
             and bool(d.get("backoff_samples")),
             "post": "telemetry.jsonl"},
        ],
    },
}


# --------------------------------------------------------------------------- #
# 状态
# --------------------------------------------------------------------------- #
def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def load_state() -> Dict[str, Any]:
    if os.path.isfile(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "rounds" in data:
                return data
        except (OSError, ValueError):
            pass
    return {"role": ROLE, "sop_version": SOP_VERSION, "current_round": 0,
            "rounds": {}, "updated_at": None}


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(WORKSPACE, exist_ok=True)
    state["updated_at"] = _now()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# 子进程
# --------------------------------------------------------------------------- #
def run_agent(*argv: str, timeout: int = 180) -> Dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    proc = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *argv],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env, timeout=timeout)
    elapsed = int((time.time() - t0) * 1000)
    payload: Dict[str, Any] = {}
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            try:
                payload = json.loads(line[len("__AGENT_RESULT__ "):])
            except ValueError:
                payload = {"_parse_error": line[:400]}
    return {"exit_code": proc.returncode, "result": payload,
            "stdout_tail": (proc.stdout or "")[-1500:],
            "stderr_tail": (proc.stderr or "")[-1500:], "elapsed_ms": elapsed,
            "argv": list(argv)}


def run_regression(path: str, timeout: int = 600) -> Dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.time()
    proc = subprocess.run([sys.executable, path], cwd=HERE, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env,
                          timeout=timeout)
    out = proc.stdout or ""
    err = proc.stderr or ""
    combined = out + "\n" + err
    total = passed = None
    m = re.search(r"通过\s*(\d+)\s*/\s*(\d+)", combined)
    if m:
        passed, total = int(m.group(1)), int(m.group(2))
    m = re.search(r"Ran\s+(\d+)\s+tests", combined)
    if m:
        total = int(m.group(1))
        passed = total if "FAILED" not in combined else None
    return {"path": os.path.relpath(path, HERE), "exit_code": proc.returncode,
            "passed": passed, "total": total,
            "elapsed_ms": int((time.time() - t0) * 1000),
            "stdout_tail": out[-1200:], "stderr_tail": err[-800:]}


# --------------------------------------------------------------------------- #
# 轮次执行
# --------------------------------------------------------------------------- #
def _prepare_inputs(rnd: int, rdir: str) -> List[str]:
    os.makedirs(rdir, exist_ok=True)
    written: List[str] = []
    if rnd == 1:
        path = os.path.join(rdir, "L03_input.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"severity": "P1", "status": "进行中",
                       "summary": "支付服务告警抖动，需生成恢复计划",
                       "checks": [{"ok": True, "dim": "alert", "msg": "告警已触发"}]},
                      f, ensure_ascii=False, indent=2)
        written.append(path)
    if rnd == 2:
        from engines import R20SpecLedger
        path = os.path.join(rdir, "L04_artifact.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(R20SpecLedger().demo_artifact(), f, ensure_ascii=False, indent=2)
        written.append(path)
    return written


def run_round(rnd: int, verbose: bool = True) -> Dict[str, Any]:
    if rnd not in ROUNDS:
        raise SystemExit(f"未知轮次: {rnd}（可选 1/2/3）")
    spec = ROUNDS[rnd]
    rdir = os.path.join(ROUNDS_DIR, f"round{rnd}")
    os.makedirs(rdir, exist_ok=True)
    inputs = _prepare_inputs(rnd, rdir)
    stages: List[Dict[str, Any]] = []

    if verbose:
        print(f"\n=== Round {rnd} · {spec['title']} ===")
    for st in spec["stages"]:
        argv = [a.replace("{dir}", rdir) for a in st["argv"]]
        run = run_agent(*argv)
        artifact_path = os.path.join(rdir, st["artifact"])
        data: Dict[str, Any] = {}
        if os.path.isfile(artifact_path):
            try:
                with open(artifact_path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = {}
        try:
            evidence_ok = bool(st["assert"](data))
        except Exception as exc:  # 证据断言异常同样判失败
            evidence_ok = False
            data = {"_assert_error": f"{type(exc).__name__}: {exc}"}
        ok = run["exit_code"] == 0 and evidence_ok
        stage = {"id": st["id"], "name": st["name"], "ok": ok,
                 "exit_code": run["exit_code"], "elapsed_ms": run["elapsed_ms"],
                 "artifact": os.path.relpath(artifact_path, HERE),
                 "artifact_bytes": os.path.getsize(artifact_path)
                 if os.path.isfile(artifact_path) else 0,
                 "evidence_ok": evidence_ok,
                 "argv": argv}
        if st.get("post"):
            post_path = os.path.join(WORKSPACE, st["post"])
            stage["post_artifact"] = os.path.relpath(post_path, HERE)
            stage["post_ok"] = os.path.isfile(post_path)
            ok = ok and stage["post_ok"]
            stage["ok"] = ok
        if not ok and run.get("stderr_tail"):
            stage["stderr_tail"] = run["stderr_tail"]
        stages.append(stage)
        if verbose:
            print(f"  [{'PASS' if ok else 'FAIL'}] {st['id']} {st['name']} "
                  f"({run['elapsed_ms']}ms)")

    legacy = run_regression(os.path.join(HERE, "run_tests.py"))
    evolution = run_regression(os.path.join(HERE, "tests", "test_evolution_l01_l10.py"))
    release = "release"
    regression = {"legacy": legacy, "evolution": evolution,
                  "release_artifact": release}
    zero_regression = (legacy["exit_code"] == 0 and evolution["exit_code"] == 0
                       and all(s["ok"] for s in stages))
    gate = {
        "role": ROLE, "sop_version": SOP_VERSION, "round": rnd,
        "title": spec["title"], "generated_at": _now(),
        "stages": stages, "inputs": [os.path.relpath(x, HERE) for x in inputs],
        "regression": regression,
        "zero_regression": zero_regression,
        "decision": "PASS" if zero_regression else "FAIL",
        "failed_stages": [s["id"] for s in stages if not s["ok"]],
        "rollback": "保留上一轮 gate.json 与 workspace/bundles；"
                    "代码回退至 git 上一提交，状态文件 round 字段回退 1。",
    }
    gate_path = os.path.join(rdir, "gate.json")
    with open(gate_path, "w", encoding="utf-8") as f:
        json.dump(gate, f, ensure_ascii=False, indent=2)

    state = load_state()
    state["rounds"][str(rnd)] = {
        "round": rnd, "title": spec["title"], "decision": gate["decision"],
        "completed_at": _now(), "gate": os.path.relpath(gate_path, HERE),
        "stages": {s["id"]: ("PASS" if s["ok"] else "FAIL") for s in stages},
        "legacy": {"passed": legacy["passed"], "total": legacy["total"]},
        "evolution": {"passed": evolution["passed"], "total": evolution["total"]},
    }
    if zero_regression:
        state["current_round"] = max(state.get("current_round", 0), rnd)
    save_state(state)

    if verbose:
        print(f"  legacy={legacy['passed']}/{legacy['total']} "
              f"evolution={evolution['passed']}/{evolution['total']} "
              f"=> {gate['decision']}")
    return gate


def run_all(verbose: bool = True) -> Dict[str, Any]:
    state = load_state()
    results = []
    for rnd in (1, 2, 3):
        prev = state["rounds"].get(str(rnd))
        if prev and prev.get("decision") == "PASS":
            if verbose:
                print(f"Round {rnd} 已完成且 PASS，跳过（--stage {rnd} 可强制重跑）")
            results.append({"round": rnd, "decision": "SKIP"})
            continue
        gate = run_round(rnd, verbose)
        results.append({"round": rnd, "decision": gate["decision"]})
        if gate["decision"] != "PASS":
            if verbose:
                print(f"Round {rnd} 未通过，停止推进（零回归门禁）。")
            break
    return {"ok": all(r["decision"] in ("PASS", "SKIP") for r in results),
            "results": results, "state": load_state()}


def print_status() -> int:
    state = load_state()
    print(f"R20 SOP v{SOP_VERSION} 自动演进状态")
    print(f"  current_round = {state.get('current_round', 0)} / 3")
    print(f"  state_file    = {os.path.relpath(STATE_PATH, HERE)}")
    for rnd in (1, 2, 3):
        rec = state["rounds"].get(str(rnd))
        if not rec:
            print(f"  Round {rnd}: PENDING")
            continue
        print(f"  Round {rnd}: {rec['decision']}  legacy={rec['legacy']} "
              f"evolution={rec['evolution']}")
        for sid, status in rec["stages"].items():
            print(f"      {sid}: {status}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R20 SOP v13.0 自动演进执行器")
    ap.add_argument("--stage", type=int, default=0, choices=[0, 1, 2, 3])
    ap.add_argument("--round", type=int, default=0, choices=[0, 1, 2, 3])
    ap.add_argument("--run-all", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    rnd = args.stage or args.round
    verbose = not args.quiet

    if args.status:
        return print_status()
    if rnd:
        gate = run_round(rnd, verbose)
        return 0 if gate["decision"] == "PASS" else 1
    if args.run_all:
        out = run_all(verbose)
        return 0 if out["ok"] else 1
    return print_status()


if __name__ == "__main__":
    raise SystemExit(main())
