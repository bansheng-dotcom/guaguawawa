#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py - R06 蛙得清 · 十维演进物理调度状态机执行器。

严格贯彻《SOP_AGENT_EVOLUTION_UNIVERSAL.md v13.0》：
1. 十轮分步执行状态机 (Round 1 -> Round 10)，每轮五步闭环：
   穿透体检 → 标杆对齐 → 架构跃迁 → 物理工件验收 → 双轨零破坏回归；
2. 三轮 SOP 批次 (Stage 1/2/3)：一次完整 stage 执行计为一轮 SOP 升级；
3. 状态机与 SOP 轮次轨迹全部落盘 workspace/evolution_state.json，失败强熔断。

用法：
    python auto_evolve_runner.py --status           # 演进看板
    python auto_evolve_runner.py --stage 1          # 第 1 轮 SOP（L01~L03）
    python auto_evolve_runner.py --stage 2          # 第 2 轮 SOP（L04~L06）
    python auto_evolve_runner.py --stage 3          # 第 3 轮 SOP（L07~L10）
    python auto_evolve_runner.py --round 5          # 仅执行单层演进
    python auto_evolve_runner.py --run-all          # 连续驱动 10 层
    python auto_evolve_runner.py --reset            # 重置状态机
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List

# Windows 终端 Unicode 编码安全防御
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.join(HERE, "workspace")
STATE_FILE = os.path.join(WS, "evolution_state.json")
PY = sys.executable

