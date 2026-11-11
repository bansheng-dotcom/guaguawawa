#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py - R12 蛙引流 · 增长运营官 十轮渐进式演进物理调度执行器。

严格贯彻《SOP_AGENT_EVOLUTION_UNIVERSAL.md v9.0》要求：
1. 真正的 10 轮分步执行状态机 (Round 1 -> Round 10) 与推荐 3 轮批次执行 (Batch 1~3 / Stage 1~3)；
2. 每一轮包含完整的五步闭环：
   - 步骤 1: 穿透体检 (Reality Audit)
   - 步骤 2: 标杆对齐 (Benchmark Sourcing)
   - 步骤 3: 架构跃迁与引擎加载 (Architectural Upgrade)
   - 步骤 4: 物理工件生成与校验 (Physical Artifact Validation)
   - 步骤 5: 双轨零破坏回归门禁 (Dual Zero-Regression Gate - 原基准测试 + L01-L10集成测试)
3. 状态机记录落盘至 workspace/evolution_state.json，每轮独立打卡，失败强阻断熔断。

用法：
    python auto_evolve_runner.py --status           # 查看当前演进轮次状态
    python auto_evolve_runner.py --round 1          # 仅执行指定第 N 轮演进 (1~10)
    python auto_evolve_runner.py --stage 1          # 执行指定 Stage/Batch 1 (L01~L03 基石阶段)
    python auto_evolve_runner.py --batch 1          # 等同于 --stage 1
    python auto_evolve_runner.py --stage 2          # 执行指定 Stage/Batch 2 (L04~L06 深度阶段)
    python auto_evolve_runner.py --stage 3          # 执行指定 Stage/Batch 3 (L07~L10 交付阶段)
    python auto_evolve_runner.py --run-all          # 自动化驱动 10 轮全打卡
    python auto_evolve_runner.py --reset            # 重置演进状态机
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
from typing import Any, Dict, List, Optional

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

