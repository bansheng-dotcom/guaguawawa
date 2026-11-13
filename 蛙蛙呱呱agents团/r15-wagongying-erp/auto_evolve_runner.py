#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py - R15 蛙供应 · ERP 与供应链运营官 十轮渐进式演进物理调度执行器。

严格贯彻《Universal Agent 10-Stage Evolution SOP v12.0》要求：
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

# 10 轮阶梯元模型定义（特化于 R15 蛙供应 · ERP 与供应链运营官）
EVOLUTION_STAGES = [
    {
        "round": 1,
        "layer": "L01",
        "name": "工具实体层 (Real Supply Chain Sandbox & Inventory Conservation Probes)",
        "audit": "检查库存预计量计算、BOM配方多阶展开、采购超收校验散落在 skills/ 中，缺乏独立确定性计算沙箱；缺少可独立调用的库存守恒探针与安全库存/ROP 算子。对标 Frappe ERPNext / Odoo / Apache OFBiz 构建真实沙箱与物料守恒探针。",
        "bench": "Frappe ERPNext / Odoo / Apache OFBiz (Stars > 15k~35k)",
        "engine_module": "engines.runtime_engine",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "probe"],
        "artifact_expected": "engines/runtime_engine.py",
    },
    {
        "round": 2,
        "layer": "L02",
        "name": "意图解构层 (Intent Decompiler & Supply Chain 5-Stage Kahn DAG)",
        "audit": "检查复合供应链需求无法结构化编排与自动拓扑解构；对标 DSPy/Ray DAG 编译包含【需求审查/询比价/采购订单/生产发料/收货入库】5 阶段标准的 Kahn 拓扑交付 DAG 与工时估算。",
        "bench": "DSPy / Ray DAG (Stars > 20k)",
        "engine_module": "engines.intent_compiler",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "decompile", "--query", "紧急采购200件芯片物料，需要询价两家供应商并安排排产领料入库"],
        "artifact_expected": "engines/intent_compiler.py",
    },
    {
        "round": 3,
        "layer": "L03",
        "name": "自愈反思层 (Reflexive Healing & Supply Chain Redline Guard)",
        "audit": "检查供应链违规红线（越权代付款、负库存超发、无授权超收、私自修改历史库存账目）缺乏刚性审判与就地自纠；对标 Reflexion 落地四大红线拦截与反思修复。",
        "bench": "Reflexion / Critic-Agent (Stars > 40k)",
        "engine_module": "engines.reflexive_healer",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "heal", "--action", "代付款"],
        "artifact_expected": "engines/reflexive_healer.py",
    },
    {
        "round": 4,
        "layer": "L04",
        "name": "领域账本层 (Domain Spec Ledger & ERP Single Source of Truth)",
        "audit": "检查 8 维门禁阈值、北极星指标（IRA >= 99.8%、OTIF >= 98.0%、超收容差 0.00）散落硬编码；动态加载 ERP_SPEC.md 单一信任源，统一定义北极星指标、计算公式与 8 维发布硬门禁。",
        "bench": "dbt Semantic Layer / ERPNext Doctypes (Stars > 15k)",
        "engine_module": "engines.spec_ledger",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "spec"],
        "artifact_expected": "ERP_SPEC.md",
    },
    {
        "round": 5,
        "layer": "L05",
        "name": "质感去劣化 (Supply Slop Guard & Anti-Slop Enforcement)",
        "audit": "检查供应链报告充斥'整体良好'、'按需采购'、'视情况而定'、'相关细节待定'等假大空废话与无行动力套话；对标 reviewdog/Vale 构建物理级套话清洗与量化事实/责任人注入。",
        "bench": "reviewdog / Vale / StyleGuide (Stars > 10k)",
        "engine_module": "engines.slop_guard",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "slop", "--text", "目前库存整体良好，本月按需采购，供应商表现良好，相关细节待定。"],
        "artifact_expected": "engines/slop_guard.py",
    },
    {
        "round": 6,
        "layer": "L06",
        "name": "横向决策层 (Comparative Supply Chain Replenishment Scenario Matrix)",
        "audit": "检查采购或补货决策单一（一锤子买卖）；拒绝单一方案，自动裂变【极速敏捷版 (JIT Rush) / 稳健经济批量版 (EOQ Balanced) / 战略安全缓冲版 (Buffer Maximized)】三维方案看板与多维 ROI 权衡矩阵。",
        "bench": "Scenario Planning / MCDA (Stars > 5k)",
        "engine_module": "engines.scenario_matrix",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "scenario", "--item-code", "CPU_SERVER", "--demand", "2000"],
        "artifact_expected": "engines/scenario_matrix.py",
    },
    {
        "round": 7,
        "layer": "L07",
        "name": "伴生消费层 (Downstream Consumption & ERP Asset Bundle)",
        "audit": "检查下游机器可消费性；伴生导出 erp_bundle.json、erp_audit.sarif.json (OASIS SARIF v2.1.0 国际标准) 与 erp_inventory_chart.vega.json 图表元数据。",
        "bench": "OASIS SARIF v2.1.0 / Vega-Lite (Stars > 11k)",
        "engine_module": "engines.asset_bundle",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "bundle", "--run-id", "demo_run_bundle_01"],
        "artifact_expected": "engines/asset_bundle.py",
    },
    {
        "round": 8,
        "layer": "L08",
        "name": "局部差量层 (RFC 6902 Supply Chain Differential Patch)",
        "audit": "检查采购单/物料明细/库存调整单微调单一行项目需推倒重来；对标 RFC 6902 实现条目级差量热修无损置换与增量总额/物料守恒重算。",
        "bench": "RFC 6902 (JSON Patch) / diff-match-patch (Stars > 8k)",
        "engine_module": "engines.diff_patch_engine",
        "verify_cmd": [sys.executable, "-c", "from engines import ERPDiffPatchEngine; e=ERPDiffPatchEngine(); p=e.create_patch({'actual_qty':100}, {'actual_qty':120}); assert len(p)==1; print('L08 Patch OK')"],
        "artifact_expected": "engines/diff_patch_engine.py",
    },
    {
        "round": 9,
        "layer": "L09",
        "name": "会话记忆层 (Persistent Session State & Disambiguation)",
        "audit": "检查跨轮多会话在供应链调度上下文中失忆；维护 workspace/session_state.json 记忆池，支持'按刚才第二套方案补货'、'把刚才那批物料追加 50 件'等自然语言代词消歧与快照回滚。",
        "bench": "MemGPT (Letta) / LangGraph State Store (Stars > 15k)",
        "engine_module": "engines.session_memory",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "memory", "--query", "按刚才第二套方案补货"],
        "artifact_expected": "engines/session_memory.py",
    },
    {
        "round": 10,
        "layer": "L10",
        "name": "工业容灾层 (Watchdog Circuit Breaker & Telemetry)",
        "audit": "检查外部 ERP/WMS/供应商 EDI 接口网络抖动与超时无防线；具备 CLOSED/OPEN/HALF_OPEN 三态看门狗熔断器、指数退避全抖动重试及 telemetry.jsonl 全链路遥测追踪。",
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
        "agent": "r15-wagongying-erp",
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
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
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
    rc_probe, out_probe, err_probe = run_cmd(stage["verify_cmd"])
    if rc_probe != 0:
        print(f"   ❌ CLI 验证探针执行失败:\n{out_probe}\n{err_probe}")
        return False
    print(f"   ✅ CLI 验证探针实跑成功，物理工件符合预期。")

    # 步骤 5: 双轨零破坏回归门禁 (Dual Zero-Regression Gate)
    print(f"[步骤 5/5] 双轨零破坏回归门禁 (Dual Zero-Regression Gate)...")
    reg_ok = run_dual_regression()
    if not reg_ok:
        print(f"   ❌ 双轨回归门禁未通过，演进阻断！")
        return False
    print(f"   ✅ 双轨回归门禁 100% 通过 (原基准测试 + 演进集成测试 全绿)！")

    # 更新并持久化状态机
    state = load_state()
    if round_num not in state["completed_rounds"]:
        state["completed_rounds"].append(round_num)
        state["completed_rounds"].sort()
    state["rounds_completed"] = len(state["completed_rounds"])
    state["current_round"] = round_num
    state["stage"] = 1 if round_num <= 3 else (2 if round_num <= 6 else 3)
    state["status"] = "ALL_GREEN" if len(state["completed_rounds"]) == 10 else "IN_PROGRESS"

    history_entry = {
        "round": round_num,
        "layer": stage["layer"],
        "name": stage["name"],
        "timestamp": datetime.datetime.now().isoformat(),
        "verdict": "PASS",
    }
    state["round_history"].append(history_entry)
    save_state(state)

    print(f"\n🎉 [第 {round_num:02d} 轮演进打卡成功] 状态机已落盘至 workspace/evolution_state.json")
    return True


def execute_stage(stage_num: int) -> bool:
    """执行指定的 Stage 批次演进 (Stage 1: R1~3, Stage 2: R4~6, Stage 3: R7~10)。"""
    stage_ranges = {
        1: (1, 3, "Stage 1 / Batch 1: 执行基石阶段 (L01~L03)"),
        2: (4, 6, "Stage 2 / Batch 2: 专业深度阶段 (L04~L06)"),
        3: (7, 10, "Stage 3 / Batch 3: 工业交付阶段 (L07~L10)"),
    }
    if stage_num not in stage_ranges:
        print(f"[ERROR] 阶段批次超限: {stage_num} (有效范围 1~3)")
        return False

    start_r, end_r, label = stage_ranges[stage_num]
    print("\n" + "#" * 80)
    print(f"📦 [STAGE EXECUTION] 开始执行 {label}")
    print("#" * 80)

    for r in range(start_r, end_r + 1):
        ok = execute_round(r)
        if not ok:
            print(f"[ABORT] 阶段 {stage_num} 在第 {r} 轮失败，流水线阻断。")
            return False

    print("\n" + "#" * 80)
    print(f"🏆 [STAGE SUCCESS] {label} 全部轮次圆满通过！")
    print("#" * 80)
    return True


def print_status() -> None:
    """打印当前十维演进元模型完成看板。"""
    state = load_state()
    completed = set(state.get("completed_rounds", []))
    total_rounds = len(EVOLUTION_STAGES)

    print("\n" + "=" * 80)
    print("📈 R15 蛙供应 · ERP 与供应链运营官 十轮渐进式演进状态看板 (SOP v12.0)")
    print("=" * 80)
    print(f"当前阶段: Stage {state.get('stage', 1)} | 已完成轮次: {len(completed)} / {total_rounds} | 状态: {state.get('status', 'INIT')}")
    print("-" * 80)

    for s in EVOLUTION_STAGES:
        r = s["round"]
        is_done = r in completed
        mark = "✅ [PASS]" if is_done else "⬜ [PEND]"
        print(f"{mark} Round {r:02d} ({s['layer']}): {s['name']}")

    print("=" * 80)


def reset_state() -> None:
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            print("[INFO] 演进状态机已重置为初始状态。")
        except Exception as e:
            print(f"[WARN] 重置状态机异常: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="R15 蛙供应 十轮演进自动化调度执行器")
    parser.add_argument("--status", action="store_true", help="打印当前演进看板")
    parser.add_argument("--round", type=int, help="执行指定单轮演进 (1~10)")
    parser.add_argument("--stage", type=int, help="执行指定阶段演进 (1: L01-L03, 2: L04-L06, 3: L07-L10)")
    parser.add_argument("--run-all", action="store_true", help="自动推进全部演进阶段")
    parser.add_argument("--reset", action="store_true", help="重置演进状态机")

    args = parser.parse_args()

    if args.reset:
        reset_state()
        return 0

    if args.status:
        print_status()
        return 0

    if args.round:
        ok = execute_round(args.round)
        return 0 if ok else 1

    if args.stage:
        ok = execute_stage(args.stage)
        return 0 if ok else 1

    if args.run_all:
        for st in (1, 2, 3):
            ok = execute_stage(st)
            if not ok:
                return 1
        print_status()
        return 0

    print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