# 10 层阶梯元模型：每层至少 3 项真实架构升级点
EVOLUTION_STAGES = [
    {
        "round": 1,
        "layer": "L01",
        "name": "工具实体层 (Real Analytical Tool & Engine Layer)",
        "audit": "分析引擎此前仅纯 Python 手算，无真实列式 SQL 驱动；货币累加无分位约束，勾稽无容差门禁。",
        "bench": "DuckDB (Stars > 23k) / DuckDB-Wasm / Polars (Stars > 30k)",
        "engine_module": "engines.analysis_engine",
        "capabilities": [
            "DuckDB 嵌入式真实 SQL 沙箱 (register_records / register_csv / aggregate 下推)",
            "确定性货币分位 ROUND_HALF_UP + 零容差守恒勾稽 (conservation_check)",
            "多引擎能力清单/健康探测/延迟采样与 DuckDB->Native 平滑降级",
        ],
        "verify_cmds": [
            [PY, "agent.py", "evolve", "sql"],
            [PY, "agent.py", "evolve", "probe"],
        ],
        "artifacts": ["engines/analysis_engine.py", "workspace/evolve_l01_sql.json"],
    },
    {
        "round": 2,
        "layer": "L02",
        "name": "意图解构层 (Intent Decompilation & DAG Compilation)",
        "audit": "此前依赖链是硬编码串联，未做真实 Kahn 拓扑排序、无环路检测、无并行波次与工时预算。",
        "bench": "DSPy (Stars > 24k) / Ray DAG (Stars > 36k) / LangGraph (Stars > 10k)",
        "engine_module": "engines.intent_decompiler",
        "capabilities": [
            "显式依赖声明 + Kahn 入度削减拓扑排序 + 环路检测",
            "并行波次 (waves) 与关键路径/并行增益工时预算估算",
            "指标/维度别名归一、时间窗语义化与冲突告警",
        ],
        "verify_cmds": [
            [PY, "agent.py", "evolve", "plan", "--query",
             "分析上周抖音渠道GMV转化率为什么下滑，做质检归因和图表报告", "--rows", "100000"],
            [PY, "agent.py", "evolve", "decompile", "--query", "分析一下上周抖音GMV转化率为什么大幅下滑"],
        ],
        "artifacts": ["engines/intent_decompiler.py", "workspace/evolve_l02_dag.json"],
    },
    {
        "round": 3,
        "layer": "L03",
        "name": "自愈反思层 (Reflexive Healing & Critic Layer)",
        "audit": "此前只能扫顶层 NaN，无深层定位；越权拍板仅做字符串软化，无红线证据链与反思闭环。",
        "bench": "Reflexion (Stars > 2k) / Self-Debug / Critic-Agent / OpenHands (Stars > 60k)",
        "engine_module": "engines.reflexive_healer",
        "capabilities": [
            "递归 JSON Pointer 深层 NaN/Inf 定位与安全兜底",
            "结构化红线审判 (R06-REDLINE-101/201/301/401) 与 [REDLINE BLOCKED] 移交",
            "Reflexion 审计-自愈-复审闭环 + 经验沉淀复用 + SQL Self-Debug 重写",
        ],
        "verify_cmds": [
            [PY, "agent.py", "evolve", "heal"],
        ],
        "artifacts": ["engines/reflexive_healer.py", "workspace/evolve_l03_heal.json"],
    },
    {
        "round": 4,
        "layer": "L04",
        "name": "领域账本层 (Metrics Spec Ledger Layer)",
        "audit": "此前账本解析只做正则取值，无完整性校验、无指纹、无跨轮漂移门禁、无下游规则包导出。",
        "bench": "dbt MetricFlow (Stars > 11k) / Cube.js (Stars > 18k)",
        "engine_module": "engines.metrics_spec_ledger",
        "capabilities": [
            "账本 SHA256 指纹与 schema 完整性校验",
            "基线快照与口径漂移 (drift) 门禁告警",
            "编译导出下游可消费的规则包 metrics_rules.json",
        ],
        "verify_cmds": [
            [PY, "-c",
             "from engines import MetricsSpecLedgerParser; p=MetricsSpecLedgerParser(); s=p.parse(); "
             "print('L04 OK', s['integrity']['sha256'][:8], s['schema']['valid'])"],
            [PY, "agent.py", "evolve", "spec"],
        ],
        "artifacts": ["METRICS_SPEC.md", "engines/metrics_spec_ledger.py", "workspace/bundles/metrics_rules.json"],
    },
    {
        "round": 5,
        "layer": "L05",
        "name": "质感去劣化 (Anti-Slop & Quality Enforcement)",
        "audit": "此前只按词表扣分，无法识别无源数字幻觉，也不检查结论是否给出归因驱动因素与 DRI。",
        "bench": "reviewdog (Stars > 8k) / Vale (Stars > 4k)",
        "engine_module": "engines.data_slop_guard",
        "capabilities": [
            "分节审计 + 扩展假大空词库与行动力加权评分",
            "数字溯源幻觉审计 (报告数值须可在数据集/基准中复现)",
            "归因完整性门禁 (驱动因素/贡献度/对照基准) 与 DRI+量化动作注入",
        ],
        "verify_cmds": [
            [PY, "-c",
             "from engines import DataSlopGuard; g=DataSlopGuard(); "
             "print(g.audit_report('渠道A贡献了-1200元，占总跌幅65%，同比基准-2.1pp'))"],
            [PY, "agent.py", "evolve", "slop"],
        ],
        "artifacts": ["engines/data_slop_guard.py", "workspace/evolve_l05_slop.json"],
    },
    {
        "round": 6,
        "layer": "L06",
        "name": "横向决策层 (Comparative Scenario Matrix Layer)",
        "audit": "此前只做三套线性推演，无 MCDA 权重打分、无置信区间、无敏感性分析验证推荐稳健性。",
        "bench": "MCDA / Scenario Planning / Stylescapes",
        "engine_module": "engines.scenario_matrix",
        "capabilities": [
            "四准则加权 MCDA 打分与排名 (增长/ROI/风险/成本)",
            "区间预测 (置信带) 与风险调整期望值",
            "±20% 敏感性分析 (龙卷风) 验证推荐排名稳健性",
        ],
        "verify_cmds": [
            [PY, "agent.py", "evolve", "scenario", "--base", "200000", "--growth", "0.20"],
        ],
        "artifacts": ["engines/scenario_matrix.py", "workspace/evolve_l06_scenario.json"],
    },
    {
        "round": 7,
        "layer": "L07",
        "name": "伴生消费层 (Downstream Consumption & Asset Bundle)",
        "audit": "此前 Bundle 无指纹、无血缘、无 schema 版本约束，Vega/SARIF 字段单薄，下游无法做完整性校验。",
        "bench": "OASIS SARIF v2.1.0 / Vega-Lite (Stars > 17k) / Frictionless Data",
        "engine_module": "engines.asset_bundle",
        "capabilities": [
            "Bundle 清单 + 逐工件 SHA256 指纹 + 数据血缘 lineage",
            "Vega-Lite 类型推断与规范校验 (nominal/quantitative)",
            "SARIF 多规则注册、fingerprints 与 invocations 执行状态",
        ],
        "verify_cmds": [
            [PY, "agent.py", "evolve", "bundle", "--run-id", "runner_r07_test"],
            [PY, "agent.py", "evolve", "verify-bundle", "--run-id", "runner_r07_test"],
        ],
        "artifacts": ["engines/asset_bundle.py", "workspace/analysis_bundle_runner_r07_test.json"],
    },
    {
        "round": 8,
        "layer": "L08",
        "name": "局部差量层 (RFC 6901/6902 Differential Recalculation)",
        "audit": "此前 Patch 只支持顶层键，无数组、无 move/copy/test、无逆补丁，改一处嵌套字段仍需全量替换。",
        "bench": "RFC 6901 (JSON Pointer) / RFC 6902 (JSON Patch) / diff-match-patch (Stars > 7k)",
        "engine_module": "engines.diff_patch_engine",
        "capabilities": [
            "RFC 6901 JSON Pointer 递归差量 (支持对象与数组下标、'-' 追加)",
            "RFC 6902 全算子 add/remove/replace/move/copy/test",
            "逆补丁生成与原状态回放验证 + 局部切片差量重算",
        ],
        "verify_cmds": [
            [PY, "-c",
             "from engines import AnalysisDiffPatchEngine; p=AnalysisDiffPatchEngine(); "
             "d=p.create_patch({'a':{'b':1}}, {'a':{'b':2}}); print(d, p.apply_patch({'a':{'b':1}}, d))"],
            [PY, "agent.py", "evolve", "patch"],
        ],
        "artifacts": ["engines/diff_patch_engine.py", "workspace/evolve_l08_patch.json"],
    },
    {
        "round": 9,
        "layer": "L09",
        "name": "会话记忆层 (Persistent Session State & Disambiguation)",
        "audit": "此前存盘无文件锁与 TTL、无槽位置信度、无方案槽位记忆，回滚后缺少 redo 能力。",
        "bench": "MemGPT / Letta (Stars > 18k) / LangGraph State Store",
        "engine_module": "engines.session_memory",
        "capabilities": [
            "带 TTL 的跨进程文件锁与原子写入",
            "槽位置信度 + 方案槽位记忆 (第 N 套方案) 与代词消歧",
            "回滚 redo 栈、TTL 快照裁剪与 turn 口径一致",
        ],
        "verify_cmds": [
            [PY, "-c",
             "from engines import AnalysisSessionMemoryPool; m=AnalysisSessionMemoryPool(); "
             "print(m.resolve_pronouns('按第二套方案看刚才的指标'))"],
            [PY, "agent.py", "evolve", "memory", "--list"],
        ],
        "artifacts": ["engines/session_memory.py", "workspace/session_state.json"],
    },
    {
        "round": 10,
        "layer": "L10",
        "name": "工业容灾层 (Watchdog Circuit Breaker & Telemetry)",
        "audit": "此前熔断只看连续失败次数，无滑窗失败率、无进程级隔离硬杀，遥测无 traceparent 传播与聚合分位。",
        "bench": "Temporal (Stars > 40k) / OpenTelemetry (Stars > 20k) / Tenacity / Resilience4j",
        "engine_module": "engines.telemetry_watchdog",
        "capabilities": [
            "滑窗失败率自适应熔断 + Full Jitter 退避",
            "子进程级硬超时隔离 (超时强杀，不拖垮主进程)",
            "W3C traceparent 传播、采样与 p50/p95/p99 遥测聚合",
        ],
        "verify_cmds": [
            [PY, "-c",
             "from engines import AnalysisWatchdogBreaker, AnalysisTelemetryTracer; "
             "b=AnalysisWatchdogBreaker(); r=b.run_isolated([__import__('sys').executable,'-c','import time;time.sleep(2)'],0.2); "
             "print('L10 isolated', r['status'])"],
            [PY, "agent.py", "evolve", "telemetry", "--recent", "3"],
        ],
        "artifacts": ["engines/telemetry_watchdog.py", "workspace/telemetry.jsonl"],
    },
]