# 10 轮阶梯元模型定义（特化于 R12 蛙引流 · 增长运营官）
EVOLUTION_STAGES = [
    {
        "round": 1,
        "layer": "L01",
        "name": "工具实体层 (Real Growth Experiment Sandbox & Metric Probes)",
        "audit": "检查增长指标复算、漏斗转化与显著性检验是否真实可计算；对标 PostHog/GrowthBook 构建真实沙箱与确定性计算引擎。",
        "bench": "PostHog / GrowthBook (Stars > 10k)",
        "engine_module": "engines.runtime_engine",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "probe"],
        "artifact_expected": "engines/runtime_engine.py",
    },
    {
        "round": 2,
        "layer": "L02",
        "name": "意图解构层 (Intent Decompiler & Growth DAG)",
        "audit": "检查复合增长诉求无法解构；对标 DSPy/Ray DAG 编译包含获客、留存、裂变及分析的拓扑 DAG。",
        "bench": "DSPy / Ray DAG (Stars > 20k)",
        "engine_module": "engines.intent_compiler",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "decompile", "--query", "设计全域裂变并提升留存率与ROI"],
        "artifact_expected": "engines/intent_compiler.py",
    },
    {
        "round": 3,
        "layer": "L03",
        "name": "自愈反思层 (Reflexive Healing & Redline Guard)",
        "audit": "检查无界补贴与违规刷量风险；拦截缺乏 ROI 支撑的纯现金补贴等红线行为，保障反脆弱自愈。",
        "bench": "Reflexion / Critic-Agent (Stars > 40k)",
        "engine_module": "engines.reflexive_healer",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "heal", "--action", "cash subsidy"],
        "artifact_expected": "engines/reflexive_healer.py",
    },
    {
        "round": 4,
        "layer": "L04",
        "name": "领域账本层 (Domain Spec Ledger & GROWTH SSOT)",
        "audit": "检查增长规范散落无单一信任源；动态加载 GROWTH_SPEC.md，统一定义北极星指标、8维门禁与全渠道矩阵。",
        "bench": "PostHog / dbt Semantic Layer / GrowthBook (Stars > 15k)",
        "engine_module": "engines.spec_ledger",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "spec"],
        "artifact_expected": "GROWTH_SPEC.md",
    },
    {
        "round": 5,
        "layer": "L05",
        "name": "质感去劣化 (Growth Slop Guard & Statistical Significance)",
        "audit": "检查空泛无意义夸大表述（如'显著提升'、'待定'）；强制要求置信度区间与 p<0.05 统计显著性证据。",
        "bench": "reviewdog / Vale / StyleGuide (Stars > 10k)",
        "engine_module": "engines.slop_guard",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "slop", "--text", "转化率预期将在下个季度获得显著提升"],
        "artifact_expected": "engines/slop_guard.py",
    },
    {
        "round": 6,
        "layer": "L06",
        "name": "横向决策层 (Comparative Scenario Matrix Board)",
        "audit": "检查策略输出单一缺乏权衡；自动裂变 [极速轻量 / 稳健精益 / 全域ROI平衡] 三维决策看板。",
        "bench": "Scenario Planning / MCDA (Stars > 5k)",
        "engine_module": "engines.scenario_matrix",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "scenario", "--topic", "全渠道增长获客"],
        "artifact_expected": "engines/scenario_matrix.py",
    },
    {
        "round": 7,
        "layer": "L07",
        "name": "伴生消费层 (Downstream Consumption & Growth Asset Bundle)",
        "audit": "检查下游机器可消费性；伴生导出 growth_bundle.json、growth_audit.sarif.json (OASIS SARIF v2.1.0) 与 vega_charts.json 图表元数据。",
        "bench": "OASIS SARIF v2.1.0 / Vega / OpenTelemetry (Stars > 10k)",
        "engine_module": "engines.asset_bundle",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "bundle", "--run-id", "test_bundle_run"],
        "artifact_expected": "engines/asset_bundle.py",
    },
    {
        "round": 8,
        "layer": "L08",
        "name": "局部差量层 (RFC 6902 Growth Differential Patch)",
        "audit": "检查参数微调需全量重算开销；对标 RFC 6902 实现策略参数条目级差量热修无损置换，增量计算预算与ROI弹性。",
        "bench": "RFC 6902 (JSON Patch) / diff-match-patch (Stars > 8k)",
        "engine_module": "engines.diff_patch_engine",
        "verify_cmd": [sys.executable, "-c", "from engines import GrowthDiffPatchEngine; e=GrowthDiffPatchEngine(); p=e.create_patch({'budget':1000}, {'budget':2000}); assert len(p)==1; print('L08 Patch OK')"],
        "artifact_expected": "engines/diff_patch_engine.py",
    },
    {
        "round": 9,
        "layer": "L09",
        "name": "会话记忆层 (Persistent Session State & Disambiguation)",
        "audit": "检查多轮增长决策上下文丢失；维护 workspace/session_state.json 记忆池，支持'按刚才第二套方案'代词消歧与快照回滚。",
        "bench": "MemGPT (Letta) / LangGraph State Store (Stars > 15k)",
        "engine_module": "engines.session_memory",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "memory", "--query", "按刚才第二套稳健方案执行"],
        "artifact_expected": "engines/session_memory.py",
    },
    {
        "round": 10,
        "layer": "L10",
        "name": "工业容灾层 (Watchdog Circuit Breaker & Telemetry)",
        "audit": "检查高并发增长计算与外部API抖动；具备 CLOSED/OPEN/HALF_OPEN 三态熔断看门狗、指数退避抖动重试及 telemetry.jsonl 追踪。",
        "bench": "Temporal / Tenacity / OpenTelemetry (Stars > 25k)",
        "engine_module": "engines.telemetry_watchdog",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "watchdog"],
        "artifact_expected": "engines/telemetry_watchdog.py",
    },
]


def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "agent": "r12-wayingliu-growth",
        "initialized_at": datetime.datetime.now().isoformat(),
        "stage": 1,
        "rounds_completed": 0,
        "current_round": 0,
        "completed_rounds": [],
        "round_history": [],
        "status": "INIT",
    }


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def run_cmd(argv: List[str]) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, p.stdout, p.stderr


