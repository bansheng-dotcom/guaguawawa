#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py - R07 蛙得明 · 产品经理 十轮渐进式演进物理调度执行器。

严格贯彻《SOP_AGENT_EVOLUTION_UNIVERSAL.md》：
1. 真正的 10 轮分步执行状态机 (Round 1 -> Round 10)，`--stage` 对齐三大批次；
2. 每一轮包含完整的五步闭环：
   - 步骤 1: 穿透体检 (Reality Audit)
   - 步骤 2: 标杆对齐 (Benchmark Sourcing)
   - 步骤 3: 架构跃迁与引擎装配 (Architectural Upgrade)
   - 步骤 4: 物理工件生成与命令级探针校验 (Physical Artifact Validation)
   - 步骤 5: 双轨零破坏回归门禁 (Legacy run_tests.py + Evolution pytest + 闭环矩阵)
3. 状态机记录落盘至 workspace/evolution_state.json，每轮独立打卡；任一步失败即熔断，
   绝不把「上一轮的绿灯」当作本轮通过。

用法：
    python auto_evolve_runner.py --status            # 查看当前演进轮次状态
    python auto_evolve_runner.py --stage 1|2|3       # 执行指定阶段批次 (L01-03 / L04-06 / L07-10)
    python auto_evolve_runner.py --round N           # 仅执行指定第 N 轮演进
    python auto_evolve_runner.py --run-all           # 自动连续推进未完成的全部轮次
    python auto_evolve_runner.py --reset             # 重置演进状态机