STAGE_GROUPS = {
    1: {"name": "执行基石阶段 (L01~L03)", "rounds": [1, 2, 3]},
    2: {"name": "专业深度阶段 (L04~L06)", "rounds": [4, 5, 6]},
    3: {"name": "工业交付阶段 (L07~L10)", "rounds": [7, 8, 9, 10]},
}


def _empty_state() -> Dict[str, Any]:
    return {
        "agent": "r06-wadeqing-analyst",
        "runner_version": "13.0",
        "initialized_at": datetime.datetime.now().isoformat(),
        "cycle": 2,
        "current_round": 0,
        "completed_rounds": [],
        "round_history": [],
        "sop_round_count": 0,
        "sop_rounds": [],
    }


def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            base = _empty_state()
            for k, v in base.items():
                state.setdefault(k, v)
            return state
        except Exception:
            pass
    return _empty_state()


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = f"{STATE_FILE}.tmp_{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def run_cmd(argv: List[str]) -> tuple:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, p.stdout, p.stderr


def run_dual_regression() -> tuple:
    """双轨零破坏回归：既有 155 项门禁 + L01~L10 演进集成套件。"""
    rc, stdout, stderr = run_cmd([PY, "run_tests.py"])
    total = ""
    for line in stdout.splitlines():
        if "PASS " in line and "/" in line:
            total = line.strip()
    return rc == 0 and "ALL GREEN" in stdout, total, stderr