def run_dual_regression() -> bool:
    """运行双轨零破坏回归门禁：全量基准测试 + 演进集成测试。"""
    # 1. 运行原有基准测试套件
    rc_base, stdout_base, stderr_base = run_cmd([sys.executable, "run_tests.py"])
    if rc_base != 0 or ("全绿" not in stdout_base and "通过" not in stdout_base):
        print(f"[REGRESSION FAIL] 基准测试未通过:\n{stdout_base}\n{stderr_base}")
        return False

    # 2. 运行 pytest 集成测试
    rc_pytest, stdout_pytest, stderr_pytest = run_cmd([sys.executable, "-m", "pytest", "tests"])
    if rc_pytest != 0 or "passed" not in stdout_pytest:
        print(f"[REGRESSION FAIL] pytest 测试未通过:\n{stdout_pytest}\n{stderr_pytest}")
        return False

    return True


def execute_round(round_num: int) -> bool:
    """执行单个具体轮次的演进闭环。"""
    if round_num < 1 or round_num > 10:
        print(f"[ERROR] 轮次超限: {round_num} (有效范围 1~10)")
        return False

    stage = EVOLUTION_STAGES[round_num - 1]
    print("\n" + "=" * 80)
    print(f"🚀 [AUTO-EVOLVE] 正在启动第 {round_num:02d} / 10 轮升级演进...")
    print(f"   阶梯定位: {stage['layer']} - {stage['name']}")
    print(f"   开源对标: {stage['bench']}")
    print("=" * 80)

    # 步骤 1: 穿透体检 (Reality Audit)
    print(f"[步骤 1/5] 穿透体检 (Reality Audit)...")
    print(f"   审查要点: {stage['audit']}")

    # 步骤 2: 标杆对齐 (Benchmark Sourcing)
    print(f"[步骤 2/5] 标杆对齐 (Benchmark Sourcing)...")
    print(f"   对标库: {stage['bench']}")

    # 步骤 3: 架构跃迁与引擎加载 (Architectural Upgrade)
    print(f"[步骤 3/5] 架构跃迁与引擎加载...")
    module_name = stage["engine_module"]
    try:
        __import__(module_name)
        print(f"   ✅ 核心引擎已成功装配: {module_name}")
    except ImportError as e:
        print(f"   ❌ 引擎加载失败: {module_name}, 错误: {e}")
        return False

    # 步骤 4: 物理工件生成与校验 (Physical Artifact Validation)
    print(f"[步骤 4/5] 物理工件生成与命令级探针校验...")
    expected_file = os.path.join(HERE, stage["artifact_expected"])
    if not os.path.exists(expected_file):
        print(f"   ❌ 关键物理工件缺失: {stage['artifact_expected']}")
        return False
    print(f"   ✅ 关键物理工件存在: {stage['artifact_expected']}")

    rc, stdout, stderr = run_cmd(stage["verify_cmd"])
    if rc != 0:
        print(f"   ❌ 探针命令校验失败 (exit={rc}):\n{stderr or stdout}")
        return False
    print(f"   ✅ 探针命令校验通过: {stdout.strip()[:100]}...")

    # 步骤 5: 双轨零破坏回归门禁 (Dual Zero-Regression Gate)
    print(f"[步骤 5/5] 双轨零破坏回归门禁 (Dual Zero-Regression Gate)...")
    if not run_dual_regression():
        print(f"   ❌ 回归门禁校验失败！存在破坏性变更或用例失败！")
        return False
    print(f"   ✅ 回归门禁 100% 绿灯通过！")

    # 状态机打卡落盘
    state = load_state()
    round_record = {
        "round": round_num,
        "layer": stage["layer"],
        "name": stage["name"],
        "bench": stage["bench"],
        "completed_at": datetime.datetime.now().isoformat(),
        "status": "PASSED",
    }
    state["current_round"] = round_num
    if round_num not in state.get("completed_rounds", []):
        state.setdefault("completed_rounds", []).append(round_num)
    state["rounds_completed"] = len(state["completed_rounds"])
    state["stage"] = 1 if round_num <= 3 else (2 if round_num <= 6 else 3)
    state["status"] = "ALL_GREEN" if state["rounds_completed"] >= 10 else "IN_PROGRESS"
    state.setdefault("round_history", []).append(round_record)
    save_state(state)

    print(f"\n🎉 [AUTO-EVOLVE] 第 {round_num:02d} 轮演进打卡成功！已持久化至 {STATE_FILE}\n")
    return True


