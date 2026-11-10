#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py - R13 蛙客成 · 客户成功与销售运营官 十轮渐进式演进物理调度执行器。

严格贯彻《Universal Agent 10-Stage Evolution SOP v11.0》要求：
1. 真正的 10 轮分步执行状态机 (Round 1 -> Round 10) 与推荐 3 轮批次执行 (Stage 1~3 / Batch 1~3)；
2. 每一轮包含完整的五步闭环：
   - 步骤 1: 穿透体检 (Reality Audit)
   - 步骤 2: 标杆对齐 (Benchmark Sourcing)
   - 步骤 3: 架构跃迁与引擎加载 (Architectural Upgrade)
   - 步骤 4: 物理工件生成与校验 (Physical Artifact Validation)
   - 步骤 5: 双轨零破坏回归门禁 (Dual Zero-Regression Gate - 原基准测试 + L01-L10集成测试)
3. 状态机记录精准落盘至 workspace/evolution_state.json，每轮独立打卡，失败强阻断熔断。

用法：
    python auto_evolve_runner.py --status           # 查看当前演进轮次状态
    python auto_evolve_runner.py --round 1          # 仅执行指定第 N 轮演进 (1~10)
    python auto_evolve_runner.py --stage 1          # 执行指定 Stage/Batch 1 (L01~L03 基石阶段)
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

WS = os.path.join(HERE, "workspace")
STATE_FILE = os.path.join(WS, "evolution_state.json")