def execute_round(round_num: int, sop_round: int = 0, verbose: bool = True) -> bool:
    if round_num < 1 or round_num > 10:
        print(f"[ERROR] 轮次超限: {round_num} (有效范围 1~10)")
        return False

    stage = EVOLUTION_STAGES[round_num - 1]
    t0 = time.time()
    if verbose:
        print("\n" + "-" * 78)
        print(f"▶ Round {round_num:02d} | {stage['layer']} {stage['name']}")
        print(f"  体检病灶: {stage['audit']}")
        print(f"  开源标杆: {stage['bench']}")
        print("  架构升级点:")
        for i, cap in enumerate(stage["capabilities"], 1):
            print(f"    {i}. {cap}")

    # 步骤3：核心模块必须真实存在
    module_path = os.path.join(HERE, stage["engine_module"].replace(".", os.sep) + ".py")
    if not os.path.exists(module_path):
        print(f"  [FAIL] 核心引擎模块缺失: {stage['engine_module']}")
        return False

    # 步骤4：物理工件验收（真实 CLI 跑批）
    for cmd in stage["verify_cmds"]:
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            print(f"  [FAIL] 物理验收命令失败 (rc={rc}): {' '.join(cmd[1:])}")
            print(f"         stderr: {err.strip()[:500]}")
            return False
        tail = (out.strip().splitlines() or [""])[-1]
        if verbose:
            print(f"  [ok] CLI 实跑: {' '.join(cmd[1:])} -> {tail[:160]}")

    for rel in stage["artifacts"]:
        path = os.path.join(HERE, rel)
        if not os.path.exists(path):
            print(f"  [FAIL] 物理工件未落盘: {rel}")
            return False
    if verbose:
        print(f"  [ok] 物理工件已落盘: {', '.join(stage['artifacts'])}")

    # 步骤5：双轨零破坏回归
    reg_ok, total, err = run_dual_regression()
    if not reg_ok:
        print(f"  [FAIL] 双轨回归门禁未通过！安全熔断。{err.strip()[:300]}")
        return False
    if verbose:
        print(f"  [ok] 双轨回归 100% ALL GREEN ({total})")

    duration = round((time.time() - t0) * 1000, 2)
    state = load_state()
    state["current_round"] = round_num
    if round_num not in state["completed_rounds"]:
        state["completed_rounds"].append(round_num)
        state["completed_rounds"].sort()
    state["round_history"].append({
        "cycle": state.get("cycle", 1),
        "sop_round": sop_round,
        "round": round_num,
        "layer": stage["layer"],
        "name": stage["name"],
        "timestamp": datetime.datetime.now().isoformat(),
        "duration_ms": duration,
        "engine_module": stage["engine_module"],
        "capabilities": stage["capabilities"],
        "capability_count": len(stage["capabilities"]),
        "artifacts": stage["artifacts"],
        "regression_status": "ALL_GREEN_100_PASS",
    })
    save_state(state)
    if verbose:
        print(f"  ✔ Round {round_num:02d} 结项 ({duration} ms)")
    return True


