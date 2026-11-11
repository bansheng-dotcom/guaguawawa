#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py — R19 蛙智模 · 模型工程与 AI 评估官
十维渐进式演进物理调度状态机执行器 (SOP v13.0)。

严格贯彻《Universal Agent 10-Stage Evolution SOP v13.0》：
1. 十轮分步状态机 (Round 1 → Round 10)，支持 SOP 推荐三批次
   (Stage/SOP-Round 1 = L01~L03 执行基石；2 = L04~L06 专业深度；3 = L07~L10 工业交付)；
2. 每轮完整五步闭环：
   Step 1 穿透体检 (Reality Audit) —— 明确本轮 R19 真实代码断点；
   Step 2 标杆对齐 (Benchmark Sourcing) —— Stars > 1k 开源项目及吸收机制；
   Step 3 架构跃迁 (Architectural Upgrade) —— 必须存在解耦 `engines/` 引擎；
   Step 4 物理工件验收 (Physical Artifact Validation) —— CLI 实跑 + 落盘 + SHA256；
   Step 5 双轨零破坏回归 (Dual Zero-Regression) —— 基准 run_tests.py + 十维集成测试；
3. 每轮打卡落盘 `workspace/rounds/round_XX_gate.json`（探针输出 / 工件指纹 / 回归数字），
   状态机轨迹落盘 `workspace/evolution_state.json`（含 3 轮 SOP 批次台账）；
4. 任一环节失败立即熔断，禁止越级/伪造打卡。

用法：
    python auto_evolve_runner.py --status            # 十轮演进看板
    python auto_evolve_runner.py --stage 1           # 执行 SOP 第 1 轮（L01~L03）
    python auto_evolve_runner.py --sop-round 2       # 同上（--stage 的语义别名）
    python auto_evolve_runner.py --round 4           # 单独执行某一层
    python auto_evolve_runner.py --run-all           # 连续推进 3 轮 SOP / 10 层
    python auto_evolve_runner.py --reset             # 重置状态机（保留物理工件）
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
# --- 引导仓库根入 sys.path：本文件可被直接 `python xxx.py` 执行 ---
_boot = os.path.dirname(os.path.abspath(__file__))
while _boot and not os.path.isdir(os.path.join(_boot, "core")):
    _boot = os.path.dirname(_boot)
if _boot and _boot not in sys.path:
    sys.path.insert(0, _boot)
from core.workspace import role_workspace  # noqa: E402
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

WS = os.path.join(role_workspace(HERE))
ROUNDS_DIR = os.path.join(WS, "rounds")
STATE_FILE = os.path.join(WS, "evolution_state.json")
_PY = sys.executable


def _cli(*args: str) -> List[str]:
    return [_PY, os.path.join(HERE, "agent.py"), "evolve", *args]