def execute_batch(batch_num: int) -> bool:
    """执行推荐的 3 阶段工作流升级批次：
    Batch 1 / Stage 1: Round 1~3 (L01~L03 基石阶段)
    Batch 2 / Stage 2: Round 4~6 (L04~L06 深度阶段)
    Batch 3 / Stage 3: Round 7~10 (L07~L10 交付阶段)
    """
    batch_map = {
        1: (1, 3, "第 1 轮升级：基石阶段 (L01~L03)"),
        2: (4, 6, "第 2 轮升级：专业深度阶段 (L04~L06)"),
        3: (7, 10, "第 3 轮升级：工业交付阶段 (L07~L10)"),
    }
    if batch_num not in batch_map:
        print(f"[ERROR] 无效批次/阶段: {batch_num} (有效范围 1~3)")
        return False

    start_r, end_r, batch_name = batch_map[batch_num]
    print("\n" + "#" * 80)
    print(f"🔥 [WORKFLOW BATCH/STAGE {batch_num}] 启动 {batch_name}")
    print("#" * 80)

    for r in range(start_r, end_r + 1):
        ok = execute_round(r)
        if not ok:
            print(f"💥 批次/阶段 {batch_num} 在 Round {r} 失败熔断！")
            return False
        time.sleep(0.3)

    print(f"\n🌟 [WORKFLOW BATCH/STAGE {batch_num} COMPLETED] {batch_name} 全部阶段顺利达成 100% PASS！\n")
    return True


def print_status() -> None:
    state = load_state()
    print("=" * 80)
    print(f"📊 R12 蛙引流 · 演进状态机看板")
    print(f"   初始化时间: {state.get('initialized_at')}")
    print(f"   当前阶段 (Stage): Stage {state.get('stage', 1)} / 3")
    print(f"   完成轮数: {state.get('rounds_completed', 0)} / 10 轮")
    print(f"   整体状态: {state.get('status', 'PENDING')}")
    print(f"   已完成轮次: {state.get('completed_rounds', [])}")
    print("-" * 80)
    for s in EVOLUTION_STAGES:
        r = s["round"]
        is_done = r in state.get("completed_rounds", [])
        mark = "✅ PASSED" if is_done else "⏳ PENDING"
        print(f"   Round {r:02d} [{s['layer']}]: {s['name'][:38]:<38} -> {mark}")
    print("=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(description="R12 蛙引流 · 十轮渐进式演进物理调度执行器")
    parser.add_argument("--status", action="store_true", help="查看当前演进轮次状态")
    parser.add_argument("--round", type=int, help="执行指定轮次 (1~10)")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="执行指定阶段 (1:L01~L03, 2:L04~L06, 3:L07~L10)")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], help="等同于 --stage")
    parser.add_argument("--run-all", action="store_true", help="从当前轮次往后自动连续推进或跑满 10 轮")
    parser.add_argument("--reset", action="store_true", help="重置状态机")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print("✅ 演进状态机已重置。")
        return 0

    if args.status:
        print_status()
        return 0

    target_stage = args.stage if args.stage is not None else args.batch
    if target_stage is not None:
        ok = execute_batch(target_stage)
        return 0 if ok else 1

    if args.round is not None:
        ok = execute_round(args.round)
        return 0 if ok else 1

    if args.run_all:
        state = load_state()
        completed = set(state.get("completed_rounds", []))
        for r in range(1, 11):
            if r not in completed:
                ok = execute_round(r)
                if not ok:
                    print(f"💥 自动化演进在第 {r} 轮熔断阻断！请排查原因。")
                    return 1
                completed.add(r)
                time.sleep(0.3)
        print("🎉 全部 10 轮演进执行完毕！已达成 10 轮全打卡！")
        print_status()
        return 0

    print_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