"""
from __future__ import annotations

import argparse
import datetime
import json
import os

import subprocess
import sys
# --- 引导仓库根入 sys.path：本文件可被直接 `python xxx.py` 执行 ---
_boot = os.path.dirname(os.path.abspath(__file__))
while _boot and not os.path.isdir(os.path.join(_boot, "core")):
    _boot = os.path.dirname(_boot)
if _boot and _boot not in sys.path:
    sys.path.insert(0, _boot)
from core.workspace import role_workspace  # noqa: E402
import time
from typing import Any, Dict, List, Optional, Tuple

# Windows 终端 Unicode 编码安全防御
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for p in (HERE, AGENTS, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

WS = os.path.join(role_workspace(HERE))
STATE_FILE = os.path.join(WS, "evolution_state.json")
TMP_DIR = os.path.join(WS, "tmp")
BUNDLES_DIR = os.path.join(WS, "bundles")

STAGE_BATCHES = {
    1: {"name": "执行基石 (L01~L03)", "rounds": [1, 2, 3]},
    2: {"name": "专业深度 (L04~L06)", "rounds": [4, 5, 6]},
    3: {"name": "工业交付 (L07~L10)", "rounds": [7, 8, 9, 10]},
}

# 10 轮阶梯元模型定义（特化于 R07 产品经理 PM），verify_cmd 均为真实可执行探针。
EVOLUTION_STAGES: List[Dict[str, Any]] = [
    {
        "round": 1,
        "layer": "L01",
        "name": "工具实体层 (Real PM Sandbox & Deterministic Calculation Engine)",
        "audit": "技能层是否真算：RICE/ICE/Opportunity 是否由真实算子计算而非回填固定分；"
                 "PRD 八门禁、Backlog、发布门禁是否逐条判据而非恒真。",
        "bench": "Productboard / Aha! / OpenHands (Stars > 15k)",
        "bench_tokens": ["productboard", "airfocus"],
        "engine_module": "engines.pm_runtime_engine",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "probe"],
        "artifacts": [],
        "probe_expect": "PMRuntimeEngine 健康探针 healthy",
    },
    {
        "round": 2,
        "layer": "L02",
        "name": "意图解构层 (Intent Decompiler & Agile Delivery DAG)",
        "audit": "复合需求能否解构为 Kahn 拓扑 DAG 与工时估算，而非关键词硬匹配。",
        "bench": "DSPy / Ray DAG (Stars > 20k)",
        "bench_tokens": ["dspy", "ray dag"],
        "engine_module": "engines.intent_dag_compiler",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "decompile", "--query",
                       "提升企业客户协作效率，完成JTBD调研与PRD故事拆解，制定RICE优先级与里程碑路线图"],
        "artifacts": [],
        "probe_expect": "5 节点 Kahn DAG + 工时估算",
    },
    {
        "round": 3,
        "layer": "L03",
        "name": "自愈反思层 (Reflexive Healing & Critic Layer)",
        "audit": "PRD 缺陷能否就地自愈；越界拍板 / 越界写工程实现的红线是否硬拦截。",
        "bench": "Reflexion / Critic-Agent / OpenHands (Stars > 40k)",
        "bench_tokens": ["reflexion", "openhands"],
        "engine_module": "engines.pm_reflexive_healer",
        "verify_cmd": [sys.executable, "-c",
                       "from engines import PMReflexiveHealer; h=PMReflexiveHealer(); "
                       "r=h.audit_redlines({'title':'t','executive_summary':'必须由我拍板决定'}); "
                       "assert len(r)>=1, r; "
                       "g=h.audit_and_heal('prd',{'title':'t','executive_summary':'立即上线','acceptance_criteria':[]}); "
                       "assert g['is_healed']; print('L03 Critic OK')"],
        "artifacts": [],
        "probe_expect": "红线拦截 + 自愈补齐",
    },
    {
        "round": 4,
        "layer": "L04",
        "name": "领域账本层 (Domain Spec Ledger & PM SSOT)",
        "audit": "JTBD 准则、RICE 量纲、PRD 八门禁、OKR 3x3、埋点契约、发布 SLA 是否唯一 SSOT。",
        "bench": "Productboard / Pragmatic Institute / dbt MetricFlow (Stars > 15k)",
        "bench_tokens": ["productboard", "metricflow"],
        "engine_module": "engines.pm_spec_ledger",
        "verify_cmd": [sys.executable, "-c",
                       "from engines.pm_spec_ledger import PMSpecLedger; "
                       "l=PMSpecLedger(); spec=l.load_spec(); "
                       "assert spec['spec_loaded']; "
                       "assert len(spec['rules']['prd_gates'])==8; "
                       "print('L04 Spec Ledger OK')"],
        "artifacts": [],
        "probe_expect": "PM_SPEC.md 动态加载 + 8 门禁",
    },
    {
        "round": 5,
        "layer": "L05",
        "name": "质感去劣化 (PM Slop Guard & Anti-Hallucination)",
        "audit": "PRD 中的假大空/占位/不可验收措辞能否被物理拦截并替换为量化判据。",
        "bench": "reviewdog / StyleGuide / Vale (Stars > 10k)",
        "bench_tokens": ["reviewdog", "vale"],
        "engine_module": "engines.pm_slop_guard",
        "verify_cmd": [sys.executable, "-c",
                       "from engines.pm_slop_guard import PMSlopGuard; "
                       "g=PMSlopGuard(); r=g.audit_text('优化性能并提升用户体验'); "
                       "assert not r['is_clean']; print('L05 SlopGuard OK')"],
        "artifacts": [],
        "probe_expect": "套话拦截 + 量化替换",
    },
    {
        "round": 6,
        "layer": "L06",
        "name": "横向决策层 (Comparative Scenario Matrix Layer)",
        "audit": "需求输出是否只有一锤子方案，缺少【极简/基准/旗舰】横向权衡与 ROI 矩阵。",
        "bench": "Stylescapes / Scenario Planning / MCDA (Stars > 5k)",
        "bench_tokens": ["stylescapes", "mcda"],
        "engine_module": "engines.scenario_matrix",
        "verify_cmd": [sys.executable, "-c",
                       "from engines.scenario_matrix import ScenarioMatrix; "
                       "m=ScenarioMatrix(); r=m.generate_matrix('AI写作','提升创作效率'); "
                       "assert len(r['scenarios'])==3; assert 'tradeoff_matrix' in r; "
                       "print('L06 Scenario Matrix OK')"],
        "artifacts": [],
        "probe_expect": "三方案 + ROI 权衡矩阵",
    },
    {
        "round": 7,
        "layer": "L07",
        "name": "伴生消费层 (Downstream Consumption & Asset Bundle)",
        "audit": "PRD 是否只有 Markdown，下游 R08/R09 无法机器解析；缺 SARIF/AST/Vega 伴生件。",
        "bench": "microsoft/sarif-tools (SARIF 2.1.0) / vega-lite (Stars > 1k)",
        "bench_tokens": ["sarif-tools", "vega-lite"],
        "engine_module": "engines.asset_bundle",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "bundle",
                       "--input", "examples/prd.json", "--out-dir", BUNDLES_DIR],
        "artifacts": [
            os.path.join(BUNDLES_DIR, "prd_bundle.json"),
            os.path.join(BUNDLES_DIR, "prd_ast.json"),
            os.path.join(BUNDLES_DIR, "prd_audit.sarif.json"),
            os.path.join(BUNDLES_DIR, "prd_gates_chart.vega.json"),
            os.path.join(BUNDLES_DIR, "artifact_manifest.json"),
        ],
        "probe_expect": "4 件伴生工件落盘 + SHA256 内容寻址",
    },
    {
        "round": 8,
        "layer": "L08",
        "name": "局部差量层 (RFC 6902 PRD Differential Patch)",
        "audit": "改一条验收标准就要全量重生成 PRD，无法保留已确认部分，重复消耗高。",
        "bench": "RFC 6902 (JSON Patch) / diff-match-patch (Stars > 8k)",
        "bench_tokens": ["rfc 6902", "diff-match-patch"],
        "engine_module": "engines.diff_patch_engine",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "patch",
                       "--input", "examples/prd.json",
                       "--ops", "examples/prd_patch_ops.json",
                       "--out-dir", os.path.join(WS, "patched")],
        "artifacts": [os.path.join(WS, "patched", "prd_patched.json"),
                      os.path.join(WS, "patched", "prd_patch.diff.json")],
        "probe_expect": "RFC 6902 增量补丁 + 未改动字段零漂移",
    },
    {
        "round": 9,
        "layer": "L09",
        "name": "会话记忆层 (Persistent Session State & Disambiguation)",
        "audit": "多轮需求对话里「按刚才第二套方案」这类代词无法消歧，跨会话彻底失忆。",
        "bench": "MemGPT (Letta) / LangGraph State Store (Stars > 15k)",
        "bench_tokens": ["memgpt", "langgraph"],
        "engine_module": "engines.session_memory",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "session",
                       "--self-test"],
        "artifacts": [os.path.join(WS, "session_state.json")],
        "probe_expect": "代词消歧 + 快照树 + 一键回滚",
    },
    {
        "round": 10,
        "layer": "L10",
        "name": "工业容灾层 (Watchdog Circuit Breaker & Telemetry)",
        "audit": "外部依赖抖动/超时直接瘫痪，无熔断三态、无退避重试、无全链路遥测。",
        "bench": "Temporal / OpenTelemetry / Tenacity (Stars > 25k)",
        "bench_tokens": ["temporal", "opentelemetry", "tenacity"],
        "engine_module": "engines.telemetry_watchdog",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "watchdog", "--self-test"],
        "artifacts": [os.path.join(WS, "telemetry.jsonl")],
        "probe_expect": "CLOSED/OPEN/HALF_OPEN 三态 + 抖动退避 + telemetry.jsonl",
    },
]


# --------------------------------------------------------------------------- #
# 状态机持久化
# --------------------------------------------------------------------------- #
def _empty_state() -> Dict[str, Any]:
    return {
        "agent": "r07-wademing-pm",
        "initialized_at": datetime.datetime.now().isoformat(),
        "current_round": 0,
        "completed_rounds": [],
        "round_history": [],
    }


def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            completed = [int(r) for r in state.get("completed_rounds", [])]
            state["completed_rounds"] = sorted(set(completed))
            # 自愈：历史状态里 current_round 可能落后于 completed_rounds
            state["current_round"] = max(completed) if completed else 0
            # 历史卫生：同一轮只保留最新一条，旧记录缺字段时补齐
            history: Dict[int, Dict[str, Any]] = {}
            completed_set = set(state["completed_rounds"])
            for item in state.get("round_history", []):
                if not isinstance(item, dict):
                    continue
                num = int(item.get("round", 0) or 0)
                if num <= 0:
                    continue
                # 未在 completed_rounds 里的历史条目不得默认为 PASSED
                item["status"] = item.get("status") if num in completed_set else "UNKNOWN"
                item.setdefault("pytest_summary", "")
                item.setdefault("artifacts", [])
                history[num] = item
            state["round_history"] = [history[k] for k in sorted(history)]
            return state
        except Exception:
            pass
    return _empty_state()


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


# --------------------------------------------------------------------------- #
# 子进程执行与门禁
# --------------------------------------------------------------------------- #
def run_cmd(argv: List[str], timeout: int = 300) -> Tuple[int, str, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        proc = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", f"探针超时 {timeout}s: {' '.join(argv)}"
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _tail(text: str, lines: int = 6) -> str:
    rows = [r for r in text.strip().splitlines() if r.strip()]
    return "\n".join(rows[-lines:])


def _engine_source(module_name: str) -> Tuple[Optional[str], str]:
    """定位引擎源码文件并读回文本（供步骤 1/2 做真实校验，而非恒真打印）。"""
    import importlib.util
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, AttributeError, ValueError):
        return None, ""
    if spec is None or not spec.origin or not os.path.isfile(spec.origin):
        return None, ""
    try:
        with open(spec.origin, "r", encoding="utf-8") as fh:
            return spec.origin, fh.read()
    except OSError:
        return None, ""


def _audit_gate(stage: Dict[str, Any]) -> Dict[str, Any]:
    """步骤 1 真实体检：引擎源码必须存在、非空壳，探针命令必须可执行。"""
    path, source = _engine_source(stage["engine_module"])
    checks = {
        "engine_file_exists": bool(path),
        "engine_lines_ge_50": len([ln for ln in source.splitlines() if ln.strip()]) >= 50,
        "probe_command_declared": bool(stage.get("verify_cmd")),
        "audit_note_declared": len(str(stage.get("audit", "")).strip()) >= 10,
    }
    return {"ok": all(checks.values()), "checks": checks,
            "engine_source": path, "source_lines": len(source.splitlines()),
            "detail": stage["audit"]}


def _benchmark_gate(stage: Dict[str, Any]) -> Dict[str, Any]:
    """步骤 2 真实对标：引擎源码必须显式引用该开源标杆（防止「只写报告不落地」）。"""
    path, source = _engine_source(stage["engine_module"])
    low = source.lower()
    tokens = [t.lower() for t in stage.get("bench_tokens", [])]
    hits = {t: (t in low) for t in tokens}
    return {"ok": bool(path) and bool(tokens) and all(hits.values()),
            "benchmark": stage["bench"], "token_hits": hits,
            "engine_source": path}


def run_dual_regression(verbose: bool = True) -> Dict[str, Any]:
    """双轨零破坏回归门禁。

    轨道 A（历史契约）：run_tests.py 端到端验收 + pytest tests/ 单元与集成测试；
    轨道 B（演进契约）：verify_loop.py 29 动作 × 干净/脏 双向闭环矩阵。
    """
    gates = [
        ("legacy_run_tests", [sys.executable, "run_tests.py"]),
        ("evolution_pytest", [sys.executable, "-m", "pytest", "tests", "-q"]),
        ("closed_loop_matrix", [sys.executable, "verify_loop.py"]),
    ]
    report: Dict[str, Any] = {"gates": {}, "ok": True}
    for name, cmd in gates:
        rc, out, err = run_cmd(cmd)
        merged = (out or "") + ("\n" + err if err else "")
        passed = rc == 0
        report["gates"][name] = {"ok": passed, "rc": rc, "tail": _tail(merged, 4)}
        report["ok"] = report["ok"] and passed
        if verbose:
            mark = "✅" if passed else "❌"
            print(f"   {mark} {name}: rc={rc}")
            if not passed:
                print("      " + _tail(merged, 8).replace("\n", "\n      "))
    # 结果摘要行（用于报告取证）
    pytest_tail = report["gates"]["evolution_pytest"]["tail"]
    report["pytest_summary"] = pytest_tail.splitlines()[-1] if pytest_tail else ""
    legacy_tail = report["gates"]["legacy_run_tests"]["tail"]
    report["legacy_summary"] = legacy_tail.splitlines()[-1] if legacy_tail else ""
    return report


def _check_artifacts(paths: List[str], since: float = 0.0) -> Tuple[bool, List[Dict[str, Any]]]:
    """工件验收：必须存在、非空，且是本轮探针新生成（mtime >= 探针开始时间）。"""
    rows: List[Dict[str, Any]] = []
    ok = True
    for path in paths:
        exists = os.path.isfile(path)
        size = os.path.getsize(path) if exists else 0
        mtime = os.path.getmtime(path) if exists else 0.0
        fresh = bool(exists) and (since <= 0 or mtime >= since - 2.0)
        rows.append({"path": path, "exists": exists, "bytes": size,
                     "fresh": fresh, "mtime": mtime})
        ok = ok and exists and size > 0 and fresh
    return ok, rows


def execute_round(round_num: int, verbose: bool = True) -> Dict[str, Any]:
    """执行单个具体轮次的五步闭环，返回结构化结果（不写状态）。"""
    if round_num < 1 or round_num > len(EVOLUTION_STAGES):
        return {"ok": False, "error": f"轮次超限: {round_num} (有效范围 1~10)"}
    stage = EVOLUTION_STAGES[round_num - 1]
    batch = next((n for n, b in STAGE_BATCHES.items() if round_num in b["rounds"]), 0)
    record: Dict[str, Any] = {"round": round_num, "layer": stage["layer"],
                              "name": stage["name"], "bench": stage["bench"],
                              "batch": batch, "steps": {}, "ok": False}
    if verbose:
        print("\n" + "=" * 82)
        print(f"🚀 [AUTO-EVOLVE] 第 {round_num:02d}/10 轮升级 · 批次 {batch} · {stage['layer']}")
        print(f"   阶梯定位: {stage['name']}")
        print(f"   开源对标: {stage['bench']}")
        print("=" * 82)

    # 步骤 1: 穿透体检 (Reality Audit) —— 校验引擎源码真实存在且非空壳
    audit = _audit_gate(stage)
    if verbose:
        print("[步骤 1/5] 穿透体检 (Reality Audit)")
        print(f"   审查要点: {stage['audit']}")
        print(f"   源码校验: {'✅' if audit['ok'] else '❌'} {audit['engine_source']}"
              f" ({audit['source_lines']} 行)")
        if not audit["ok"]:
            print(f"   未通过项: {[k for k, v in audit['checks'].items() if not v]}")
    record["steps"]["audit"] = audit
    if not audit["ok"]:
        return record

    # 步骤 2: 标杆对齐 (Benchmark Sourcing) —— 引擎源码必须显式引用对标项目
    benchmark = _benchmark_gate(stage)
    if verbose:
        print(f"[步骤 2/5] 标杆对齐 (Benchmark Sourcing): {stage['bench']}")
        print(f"   源码引用: {'✅' if benchmark['ok'] else '❌'} {benchmark['token_hits']}")
    record["steps"]["benchmark"] = benchmark
    if not benchmark["ok"]:
        return record

    # 步骤 3: 架构跃迁与引擎装配
    module_name = stage["engine_module"]
    try:
        __import__(module_name)
        engine_ok = True
        detail = f"引擎装配成功: {module_name}"
    except Exception as exc:  # noqa: BLE001 - 装配失败必须熔断
        engine_ok = False
        detail = f"引擎装配失败: {module_name}: {exc}"
    if verbose:
        print(f"[步骤 3/5] 架构跃迁与引擎装配: {'✅' if engine_ok else '❌'} {detail}")
    record["steps"]["upgrade"] = {"ok": engine_ok, "detail": detail}
    if not engine_ok:
        return record

    # 步骤 4: 物理工件生成与命令级探针校验
    os.makedirs(TMP_DIR, exist_ok=True)
    probe_started = time.time()
    probe_rc, probe_out, probe_err = run_cmd(stage["verify_cmd"])
    probe_ok = probe_rc == 0
    art_ok, artifacts = _check_artifacts(stage.get("artifacts", []), since=probe_started)
    step4_ok = probe_ok and art_ok
    if verbose:
        print(f"[步骤 4/5] 物理工件验收: 探针 rc={probe_rc} {'✅' if probe_ok else '❌'}"
              f" / 工件 {'✅' if art_ok else '❌'} ({len(artifacts)} 项)")
        if probe_out.strip():
            print("   " + _tail(probe_out, 2).replace("\n", "\n   "))
        if not probe_ok and probe_err.strip():
            print("   " + _tail(probe_err, 6).replace("\n", "\n   "))
    record["steps"]["artifact"] = {
        "ok": step4_ok,
        "probe_rc": probe_rc,
        "probe_expect": stage.get("probe_expect", ""),
        "probe_tail": _tail(probe_out, 2),
        "artifacts": artifacts,
    }
    if not step4_ok:
        return record

    # 步骤 5: 双轨零破坏回归门禁
    if verbose:
        print("[步骤 5/5] 双轨零破坏回归门禁 (Legacy + Evolution + Closed-Loop)")
    regression = run_dual_regression(verbose=verbose)
    record["steps"]["regression"] = regression
    if not regression["ok"]:
        return record

    record["ok"] = True
    record["completed_at"] = datetime.datetime.now().isoformat()
    record["status"] = "PASSED"
    record["pytest_summary"] = regression.get("pytest_summary", "")
    record["legacy_summary"] = regression.get("legacy_summary", "")
    _emit_round_telemetry(record, regression)
    if verbose:
        print(f"\n🎉 第 {round_num:02d} 轮（{stage['layer']}）五步闭环全绿")
    return record


def _emit_round_telemetry(record: Dict[str, Any], regression: Dict[str, Any]) -> None:
    """把本轮真实门禁结论写入 telemetry.jsonl（状态由 rc 推导，父 span 同源）。"""
    try:
        from engines.telemetry_watchdog import TelemetryTracer
        tracer = TelemetryTracer()
        gates = regression.get("gates", {})
        status = "OK" if regression.get("ok") and record.get("ok") else "ERROR"
        try:
            with tracer.span(
                    f"evolve.round.{record['round']}",
                    payload={"layer": record["layer"], "ok": record["ok"]},
                    attributes={"batch": record.get("batch"),
                                "round": record["round"]}):
                for name, info in gates.items():
                    tracer.log(f"gate.{name}",
                               status="OK" if info.get("ok") else "ERROR",
                               payload={"rc": info.get("rc")},
                               attributes={"round": record["round"]})
                if status != "OK":
                    # 让父 span 与子 span 状态一致，禁止父 OK / 子 ERROR 的矛盾链路
                    raise RuntimeError("round not ok")
        except RuntimeError:
            pass
        tracer.log("evolve.round.persisted", status=status,
                   payload={"completed_at": record.get("completed_at")},
                   attributes={"round": record["round"]})
    except Exception as exc:  # noqa: BLE001 - 遥测失败不得阻断升级主流程
        print(f"   [warn] 遥测写入失败（不阻断）：{exc}")


def commit_round(record: Dict[str, Any]) -> None:
    """仅当本轮五步全绿时才写状态机（失败不得留下打卡痕迹）。"""
    if not record.get("ok"):
        return
    state = load_state()
    rnd = int(record["round"])
    history = [h for h in state.get("round_history", [])
               if int(h.get("round", 0)) != rnd]
    history.append({
        "round": rnd,
        "layer": record["layer"],
        "name": record["name"],
        "bench": record["bench"],
        "batch": record.get("batch"),
        "completed_at": record.get("completed_at"),
        "status": "PASSED",
        "pytest_summary": record.get("pytest_summary", ""),
        "legacy_summary": record.get("legacy_summary", ""),
        "artifacts": [a["path"] for a in record["steps"]["artifact"]["artifacts"]],
    })
    state["round_history"] = history
    completed = sorted(set(state.get("completed_rounds", [])) | {rnd})
    state["completed_rounds"] = completed
    state["current_round"] = max(completed)
    state["last_updated_at"] = datetime.datetime.now().isoformat()
    save_state(state)


def print_status() -> None:
    state = load_state()
    completed = set(state.get("completed_rounds", []))
    print("=" * 82)
    print("📊 R07 蛙得明 · 十轮演进状态机看板")
    print(f"   初始化时间: {state.get('initialized_at')}")
    print(f"   当前轮次: Round {state.get('current_round')} / 10")
    print(f"   已完成轮次: {sorted(completed)}")
    print("-" * 82)
    for num, batch in STAGE_BATCHES.items():
        done = [r for r in batch["rounds"] if r in completed]
        print(f"   批次 {num} {batch['name']}: {len(done)}/{len(batch['rounds'])} 完成")
    print("-" * 82)
    for s in EVOLUTION_STAGES:
        r = s["round"]
        mark = "✅ PASSED" if r in completed else "⏳ PENDING"
        print(f"   Round {r:02d} [{s['layer']}]: {s['name'][:40]:<40} -> {mark}")
    print("=" * 82)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="R07 蛙得明 · 十轮渐进式演进物理调度执行器")
    parser.add_argument("--status", action="store_true", help="查看当前演进轮次状态")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="执行指定阶段批次")
    parser.add_argument("--round", type=int, help="执行指定轮次 (1~10)")
    parser.add_argument("--run-all", action="store_true", help="自动连续推进未完成轮次")
    parser.add_argument("--reset", action="store_true", help="重置状态机")
    parser.add_argument("--force", action="store_true",
                        help="跳过前置轮次校验（仅用于修复后的定点重跑）")
    args = parser.parse_args(argv)

    if args.reset:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print("✅ 演进状态机已重置。")
        return 0

    if args.status or not (args.stage or args.round or args.run_all):
        print_status()
        return 0

    targets: List[int] = []
    if args.round is not None:
        targets = [args.round]
    elif args.stage is not None:
        targets = [r for r in STAGE_BATCHES[args.stage]["rounds"]
                   if r not in set(load_state().get("completed_rounds", []))]
        if not targets:
            print(f"✨ 批次 {args.stage} 已全部完成。")
            print_status()
            return 0
    elif args.run_all:
        completed = set(load_state().get("completed_rounds", []))
        targets = [r for r in range(1, 11) if r not in completed]
        if not targets:
            print("✨ 10 轮演进已全部完成！")
            print_status()
            return 0

    for rnd in targets:
        completed_now = set(load_state().get("completed_rounds", []))
        if rnd > 1 and (rnd - 1) not in completed_now and not args.force:
            print(f"❌ 前置轮次 {rnd - 1} 未通过，禁止越级执行第 {rnd} 轮"
                  f"（确需定点重跑请加 --force）。")
            return 1
        record = execute_round(rnd)
        if not record.get("ok"):
            failed = [k for k, v in record.get("steps", {}).items()
                      if isinstance(v, dict) and not v.get("ok")]
            print(f"\n💥 第 {rnd} 轮熔断阻断（失败步骤: {failed or ['未知']}），"
                  f"状态机不打卡。请排查后重跑。")
            return 1
        commit_round(record)
        print(f"   📝 已落盘 {STATE_FILE}")
        time.sleep(0.3)

    print_status()
    print("🎉 目标轮次全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
