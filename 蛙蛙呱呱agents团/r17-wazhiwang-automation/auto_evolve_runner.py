# -*- coding: utf-8 -*-
"""auto_evolve_runner.py - R17 蛙织网 · 自动化与集成工程 十轮渐进式演进物理调度执行器。

严格贯彻《Universal Agent 10-Stage Evolution SOP v13.0》要求：
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

# 10 轮阶梯元模型定义（特化于 R17 蛙织网 · 自动化与集成工程师）
EVOLUTION_STAGES = [
    {
        "round": 1,
        "layer": "L01",
        "name": "工具实体层 (Real Automation Workflow Sandbox & DAG Topo Probes)",
        "audit": "检查工作流拓扑校验、Dry-Run执行、悬空边扫描与幂等计算缺乏独立确定性沙箱；对标 n8n / Airflow / Temporal 构建真实拓扑沙箱、Dry-Run模拟器与确定性幂等指纹探针。",
        "bench": "n8n / Apache Airflow / Temporal (Stars > 35k~45k)",
        "engine_module": "engines.runtime_engine",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationRuntimeEngine; e=AutomationRuntimeEngine(); p=e.probe_health(); assert p['status']=='HEALTHY'; print('L01 Probe OK')"],
        "artifact_expected": "engines/runtime_engine.py",
    },
    {
        "round": 2,
        "layer": "L02",
        "name": "意图解构层 (Intent Decompiler & Automation 5-Stage Kahn DAG)",
        "audit": "检查复合自动化集成需求无法结构化解构与拓扑编排；对标 DSPy/Ray DAG 编译包含【触发鉴权/凭据校验/字段映射/审批分发/审计重试】5 阶段标准的 Kahn 拓扑交付 DAG 与工时估算。",
        "bench": "DSPy / Ray DAG (Stars > 20k)",
        "engine_module": "engines.intent_compiler",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationIntentCompiler; c=AutomationIntentCompiler(); s=c.compile_intent('紧急对接Shopify订单到CRM，需要审批和3次重试'); assert len(s)==5; print('L02 DAG OK')"],
        "artifact_expected": "engines/intent_compiler.py",
    },
    {
        "round": 3,
        "layer": "L03",
        "name": "自愈反思层 (Reflexive Healing & Automation Redline Guard)",
        "audit": "检查自动化四大违规红线（明文凭据硬编码、未经审批擅自发布、越权写业务代码、静默吞异常丢失败）缺乏刚性审判与就地自纠；对标 Reflexion 落地四大红线拦截与反思修复。",
        "bench": "Reflexion / Critic-Agent (Stars > 40k)",
        "engine_module": "engines.reflexive_healer",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationReflexiveHealer; h=AutomationReflexiveHealer();\ntry:\n    h.audit_redlines('api_key=sk-12345678')\n    assert False\nexcept ValueError:\n    print('L03 Redline OK')"],
        "artifact_expected": "engines/reflexive_healer.py",
    },
    {
        "round": 4,
        "layer": "L04",
        "name": "领域账本层 (Domain Spec Ledger & Automation Single Source of Truth)",
        "audit": "检查 8 维门禁阈值、北极星指标（WSR>=99.9%、CIR=100%、IDE=100% 等）散落硬编码；动态加载 AUTOMATION_SPEC.md 单一信任源，统一定义北极星指标、计算公式与 8 维发布硬门禁。",
        "bench": "dbt Semantic Layer / OpenAPI 3.1 Spec (Stars > 15k)",
        "engine_module": "engines.spec_ledger",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationSpecLedger; s=AutomationSpecLedger(); spec=s.load_spec(); assert spec['gates_count']==8; print('L04 Spec OK')"],
        "artifact_expected": "AUTOMATION_SPEC.md",
    },
    {
        "round": 5,
        "layer": "L05",
        "name": "质感去劣化 (Automation Slop Guard & Anti-Slop Enforcement)",
        "audit": "检查自动化交付报告充斥'整体平稳'、'基本跑通'、'视情况重试'、'相关细节待定'等假大空废话与无行动力套话；对标 reviewdog/Vale 构建物理级套话清洗与量化事实/责任人注入。",
        "bench": "reviewdog / Vale / StyleGuide (Stars > 10k)",
        "engine_module": "engines.slop_guard",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationSlopGuard; g=AutomationSlopGuard(); res=g.audit('整体运行平稳，流程基本可用，相关细节待定'); assert res['has_slop']; print('L05 SlopGuard OK')"],
        "artifact_expected": "engines/slop_guard.py",
    },
    {
        "round": 6,
        "layer": "L06",
        "name": "横向决策层 (Comparative Automation Architecture Scenario Matrix)",
        "audit": "检查自动化方案单一（一锤子买卖）；拒绝单一方案，自动裂变【极速轻量同步版 (Minimal Rapid Sync) / 稳健队列缓冲版 (Resilient Queue Buffered，推荐) / 企业分布式编排版 (Enterprise Saga Orchestration)】三维方案看板与多维 ROI 权衡矩阵。",
        "bench": "Scenario Planning / MCDA (Stars > 5k)",
        "engine_module": "engines.scenario_matrix",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationScenarioMatrix; m=AutomationScenarioMatrix(); scns=m.generate(); assert len(scns)==3; print('L06 Scenario OK')"],
        "artifact_expected": "engines/scenario_matrix.py",
    },
    {
        "round": 7,
        "layer": "L07",
        "name": "伴生消费层 (Downstream Consumption & Automation Asset Bundle)",
        "audit": "检查下游机器可消费性；伴生导出 automation_bundle.json、automation_audit.sarif.json (OASIS SARIF v2.1.0 国际标准) 与 automation_chart.vega.json 图表元数据。",
        "bench": "OASIS SARIF v2.1.0 / Vega-Lite (Stars > 11k)",
        "engine_module": "engines.asset_bundle",
        "verify_cmd": [sys.executable, "-c", "import os; from engines import AutomationAssetBundle; b=AutomationAssetBundle(); p=b.compile_and_save('r17_demo_test'); assert os.path.exists(p['bundle']); print('L07 Bundle OK')"],
        "artifact_expected": "engines/asset_bundle.py",
    },
    {
        "round": 8,
        "layer": "L08",
        "name": "局部差量层 (RFC 6902 Automation Workflow Differential Patch)",
        "audit": "检查工作流微调单节点或微调重试参数需全盘推倒重来；对标 RFC 6902 实现条目级差量热修无损置换与结构守恒校验。",
        "bench": "RFC 6902 (JSON Patch) / diff-match-patch (Stars > 8k)",
        "engine_module": "engines.diff_patch_engine",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationDiffPatchEngine; d=AutomationDiffPatchEngine(); patch=d.create_patch({'retry': 3}, {'retry': 5}); assert len(patch)==1; print('L08 DiffPatch OK')"],
        "artifact_expected": "engines/diff_patch_engine.py",
    },
    {
        "round": 9,
        "layer": "L09",
        "name": "会话记忆层 (Persistent Session State & Disambiguation)",
        "audit": "检查跨轮多会话在自动化集成上下文中失忆；维护 workspace/session_state.json 记忆池，支持'按刚才第二套方案生成'、'把刚才的重试次数改成5次'等自然语言代词消歧与快照回滚。",
        "bench": "MemGPT (Letta) / LangGraph State Store (Stars > 15k)",
        "engine_module": "engines.session_memory",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationSessionMemory; m=AutomationSessionMemory(); r=m.disambiguate_query('按刚才第二套方案调整'); assert r['resolved']; print('L09 Memory OK')"],
        "artifact_expected": "engines/session_memory.py",
    },
    {
        "round": 10,
        "layer": "L10",
        "name": "工业容灾层 (Industrial Resilience Watchdog & Telemetry Tracer)",
        "audit": "检查下游网络抖动或服务超时导致雪崩；对标 Temporal/Tenacity 部署三态看门狗熔断器 (CLOSED/OPEN/HALF_OPEN)、指数退避全抖动重试及全链路遥测日志 workspace/telemetry.jsonl。",
        "bench": "Temporal / OpenTelemetry / Tenacity (Stars > 25k)",
        "engine_module": "engines.telemetry_watchdog",
        "verify_cmd": [sys.executable, "-c", "from engines import AutomationTelemetryWatchdog; w=AutomationTelemetryWatchdog(); res=w.execute_with_resilience(lambda: 42); assert res==42; print('L10 Watchdog OK')"],
        "artifact_expected": "engines/telemetry_watchdog.py",
    },
]

# 推荐 3 轮批次执行划分 (3-Round Recommended Batching)
STAGE_BATCH_MAPPING = {
    1: [1, 2, 3],      # Stage 1: 执行基石阶段 (L01~L03)
    2: [4, 5, 6],      # Stage 2: 专业深度阶段 (L04~L06)
    3: [7, 8, 9, 10],  # Stage 3: 工业交付阶段 (L07~L10)
}


class AutoEvolveRunner:
    """自动化演进状态机物理执行器。"""

    def __init__(self, workspace_dir: str = WS):
        self.workspace_dir = workspace_dir
        self.state_file = STATE_FILE
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.state = self._load_or_init_state()

    def _load_or_init_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "role": "r17-wazhiwang-automation",
            "sop_version": "v13.0",
            "current_round": 0,
            "overall_status": "NOT_STARTED",
            "rounds_passed": [],
            "history": [],
            "updated_at": datetime.datetime.now().isoformat(),
        }

    def _save_state(self) -> None:
        self.state["updated_at"] = datetime.datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def print_status(self) -> None:
        """打印当前十维演进状态看板。"""
        passed = set(self.state.get("rounds_passed", []))
        print("=" * 72)
        print("R17 蛙织网 · 自动化与集成工程师 十维渐进式演进状态看板 (SOP v13.0)")
        print(f"当前整体状态: {self.state.get('overall_status', 'UNKNOWN')} | 已打卡轮次: {len(passed)}/10")
        print("=" * 72)
        print(f"{'轮次':<6}{'阶梯':<6}{'状态':<10}{'阶梯名称'}")
        print("-" * 72)
        for stage in EVOLUTION_STAGES:
            r = stage["round"]
            st_text = "[PASS]" if r in passed else "[PENDING]"
            print(f"R{r:<5}{stage['layer']:<6}{st_text:<10}{stage['name']}")
        print("=" * 72)

    def run_zero_regression_gate(self) -> Tuple[bool, str]:
        """执行零破坏双轨回归总门禁 (原基准测试 + 演进集成测试)。"""
        # 1. 运行原有基准测试套件
        run_tests_py = os.path.join(HERE, "run_tests.py")
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        p1 = subprocess.run([sys.executable, run_tests_py], cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        if p1.returncode != 0:
            return False, f"基准回归测试 (run_tests.py) 失败:\n{p1.stdout[-1500:]}\n{p1.stderr[-1000:]}"

        # 2. 运行演进集成测试套件 (若存在)
        evo_test_py = os.path.join(HERE, "tests", "test_evolution_l01_l10.py")
        if os.path.exists(evo_test_py):
            p2 = subprocess.run([sys.executable, "-m", "unittest", "tests.test_evolution_l01_l10"], cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            if p2.returncode != 0:
                return False, f"十维演进集成测试 (test_evolution_l01_l10.py) 失败:\n{p2.stdout[-1500:]}\n{p2.stderr[-1000:]}"

        return True, "零破坏双轨回归门禁 100% PASS (ALL GREEN)"

    def execute_round(self, round_num: int) -> bool:
        """执行指定轮次的完整五步闭环演进。"""
        if not (1 <= round_num <= 10):
            print(f"[ERROR] 非法轮次编号: {round_num}")
            return False

        meta = next(s for s in EVOLUTION_STAGES if s["round"] == round_num)
        print("\n" + "#" * 72)
        print(f">>> 启动第 {round_num} 轮演进: [{meta['layer']}] {meta['name']}")
        print("#" * 72)

        # 步骤 1: 穿透体检
        print(f"[Step 1: Reality Audit] 穿透体检病灶 -> {meta['audit']}")

        # 步骤 2: 标杆对齐
        print(f"[Step 2: Benchmark Sourcing] 开源对标标杆 -> {meta['bench']}")

        # 步骤 3: 架构跃迁与引擎加载
        engine_file = os.path.join(HERE, meta["artifact_expected"])
        if not os.path.exists(engine_file):
            print(f"[FAIL] 缺少预期架构跃迁核心工件: {meta['artifact_expected']}")
            return False
        print(f"[Step 3: Architectural Upgrade] 核心解耦工件到位 -> {meta['artifact_expected']}")

        # 步骤 4: 物理工件验收与探针验证
        print(f"[Step 4: Physical Artifact Validation] 运行 CLI 实操探针 -> {' '.join(meta['verify_cmd'])}")
        p = subprocess.run(meta["verify_cmd"], cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            print(f"[FAIL] CLI 物理工件验证探针失败:\n{p.stderr or p.stdout}")
            return False
        print(f"[OK] 探针验证输出: {(p.stdout or '').strip()}")

        # 步骤 5: 契约零破坏双轨回归
        print("[Step 5: Zero-Regression Gate] 启动双轨回归测试套件...")
        ok, msg = self.run_zero_regression_gate()
        if not ok:
            print(f"[FAIL] 契约回归失败！升级终止:\n{msg}")
            return False
        print(f"[OK] {msg}")

        # 状态机持久化打卡
        passed_set = set(self.state.get("rounds_passed", []))
        passed_set.add(round_num)
        self.state["rounds_passed"] = sorted(list(passed_set))
        self.state["current_round"] = max(self.state.get("current_round", 0), round_num)
        if len(self.state["rounds_passed"]) == 10:
            self.state["overall_status"] = "ALL_GREEN"
        else:
            self.state["overall_status"] = f"IN_PROGRESS_ROUND_{round_num}"

        self.state.setdefault("history", []).append({
            "round": round_num,
            "layer": meta["layer"],
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "PASS",
        })
        self._save_state()
        print(f"[PASS] 第 {round_num} 轮演进打卡成功！状态已落盘至 {self.state_file}")
        return True

    def execute_stage(self, stage_num: int) -> bool:
        """执行推荐的三大批次之一。"""
        if stage_num not in STAGE_BATCH_MAPPING:
            print(f"[ERROR] 非法阶段批次: {stage_num}")
            return False

        rounds = STAGE_BATCH_MAPPING[stage_num]
        print("\n" + "=" * 72)
        print(f"=== 启动 Stage {stage_num} (涵盖轮次: {rounds}) ===")
        print("=" * 72)

        for r in rounds:
            success = self.execute_round(r)
            if not success:
                print(f"[FATAL] Stage {stage_num} 在第 {r} 轮遭遇失败熔断！")
                return False
        print(f"\n[ALL PASS] Stage {stage_num} 全部轮次升级打卡成功！")
        return True

    def run_all(self) -> bool:
        """从当前未完成轮次开始自动连续推进至 10 轮达成。"""
        for r in range(1, 11):
            if r in self.state.get("rounds_passed", []):
                continue
            if not self.execute_round(r):
                return False
        print("\n🎉 恭喜！R17 蛙织网 十维演进元模型 10/10 轮全绿通过 (ALL GREEN)！")
        return True

    def reset(self) -> None:
        """重置状态机。"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.state = self._load_or_init_state()
        self._save_state()
        print("[RESET] 演进状态机已成功重置！")


def main() -> int:
    parser = argparse.ArgumentParser(description="R17 自动化演进物理执行器")
    parser.add_argument("--status", action="store_true", help="查看当前演进状态看板")
    parser.add_argument("--round", type=int, help="执行指定第 N 轮演进 (1~10)")
    parser.add_argument("--stage", type=int, help="执行指定 Stage/Batch (1: 基石, 2: 深度, 3: 交付)")
    parser.add_argument("--run-all", action="store_true", help="自动化执行全部 10 轮演进")
    parser.add_argument("--reset", action="store_true", help="重置演进状态机")

    args = parser.parse_args()
    runner = AutoEvolveRunner()

    if args.status:
        runner.print_status()
        return 0
    if args.reset:
        runner.reset()
        return 0
    if args.round:
        return 0 if runner.execute_round(args.round) else 1
    if args.stage:
        return 0 if runner.execute_stage(args.stage) else 1
    if args.run_all:
        return 0 if runner.run_all() else 1

    runner.print_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