# 十轮阶梯元模型（R19 蛙智模特化：全部锚定模型工程链真实断点）
EVOLUTION_STAGES: List[Dict[str, Any]] = [
    {
        "round": 1, "layer": "L01", "stage": 1,
        "name": "工具实体层（真实评估精算沙箱：指标/分位/守恒/资产取证）",
        "audit": "7 个技能只做「字段在不在」的判断题，没有任何真实评估算子："
                 "accuracy/precision/recall/F1/混淆矩阵靠人工口算，延迟分位无确定性实现，"
                 "模型资产只校验 path 非空（空路径也算资产）。属于「只有手脚模型、没有手脚」。",
        "bench": "mlflow/mlflow (>20k) · scikit-learn/scikit-learn (>60k) · Evidently AI",
        "engine_module": "engines/runtime_engine.py",
        "verify_cmd": _cli("probe", "--out", "workspace/rounds/L01_probe.json"),
        "artifacts_expected": ["workspace/rounds/L01_probe.json"],
        "capabilities": [
            "确定性分类指标沙箱 (confusion_matrix / accuracy / precision / recall / f1)",
            "混淆计数守恒 (tp+fp+tn+fn == n，容差 0.00) 与零除安全",
            "延迟分位精算 p50/p95/p99 与物理资产取证 (magic / bytes / SHA256)",
        ],
    },
    {
        "round": 2, "layer": "L02", "stage": 1,
        "name": "意图解构层（复合诉求 → 5 阶段 Kahn 交付 DAG + 工时预算）",
        "audit": "意图路由只有 14 条关键词硬匹配，只能回答「调哪个技能」，"
                 "答不出动几个阶段、几步、几天、谁先谁后、瓶颈在哪；无拓扑排序、无环检测。",
        "bench": "stanfordnlp/dspy (>17k) · ray-project/ray (>33k) · apache/airflow (>36k)",
        "engine_module": "engines/intent_compiler.py",
        "verify_cmd": _cli("decompile",
                           "--text", "紧急评估客服助手模型，准确率>=0.9，P95<200ms，明天发布，500条样本",
                           "--out", "workspace/rounds/L02_dag.json",
                           "--md", "workspace/rounds/L02_dag.md"),
        "artifacts_expected": ["workspace/rounds/L02_dag.json",
                               "workspace/rounds/L02_dag.md"],
        "capabilities": [
            "复合诉求实体抽取 (模型/数据集/指标阈值/延迟预算/截止/风险)",
            "5 阶段 Kahn 拓扑 DAG 编译 (stages/deps/工时/责任人/交付物)",
            "拓扑排序 + 并行波次 + 关键路径 + 环路检测与工时预算",
        ],
    },
    {
        "round": 3, "layer": "L03", "stage": 1,
        "name": "自愈反思层（Reflexion 自纠闭环 + 五条红线刚性审判）",
        "audit": "缺 expected/predicted、枚举写成 prod/pass/Medium 时直接崩溃或误判，"
                 "无就地自愈；三条红线只写在 SKILL.md 文字里，代码层零拦截；"
                 "PASS 缺回归证据不会保守降级，坏结论原样吐给下游。",
        "bench": "noahshinn/reflexion (>3k) · microsoft/autogen (>42k) · langchain",
        "engine_module": "engines/reflexive_healer.py",
        "verify_cmd": _cli("heal",
                           "--artifact", "examples/evaluation_dataset.json",
                           "--action", "这个新版效果看起来不错，直接上线吧",
                           "--out", "workspace/rounds/L03_heal.json"),
        "artifacts_expected": ["workspace/rounds/L03_heal.json"],
        "capabilities": [
            "五条角色红线刚性审判 ([REDLINE BLOCKED] RL-01..RL-05) 与 handoff 声明",
            "枚举/字段别名归一 (prod→production, ground_truth→expected) 与缺省补齐",
            "Reflexion 有界反思闭环 (审计→自愈→复审, max 3 轮, 不收敛即熔断)",
        ],
    },
    {
        "round": 4, "layer": "L04", "stage": 2,
        "name": "领域账本层（ML_SPEC.md 单一信任源 + 8 维发布硬门禁）",
        "audit": "8 个门禁阈值与白名单散落在 thresholds.json、7 个 skill、review.py 与 "
                 "contracts.py 里，口径三处各写一遍；没有统一发布门禁概念，"
                 "证据链/回归/资产溯源/阶段唯一性无法整体裁决，也无账本指纹。",
        "bench": "dbt-labs/dbt-semantic-layer (>10k) · mlflow Model Registry · OASIS SARIF v2.1.0",
        "engine_module": "engines/spec_ledger.py",
        "verify_cmd": _cli("spec", "--out", "workspace/rounds/L04_spec.json",
                           "--export-dir", "workspace/bundles"),
        "artifacts_expected": ["workspace/rounds/L04_spec.json",
                               "workspace/bundles/ml_gates.json", "ML_SPEC.md"],
        "capabilities": [
            "ML_SPEC.md 动态加载 + SHA256 账本指纹 + KPI/门禁完整性校验",
            "8 维发布硬门禁统一裁决 (verify_gate_compliance) 与违规定位",
            "账本一键导出 ml_gates.json / ml_gate_matrix.md 供下游机器消费",
        ],
    },
    {
        "round": 5, "layer": "L05", "stage": 2,
        "name": "质感去劣化（MLSlopGuard 物理清洗假大空与无行动力汇报）",
        "audit": "评估/发布汇报充斥「整体表现良好 / 效果显著提升 / 相关细节待定 / 基本可用」，"
                 "无可复算数字、无 DRI；review.py 只拦三个词，换个说法就漏过去。",
        "bench": "reviewdog/reviewdog (>8k) · errata-ai/vale (>4k) · pbakaus/impeccable",
        "engine_module": "engines/slop_guard.py",
        "verify_cmd": _cli("slop",
                           "--text", "模型评估整体良好，相关细节待定，持续关注",
                           "--out", "workspace/rounds/L05_slop.json"),
        "artifacts_expected": ["workspace/rounds/L05_slop.json"],
        "capabilities": [
            "扩展假大空词库 (28 条) 物理替换与命中定位",
            "量化证据门禁 (accuracy/F1/P95/样本量) 强制绑定",
            "DRI 注入与 Actionability 行动力评分 (0~100)",
        ],
    },
    {
        "round": 6, "layer": "L06", "stage": 2,
        "name": "横向决策层（三维发布方案裂变 + MCDA ROI 权衡矩阵）",
        "audit": "发布只有「放行/驳回」一个开关，一锤子买卖；没有快而轻/稳而全/严而保"
                 "三种成本-风险偏好的横向对比，无 MCDA 打分、无敏感性分析。",
        "bench": "Scenario Planning / MCDA · huashu-design/Stylescapes (>1k)",
        "engine_module": "engines/scenario_matrix.py",
        "verify_cmd": _cli("scenario", "--model-name", "客服助手",
                           "--dataset-size", "500",
                           "--out", "workspace/rounds/L06_scenarios.json",
                           "--md", "workspace/rounds/L06_scenarios.md"),
        "artifacts_expected": ["workspace/rounds/L06_scenarios.json",
                               "workspace/rounds/L06_scenarios.md"],
        "capabilities": [
            "三维方案裂变 (SCN_A_QUICK / SCN_B_STEADY / SCN_C_STRICT)",
            "四准则加权 MCDA 打分 (speed/evidence/risk/cost) 与推荐判定",
            "±20% 权重敏感性分析 + Markdown 决策看板渲染",
        ],
    },
    {
        "round": 7, "layer": "L07", "stage": 3,
        "name": "伴生消费层（Bundle / SARIF v2.1.0 / Vega-Lite 资产包）",
        "audit": "产物只有人类可读 Markdown/JSON，CI、模型注册库、看板引擎必须人肉二次录入；"
                 "发布证据散在 checks[] 里，缺 OASIS SARIF 标准格式；图表无 Vega 规格。",
        "bench": "microsoft/sarif-tools (>1k) · vega/vega-lite (>4k) · OASIS SARIF v2.1.0",
        "engine_module": "engines/asset_bundle.py",
        "verify_cmd": _cli("bundle", "--run-id", "L07",
                           "--out-dir", "workspace/bundles",
                           "--out", "workspace/rounds/L07_bundle.json"),
        "artifacts_expected": ["workspace/rounds/L07_bundle.json",
                               "workspace/bundles/ml_bundle_L07.json",
                               "workspace/bundles/ml_audit_L07.sarif.json",
                               "workspace/bundles/ml_eval_chart_L07.vega.json"],
        "capabilities": [
            "Bundle 工件清单 + 逐文件 SHA256 指纹 + 阶段血缘 (lineage AST)",
            "OASIS SARIF v2.1.0 审计结果 (tool/rules/results/invocations/artifacts)",
            "Vega-Lite v5 指标图表规格，供前端图表引擎直接渲染",
        ],
    },
    {
        "round": 8, "layer": "L08", "stage": 3,
        "name": "局部差量层（RFC 6902 JSON Patch + 指标增量重算）",
        "audit": "改一条评估记录（tp 1→2）必须整份评估集重跑重评分，旧门禁结果全被冲掉；"
                 "没有标准 Patch 可机器应用/回放；改完不触发派生指标与守恒的增量重算。",
        "bench": "RFC 6902 (JSON Patch) · google/diff-match-patch (>7k) · jsonpatch (>1k)",
        "engine_module": "engines/diff_patch_engine.py",
        "verify_cmd": _cli("patch", "--out", "workspace/rounds/L08_patch.json"),
        "artifacts_expected": ["workspace/rounds/L08_patch.json"],
        "capabilities": [
            "RFC 6902 递归 diff (add/remove/replace + ~0/~1 指针转义)",
            "apply_patch 深拷贝无损应用 + test/remove/add/replace 语义",
            "评估指标增量重算 + 守恒校验 + 8 维门禁影响面定位",
        ],
    },
    {
        "round": 9, "layer": "L09", "stage": 3,
        "name": "会话记忆层（持久化记忆池 + 代词消歧 + 快照回滚）",
        "audit": "第二轮对话彻底失忆：「按刚才第二套方案调整」「把上次那个模型的阈值调高 0.05」"
                 "「换成上次的评估集」无法解析；无持久化记忆池，进程退出即丢；无回滚。",
        "bench": "MemGPT/letta (>15k) · langchain-ai/langgraph (>10k)",
        "engine_module": "engines/session_memory.py",
        "verify_cmd": _cli("memory",
                           "--query", "按刚才第二套方案调整，把上次那个模型的阈值调高0.05",
                           "--out", "workspace/rounds/L09_session.json"),
        "artifacts_expected": ["workspace/rounds/L09_session.json",
                               "workspace/session_state.json"],
        "capabilities": [
            "持久化 session_state.json 记忆池 + slots/entities 双向同步 (SOP §5.14)",
            "自然语言代词消歧 (第二套方案 / 上次那个模型 / 阈值调高 0.05)",
            "历史版本快照树 + 一键回滚 (rollback)",
        ],
    },
    {
        "round": 10, "layer": "L10", "stage": 3,
        "name": "工业容灾层（三态熔断 + 全抖动退避 + 全链路遥测）",
        "audit": "外部评估/检索/模型仓库抖动直接抛栈崩溃或 except: pass 静默吞异常；"
                 "无超时熔断，一个卡死任务拖垮发布链；无 TraceID/SpanID/耗时遥测无法定位。",
        "bench": "temporalio/temporal (>12k) · open-telemetry/opentelemetry-python (>2k) · jd/tenacity (>6k)",
        "engine_module": "engines/telemetry_watchdog.py",
        "verify_cmd": _cli("watchdog", "--out", "workspace/rounds/L10_telemetry.json"),
        "artifacts_expected": ["workspace/rounds/L10_telemetry.json",
                               "workspace/telemetry.jsonl"],
        "capabilities": [
            "CLOSED/OPEN/HALF_OPEN 三态熔断器与恢复窗口",
            "指数退避 + Full Jitter 重试 (可注入 RNG，确定性可测)",
            "telemetry.jsonl 全链路遥测 (TraceID/SpanID/SHA256/耗时/状态)",
        ],
    },
]