def execute_stage(stage_num: int) -> bool:
    """执行一个完整 SOP 轮次（一次 stage 批次 = 一轮 SOP 升级）。"""
    if stage_num not in STAGE_GROUPS:
        print(f"[ERROR] 非法 stage: {stage_num} (有效 1/2/3)")
        return False

    group = STAGE_GROUPS[stage_num]
    state = load_state()
    sop_round = int(state.get("sop_round_count", 0)) + 1
    started = datetime.datetime.now().isoformat()
    t0 = time.time()

    print("=" * 78)
    print(f"🚀 [SOP 第 {sop_round} 轮] {group['name']} | Rounds {group['rounds']}")
    print("=" * 78)

    completed: List[int] = []
    for r in group["rounds"]:
        if not execute_round(r, sop_round=sop_round):
            print(f"\n❌ SOP 第 {sop_round} 轮在第 {r} 层熔断，拒绝后续升级。")
            return False
        completed.append(r)

    duration = round(time.time() - t0, 2)
    state = load_state()
    state["sop_round_count"] = sop_round
    state.setdefault("sop_rounds", []).append({
        "round_index": sop_round,
        "stage": stage_num,
        "stage_name": group["name"],
        "layers": [EVOLUTION_STAGES[r - 1]["layer"] for r in completed],
        "rounds": completed,
        "started_at": started,
        "finished_at": datetime.datetime.now().isoformat(),
        "duration_sec": duration,
        "capability_upgrades": sum(len(EVOLUTION_STAGES[r - 1]["capabilities"]) for r in completed),
        "dual_regression": "ALL_GREEN_100_PASS",
    })
    save_state(state)

    print("\n" + "=" * 78)
    print(f"🏁 SOP 第 {sop_round} 轮完成: {group['name']} | 层 {completed} | 耗时 {duration}s")
    print("   双轨回归: ALL GREEN 100% PASS | 工件与打卡已落盘 workspace/evolution_state.json")
    print("=" * 78)
    return True


def print_status() -> None:
    state = load_state()
    print("=" * 72)
    print("R06 蛙得清 · 十维演进 / 三轮 SOP 状态看板")
    print("=" * 72)
    print(f"当前 cycle: {state.get('cycle')} | 已完成 SOP 轮次: {state.get('sop_round_count', 0)} / 3")
    for sr in state.get("sop_rounds", []):
        print(f"  SOP 第 {sr['round_index']} 轮 [{sr['stage_name']}] "
              f"{sr['layers']} | 升级点 {sr['capability_upgrades']} | "
              f"{sr['duration_sec']}s | {sr['dual_regression']}")
    print("-" * 72)
    for st in EVOLUTION_STAGES:
        r = st["round"]
        done = r in state["completed_rounds"]
        mark = "✅ PASS" if done else "⏳ PENDING"
        print(f"Round {r:02d}: {mark:10s} {st['layer']} - {st['name']}")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="R06 10-Stage / 3-Round SOP Evolution Runner")
    parser.add_argument("--status", action="store_true", help="查看演进进度状态")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="执行一轮完整 SOP 批次")
    parser.add_argument("--round", type=int, help="执行指定单层 (1~10)")
    parser.add_argument("--run-all", action="store_true", help="连续驱动 10 层演进")
    parser.add_argument("--reset", action="store_true", help="重置状态机")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print("[OK] 演进状态机已重置。")
        return 0
    if args.status:
        print_status()
        return 0
    if args.stage:
        return 0 if execute_stage(args.stage) else 1
    if args.round:
        return 0 if execute_round(args.round) else 1
    if args.run_all:
        total0 = time.time()
        for r in range(1, 11):
            if not execute_round(r):
                print(f"\n❌ 流水线在第 {r} 轮熔断阻断！")
                return 1
        print(f"\n🏆 10 层全部完成，总耗时 {round(time.time() - total0, 2)}s")
        print_status()
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