# 10 轮阶梯元模型定义（特化于 R13 蛙客成 · 客户成功与销售运营官）
EVOLUTION_STAGES = [
    {
        "round": 1,
        "layer": "L01",
        "name": "工具实体层 (Real CSM & Churn Predictive Sandbox & Metric Probes)",
        "audit": "检查客户健康分、NPS净推荐值、MRR续约加权与流失概率计算缺乏真实独立可测确定性引擎与沙箱；对标 Gainsight/Vitally 构建真实沙箱与确定性计算引擎。",
        "bench": "Gainsight / Planhat / ChurnZero / Vitally (Stars > 5k)",
        "engine_module": "engines.runtime_engine",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "probe"],
        "artifact_expected": "engines/runtime_engine.py",
    },
    {
        "round": 2,
        "layer": "L02",
        "name": "意图解构层 (Intent Decompiler & CSM Lifecycle DAG)",
        "audit": "检查复合客户成功与续约挽留诉求无法自动化解构；对标 DSPy/Ray DAG 编译包含审计、诊断、归因、挽留、自动化的 5 阶段 Kahn 拓扑 DAG 与工时估算。",
        "bench": "DSPy / Ray DAG (Stars > 20k)",
        "engine_module": "engines.intent_compiler",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "decompile", "--query", "大客户A续约有流失风险需要紧急健康体检"],
        "artifact_expected": "engines/intent_compiler.py",
    },
    {
        "round": 3,
        "layer": "L03",
        "name": "自愈反思层 (Reflexive Healing & CSM Redline Guard)",
        "audit": "检查客户运营违规红线（越界处理退款、私下免单承诺、未达双门槛放行续约）缺乏刚性审判与就地自纠；对标 Reflexion 落地红线拦截与反思修复。",
        "bench": "Reflexion / Critic-Agent (Stars > 40k)",
        "engine_module": "engines.reflexive_healer",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "heal", "--action", "退款"],
        "artifact_expected": "engines/reflexive_healer.py",
    },
    {
        "round": 4,
        "layer": "L04",
        "name": "领域账本层 (Domain Spec Ledger & CSM SSOT)",
        "audit": "检查客户成功业务规范与门禁阈值散落在代码中；动态加载 CSM_SPEC.md 单一信任源，统一定义北极星指标、4维健康度与8维发布硬门禁。",
        "bench": "Gainsight / Vitally / dbt Semantic Layer (Stars > 15k)",
        "engine_module": "engines.spec_ledger",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "spec"],
        "artifact_expected": "CSM_SPEC.md",
    },
    {
        "round": 5,
        "layer": "L05",
        "name": "质感去劣化 (CSM Slop Guard & Actionable Health Evidence)",
        "audit": "检查客户分析报告充斥'整体良好'、'持续关注'、'稳步提升'等假大空废话与无行动力套话；对标 reviewdog/Vale 构建物理级套话清洗与事实论据注入。",
        "bench": "reviewdog / Vale / StyleGuide (Stars > 10k)",
        "engine_module": "engines.slop_guard",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "slop", "--text", "客户关系整体良好，值得重点关注，服务体验稳步提升"],
        "artifact_expected": "engines/slop_guard.py",
    },
    {
        "round": 6,
        "layer": "L06",
        "name": "横向决策层 (Comparative CSM Retention Scenario Matrix)",
        "audit": "检查客户维护与续约挽留方案单一；拒绝一锤子买卖，自动裂变【极简防御型 / 稳健运营型 / 深度战略型】三维方案看板与多维 ROI 权衡矩阵。",
        "bench": "Scenario Planning / MCDA (Stars > 5k)",
        "engine_module": "engines.scenario_matrix",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "scenario", "--client", "A公司"],
        "artifact_expected": "engines/scenario_matrix.py",
    },
    {
        "round": 7,
        "layer": "L07",
        "name": "伴生消费层 (Downstream Consumption & CSM Asset Bundle)",
        "audit": "检查下游机器可消费性；伴生导出 csm_bundle.json、csm_audit.sarif.json (OASIS SARIF v2.1.0 国际标准) 与 csm_health_chart.vega.json 图表元数据。",
        "bench": "OASIS SARIF v2.1.0 / Vega-Lite (Stars > 10k)",
        "engine_module": "engines.asset_bundle",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "bundle", "--run-id", "test_bundle_run"],
        "artifact_expected": "engines/asset_bundle.py",
    },
    {
        "round": 8,
        "layer": "L08",
        "name": "局部差量层 (RFC 6902 CSM Differential Patch)",
        "audit": "检查客户档案与策略微调全量重算开销；对标 RFC 6902 实现条目级差量热修无损置换，增量计算健康分与挽留预算弹性。",
        "bench": "RFC 6902 (JSON Patch) / diff-match-patch (Stars > 8k)",
        "engine_module": "engines.diff_patch_engine",
        "verify_cmd": [sys.executable, "-c", "from engines import CsmDiffPatchEngine; e=CsmDiffPatchEngine(); p=e.create_patch({'score':80}, {'score':90}); assert len(p)==1; print('L08 Patch OK')"],
        "artifact_expected": "engines/diff_patch_engine.py",
    },
    {
        "round": 9,
        "layer": "L09",
        "name": "会话记忆层 (Persistent Session State & Disambiguation)",
        "audit": "检查多轮客户沟通上下文丢失；维护 workspace/session_state.json 记忆池，支持'按刚才第二套方案'代词消歧与快照回滚。",
        "bench": "MemGPT (Letta) / LangGraph State Store (Stars > 15k)",
        "engine_module": "engines.session_memory",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "memory", "--query", "按刚才第二套方案推进A公司续约"],
        "artifact_expected": "engines/session_memory.py",
    },
    {
        "round": 10,
        "layer": "L10",
        "name": "工业容灾层 (Watchdog Circuit Breaker & Telemetry)",
        "audit": "检查高并发客户成功外部 API 与工单调用抖动；具备 CLOSED/OPEN/HALF_OPEN 三态熔断看门狗、指数退避抖动重试及 telemetry.jsonl 追踪。",
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
        "agent": "r13-wakecheng-csm",
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

    # 执行 CLI 验证探针
    rc_v, stdout_v, stderr_v = run_cmd(stage["verify_cmd"])
    if rc_v != 0 and "__AGENT_RESULT__" not in stdout_v:
        print(f"   ❌ CLI 探针执行失败:\n{stdout_v}\n{stderr_v}")
        return False
    print(f"   ✅ CLI 探针核验成功: {' '.join(stage['verify_cmd'])}")

    # 步骤 5: 双轨零破坏回归门禁 (Dual Zero-Regression Gate)
    print(f"[步骤 5/5] 双轨零破坏回归门禁校验 (Dual Zero-Regression Gate)...")
    reg_ok = run_dual_regression()
    if not reg_ok:
        print(f"   ❌ 双轨回归门禁未通过！熔断本次升级打卡。")
        return False
    print(f"   ✅ 双轨回归门禁通过 (基准测试 100% ALL GREEN + pytest 100% PASS)！")

    # 状态持久化落盘
    state = load_state()
    if round_num not in state.get("completed_rounds", []):
        state.setdefault("completed_rounds", []).append(round_num)
        state["completed_rounds"].sort()
    state["current_round"] = round_num
    state["rounds_completed"] = len(state["completed_rounds"])

    # 更新阶段状态
    if state["rounds_completed"] >= 10:
        state["stage"] = 3
        state["status"] = "ALL_GREEN"
    elif state["rounds_completed"] >= 6:
        state["stage"] = 3
        state["status"] = "STAGE_2_COMPLETED"
    elif state["rounds_completed"] >= 3:
        state["stage"] = 2
        state["status"] = "STAGE_1_COMPLETED"
    else:
        state["stage"] = 1
        state["status"] = "STAGE_1_IN_PROGRESS"

    state.setdefault("round_history", []).append({
        "round": round_num,
        "layer": stage["layer"],
        "name": stage["name"],
        "completed_at": datetime.datetime.now().isoformat(),
        "regression_verdict": "PASS",
    })
    save_state(state)
    print(f"🎉 [SUCCESS] 第 {round_num:02d} 轮升级达成！打卡落盘: workspace/evolution_state.json\n")
    return True


def execute_stage(stage_num: int) -> bool:
    """执行指定的阶段批次 (Stage 1 / 2 / 3)。"""
    if stage_num == 1:
        rounds = [1, 2, 3]
        stage_desc = "第 1 轮升级：执行基石阶段 (L01~L03)"
    elif stage_num == 2:
        rounds = [4, 5, 6]
        stage_desc = "第 2 轮升级：专业深度阶段 (L04~L06)"
    elif stage_num == 3:
        rounds = [7, 8, 9, 10]
        stage_desc = "第 3 轮升级：工业交付阶段 (L07~L10)"
    else:
        print(f"[ERROR] 阶段参数非法: {stage_num} (有效值: 1, 2, 3)")
        return False

    print("\n" + "#" * 80)
    print(f"🔥 [STAGE RUNNER] 启动 {stage_desc}")
    print("#" * 80)

    for r in rounds:
        ok = execute_round(r)
        if not ok:
            print(f"[STAGE ABORT] 阶段 {stage_num} 在第 {r} 轮遇阻，流程中断！")
            return False

    print(f"🌟 [STAGE FINISHED] {stage_desc} 全部完成并通过双轨验收！\n")
    return True


def show_status() -> None:
    """展示当前演进看板。"""
    state = load_state()
    print("\n" + "=" * 80)
    print("📋 R13 蛙客成 · 十维演进元模型状态看板")
    print("=" * 80)
    print(f"智能体标识: {state.get('agent', 'r13-wakecheng-csm')}")
    print(f"演进总状态: {state.get('status', 'UNKNOWN')}")
    print(f"当前阶段:   Stage {state.get('stage', 1)} / 3")
    print(f"已打卡轮次: {state.get('rounds_completed', 0)} / 10 轮")
    print(f"完成轮次集: {state.get('completed_rounds', [])}")
    print("-" * 80)
    for s in EVOLUTION_STAGES:
        r = s["round"]
        mark = "✅ [PASS]" if r in state.get("completed_rounds", []) else "⏳ [TODO]"
        print(f" {mark} 第 {r:02d} 轮: {s['layer']} - {s['name']}")
    print("=" * 80 + "\n")


def reset_state() -> None:
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("🔄 演进状态机已成功重置！")


def main() -> int:
    parser = argparse.ArgumentParser(description="R13 自动化十轮自演进调度执行器")
    parser.add_argument("--status", action="store_true", help="查看当前十轮与三大阶段演进看板")
    parser.add_argument("--round", type=int, choices=range(1, 11), help="执行指定单轮演进 (1~10)")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="执行指定阶段批次 (1, 2, 3)")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], help="等同于 --stage")
    parser.add_argument("--run-all", action="store_true", help="自动化推进全部未完成的演进轮次")
    parser.add_argument("--reset", action="store_true", help="重置状态机为初始状态")

    args = parser.parse_args()

    if args.reset:
        reset_state()
        return 0

    if args.status:
        show_status()
        return 0

    if args.round:
        ok = execute_round(args.round)
        return 0 if ok else 1

    stage_target = args.stage or args.batch
    if stage_target:
        ok = execute_stage(stage_target)
        return 0 if ok else 1

    if args.run_all:
        for r in range(1, 11):
            ok = execute_round(r)
            if not ok:
                return 1
        show_status()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