# --------------------------------------------------------------------------- #
# Cycle 2：对已全绿的十层做「第二轮真实能力加深」（严格超集，旧行为零破坏）
# --------------------------------------------------------------------------- #
_C2 = "workspace/rounds/cycle2"
EVOLUTION_STAGES_CYCLE2: List[Dict[str, Any]] = [
    {
        "round": 1, "layer": "L01", "stage": 1,
        "name": "指标精算 II（多分类 + 机会校正一致性 + 类别不均衡可解释）",
        "audit": "cycle 1 只有二分类与点估计：3 类及以上直接不可评；类别不均衡时 accuracy "
                 "掩盖少数类崩塌；没有 kappa/MCC，无法区分「真会判」与「全猜多数类」。",
        "bench": "scikit-learn metrics (macro/weighted) · imbalanced-learn · Cohen's kappa / MCC 原始论文",
        "engine_module": "engines/runtime_engine.py",
        "verify_cmd": _cli("probe2", "--out", f"{_C2}/L01_probe2.json"),
        "artifacts_expected": [f"{_C2}/L01_probe2.json"],
        "capabilities": [
            "多分类混淆矩阵 + macro/micro/weighted P/R/F1（sklearn 同口径）",
            "Cohen's kappa / MCC / 平衡准确率（机会校正 + 不均衡鲁棒）",
        ],
    },
    {
        "round": 2, "layer": "L02", "stage": 1,
        "name": "进度网络 II（CPM 正逆推 + 截止期裁决 + 赶工计划）",
        "audit": "cycle 1 只算关键路径总时长，答不出每阶段 ES/EF/LS/LF 与浮时，"
                 "无法识别近关键任务；截止期不可行时也没有可执行的赶工压缩方案。",
        "bench": "PMBOK CPM/float · Leila resource-constrained scheduling · apache/airflow SLA",
        "engine_module": "engines/intent_compiler.py",
        "verify_cmd": _cli("dag2",
                           "--text", "紧急评估客服助手模型，准确率>=0.9，P95<200ms，8小时发布，500条样本",
                           "--deadline", "8",
                           "--out", f"{_C2}/L02_cpm.json"),
        "artifacts_expected": [f"{_C2}/L02_cpm.json"],
        "capabilities": [
            "CPM 正逆推 ES/EF/LS/LF + 总浮时/自由浮时 + 近关键任务",
            "截止期可行性裁决 + 关键路径赶工压缩建议 (crash plan)",
        ],
    },
    {
        "round": 3, "layer": "L03", "stage": 1,
        "name": "自愈治理 II（分诊修复计划 + 红线语料自评 + 幂等不动点）",
        "audit": "cycle 1 的自愈笔记是扁平列表，没人知道先修哪条、谁负责；三条红线只有代码规则、"
                 "没有回归语料，召回率与误报率不可测；二次修复是否稳定未验证。",
        "bench": "noahshinn/reflexion · OWASP LLM Top-10 red-team corpus · PagerDuty incident triage",
        "engine_module": "engines/reflexive_healer.py",
        "verify_cmd": _cli("heal2", "--out", f"{_C2}/L03_heal2.json"),
        "artifacts_expected": [f"{_C2}/L03_heal2.json"],
        "capabilities": [
            "分诊式修复计划（问题→动作→责任人→严重度，阻断优先）",
            "20 条红线回归语料自评测（召回/误报/逐码覆盖）",
            "自愈幂等性校验（二次修复不动点）",
        ],
    },
    {
        "round": 4, "layer": "L04", "stage": 2,
        "name": "账本治理 II（版本差量 + 自洽 Lint + 口径漂移）",
        "audit": "cycle 1 只能导出当前账本，无法回答「这版比上版改了什么、是否 breaking」；"
                 "重复门禁、空阈值、KPI 缺公式、阈值偏离内置口径都不可发现。",
        "bench": "dbt model contracts/versioning · OPA conftest · OpenAPI diff",
        "engine_module": "engines/spec_ledger.py",
        "verify_cmd": _cli("spec2", "--out", f"{_C2}/L04_spec2.json"),
        "artifacts_expected": [f"{_C2}/L04_spec2.json"],
        "capabilities": [
            "账本版本差量 diff（门禁/KPI 增删改 + 阈值变更影响面）",
            "账本自洽 Lint（重复门禁/空阈值/空公式/指纹缺失/口径漂移）",
        ],
    },
    {
        "round": 5, "layer": "L05", "stage": 2,
        "name": "质感防线 II（正则族双语套话 + 证据密度）",
        "audit": "cycle 1 的 28 条精确词表可被「可能存在一定风险」「显著提升」「significantly "
                 "improved」等变体绕过；只查 4 个指标，长文空话仍可过审，缺证据密度阈值。",
        "bench": "errata-ai/vale · proselint · reviewdog",
        "engine_module": "engines/slop_guard.py",
        "verify_cmd": _cli("slop2",
                           "--text", "模型可能存在一定的风险，效果显著提升，significantly improved，整体基本符合预期。",
                           "--out", f"{_C2}/L05_slop2.json"),
        "artifacts_expected": [f"{_C2}/L05_slop2.json"],
        "capabilities": [
            "正则族模糊限定词/英文套话检测（中英双语，非精确词）",
            "证据密度指标（每百字可复算数字数 + 声明/证据比）",
        ],
    },
    {
        "round": 6, "layer": "L06", "stage": 2,
        "name": "决策稳健 II（TOPSIS + Pareto 前沿 + Minimax Regret）",
        "audit": "cycle 1 只有加权和排序：权重轻微变化即翻转，无法识别非支配方案，"
                 "也没有最坏情况后悔值视角，高风险发布决策缺少稳健性交叉验证。",
        "bench": "Hwang & Yoon TOPSIS · Pareto dominance · Savage minimax regret",
        "engine_module": "engines/scenario_matrix.py",
        "verify_cmd": _cli("scenario2", "--model-name", "客服助手",
                           "--dataset-size", "500",
                           "--out", f"{_C2}/L06_mcda2.json"),
        "artifacts_expected": [f"{_C2}/L06_mcda2.json"],
        "capabilities": [
            "TOPSIS 相对贴近度排序（向量归一 + 正负理想解）",
            "Pareto 非支配前沿识别",
            "Minimax Regret 最坏后悔值稳健裁决",
        ],
    },
    {
        "round": 7, "layer": "L07", "stage": 3,
        "name": "资产互操作 II（SARIF 基线/抑制 + JUnit + Merkle + Schema 自校验）",
        "audit": "cycle 1 的 SARIF 缺 baselineState/suppressions/规则帮助，CI 无法判断新增还是存量；"
                 "无 JUnit，测试平台不能直接消费；工件无 Merkle 根，整包不可内容寻址；bundle 无 schema 自检。",
        "bench": "OASIS SARIF v2.1.0 baselineState · JUnit XML · RFC 6962 Merkle",
        "engine_module": "engines/asset_bundle.py",
        "verify_cmd": _cli("bundle2", "--run-id", "C2",
                           "--out-dir", "workspace/bundles/cycle2",
                           "--out", f"{_C2}/L07_bundle2.json"),
        "artifacts_expected": [f"{_C2}/L07_bundle2.json",
                               "workspace/bundles/cycle2/ml_bundle_C2.json",
                               "workspace/bundles/cycle2/ml_junit_C2.xml"],
        "capabilities": [
            "SARIF baselineState/suppressions + 规则 help/helpUri/tags",
            "JUnit XML 导出（CI 直接消费）+ Merkle 内容寻址根",
            "Bundle schema 自校验（必填字段/血缘完整性）",
        ],
    },
    {
        "round": 8, "layer": "L08", "stage": 3,
        "name": "差量安全 II（逆 Patch 回滚 + 漂移冲突 + Patch 压缩）",
        "audit": "cycle 1 只会正向 apply：打错补丁无法回滚；基线已漂移时冲突被掩盖或抛裸异常；"
                 "同一路径多次 replace 与冗余 test 不去重，Patch 体积膨胀。",
        "bench": "RFC 6902 inverse · jsonpatch conflict detection · google/diff-match-patch",
        "engine_module": "engines/diff_patch_engine.py",
        "verify_cmd": _cli("patch2", "--out", f"{_C2}/L08_patch2.json"),
        "artifacts_expected": [f"{_C2}/L08_patch2.json"],
        "capabilities": [
            "Patch 逆运算回滚（逐 op 旧值快照 + 反向应用）",
            "基线漂移冲突检测（逐 op 定位 index/path/reason）",
            "Patch 压缩合并（去冗余/同路径归一 + 缩减率）",
        ],
    },
    {
        "round": 9, "layer": "L09", "stage": 3,
        "name": "记忆治理 II（快照 diff + 多轮冲突消解 + TTL/LRU）",
        "audit": "cycle 1 有快照但无法比较两次差异；多轮改口「调高再调低」没有 provenance 与冲突台账；"
                 "槽位与快照无限增长，进程长期驻留必然膨胀。",
        "bench": "MemGPT/letta memory eviction · langgraph checkpoint diff · Redis TTL/LRU",
        "engine_module": "engines/session_memory.py",
        "verify_cmd": _cli("memory2", "--out", f"{_C2}/L09_memory2.json"),
        "artifacts_expected": [f"{_C2}/L09_memory2.json"],
        "capabilities": [
            "快照差量 diff（新增/删除/变更槽位）",
            "多轮指代冲突消解（后写胜出 + provenance 溯源）",
            "槽位 TTL 过期 + 快照 LRU 压缩",
        ],
    },
    {
        "round": 10, "layer": "L10", "stage": 3,
        "name": "容灾观测 II（滑窗失败率熔断 + 遥测聚合 + Trace 重建）",
        "audit": "cycle 1 熔断只看连续失败次数，20% 慢失败永远不触发；没有 p50/p95/p99 与错误率聚合；"
                 "TraceID 只落盘不重建，排障仍需人肉 grep。",
        "bench": "resilience4j sliding window · OpenTelemetry metrics · Jaeger trace model",
        "engine_module": "engines/telemetry_watchdog.py",
        "verify_cmd": _cli("watchdog2", "--out", f"{_C2}/L10_telemetry2.json"),
        "artifacts_expected": [f"{_C2}/L10_telemetry2.json"],
        "capabilities": [
            "滑动窗口失败率熔断 + 半开探测配额",
            "遥测聚合（p50/p95/p99、错误率、分 span 统计）",
            "Trace 重建（按 trace_id 还原 span 序列与总耗时）",
        ],
    },
]

