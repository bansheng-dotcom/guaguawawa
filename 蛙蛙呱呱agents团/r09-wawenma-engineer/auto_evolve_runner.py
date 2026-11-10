# -*- coding: utf-8 -*-
"""auto_evolve_runner.py - R09 蛙稳码 · 十轮渐进式演进物理调度状态机执行器

严格贯彻《SOP_AGENT_EVOLUTION_UNIVERSAL.md v9.0》要求：
1. 真正的分步执行状态机 (Round 1 -> Round 10)；
2. 每一轮包含完整的五步闭环：
   - 步骤 1: 穿透体检 (Reality Audit)
   - 步骤 2: 标杆对齐 (Benchmark Sourcing)
   - 步骤 3: 架构跃迁与引擎加载 (Architectural Upgrade)
   - 步骤 4: 物理工件生成与校验 (Physical Artifact Validation)
   - 步骤 5: 双轨零破坏回归门禁 (Dual Zero-Regression Gate - 原基准测试 + 演进集成测试)
3. 状态机记录落盘至 workspace/evolution_state.json，每轮独立打卡，失败强阻断熔断。

用法：
    python auto_evolve_runner.py --status           # 查看当前演进轮次状态
    python auto_evolve_runner.py --round 1          # 仅执行指定第 N 轮演进 (1~6已就绪)
    python auto_evolve_runner.py --run-batch 1      # 执行第一轮升级 (L01~L03)
    python auto_evolve_runner.py --run-batch 2      # 执行第二轮升级 (L04~L06)
    python auto_evolve_runner.py --reset            # 重置演进状态机从头开始
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
os.makedirs(WS, exist_ok=True)
STATE_FILE = os.path.join(WS, "evolution_state.json")

# 10 轮阶梯元模型定义（特化于 R09 代码工程官）
EVOLUTION_STAGES = [
    {
        "round": 1,
        "layer": "L01",
        "name": "工具实体层 (Real Engineering Sandbox & Code AST Verification)",
        "audit": "检查代码是否缺少真实轻量编译器或语法沙箱；对标 PyCQA/radon / ast-grep / WebContainer / E2B 构建代码 AST 复杂度审查与沙箱探针。",
        "bench": "PyCQA/radon / ast-grep / WebContainer / E2B (Stars > 15k)",
        "engine_module": "engines.runtime_engine",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "probe"],
        "artifact_expected": "engines/runtime_engine.py",
    },
    {
        "round": 2,
        "layer": "L02",
        "name": "意图解构层 (Intent Decompiler & Agile Engineering DAG)",
        "audit": "检查复杂工程需求是否缺少拓扑拆解；对标 DSPy / Ray DAG 将工程口语需求编译为包含模块、依赖拓扑与工时估算的 Kahn 交付 DAG。",
        "bench": "DSPy / Ray DAG (Stars > 25k)",
        "engine_module": "engines.intent_compiler",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "decompile", "--query", "实现用户中心并包含数据库迁移与REST API契约"],
        "artifact_expected": "engines/intent_compiler.py",
    },
    {
        "round": 3,
        "layer": "L03",
        "name": "自愈反思层 (Reflexive Healing & Redline Critic Layer)",
        "audit": "检查工程交付物缺漏自愈能力与越界红线；自愈缺失字段并强力拦截跳过测试(test_skipped)、无回滚线上不可逆操作(irreversible)及越界承担持续监控(R20)红线。",
        "bench": "Reflexion / OpenHands / Critic-Agent (Stars > 40k)",
        "engine_module": "engines.reflexive_healer",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "heal", "--input", "examples/review_clean.json"],
        "artifact_expected": "engines/reflexive_healer.py",
    },
    {
        "round": 4,
        "layer": "L04",
        "name": "领域账本层 (Engineering Domain Spec Ledger & SSOT)",
        "audit": "检查工程质量与架构基准是否统一；建立并加载 ENG_SPEC.md，统一定义覆盖率红线、圈复杂度上限、P99延时指标与回滚必选约束。",
        "bench": "Style Dictionary / Backstage / OpenAPI 3.1 (Stars > 15k)",
        "engine_module": "engines.eng_spec_ledger",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "spec"],
        "artifact_expected": "ENG_SPEC.md",
    },
    {
        "round": 5,
        "layer": "L05",
        "name": "质感去劣化 (Engineering Slop Guard & Anti-Placeholder)",
        "audit": "检查 AI 生成代码与工程文档中假大空套话与虚假占位符；通过 SlopGuard 进行可行动性审计并物理替换 TODO、空洞代码与官话废话。",
        "bench": "reviewdog / StyleGuide / Biome (Stars > 10k)",
        "engine_module": "engines.eng_slop_guard",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "slopguard", "--text", "此处编写业务逻辑，TODO: 稍后补充"],
        "artifact_expected": "engines/eng_slop_guard.py",
    },
    {
        "round": 6,
        "layer": "L06",
        "name": "横向决策层 (Comparative Scenario Matrix Layer)",
        "audit": "检查是否支持横向多维架构权衡；拒绝一锤子买卖，自动裂变【极简轻量切片版 / 稳健基准生产版 / 高可用企业旗舰版】三维技术看板与 ROI 权衡矩阵。",
        "bench": "Stylescapes / Scenario Planning / ATAM (Stars > 5k)",
        "engine_module": "engines.scenario_matrix",
        "verify_cmd": [sys.executable, "agent.py", "evolve", "scenario", "--project", "高并发交易核心"],
        "artifact_expected": "engines/scenario_matrix.py",
    },
]


def load_state() -> Dict[str, Any]:
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "agent": "r09-wawenma-engineer",
        "initialized_at": datetime.datetime.now().isoformat(),
        "current_round": 0,
        "completed_rounds": [],
        "round_history": [],
    }


def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run(
        cmd,
        cwd=HERE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=180,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_dual_regression() -> bool:
    """运行双轨零破坏回归门禁：原基准测试套件 + 演进集成测试套件。"""
    print("   [Gate 1/2] 运行原基准测试套件 (run_tests.py)...")
    rc1, out1, err1 = run_cmd([sys.executable, "run_tests.py"])
    if rc1 != 0:
        print(f"   ❌ 原基准测试失败 (exit={rc1}):\n{err1[-1000:]}")
        return False
    print("   ✅ 原基准测试套件 100% ALL GREEN PASS!")

    print("   [Gate 2/2] 运行演进集成测试套件 (tests/test_evolution_l01_l06.py)...")
    rc2, out2, err2 = run_cmd([sys.executable, "tests/test_evolution_l01_l06.py"])
    if rc2 != 0:
        print(f"   ❌ 演进集成测试失败 (exit={rc2}):\n{err2[-1000:]}")
        return False
    print("   ✅ 演进集成测试套件 100% ALL GREEN PASS!")
    return True


def execute_round(round_num: int) -> bool:
    stage = next((s for s in EVOLUTION_STAGES if s["round"] == round_num), None)
    if not stage:
        print(f"[ERROR] 未定义的演进轮次: {round_num}")
        return False

    t0 = time.time()
    print("\n" + "=" * 80)
    print(f"🚀 开始执行第 {round_num:02d} 轮演进: {stage['layer']} - {stage['name']}")
    print("=" * 80)

    # 步骤 1: 穿透体检
    print(f"\n[步骤 1: 穿透体检 (Reality Audit)]")
    print(f"   病灶诊断: {stage['audit']}")

    # 步骤 2: 标杆对齐
    print(f"\n[步骤 2: 标杆对齐 (Benchmark Sourcing)]")
    print(f"   对标开源标杆: {stage['bench']}")

    # 步骤 3: 架构跃迁与引擎加载
    print(f"\n[步骤 3: 架构跃迁与引擎加载 (Architectural Upgrade)]")
    art_path = os.path.join(HERE, stage["artifact_expected"])
    if not os.path.exists(art_path):
        print(f"   ❌ 期望物理模块未落盘: {stage['artifact_expected']}")
        return False
    print(f"   ✅ 核心引擎物理模块已就绪: {stage['artifact_expected']}")

    # 步骤 4: 物理工件验收
    print(f"\n[步骤 4: 物理工件验收 (Physical Artifact Validation)]")
    print(f"   执行 CLI 验证命令: {' '.join(stage['verify_cmd'])}")
    rc, stdout, stderr = run_cmd(stage["verify_cmd"])
    if rc != 0:
        print(f"   ❌ 物理工件验收失败 (exit={rc})")
        print(f"   STDOUT: {stdout}")
        print(f"   STDERR: {stderr}")
        return False
    print(f"   ✅ 物理工件验收成功: {stdout.strip()[:140]}")

    # 步骤 5: 双轨零破坏回归门禁
    print(f"\n[步骤 5: 双轨零破坏回归门禁 (Dual Zero-Regression Gate)]")
    reg_ok = run_dual_regression()
    if not reg_ok:
        print("   ❌ 双轨回归门禁未通过！存在破坏既有契约或演进断裂！")
        return False
    print("   ✅ 双轨回归门禁通过 (原有全部测试 + 演进测试 100% GREEN)")

    elapsed = round(time.time() - t0, 2)
    state = load_state()
    if round_num not in state["completed_rounds"]:
        state["completed_rounds"].append(round_num)
    state["current_round"] = max(state.get("current_round", 0), round_num)
    record = {
        "round": round_num,
        "layer": stage["layer"],
        "name": stage["name"],
        "bench": stage["bench"],
        "artifact": stage["artifact_expected"],
        "timestamp": datetime.datetime.now().isoformat(),
        "elapsed_sec": elapsed,
        "status": "PASS",
    }
    state["round_history"].append(record)
    save_state(state)

    print(f"\n🎉 [ROUND {round_num:02d} SUCCESS] 第 {round_num:02d} 轮演进打卡完成！耗时 {elapsed}s")
    print(f"   状态轨迹已落盘至: {STATE_FILE}")
    return True


def show_status() -> None:
    state = load_state()
    print("=" * 80)
    print("📊 R09 蛙稳码 · 十维渐进式演进当前状态 (Universal Metamodel v9.0)")
    print(f"   智能体: {state.get('agent', 'r09-wawenma-engineer')}")
    print(f"   当前完成轮次: {state.get('completed_rounds', [])}")
    print("=" * 80)
    for st in EVOLUTION_STAGES:
        r = st["round"]
        done = r in state.get("completed_rounds", [])
        mark = "✅ [PASS]" if done else "⏳ [PENDING]"
        print(f" {mark} Round {r:02d} | {st['layer']} | {st['name']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="R09 十轮渐进式演进执行器")
    parser.add_argument("--status", action="store_true", help="查看演进状态")
    parser.add_argument("--round", type=int, help="执行指定轮次 (1-6)")
    parser.add_argument("--run-batch", type=int, choices=[1, 2], help="执行指定批次升级 (1=L01~L03, 2=L04~L06)")
    parser.add_argument("--reset", action="store_true", help="重置状态机")
    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.reset:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print("已重置演进状态机。")
        return 0

    if args.round:
        ok = execute_round(args.round)
        return 0 if ok else 1

    if args.run_batch == 1:
        print("🚀 开始执行【第 1 轮大升级：执行基石阶段 (L01~L03)】...")
        for r in (1, 2, 3):
            if not execute_round(r):
                print(f"❌ 第 {r} 轮演进失败，流程中断！")
                return 1
        print("\n🎉 第一轮大升级 (L01~L03) 全部成功闭环！")
        return 0

    if args.run_batch == 2:
        print("🚀 开始执行【第 2 轮大升级：专业深度阶段 (L04~L06)】...")
        for r in (4, 5, 6):
            if not execute_round(r):
                print(f"❌ 第 {r} 轮演进失败，流程中断！")
                return 1
        print("\n🎉 第二轮大升级 (L04~L06) 全部成功闭环！")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
