#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py —— R18 蛙数仓 · 十维渐进式演进物理调度执行器 (SOP v13.0)。

严格贯彻《Universal Agent 10-Stage Evolution SOP v13.0》：
1. 十轮分步状态机（Round 1 → Round 10），并支持推荐三批次（Stage 1/2/3）；
2. 每轮完整五步闭环：穿透体检 → 标杆对齐 → 架构跃迁 → 物理工件验收 → 双轨回归；
3. 每轮打卡都落盘真实物理工件 `workspace/rounds/round_XX_gate.json`（含探针输出、
   工件 SHA256、体积、回归测试数字），状态机轨迹落盘 `workspace/evolution_state.json`；
4. 任一环节失败即熔断，后续轮次禁止启动（严禁伪造打卡）。

用法：
    python auto_evolve_runner.py --status          # 十轮演进状态看板
    python auto_evolve_runner.py --stage 1         # 批次 1：L01~L03 执行基石
    python auto_evolve_runner.py --stage 2         # 批次 2：L04~L06 专业深度
    python auto_evolve_runner.py --stage 3         # 批次 3：L07~L10 工业交付
    python auto_evolve_runner.py --round 1         # 单独执行某一轮
    python auto_evolve_runner.py --run-all         # 连续推进未完成轮次
    python auto_evolve_runner.py --reset           # 重置状态机（保留物理工件）
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# Windows 终端 Unicode 编码安全防御（SOP §5.2）
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover
            pass

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(AGENTS)
for _p in (HERE, AGENTS, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

WS = os.path.join(HERE, "workspace")
ROUNDS_DIR = os.path.join(WS, "rounds")
STATE_FILE = os.path.join(WS, "evolution_state.json")

_PY = sys.executable


def _probe(module: str, *args: str) -> List[str]:
    return [_PY, "-m", module, *args]


# 十轮阶梯元模型（R18 蛙数仓特化：全部锚定真实数据管道断点）
EVOLUTION_STAGES: List[Dict[str, Any]] = [
    {
        "round": 1, "layer": "L01", "stage": 1,
        "name": "工具实体层（真实分析型 SQL 沙箱 + 质量门禁 SQL 化）",
        "audit": "质量门禁的 row_count/null_ratio/dup_ratio 全靠输入自报，换个假数字也能过；"
                 "增量合并无守恒校验，属于「只有手脚模型、没有手脚」。",
        "bench": "duckdb/duckdb(>25k) · apache/arrow(>14k) · dbt-labs/dbt-core(>10k)",
        "engine_module": "engines/runtime_engine.py",
        "verify_cmd": _probe("engines.runtime_engine", "--probe",
                             "--out", "workspace/rounds/L01_probe.json"),
        "artifact_expected": "workspace/rounds/L01_probe.json",
    },
    {
        "round": 2, "layer": "L02", "stage": 1,
        "name": "意图解构层（自然语言 → 5 阶段 Kahn 交付 DAG + 工时预算）",
        "audit": "意图路由只有 14 条关键词硬匹配，只能回答「调哪个技能」，"
                 "答不出动几张表、要多久、依赖先后、瓶颈在哪。",
        "bench": "stanfordnlp/dspy(>17k) · ray-project/ray(>33k) · apache/airflow(>36k)",
        "engine_module": "engines/intent_compiler.py",
        "verify_cmd": _probe("engines.intent_compiler",
                             "--text", "把 orders 和 dwd_orders 最近30天的增量数据做成看板，2小时内要新鲜，空值率不超过0.05",
                             "--out", "workspace/rounds/L02_dag.json",
                             "--md", "workspace/rounds/L02_dag.md"),
        "artifact_expected": "workspace/rounds/L02_dag.json",
    },
    {
        "round": 3, "layer": "L03", "stage": 1,
        "name": "自愈反思层（Reflexion 有界重试 + 四条角色红线刚性审判）",
        "audit": "缺字段/别名漂移直接 KeyError 崩溃；凭据、擅自回填、越界统计结论、"
                 "越权资金四条红线只写在 SKILL.md 文字里，代码层零拦截。",
        "bench": "noahshinn/reflexion(>3k) · microsoft/autogen(>42k) · Significant-Gravitas/AutoGPT(>165k)",
        "engine_module": "engines/reflexive_healer.py",
        "verify_cmd": _probe("engines.reflexive_healer",
                             "--artifact", "examples/connection.json",
                             "--out", "workspace/rounds/L03_heal.json"),
        "artifact_expected": "workspace/rounds/L03_heal.json",
    },
    {
        "round": 4, "layer": "L04", "stage": 2,
        "name": "领域账本层（DATAENG_SPEC.md 单一信任源 + 8 维发布门禁）",
        "audit": "8 维门禁阈值、北极星指标（PSR/FSR/DQR/LCR）散落各 skill 与 "
                 "thresholds.json，口径随任务漂移，无统一 SSOT。",
        "bench": "dbt-labs/dbt(14139★/Apache-2.0) · OAI/OpenAPI-Specification(31311★/Apache-2.0) · "
                 "dbt-labs/metricflow(1868★/Apache-2.0)",
        "engine_module": "engines/spec_ledger.py",
        "verify_cmd": _probe("engines.spec_ledger",
                             "--out", "workspace/rounds/L04_spec.json",
                             "--export-dir", "workspace/spec_exports"),
        "artifact_expected": "workspace/rounds/L04_spec.json",
    },
    {
        "round": 5, "layer": "L05", "stage": 2,
        "name": "质感去劣化（DataEngSlopGuard 物理清洗假大空）",
        "audit": "交付报告充斥「整体良好 / 按需采购 / 视情况而定 / 相关细节待定」，"
                 "无量化值、无 DRI、无截止期，人类无法据此行动。",
        "bench": "reviewdog/reviewdog(9736★/MIT) · vale-cli/vale(6364★/MIT) · textlint/textlint(3207★/MIT)",
        "engine_module": "engines/slop_guard.py",
        "verify_cmd": _probe("engines.slop_guard",
                             "--text", "数据管道整体良好，按需采购，视情况而定，相关细节待定，持续关注",
                             "--out", "workspace/rounds/L05_slop.json"),
        "artifact_expected": "workspace/rounds/L05_slop.json",
    },
    {
        "round": 6, "layer": "L06", "stage": 2,
        "name": "横向决策层（三维管道方案裂变 + MCDA ROI 权衡矩阵）",
        "audit": "管道方案单一（一锤子买卖），人类无法在「快 / 稳 / 强一致」三种"
                 "成本-风险偏好之间做横向权衡。",
        "bench": "dbt-labs/dbt(14139★/Apache-2.0, incremental 策略谱系) · "
                 "optuna/optuna(15027★/MIT, Pareto 前沿交人类取舍) · "
                 "the-dual-space/pymoo(2994★/Apache-2.0, 归一化+加权)",
        "engine_module": "engines/scenario_matrix.py",
        "verify_cmd": _probe("engines.scenario_matrix",
                             "--out", "workspace/rounds/L06_scenarios.json",
                             "--md", "workspace/rounds/L06_scenarios.md"),
        "artifact_expected": "workspace/rounds/L06_scenarios.json",
    },
    {
        "round": 7, "layer": "L07", "stage": 3,
        "name": "伴生消费层（bundle / SARIF v2.1.0 / Vega-Lite / 血缘 AST）",
        "audit": "产物只有人类可读 Markdown/JSON，下游 CI、ERP、看板引擎必须人肉"
                 "二次录入，无法机器消费。",
        "bench": "microsoft/sarif-tools(>1k) · vega/vega-lite(>4k) · OASIS SARIF v2.1.0",
        "engine_module": "engines/asset_bundle.py",
        "verify_cmd": _probe("engines.asset_bundle",
                             "--run-id", "L07",
                             "--out-dir", "workspace/bundles",
                             "--out", "workspace/rounds/L07_bundle.json"),
        "artifact_expected": "workspace/bundles/dataeng_bundle_L07.json",
    },
    {
        "round": 8, "layer": "L08", "stage": 3,
        "name": "局部差量层（RFC 6902 JSON Patch + 增量门禁影响面重算）",
        "audit": "改一个水位/重试参数要整条管道重跑全量重验，旧门禁结果全被冲掉，"
                 "无法回答「这次微调到底影响哪几个门禁」。",
        "bench": "RFC 6902 (JSON Patch) · google/diff-match-patch(>7k)",
        "engine_module": "engines/diff_patch_engine.py",
        "verify_cmd": _probe("engines.diff_patch_engine",
                             "--base", "workspace/rounds/L02_dag.json",
                             "--out", "workspace/rounds/L08_patch.json"),
        "artifact_expected": "workspace/rounds/L08_patch.json",
    },
    {
        "round": 9, "layer": "L09", "stage": 3,
        "name": "会话记忆层（持久化记忆池 + 代词消歧 + 快照回滚）",
        "audit": "第二轮对话彻底失忆：「按刚才第二套方案调整」「把上次的 SLA 改成 2h」"
                 "无法解析，所有上下文靠人类重述。",
        "bench": "MemGPT/letta(>15k) · langchain-ai/langgraph(>10k)",
        "engine_module": "engines/session_memory.py",
        "verify_cmd": _probe("engines.session_memory",
                             "--demo", "--out", "workspace/rounds/L09_session.json"),
        "artifact_expected": "workspace/session_state.json",
    },
    {
        "round": 10, "layer": "L10", "stage": 3,
        "name": "工业容灾层（三态熔断 + 全抖动退避 + 全链路遥测）",
        "audit": "下游抖动/超时直接雪崩或静默吞异常；无 TraceID/SpanID/耗时/健康态"
                 "遥测，生产事故无法定位。",
        "bench": "temporalio/temporal(>12k) · open-telemetry/opentelemetry-python(>2k) · jd/tenacity(>6k)",
        "engine_module": "engines/telemetry_watchdog.py",
        "verify_cmd": _probe("engines.telemetry_watchdog",
                             "--probe", "--out", "workspace/rounds/L10_telemetry.json"),
        "artifact_expected": "workspace/telemetry.jsonl",
    },
]

STAGE_BATCH_MAPPING: Dict[int, List[int]] = {
    1: [1, 2, 3],       # 执行基石：L01~L03
    2: [4, 5, 6],       # 专业深度：L04~L06
    3: [7, 8, 9, 10],   # 工业交付：L07~L10
}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class R18AutoEvolveRunner:
    """R18 自动化演进状态机物理执行器。"""

    def __init__(self, workspace_dir: str = WS):
        self.workspace_dir = workspace_dir
        self.rounds_dir = os.path.join(workspace_dir, "rounds")
        self.state_file = os.path.join(workspace_dir, "evolution_state.json")
        os.makedirs(self.rounds_dir, exist_ok=True)
        self.state = self._load_or_init_state()

    # ------------------------------------------------------------------ #
    # 状态机
    # ------------------------------------------------------------------ #
    def _load_or_init_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "rounds_passed" in data:
                    return data
            except (OSError, ValueError):
                pass
        return {
            "role": "r18-washucang-dataeng",
            "sop_version": "v13.0",
            "current_round": 0,
            "overall_status": "NOT_STARTED",
            "rounds_passed": [],
            "layers_passed": [],
            "history": [],
            "updated_at": _now(),
        }

    def _save_state(self) -> None:
        self.state["updated_at"] = _now()
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def print_status(self) -> None:
        passed = set(self.state.get("rounds_passed", []))
        print("=" * 78)
        print("R18 蛙数仓 · 数据工程与管道官  十维渐进式演进看板 (SOP v13.0)")
        print(f"整体状态: {self.state.get('overall_status', 'UNKNOWN')} | "
              f"已打卡: {len(passed)}/10 轮 | 引擎层: {len(self.state.get('layers_passed', []))}/10")
        print("=" * 78)
        print(f"{'轮次':<5}{'阶梯':<6}{'批次':<6}{'状态':<11}{'阶梯名称'}")
        print("-" * 78)
        for s in EVOLUTION_STAGES:
            mark = "[PASS]" if s["round"] in passed else "[PENDING]"
            print(f"R{s['round']:<4}{s['layer']:<6}S{s['stage']:<5}{mark:<11}{s['name']}")
        print("=" * 78)
        print("批次: S1=L01~L03 执行基石 · S2=L04~L06 专业深度 · S3=L07~L10 工业交付")

    # ------------------------------------------------------------------ #
    # 双轨回归
    # ------------------------------------------------------------------ #
    def run_zero_regression_gate(self) -> Tuple[bool, str, Dict[str, Any]]:
        """双轨门禁：原有基准套件 + 十维演进集成套件，任一非 0 即阻断。"""
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        metrics: Dict[str, Any] = {}

        base = subprocess.run([_PY, os.path.join(HERE, "run_tests.py")], cwd=HERE,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=env)
        combined = (base.stdout or "") + (base.stderr or "")
        m = re.search(r"通过\s+(\d+)\s*/\s*(\d+)", combined)
        if m:
            metrics["baseline"] = {"passed": int(m.group(1)), "total": int(m.group(2))}
        if base.returncode != 0:
            return False, f"基准回归 run_tests.py 失败（exit={base.returncode}）：\n{combined[-1800:]}", metrics

        evo = subprocess.run(
            [_PY, "-m", "unittest", "tests.test_evolution_l01_l10"],
            cwd=HERE, capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env)
        evo_out = (evo.stdout or "") + (evo.stderr or "")
        m = re.search(r"Ran\s+(\d+)\s+tests?", evo_out)
        if m:
            metrics["evolution"] = {"tests": int(m.group(1))}
        metrics["evolution"]["ok"] = evo.returncode == 0
        if evo.returncode != 0:
            return False, f"演进集成测试失败（exit={evo.returncode}）：\n{evo_out[-1800:]}", metrics

        return True, "双轨回归 100% PASS（基准 + 演进集成）", metrics

    # ------------------------------------------------------------------ #
    # 单轮五步闭环
    # ------------------------------------------------------------------ #
    def execute_round(self, round_num: int) -> bool:
        meta = next((s for s in EVOLUTION_STAGES if s["round"] == round_num), None)
        if meta is None:
            print(f"[ERROR] 非法轮次: {round_num}")
            return False
        if round_num > 1 and (round_num - 1) not in self.state.get("rounds_passed", []):
            print(f"[BLOCKED] 第 {round_num} 轮禁止越级启动：第 {round_num - 1} 轮尚未打卡")
            return False

        print("\n" + "#" * 78)
        print(f">>> 第 {round_num} 轮演进 [{meta['layer']}] {meta['name']}  (Stage {meta['stage']})")
        print("#" * 78)
        print(f"[Step 1: Reality Audit] 真实病灶 -> {meta['audit']}")
        print(f"[Step 2: Benchmark Sourcing] 开源标杆 -> {meta['bench']}")

        engine_file = os.path.join(HERE, meta["engine_module"])
        if not os.path.exists(engine_file):
            print(f"[FAIL] 缺少架构跃迁核心工件: {meta['engine_module']}")
            return False
        print(f"[Step 3: Architectural Upgrade] 解耦引擎到位 -> {meta['engine_module']}"
              f" ({os.path.getsize(engine_file)} bytes)")

        print(f"[Step 4: Physical Artifact Validation] CLI 实跑 -> "
              f"{' '.join(meta['verify_cmd'][1:])}")
        proc = subprocess.run(meta["verify_cmd"], cwd=HERE, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if proc.returncode != 0:
            print(f"[FAIL] CLI 工件验证失败（exit={proc.returncode}）：\n"
                  f"{(proc.stderr or proc.stdout)[-1600:]}")
            return False
        print(f"[OK] 探针输出: {(proc.stdout or '').strip()[:400]}")

        artifact_path = os.path.join(HERE, meta["artifact_expected"])
        if not os.path.exists(artifact_path):
            print(f"[FAIL] 预期物理工件未落盘: {meta['artifact_expected']}")
            return False
        artifact_stat = {
            "path": meta["artifact_expected"],
            "bytes": os.path.getsize(artifact_path),
            "sha256": _sha256_file(artifact_path),
        }
        print(f"[OK] 物理工件落盘: {meta['artifact_expected']} "
              f"({artifact_stat['bytes']}B sha256={artifact_stat['sha256'][:12]}…)")

        print("[Step 5: Zero-Regression Gate] 双轨回归中…")
        ok, msg, metrics = self.run_zero_regression_gate()
        if not ok:
            print(f"[FAIL] 回归失败，升级熔断：\n{msg}")
            return False
        print(f"[OK] {msg} | {json.dumps(metrics, ensure_ascii=False)}")

        gate_record = {
            "round": round_num,
            "layer": meta["layer"],
            "stage": meta["stage"],
            "name": meta["name"],
            "audit": meta["audit"],
            "benchmark": meta["bench"],
            "engine_module": meta["engine_module"],
            "verify_cmd": meta["verify_cmd"],
            "probe_stdout": (proc.stdout or "").strip(),
            "artifact": artifact_stat,
            "regression": metrics,
            "status": "PASS",
            "timestamp": _now(),
        }
        gate_file = os.path.join(self.rounds_dir, f"round_{round_num:02d}_gate.json")
        with open(gate_file, "w", encoding="utf-8") as f:
            json.dump(gate_record, f, ensure_ascii=False, indent=2)

        passed = set(self.state.get("rounds_passed", []))
        passed.add(round_num)
        self.state["rounds_passed"] = sorted(passed)
        layers = set(self.state.get("layers_passed", []))
        layers.add(meta["layer"])
        self.state["layers_passed"] = sorted(layers)
        self.state["current_round"] = max(int(self.state.get("current_round", 0)), round_num)
        self.state["overall_status"] = (
            "ALL_GREEN" if len(self.state["rounds_passed"]) == 10
            else f"IN_PROGRESS_ROUND_{round_num}")
        self.state.setdefault("history", []).append({
            "round": round_num, "layer": meta["layer"], "stage": meta["stage"],
            "status": "PASS", "timestamp": gate_record["timestamp"],
            "artifact": artifact_stat["path"], "gate_record": os.path.relpath(gate_file, HERE),
            "regression": metrics,
        })
        self._save_state()
        print(f"[PASS] 第 {round_num} 轮打卡成功 → {os.path.relpath(gate_file, HERE)}")
        return True

    # ------------------------------------------------------------------ #
    # 批次 / 全量 / 重置
    # ------------------------------------------------------------------ #
    def execute_stage(self, stage_num: int) -> bool:
        if stage_num not in STAGE_BATCH_MAPPING:
            print(f"[ERROR] 非法批次: {stage_num}")
            return False
        rounds = STAGE_BATCH_MAPPING[stage_num]
        print("\n" + "=" * 78)
        print(f"=== 启动 Stage {stage_num} 批次演进（轮次 {rounds}） ===")
        print("=" * 78)
        for r in rounds:
            if r in self.state.get("rounds_passed", []):
                print(f"[SKIP] 第 {r} 轮已打卡，跳过")
                continue
            if not self.execute_round(r):
                print(f"[FATAL] Stage {stage_num} 在第 {r} 轮失败熔断")
                return False
        print(f"[ALL PASS] Stage {stage_num} 批次全部轮次打卡成功")
        return True

    def run_all(self) -> bool:
        for r in range(1, 11):
            if r in self.state.get("rounds_passed", []):
                continue
            if not self.execute_round(r):
                return False
        print("\n[ALL GREEN] R18 十维演进元模型 10/10 轮全绿通过")
        return True

    def reset(self) -> None:
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.state = self._load_or_init_state()
        self._save_state()
        print("[RESET] 演进状态机已重置（物理工件保留在 workspace/rounds/）")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R18 十维演进物理执行器 (SOP v13.0)")
    ap.add_argument("--status", action="store_true", help="查看十轮演进看板")
    ap.add_argument("--round", type=int, help="执行指定第 N 轮 (1~10)")
    ap.add_argument("--stage", type=int, choices=[1, 2, 3], help="执行指定批次")
    ap.add_argument("--run-all", action="store_true", help="连续推进全部未完成轮次")
    ap.add_argument("--reset", action="store_true", help="重置状态机")
    args = ap.parse_args(argv)

    runner = R18AutoEvolveRunner()
    if args.reset:
        runner.reset()
        return 0
    if args.status:
        runner.print_status()
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
    raise SystemExit(main())