STAGE_BATCH_MAPPING: Dict[int, List[int]] = {
    1: [1, 2, 3],        # 执行基石：L01~L03
    2: [4, 5, 6],        # 专业深度：L04~L06
    3: [7, 8, 9, 10],    # 工业交付：L07~L10
}
STAGE_NAMES: Dict[int, str] = {
    1: "执行基石阶段 (L01~L03)",
    2: "专业深度阶段 (L04~L06)",
    3: "工业交付阶段 (L07~L10)",
}
LAYERS: Dict[int, str] = {i: s["layer"] for i, s in
                          enumerate(EVOLUTION_STAGES, start=1)}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class R19AutoEvolveRunner:
    """R19 自动化演进状态机物理执行器。"""

    def __init__(self, workspace_dir: str = WS):
        self.workspace_dir = workspace_dir
        self.rounds_dir = os.path.join(workspace_dir, "rounds")
        self.state_file = os.path.join(workspace_dir, "evolution_state.json")
        os.makedirs(self.rounds_dir, exist_ok=True)
        self.state = self._load_or_init_state()
        self.cycle = int(self.state.get("cycle", 1) or 1)
        self.stages = EVOLUTION_STAGES if self.cycle <= 1 else EVOLUTION_STAGES_CYCLE2
        self.gate_dir = (self.rounds_dir if self.cycle <= 1
                         else os.path.join(self.rounds_dir, f"cycle{self.cycle}"))
        os.makedirs(self.gate_dir, exist_ok=True)

    def ensure_cycle(self, cycle: int) -> bool:
        """切换到新的演进 cycle：归档旧状态后重置本轮台账（保留物理工件）。"""
        cycle = int(cycle)
        if cycle <= self.cycle:
            return True
        if cycle != self.cycle + 1:
            print(f"[ERROR] 只允许顺序开启下一 cycle（当前 {self.cycle}，请求 {cycle}）")
            return False
        archive = os.path.join(self.workspace_dir,
                               f"evolution_state_cycle{self.cycle}.json")
        with open(archive, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        previous = {
            "cycle": self.cycle,
            "overall_status": self.state.get("overall_status"),
            "layers_passed": self.state.get("layers_passed", []),
            "sop_round_count": self.state.get("sop_round_count", 0),
            "archived_state": os.path.relpath(archive, HERE),
        }
        fresh = {
            "role": self.state.get("role", "r19-wazhimo-ml"),
            "name": self.state.get("name", "R19 蛙智模 · 模型工程与 AI 评估官"),
            "sop_version": self.state.get("sop_version", "v13.0"),
            "runner_version": self.state.get("runner_version", "13.0"),
            "cycle": cycle,
            "current_round": 0,
            "overall_status": f"CYCLE{cycle}_NOT_STARTED",
            "rounds_passed": [],
            "layers_passed": [],
            "history": [],
            "sop_round_count": 0,
            "sop_rounds": [],
            "previous_cycles": [previous],
            "updated_at": _now(),
        }
        self.state = fresh
        self.cycle = cycle
        self.stages = EVOLUTION_STAGES_CYCLE2
        self.gate_dir = os.path.join(self.rounds_dir, f"cycle{cycle}")
        os.makedirs(self.gate_dir, exist_ok=True)
        self._save_state()
        print(f"[CYCLE] 已归档 cycle {previous['cycle']} → {previous['archived_state']}，"
              f"启动 cycle {cycle}")
        return True

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
            "role": "r19-wazhimo-ml",
            "name": "R19 蛙智模 · 模型工程与 AI 评估官",
            "sop_version": "v13.0",
            "runner_version": "13.0",
            "cycle": 1,
            "current_round": 0,
            "overall_status": "NOT_STARTED",
            "rounds_passed": [],
            "layers_passed": [],
            "history": [],
            "sop_round_count": 0,
            "sop_rounds": [],
            "updated_at": _now(),
        }

    def _save_state(self) -> None:
        self.state["updated_at"] = _now()
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def print_status(self) -> None:
        passed = set(self.state.get("rounds_passed", []))
        sop_done = set(r.get("stage") for r in self.state.get("sop_rounds", []))
        print("=" * 88)
        print("R19 蛙智模 · 模型工程与 AI 评估官  十维渐进式演进看板 (SOP v13.0)")
        print(f"整体状态: {self.state.get('overall_status', 'UNKNOWN')} | "
              f"层打卡: {len(passed)}/10 | SOP 轮次: {len(sop_done)}/3 | "
              f"cycle={self.state.get('cycle', 1)}")
        print("=" * 88)
        print(f"{'轮次':<5}{'阶梯':<7}{'SOP轮':<7}{'状态':<12}{'阶梯名称'}")
        print("-" * 88)
        for s in self.stages:
            mark = "[PASS]" if s["round"] in passed else "[PENDING]"
            print(f"R{s['round']:<4}{s['layer']:<7}S{s['stage']:<6}{mark:<12}{s['name']}")
        print("=" * 88)
        print("SOP 轮次: S1=L01~L03 执行基石 · S2=L04~L06 专业深度 · S3=L07~L10 工业交付")

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
                             errors="replace", env=env, timeout=900)
        combined = (base.stdout or "") + (base.stderr or "")
        m = re.search(r"通过\s+(\d+)\s*/\s*(\d+)", combined)
        if m:
            metrics["baseline"] = {"passed": int(m.group(1)), "total": int(m.group(2)),
                                   "ratio": round(int(m.group(1)) / max(1, int(m.group(2))), 4)}
        if base.returncode != 0:
            return False, f"基准回归 run_tests.py 失败（exit={base.returncode}）：\n{combined[-1800:]}", metrics

        modules = ["tests.test_evolution_l01_l10"]
        if self.cycle >= 2:
            modules.append("tests.test_evolution_cycle2")
        evo_total = 0
        for module in modules:
            evo = subprocess.run(
                [_PY, "-m", "unittest", module],
                cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env, timeout=600)
            evo_out = (evo.stdout or "") + (evo.stderr or "")
            m = re.search(r"Ran\s+(\d+)\s+tests?", evo_out)
            tests = int(m.group(1)) if m else 0
            metrics.setdefault("evolution_modules", {})[module] = {
                "tests": tests, "ok": evo.returncode == 0}
            evo_total += tests
            if evo.returncode != 0:
                return False, f"演进集成测试失败 [{module}]（exit={evo.returncode}）：\n{evo_out[-1800:]}", metrics
        metrics["evolution"] = {"tests": evo_total, "ok": True,
                                "modules": len(modules)}

        metrics["all_green"] = True
        return True, "双轨回归 100% PASS（基准 + 演进集成）", metrics

    # ------------------------------------------------------------------ #
    # 单轮五步闭环
    # ------------------------------------------------------------------ #
    def execute_round(self, round_num: int) -> bool:
        meta = next((s for s in self.stages if s["round"] == round_num), None)
        if meta is None:
            print(f"[ERROR] 非法轮次: {round_num}")
            return False
        if round_num > 1 and (round_num - 1) not in self.state.get("rounds_passed", []):
            print(f"[BLOCKED] 第 {round_num} 轮禁止越级启动：第 {round_num - 1} 轮尚未打卡")
            return False
        if round_num in self.state.get("rounds_passed", []):
            print(f"[SKIP] 第 {round_num} 轮已打卡，跳过（保留原工件）")
            return True

        print("\n" + "#" * 88)
        print(f">>> 第 {round_num} 轮演进 [{meta['layer']}] {meta['name']}  "
              f"(SOP 轮次 {meta['stage']})")
        print("#" * 88)
        print(f"[Step 1: Reality Audit] 真实病灶 -> {meta['audit']}")
        print(f"[Step 2: Benchmark Sourcing] 开源标杆 -> {meta['bench']}")

        engine_file = os.path.join(HERE, meta["engine_module"])
        if not os.path.exists(engine_file):
            print(f"[FAIL] 缺少架构跃迁核心工件: {meta['engine_module']}")
            return False
        print(f"[Step 3: Architectural Upgrade] 解耦引擎到位 -> {meta['engine_module']}"
              f" ({os.path.getsize(engine_file)} bytes, {len(meta['capabilities'])} 项能力)")

        print(f"[Step 4: Physical Artifact Validation] CLI 实跑 -> "
              f"{' '.join(meta['verify_cmd'][2:])}")
        proc = subprocess.run(meta["verify_cmd"], cwd=HERE, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                              timeout=600)
        if proc.returncode != 0:
            print(f"[FAIL] CLI 工件验证失败（exit={proc.returncode}）：\n"
                  f"{(proc.stderr or proc.stdout)[-1600:]}")
            return False
        probe_line = ""
        for line in (proc.stdout or "").splitlines():
            if line.startswith("__AGENT_RESULT__ "):
                probe_line = line[len("__AGENT_RESULT__ "):]
                break
        print(f"[OK] 探针输出: {probe_line[:300]}")

        artifacts: List[Dict[str, Any]] = []
        for rel in meta["artifacts_expected"]:
            path = os.path.join(HERE, rel)
            if not os.path.exists(path):
                print(f"[FAIL] 预期物理工件未落盘: {rel}")
                return False
            artifacts.append({"path": rel, "bytes": os.path.getsize(path),
                              "sha256": _sha256_file(path)})
            print(f"[OK] 物理工件落盘: {rel} ({os.path.getsize(path)}B "
                  f"sha256={_sha256_file(path)[:12]}…)")

        print("[Step 5: Zero-Regression Gate] 双轨回归中…")
        ok, msg, metrics = self.run_zero_regression_gate()
        if not ok:
            print(f"[FAIL] 回归失败，升级熔断：\n{msg}")
            return False
        print(f"[OK] {msg} | {json.dumps(metrics, ensure_ascii=False)}")

        gate_record = {
            "cycle": self.cycle,
            "round": round_num, "layer": meta["layer"], "stage": meta["stage"],
            "sop_round": meta["stage"], "name": meta["name"],
            "audit": meta["audit"], "benchmark": meta["bench"],
            "engine_module": meta["engine_module"],
            "capabilities": meta["capabilities"],
            "capability_count": len(meta["capabilities"]),
            "verify_cmd": meta["verify_cmd"],
            "probe_stdout": probe_line[:4000],
            "artifacts": artifacts,
            "regression": metrics,
            "status": "PASS",
            "timestamp": _now(),
        }
        gate_file = os.path.join(self.gate_dir, f"round_{round_num:02d}_gate.json")
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
            "cycle": self.state.get("cycle", 1),
            "round": round_num, "layer": meta["layer"], "stage": meta["stage"],
            "sop_round": meta["stage"], "status": "PASS",
            "timestamp": gate_record["timestamp"],
            "engine_module": meta["engine_module"],
            "capabilities": meta["capabilities"],
            "capability_count": len(meta["capabilities"]),
            "artifacts": [a["path"] for a in artifacts],
            "gate_record": os.path.relpath(gate_file, HERE),
            "regression": metrics,
        })
        self._save_state()
        print(f"[PASS] 第 {round_num} 轮打卡成功 → {os.path.relpath(gate_file, HERE)}")
        return True

    # ------------------------------------------------------------------ #
    # SOP 轮次 / 批次 / 全量 / 重置
    # ------------------------------------------------------------------ #
    def execute_stage(self, stage_num: int) -> bool:
        """执行一个完整 SOP 轮次（一批次），成功后台账落 sop_rounds。"""
        if stage_num not in STAGE_BATCH_MAPPING:
            print(f"[ERROR] 非法 SOP 轮次: {stage_num}")
            return False
        rounds = STAGE_BATCH_MAPPING[stage_num]
        print("\n" + "=" * 88)
        print(f"=== 启动 SOP 第 {stage_num} 轮：{STAGE_NAMES[stage_num]}（层 {rounds}） ===")
        print("=" * 88)
        started = _now()
        caps = 0
        done_rounds: List[int] = []
        for r in rounds:
            if r in self.state.get("rounds_passed", []):
                print(f"[SKIP] 第 {r} 层已打卡，跳过")
                done_rounds.append(r)
                caps += len(next(s for s in self.stages if s["round"] == r)["capabilities"])
                continue
            if not self.execute_round(r):
                print(f"[FATAL] SOP 第 {stage_num} 轮在第 {r} 层失败熔断")
                return False
            done_rounds.append(r)
            caps += len(next(s for s in self.stages if s["round"] == r)["capabilities"])

        finished = _now()
        entry = {
            "cycle": self.cycle,
            "round_index": stage_num,
            "stage": stage_num,
            "stage_name": STAGE_NAMES[stage_num],
            "layers": [LAYERS[r] for r in rounds],
            "rounds": rounds,
            "started_at": started,
            "finished_at": finished,
            "capability_upgrades": caps,
            "dual_regression": "ALL_GREEN_100_PASS",
            "status": "PASS",
        }
        sop_rounds = [x for x in self.state.get("sop_rounds", [])
                      if x.get("round_index") != stage_num]
        sop_rounds.append(entry)
        sop_rounds.sort(key=lambda x: x["round_index"])
        self.state["sop_rounds"] = sop_rounds
        self.state["sop_round_count"] = len(sop_rounds)
        self.state["overall_status"] = (
            "ALL_GREEN" if len(self.state.get("rounds_passed", [])) == 10
            else f"SOP_ROUND_{stage_num}_DONE")
        self._save_state()
        print(f"[SOP PASS] 第 {stage_num} 轮完成：{len(rounds)} 层 / "
              f"{caps} 项架构能力升级，台账已落盘")
        return True

    def run_all(self) -> bool:
        for st in (1, 2, 3):
            if not self.execute_stage(st):
                return False
        print("\n[ALL GREEN] R19 十维演进元模型 10/10 层 · 3/3 SOP 轮次全绿通过")
        return True

    def reset(self) -> None:
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.state = self._load_or_init_state()
        self._save_state()
        print("[RESET] 演进状态机已重置（物理工件保留在 workspace/rounds/）")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R19 十维演进物理执行器 (SOP v13.0)")
    ap.add_argument("--status", action="store_true", help="查看十轮演进看板")
    ap.add_argument("--round", type=int, help="执行指定第 N 层 (1~10)")
    ap.add_argument("--stage", type=int, choices=[1, 2, 3], help="执行指定 SOP 轮次/批次")
    ap.add_argument("--sop-round", type=int, choices=[1, 2, 3],
                    help="--stage 的语义别名：一次完整 SOP 执行 = 一轮")
    ap.add_argument("--run-all", action="store_true", help="连续推进全部未完成层")
    ap.add_argument("--reset", action="store_true", help="重置状态机")
    ap.add_argument("--cycle", type=int, default=1,
                    help="演进 cycle（1=首轮建成；2=深度增强）")
    args = ap.parse_args(argv)

    runner = R19AutoEvolveRunner()
    if args.reset:
        runner.reset()
        return 0
    if args.cycle > runner.cycle:
        if not runner.ensure_cycle(args.cycle):
            return 2
    if args.status:
        runner.print_status()
        return 0
    if args.round:
        return 0 if runner.execute_round(args.round) else 1
    stage = args.sop_round or args.stage
    if stage:
        return 0 if runner.execute_stage(stage) else 1
    if args.run_all:
        return 0 if runner.run_all() else 1
    runner.print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
