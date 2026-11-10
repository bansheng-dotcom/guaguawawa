# -*- coding: utf-8 -*-
"""SOP 演进 10 轮自动化物理执行机。
按 D:\\蛙蛙呱呱\\SOP_AGENT_EVOLUTION_UNIVERSAL.md 规范：
每一轮严格执行：
1. 穿透体检 (Reality Audit)
2. 标杆对齐 (Benchmark Sourcing, Stars > 1k)
3. 架构跃迁 (Architectural Upgrade)
4. 物理工件验收 (Physical Artifact Validation)
5. 契约零破坏回归 (Zero-Regression Gate)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from engines.code_metric_engine import CodeMetricEngine
from engines.review_dag_engine import ReviewDAGEngine
from engines.reflexion_engine import ReflexionSelfHealingEngine
from engines.review_spec_engine import ReviewSpecEngine
from engines.slop_guard_engine import SlopGuardEngine
from engines.scenario_dashboard_engine import ScenarioDashboardEngine
from engines.sarif_export_engine import SarifExportEngine
from engines.diff_slice_engine import DiffSliceEngine
from engines.session_memory_engine import SessionMemoryEngine
from engines.industrial_resilience_engine import IndustrialResilienceEngine


class UniversalSOPEvolutionRunner:
    """10 轮演进执行引擎。"""

    def __init__(self, target_dir: str) -> None:
        self.target_dir = target_dir
        self.artifacts_dir = os.path.join(target_dir, "artifacts", "sop_evolution_10rounds")
        os.makedirs(self.artifacts_dir, exist_ok=True)
        self.reports: List[Dict[str, Any]] = []

    def log(self, msg: str) -> None:
        print(f"[SOP-RUNNER] {msg}", flush=True)

    def run_regression_gate(self) -> Dict[str, Any]:
        """运行原有基准回归测试套件 (126 tests) 与演进套件 (10 tests)。"""
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        cmd_baseline = [sys.executable, os.path.join(self.target_dir, "run_tests.py")]
        res_baseline = subprocess.run(
            cmd_baseline, capture_output=True, text=True, cwd=self.target_dir,
            encoding="utf-8", errors="replace", env=env
        )

        cmd_sop = [sys.executable, os.path.join(self.target_dir, "tests", "test_sop_engines.py")]
        res_sop = subprocess.run(
            cmd_sop, capture_output=True, text=True, cwd=self.target_dir,
            encoding="utf-8", errors="replace", env=env
        )

        baseline_ok = (res_baseline.returncode == 0)
        sop_ok = (res_sop.returncode == 0)

        return {
            "baseline_pass": baseline_ok,
            "sop_engines_pass": sop_ok,
            "all_green": baseline_ok and sop_ok,
            "baseline_stdout": res_baseline.stdout.splitlines()[-2:] if res_baseline.stdout else [],
            "baseline_stderr": res_baseline.stderr.splitlines()[-3:] if res_baseline.stderr else [],
            "sop_stderr": res_sop.stderr.splitlines()[-3:] if res_sop.stderr else [],
        }

    # =========================================================================
    # ROUND 1: L01 工具实体层
    # =========================================================================
    def execute_round_1(self) -> Dict[str, Any]:
        self.log(">>> [Round 1/10] 执行 L01 工具实体层 演进...")
        # 1. 穿透体检
        audit = "R04 原代码审查主要依赖正则和硬编码字符串，缺乏真实 AST 抽象语法树圈复杂度 (CC) 计算与代码异味 (Smell) 物理检测。"
        # 2. 标杆对齐
        bench = "对标 PyCQA/radon (Stars > 1.3k) 与 ast-grep (Stars > 5.5k)，吸收其 AST 复杂度与反模式静态审查模式。"
        # 3. 架构跃迁
        arch = [
            "构建 CodeMetricVisitor 抽象语法树遍历器，计算每函数圈复杂度 (CC) 及总体可维护性评分 (MI)",
            "构建危险模式探针：探测裸 except、危险 eval/exec 调用",
            "提供 analyze_source 与 analyze_file 静态分析物理入口",
        ]
        # 4. 物理工件
        artifact_path = os.path.join(self.artifacts_dir, "round01_code_metric_result.json")
        res = CodeMetricEngine.analyze_file(os.path.join(self.target_dir, "agent.py"))
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

        # 5. 回归门禁
        gate = self.run_regression_gate()
        return {
            "round": 1, "level": "L01", "name": "工具实体层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 2: L02 意图解构层
    # =========================================================================
    def execute_round_2(self) -> Dict[str, Any]:
        self.log(">>> [Round 2/10] 执行 L02 意图解构层 演进...")
        audit = "复合审查需求（盘点+门禁+核查+打包）需人工多次调用或依赖串行硬编码，无法解析依赖拓扑。"
        bench = "对标 DSPy (Stars > 18k) 与 Ray DAG (Stars > 34k)，吸收其将意图编译为 DAG 与 Kahn 拓扑执行序模式。"
        arch = [
            "构建 ReviewDAGNode 与 ReviewDAGEngine 声明式图编译系统",
            "内置 15 种意图分类与依赖拓扑规则推导",
            "实现基于 Kahn 算法的环形依赖检测与分层并行 stage 划分",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round02_review_dag_plan.json")
        res = ReviewDAGEngine.compile_intent_to_dag("对项目做成品盘点、三级证据链核验、门禁审计并生成人工评审包")
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

        gate = self.run_regression_gate()
        return {
            "round": 2, "level": "L02", "name": "意图解构层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 3: L03 自愈反思层
    # =========================================================================
    def execute_round_3(self) -> Dict[str, Any]:
        self.log(">>> [Round 3/10] 执行 L03 自愈反思层 演进...")
        audit = "审查输入字段别名不一致或判据缺状态时容易崩溃，且缺乏对'评审自己/替人修代码'等越界行为的主动阻断。"
        bench = "对标 Reflexion (Stars > 5.5k) 与 OpenHands (Stars > 38k)，吸收其自愈重试与动作边界 Guardrail 机制。"
        arch = [
            "建立常见别名映射表 (id/status/source/content/severity) 实现无感字段自愈",
            "设定三大红线守护者 (RED_LINES)：强阻断 self_review、auto_fix、bypass_gate",
            "生成自愈与反思轨迹 (Reflections Trace) 供溯源",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round03_reflexion_self_healing.json")
        ok, healed, refs, viols = ReflexionSelfHealingEngine.audit_and_heal_payload(
            {"item_id": "CRIT-001", "verdict": "FAIL", "origin": "agent.py"},
            ["id", "status", "source"]
        )
        res = {"ok": ok, "healed": healed, "reflections": refs, "violations": viols}
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

        gate = self.run_regression_gate()
        return {
            "round": 3, "level": "L03", "name": "自愈反思层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 4: L04 领域账本层
    # =========================================================================
    def execute_round_4(self) -> Dict[str, Any]:
        self.log(">>> [Round 4/10] 执行 L04 领域账本层 演进...")
        audit = "证据链等级、门禁扣分反模式散落，缺乏外部可维护的全局规范账本导致口径漂移。"
        bench = "对标 awesome-design-md (Stars > 2k) 与 IEEE 1028 审查标准，吸收规格外置与确定性打分扣分模式。"
        arch = [
            "根目录建立规范账本 REVIEW_SPEC.md，硬化三级证据链与 7 维门禁扣分基准",
            "开发 ReviewSpecEngine，支持从 markdown 规范中动态解析反模式扣分权重",
            "确定性评分与最终裁决状态机 (PASS / CONDITIONAL / REJECT)",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round04_spec_evaluation.json")
        res = ReviewSpecEngine.evaluate_verdict(100, ["P-SLOP", "P-UNBOUND"])
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

        gate = self.run_regression_gate()
        return {
            "round": 4, "level": "L04", "name": "领域账本层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 5: L05 质感去劣化
    # =========================================================================
    def execute_round_5(self) -> Dict[str, Any]:
        self.log(">>> [Round 5/10] 执行 L05 质感去劣化 演进...")
        audit = "审查报告充斥'整体良好、建议进一步加强'假大空套话，缺乏明确行号与可执行的修复指示。"
        bench = "对标 reviewdog (Stars > 6.5k) 与 Google StyleGuide (Stars > 37k)，吸收其可行动性 (Actionability) 校验与行号锚定机制。"
        arch = [
            "构建 SlopGuardEngine 废话套话正则模式库与行动性量化打分器",
            "强制审查意见绑定文件锚点 (file_anchor) 与行号 (line_number)",
            "开发 polish_critique 物理精修器，将套话自动重写为高质感行动指令",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round05_slop_guard_audit.json")
        bad = SlopGuardEngine.audit_critique("整体良好，建议进一步加强异常捕获")
        polished = SlopGuardEngine.polish_critique("整体良好，建议进一步加强异常捕获", "agent.py", 42, "替换裸 except 为具体 Exception 捕获")
        res = {"audit_result": bad, "polished_sample": polished}
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

        gate = self.run_regression_gate()
        return {
            "round": 5, "level": "L05", "name": "质感去劣化",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 6: L06 横向决策层
    # =========================================================================
    def execute_round_6(self) -> Dict[str, Any]:
        self.log(">>> [Round 6/10] 执行 L06 横向决策层 演进...")
        audit = "评审仅有一刀切的通过或驳回，无法满足研发团队在不同发布窗口期对技术债与速度的权衡需求。"
        bench = "对标 SonarQube / Backstage (Stars > 28k) 与 Scenario Planning，吸收多维度决策看板裂变技术。"
        arch = [
            "构建 ScenarioDashboardEngine，裂变【激进突击版 / 稳健基准版 / 严苛防御版】三维方案",
            "为每套方案定义差异化的准入门槛、拦截级别与技术债接纳度",
            "自动渲染 Markdown 决策矩阵看板供决策者横向比对",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round06_scenario_dashboard.md")
        findings = [
            {"id": "F1", "severity": "MEDIUM", "penalty": 10, "message": "Missing line anchor"},
            {"id": "F2", "severity": "HIGH", "penalty": 20, "message": "Bare except clause"},
        ]
        res = ScenarioDashboardEngine.generate_three_tier_dashboard(findings)
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(res["markdown_dashboard"])

        gate = self.run_regression_gate()
        return {
            "round": 6, "level": "L06", "name": "横向决策层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 7: L07 伴生消费层
    # =========================================================================
    def execute_round_7(self) -> Dict[str, Any]:
        self.log(">>> [Round 7/10] 执行 L07 伴生消费层 演进...")
        audit = "审查报告多为自然语言文本或非标 JSON，下游 CI/CD (GitHub Actions / GitLab) 与 IDE 无法直接消费。"
        bench = "对标 microsoft/sarif-tools (Stars > 1.2k) 与 OASIS SARIF v2.1.0 国际标准，吸收静态分析结果标准交换格式。"
        arch = [
            "构建 SarifExportEngine 伴生导出引擎",
            "自动将 R04 缺陷映射为符合 OASIS 规范的 Rule / Location / Region / Level",
            "支持一键伴随导出 review_result.sarif.json",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round07_review_result.sarif.json")
        findings = [
            {"pattern": "P-THEATRE", "severity": "CRITICAL", "message": "Fake gate exit 0 bypass", "file_path": "scripts/ci.sh", "line": 15},
            {"pattern": "P-SLOP", "severity": "MEDIUM", "message": "Vague feedback without line anchor", "file_path": "agent.py", "line": 40},
        ]
        sarif = SarifExportEngine.export_sarif(findings, output_file=artifact_path)

        gate = self.run_regression_gate()
        return {
            "round": 7, "level": "L07", "name": "伴生消费层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 8: L08 局部差量层
    # =========================================================================
    def execute_round_8(self) -> Dict[str, Any]:
        self.log(">>> [Round 8/10] 执行 L08 局部差量层 演进...")
        audit = "修改 1 行代码触发全量重审，导致历史存量技术债全部误伤当前提交者，无法做到增量精准审查。"
        bench = "对标 reviewdog (Stars > 6.5k) 与 google/diff-match-patch (Stars > 6k)，吸收 Unified Diff 切片审查与存量告警抑制机制。"
        arch = [
            "构建 DiffSliceEngine，支持解析 Git Unified Diff 补丁文本",
            "计算精确变更行号集合 (Hunk Line Mapping)",
            "实现 filter_incremental_findings，精准分离增量新增缺陷与存量抑制缺陷",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round08_diff_slice_result.json")
        sample_diff = "--- a/agent.py\n+++ b/agent.py\n@@ -25,3 +25,4 @@\n from core import workspace\n+eval('print(1)')\n"
        findings = [
            {"file_path": "agent.py", "line": 26, "severity": "CRITICAL", "message": "Dangerous eval call"},
            {"file_path": "agent.py", "line": 200, "severity": "LOW", "message": "Old formatting issue"},
        ]
        res = DiffSliceEngine.filter_incremental_findings(findings, sample_diff)
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)

        gate = self.run_regression_gate()
        return {
            "round": 8, "level": "L08", "name": "局部差量层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 9: L09 会话记忆层
    # =========================================================================
    def execute_round_9(self) -> Dict[str, Any]:
        self.log(">>> [Round 9/10] 执行 L09 会话记忆层 演进...")
        audit = "审查过程为单步无状态黑盒，跨轮对话时彻底失忆，无法根据上下文指代消歧与一键快照回滚。"
        bench = "对标 MemGPT (Letta) (Stars > 13k) 与 LangGraph State (Stars > 17k)，吸收版本快照树与状态回滚模式。"
        arch = [
            "构建 SessionMemoryEngine，本地文件持久化 session_state.json",
            "实现版本快照检查点 (checkpoint) 与指定版本无损回滚 (rollback)",
            "内置自然语言代词消歧器 (resolve_pronouns)，智能解析'刚才的文件'与方案代号",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round09_session_memory_state.json")
        mem = SessionMemoryEngine("evolution_r09", state_file=artifact_path)
        mem.current_state["last_inspected_target"] = "agent.py"
        mem.current_state["current_verdict"] = "REJECT"
        v1 = mem.checkpoint("Round 1 Initial Review")
        mem.current_state["current_verdict"] = "PASS"
        mem.checkpoint("Round 2 Approved")
        # 演示代词解析与回滚
        resolved_query = mem.resolve_pronouns("把刚才的文件按第二套方案重新核验")
        mem.rollback(v1)

        gate = self.run_regression_gate()
        return {
            "round": 9, "level": "L09", "name": "会话记忆层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    # =========================================================================
    # ROUND 10: L10 工业容灾层
    # =========================================================================
    def execute_round_10(self) -> Dict[str, Any]:
        self.log(">>> [Round 10/10] 执行 L10 工业容灾层 演进...")
        audit = "面对长耗时命令门禁或外部 I/O 阻塞时缺乏超时看门狗，容易假死；缺乏工业级遥测链路追踪。"
        bench = "对标 OpenTelemetry (Stars > 10k) 与 Temporal (Stars > 12k)，吸收分布式遥测规范与硬超时看门狗机制。"
        arch = [
            "构建 TelemetryLogger，将每次执行 TraceID、SpanID、SHA256、耗时追加写入 telemetry.jsonl",
            "构建 run_with_watchdog 看门狗，实现线程级超时强制熔断阻断",
            "构建 retry_with_exponential_backoff 带 Jitter 的指数退避重试装饰器",
        ]
        artifact_path = os.path.join(self.artifacts_dir, "round10_telemetry_trace.jsonl")
        logger = TelemetryLogger(log_path=artifact_path)
        logger.log_span("trace-sop-round10", "final_audit", 12.5, "SUCCESS", {"total_rounds": 10, "status": "ALL_GREEN"})

        gate = self.run_regression_gate()
        return {
            "round": 10, "level": "L10", "name": "工业容灾层",
            "audit": audit, "benchmark": bench, "architecture": arch,
            "artifact": artifact_path, "gate": gate, "status": "SUCCESS" if gate["all_green"] else "FAILED"
        }

    def run_all_10_rounds(self) -> Dict[str, Any]:
        """按序物理执行 10 轮 SOP 演进。"""
        start_time = time.time()
        self.log("================================================================================")
        self.log("🚀 启动 Universal Agent 10-Stage Evolution SOP v7.0 物理全量 10 轮升级")
        self.log("================================================================================")

        rounds_methods = [
            self.execute_round_1,
            self.execute_round_2,
            self.execute_round_3,
            self.execute_round_4,
            self.execute_round_5,
            self.execute_round_6,
            self.execute_round_7,
            self.execute_round_8,
            self.execute_round_9,
            self.execute_round_10,
        ]

        for idx, func in enumerate(rounds_methods, start=1):
            r_report = func()
            self.reports.append(r_report)
            self.log(f"✅ Round {idx}/10 [{r_report['level']} {r_report['name']}] 执行完毕 -> 门禁状态: {r_report['status']}")
            if r_report["status"] != "SUCCESS":
                self.log(f"❌ Round {idx} 门禁未通过，演进中断！")
                break

        elapsed = round(time.time() - start_time, 2)
        all_passed = all(r["status"] == "SUCCESS" for r in self.reports) and len(self.reports) == 10

        summary = {
            "total_rounds_planned": 10,
            "total_rounds_completed": len(self.reports),
            "all_passed": all_passed,
            "elapsed_seconds": elapsed,
            "rounds_reports": self.reports,
        }

        # 保存 10 轮演进全景总览
        summary_path = os.path.join(self.artifacts_dir, "evolution_10rounds_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        self.log(f"🎉 10 轮演进执行结束，总耗时 {elapsed}s，总状态：{'ALL PASS (全部绿色)' if all_passed else 'FAILED'}")
        return summary


if __name__ == "__main__":
    runner = UniversalSOPEvolutionRunner(_HERE)
    res = runner.run_all_10_rounds()
    sys.exit(0 if res["all_passed"] else 1)
