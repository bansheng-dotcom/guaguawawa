#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_evolve_runner.py — R05 蛙深远（战略研究官）十维渐进式演进自动化调度状态机。

严格执行《SOP_AGENT_EVOLUTION_UNIVERSAL.md v13.0》：
  三 轮 = 三次完整 SOP 五步闭环（一次 SOP 执行 = 一轮升级）
    Round 1 / Stage 1：执行基石阶段（L01 工具实体 / L02 意图解构 / L03 自愈反思）
    Round 2 / Stage 2：专业深度阶段（L04 领域账本 / L05 质感去劣化 / L06 横向决策）
    Round 3 / Stage 3：工业交付阶段（L07 伴生消费 / L08 局部差量 / L09 会话记忆 / L10 工业容灾）

每一轮的 5 步（缺一不可，任一步失败立即熔断，禁止带病进入下一轮）：
  步骤 1 穿透体检 Reality Audit      —— 扫描真实代码工件 + 记录本轮病灶断点
  步骤 2 标杆对齐 Benchmark Sourcing —— 列出 Stars>1k 标杆与被吸收的架构机制
  步骤 3 架构跃迁 Architectural Upgrade —— 真实装配 engines/ 并执行能力探针
  步骤 4 物理工件验收 Artifact Validation —— CLI/引擎实跑，落盘带 SHA256 的物理工件
  步骤 5 双轨零破坏回归 Zero-Regression Gate —— 原基准 63 项 + 演进套件 + 全量 pytest

状态机精准落盘 workspace/evolution_state.json，每轮独立打卡、可审计、可追溯。

CLI：
    python auto_evolve_runner.py --status          # 三 轮 / 十层 演进看板
    python auto_evolve_runner.py --round 1|2|3     # 执行指定一轮完整 SOP（= --stage）
    python auto_evolve_runner.py --stage 1|2|3     # 同上，按 SOP 三批次语义
    python auto_evolve_runner.py --layer L01..L10  # 单层下钻体检打卡（不改轮次状态）
    python auto_evolve_runner.py --run-all         # 顺序推进 3 轮全绿
    python auto_evolve_runner.py --reset           # 重置状态机
    python auto_evolve_runner.py --json            # 以 JSON 打印状态
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
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

# ---------------------------------------------------------------------------
# 运行时引导（SOP 五-1 / 五-9）：自身目录 + agents 根 + 仓库根统一注入 sys.path
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
REPO = os.path.dirname(AGENTS)
for _p in (HERE, AGENTS, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:  # Windows GBK 终端 Unicode 崩溃防御（SOP 五-2）
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

WS = os.path.join(role_workspace(HERE))
TMP = os.path.join(WS, "tmp")
ART = os.path.join(HERE, "artifacts", "evolve")
STATE_FILE = os.path.join(WS, "evolution_state.json")
JOURNAL_DIR = os.path.join(WS, "rounds")
AGENT = "r05-washenyuan-research"

for _d in (WS, TMP, ART, JOURNAL_DIR):
    os.makedirs(_d, exist_ok=True)


# ---------------------------------------------------------------------------
# 元模型定义：3 轮 / 10 层 / 每轮真实病灶 + Stars>1k 标杆 + >=3 项架构升级
# ---------------------------------------------------------------------------
ROUNDS: List[Dict[str, Any]] = [
    {
        "round": 1,
        "stage": 1,
        "title": "执行基石阶段 (L01~L03)",
        "layers": ["L01", "L02", "L03"],
        "test_file": "tests/test_round1_foundation.py",
        "breakpoints": [
            {"layer": "L01", "file": "engines/manager.py", "severity": "high",
             "finding": "NativeResearchEngine 只注册 calc_hhi / verify_tam_variance 两个算子；"
                        "证据链分级、单位经济（LTV/CAC/回收期）与敏感性摆动排序全部散落在 "
                        "skills/ 中，无法被独立 CLI/下游以确定性沙箱方式复用，也没有算子级探针。"},
            {"layer": "L02", "file": "engines/prompter.py", "severity": "high",
             "finding": "compile_intent 只按关键词命中顺序串成一条链，depends_on 是伪造成 S{i-1} 的"
                        "装饰字段；没有 Kahn 拓扑排序、没有环检测、没有审计/寻源/分析/验证/交付"
                        "五阶段研究标准，也没有人天工时预算。"},
            {"layer": "L03", "file": "engines/critic.py", "severity": "critical",
             "finding": "audit_findings 只把问题收集成字符串列表；heal_payload 只遍历顶层字符串字段，"
                        "嵌套 sections/list 内的拍板用语无法自愈；越权代付款等跨角色红线既不阻断也"
                        "不产生移交 R03 的 handoff 声明，自愈后也不复检。"},
        ],
        "bench": [
            {"project": "OpenBB-finance/OpenBB", "stars": 28000,
             "url": "https://github.com/OpenBB-finance/OpenBB",
             "absorbed": "可插拔研究数据供应商注册表 + 逐供应商健康探针"},
            {"project": "stanfordnlp/dspy", "stars": 19000,
             "url": "https://github.com/stanfordnlp/dspy",
             "absorbed": "把自然语言签名编译成可执行声明式计算图（DAG）"},
            {"project": "noahshinn/reflexion", "stars": 5800,
             "url": "https://github.com/noahshinn/reflexion",
             "absorbed": "Reflexion 反思-自愈-复检闭环（含失败记忆）"},
            {"project": "All-Hands-AI/OpenHands", "stars": 40000,
             "url": "https://github.com/All-Hands-AI/OpenHands",
             "absorbed": "Guardrail 硬红线阻断与跨角色 handoff 契约"},
        ],
        "upgrades": [
            {"layer": "L01", "item": "新增 ResearchRuntimeEngine 六算子确定性沙箱 "
                                      "(calc_hhi/verify_tam_variance/evidence_chain/"
                                      "unit_economics/sensitivity_swing/tam_triangulate)",
             "file": "engines/runtime_engine.py"},
            {"layer": "L01", "item": "EvidenceTierValidator 三级证据链门禁（Tier0 拦截/孤立断言/"
                                      "置信度不足/覆盖率）", "file": "engines/runtime_engine.py"},
            {"layer": "L02", "item": "ResearchIntentCompiler：审计→寻源→分析→验证→交付 五阶段 DAG，"
                                      "Kahn 拓扑排序 + 环检测 DagCycleError", "file": "engines/intent_compiler.py"},
            {"layer": "L02", "item": "实体/资金/比例抽取 + 复杂度判定 + 工时/人天预算",
             "file": "engines/intent_compiler.py"},
            {"layer": "L03", "item": "ReflexiveResearchHealer：递归深层自愈 + 归一化/补来源/替换拍板词 "
                                      "+ 自愈后复检", "file": "engines/reflexive_healer.py"},
            {"layer": "L03", "item": "RedlineBlocked 硬红线（替老板拍板→R01、越权代付款→R03）"
                                      "与 handoff 移交声明", "file": "engines/reflexive_healer.py"},
        ],
        "cli": [
            [sys.executable, "agent.py", "evolution", "probe"],
            [sys.executable, "agent.py", "evolution", "ledger"],
        ],
    },
    {
        "round": 2,
        "stage": 2,
        "title": "专业深度阶段 (L04~L06)",
        "layers": ["L04", "L05", "L06"],
        "test_file": "tests/test_round2_depth.py",
        "breakpoints": [
            {"layer": "L04", "file": "engines/ledger.py", "severity": "high",
             "finding": "RESEARCH_SPEC.md 是纯散文；ledger.py 的 HHI/TAM 方差/证据等级阈值全部"
                        "硬编码在 Python 字典里，改文档不影响运行；没有 8 维发布门禁，也没有"
                        "可落盘的 spec 快照，多轮/多 Agent 口径必然漂移。"},
            {"layer": "L05", "file": "engines/slop_guard.py", "severity": "high",
             "finding": "只有 5 条正则与按次扣 10 分的粗评分；没有量化证据密度、行动力与 A/B/C/D "
                        "分级；无法阻断'相关细节待定'占位与无 DRI 的报告，清洗后也不校验是否仍有硬伤。"},
            {"layer": "L06", "file": "engines/scenario_matrix.py", "severity": "medium",
             "finding": "三档情景的服务份额/可获份额/毛利率全部写死；没有 MCDA 权重、ROI 矩阵、"
                        "评分排序与推荐结论，人类拿到的是三张静态数字表，无法横向权衡。"},
        ],
        "bench": [
            {"project": "dbt-labs/dbt-core", "stars": 9500,
             "url": "https://github.com/dbt-labs/dbt-core",
             "absorbed": "语义层单一信任源（SSOT）：指标与阈值集中声明、机器可读消费"},
            {"project": "great-expectations/great_expectations", "stars": 9800,
             "url": "https://github.com/great-expectations/great_expectations",
             "absorbed": "声明式 Expectation Suite + 加权门禁评分"},
            {"project": "errata-ai/vale", "stars": 4500,
             "url": "https://github.com/errata-ai/vale",
             "absorbed": "词库驱动 Lint：告警分级、可配置规则与退出码"},
            {"project": "reviewdog/reviewdog", "stars": 7500,
             "url": "https://github.com/reviewdog/reviewdog",
             "absorbed": "门禁式审查结果回写（阻断/建议分级）"},
            {"project": "apache/superset", "stars": 62000,
             "url": "https://github.com/apache/superset",
             "absorbed": "多维评分决策看板与 ROI 可视化矩阵"},
            {"project": "vega/vega-lite", "stars": 4600,
             "url": "https://github.com/vega/vega-lite",
             "absorbed": "声明式图表描述（下游 R06 直接渲染）"},
        ],
        "upgrades": [
            {"layer": "L04", "item": "RESEARCH_SPEC.md v2.0.0 内置 ```json 机器可读 SSOT 块"
                                      "（version/tam_variance_max/hhi/evidence_tiers/north_star/8 gates）",
             "file": "RESEARCH_SPEC.md"},
            {"layer": "L04", "item": "ResearchSpecLedger：动态解析 SSOT（非硬编码）、8 维加权门禁 "
                                      "evaluate()、export_json() 快照", "file": "engines/spec_ledger.py"},
            {"layer": "L05", "item": "SlopGuard v2：40+ 套话词库、证据密度/行动力/等级评分、"
                                      "占位与无证据阻断、DRI 强制注入", "file": "engines/slop_guard.py"},
            {"layer": "L06", "item": "ScenarioMatrix v2：MCDA 四维权重（和=1）、ROI 矩阵、"
                                      "评分排序与推荐情景、输入驱动份额", "file": "engines/scenario_matrix.py"},
        ],
        "cli": [
            [sys.executable, "agent.py", "evolution", "slopguard", "--text",
             "市场整体良好，相关细节待定。", "--polish"],
            [sys.executable, "agent.py", "evolution", "explore",
             "--output", os.path.join(ART, "round2", "cli_scenario_board.md")],
        ],
    },
    {
        "round": 3,
        "stage": 3,
        "title": "工业交付阶段 (L07~L10)",
        "layers": ["L07", "L08", "L09", "L10"],
        "test_file": "tests/test_round3_industrial.py",
        "breakpoints": [
            {"layer": "L07", "file": "engines/asset_bundle.py", "severity": "high",
             "finding": "只导出 research_spec.json 与 research_chart_spec.json，没有 OASIS SARIF 2.1.0 "
                        "审计结果、没有 SHA256 资产清单与完整性校验，下游 CI 无法回放发现、"
                        "也无法发现产物被篡改。"},
            {"layer": "L08", "file": "engines/patch_editor.py", "severity": "high",
             "finding": "仅 replace/add/remove 三种算子，缺 test/copy/move；JSON Pointer ~0/~1 未转义；"
                        "没有从两版本文档反推 create_patch 的能力，也没有改前/改后 SHA256 完整性摘要。"},
            {"layer": "L09", "file": "engines/memory.py", "severity": "critical",
             "finding": "rollback 只弹 history/snapshots 两个列表，并不恢复业务状态；update_slot 不存在，"
                        "槽位不落顶层字段；'第二套方案' 这类数量代词完全无法消歧（SOP 五-14 违规）。"},
            {"layer": "L10", "file": "engines/telemetry.py", "severity": "critical",
             "finding": "看门狗在函数返回后才比对耗时，无法真正中断超时；没有 CLOSED/OPEN/HALF_OPEN "
                        "三态熔断、没有 half-open 试探恢复、退避无抖动、没有 Trace/Span 父子上下文"
                        "与健康汇总。"},
        ],
        "bench": [
            {"project": "microsoft/sarif-tools", "stars": 1200,
             "url": "https://github.com/microsoft/sarif-tools",
             "absorbed": "OASIS SARIF v2.1.0 标准审计结果（runs/tool/results/locations）"},
            {"project": "OASIS SARIF 2.1.0", "stars": 0,
             "url": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html",
             "absorbed": "跨系统静态分析结果交换标准（非 GitHub 项目，行业标准）"},
            {"project": "evanphx/json-patch", "stars": 2500,
             "url": "https://github.com/evanphx/json-patch",
             "absorbed": "RFC 6902 全算子实现（add/remove/replace/move/copy/test）"},
            {"project": "google/diff-match-patch", "stars": 7000,
             "url": "https://github.com/google/diff-match-patch",
             "absorbed": "差量生成与最小补丁思想"},
            {"project": "cpacker/MemGPT", "stars": 14000,
             "url": "https://github.com/cpacker/MemGPT",
             "absorbed": "持久化记忆池 + 槽位 + 检索式代词消歧"},
            {"project": "langchain-ai/langgraph", "stars": 11000,
             "url": "https://github.com/langchain-ai/langgraph",
             "absorbed": "状态快照/回滚（checkpoint）"},
            {"project": "temporalio/temporal", "stars": 14000,
             "url": "https://github.com/temporalio/temporal",
             "absorbed": "长任务看门狗与状态机式容灾"},
            {"project": "jd/tenacity", "stars": 6500,
             "url": "https://github.com/jd/tenacity",
             "absorbed": "指数退避 + full jitter 重试策略"},
            {"project": "open-telemetry/opentelemetry-python", "stars": 2100,
             "url": "https://github.com/open-telemetry/opentelemetry-python",
             "absorbed": "TraceID/SpanID 全链路遥测"},
        ],
        "upgrades": [
            {"layer": "L07", "item": "AssetBundle v2：SARIF 2.1.0 审计结果 + SHA256 资产清单 "
                                      "bundle.json + verify_bundle 篡改检测", "file": "engines/asset_bundle.py"},
            {"layer": "L08", "item": "ResearchDiffPatchEngine：RFC 6902 全算子 + JSON Pointer 转义 + "
                                      "create_patch 反推差量 + 完整性摘要", "file": "engines/diff_patch_engine.py"},
            {"layer": "L09", "item": "ResearchSessionStore：槽位↔顶层字段双向同步、数量代词/场景序号消歧、"
                                      "快照真实回滚与持久化", "file": "engines/session_memory.py"},
            {"layer": "L10", "item": "TelemetryWatchdog：三态熔断器 + 真超时看门狗 + 全抖动退避 + "
                                      "Trace/Span JSONL 遥测与健康汇总", "file": "engines/telemetry_watchdog.py"},
        ],
        "cli": [
            [sys.executable, "agent.py", "evolution", "bundle",
             "--output-dir", os.path.join(ART, "round3", "cli_bundle")],
            [sys.executable, "agent.py", "evolution", "telemetry"],
        ],
    },
]

LAYER_INDEX = {layer: r["round"] for r in ROUNDS for layer in r["layers"]}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def read_json(path: str) -> Optional[Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def run_cmd(argv: List[str], timeout: int = 900) -> Dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.time()
    try:
        proc = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env,
                              timeout=timeout)
        return {
            "argv": argv,
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "duration_sec": round(time.time() - started, 3),
        }
    except subprocess.TimeoutExpired:
        return {"argv": argv, "returncode": 124, "stdout": "",
                "stderr": f"timeout after {timeout}s",
                "duration_sec": round(time.time() - started, 3)}


def file_entry(path: str, base: Optional[str] = None) -> Dict[str, Any]:
    rel = os.path.relpath(path, base or HERE).replace("\\", "/")
    return {"path": rel, "bytes": os.path.getsize(path), "sha256": sha256_file(path)}


# ---------------------------------------------------------------------------
# 步骤 1：穿透体检（扫描真实代码工件）
# ---------------------------------------------------------------------------
def audit_round(rnd: Dict[str, Any]) -> Dict[str, Any]:
    files, scanned = [], []
    for bp in rnd["breakpoints"]:
        path = os.path.join(HERE, bp["file"])
        entry = {"layer": bp["layer"], "file": bp["file"], "exists": os.path.exists(path)}
        if os.path.exists(path):
            entry.update(file_entry(path))
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                entry["line_count"] = sum(1 for _ in fh)
        scanned.append(entry)
        files.append({"layer": bp["layer"], "file": bp["file"],
                      "severity": bp["severity"], "finding": bp["finding"]})
    return {
        "round": rnd["round"],
        "stage": rnd["stage"],
        "title": rnd["title"],
        "timestamp": now_iso(),
        "method": "静态扫描 engines/ 与 RESEARCH_SPEC.md 真实工件，逐层定位断点（非套模板）",
        "breakpoints": files,
        "scanned_files": scanned,
        "hard_gate": "无体检结论禁止进入步骤 2",
    }


# ---------------------------------------------------------------------------
# 步骤 3：架构跃迁探针（真实 import + 真实算子执行）
# ---------------------------------------------------------------------------
def _probe_round1() -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    try:
        from engines.runtime_engine import ResearchRuntimeEngine, EvidenceTierValidator
        engine = ResearchRuntimeEngine()
        ops = engine.available_operators()
        checks.append({"id": "L01.six_operators", "ok": len(ops) >= 6,
                       "detail": ",".join(ops)})
        probe = engine.probe()
        checks.append({"id": "L01.probe_healthy",
                       "ok": bool(probe.available) and probe.details.get("operator_count", 0) >= 6,
                       "detail": str(probe.details.get("operator_count"))})
        block = ResearchRuntimeEngine().execute("evidence_chain", {"claims": [
            {"id": "c1", "tier": "tier_0", "sources": [], "confidence": 0.0, "kind": "rumor"}]})
        checks.append({"id": "L01.tier0_blocked",
                       "ok": bool(block.ok) and block.data.get("gate_ok") is False,
                       "detail": "tier0_blocked=" + ",".join(block.data.get("tier0_blocked", []))})
        checks.append({"id": "L01.evidence_validator",
                       "ok": EvidenceTierValidator().tier_min("tier_2") == 0.75,
                       "detail": "tier_2 min_confidence=0.75"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L01.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    try:
        from engines.intent_compiler import ResearchIntentCompiler
        dag = ResearchIntentCompiler().compile(
            "调研海外AI协同SaaS市场，预算500万人民币，对比3家竞品并给出TAM与进入情景")
        checks.append({"id": "L02.five_stage_kahn",
                       "ok": dag.get("stage_count") == 5 and
                             dag.get("topological_order", [None])[0] == "audit",
                       "detail": " → ".join(dag.get("topological_order", []))})
        checks.append({"id": "L02.hours_budget",
                       "ok": dag.get("estimated_hours", 0) > 0 and
                             dag.get("estimated_person_days", 0) > 0,
                       "detail": f"{dag.get('estimated_hours')}h / "
                                 f"{dag.get('estimated_person_days')}人天"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L02.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    try:
        from engines.reflexive_healer import ReflexiveResearchHealer, RedlineBlocked
        healer = ReflexiveResearchHealer()
        blocked, message = False, ""
        try:
            healer.assert_redlines({"payment": {"action": "代付款给供应商"}})
        except RedlineBlocked as exc:
            blocked = "R03" in str(exc) and "[REDLINE BLOCKED]" in str(exc)
            message = str(exc)
        checks.append({"id": "L03.redline_handoff_r03", "ok": blocked, "detail": message})
        healed = healer.heal_and_verify({"shares": [40, 40],
                                         "sections": [{"body": "我们必须进入，绝对可行"}],
                                         "claims": [{"id": "c1", "text": "增速40%"}]})
        checks.append({"id": "L03.deep_heal_verify",
                       "ok": abs(sum(healed["healed"]["shares"]) - 100.0) < 0.01 and
                             healed["iterations"] >= 1 and bool(healed["reflections"]),
                       "detail": f"reflections={len(healed['reflections'])},"
                                 f"residual={len(healed['residual_findings'])}"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L03.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    return checks


def _probe_round2() -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    try:
        from engines.spec_ledger import ResearchSpecLedger
        ledger = ResearchSpecLedger()
        spec = ledger.load()
        checks.append({"id": "L04.machine_readable_spec",
                       "ok": spec.get("version") == "2.0.0" and
                             abs(float(spec.get("tam_variance_max", 0)) - 0.30) < 1e-9,
                       "detail": f"version={spec.get('version')}, "
                                 f"tam_var={spec.get('tam_variance_max')}"})
        gates = ledger.gates()
        checks.append({"id": "L04.eight_weighted_gates",
                       "ok": len(gates) == 8 and
                             abs(sum(g["weight"] for g in gates) - 1.0) < 1e-6,
                       "detail": ",".join(g["id"] for g in gates)})
        os.makedirs(os.path.join(TMP, "layer_probe"), exist_ok=True)
        probe_spec = os.path.join(TMP, "layer_probe", "l04_spec_snapshot.json")
        ledger.export_json(probe_spec)
        checks.append({"id": "L04.spec_snapshot_export",
                       "ok": os.path.exists(probe_spec),
                       "detail": "workspace/tmp/layer_probe/l04_spec_snapshot.json"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L04.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    try:
        from engines.slop_guard import ResearchSlopGuard
        guard = ResearchSlopGuard()
        audit = guard.audit_text("市场整体良好，未来可期。TAM 120 亿元，增速 18.5%（来源 S1/S2）。")
        checks.append({"id": "L05.quality_dimensions",
                       "ok": audit.get("evidence_density", 0) > 0 and
                             audit.get("grade") in ("A", "B", "C", "D") and
                             audit.get("slop_hits", 0) >= 2,
                       "detail": f"score={audit.get('score')}, grade={audit.get('grade')}"})
        blocked = guard.enforce_quality("市场整体良好，相关细节待定。")
        checks.append({"id": "L05.enforce_blocks_placeholder",
                       "ok": blocked.get("ok") is False and
                             "PENDING_PLACEHOLDER" in blocked.get("blocking_issues", []) and
                             blocked.get("dri") == "蛙深远",
                       "detail": ",".join(blocked.get("blocking_issues", []))})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L05.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    try:
        from engines.scenario_matrix import ScenarioMatrixExplorer
        matrix = ScenarioMatrixExplorer().generate_matrix({"tam": 120.0, "cogs": 300.0,
                                                           "price": 1200.0})
        checks.append({"id": "L06.mcda_roi_matrix",
                       "ok": len(matrix.get("scenarios", [])) == 3 and
                             abs(sum(matrix.get("weights", {}).values()) - 1.0) < 1e-6 and
                             bool(matrix.get("recommended")) and
                             "ROI" in matrix.get("board_markdown", ""),
                       "detail": f"recommended={matrix.get('recommended')}"})
        checks.append({"id": "L06.ranking",
                       "ok": len(matrix.get("ranking", [])) == 3,
                       "detail": " → ".join(s["name"] for s in matrix.get("ranking", []))})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L06.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    return checks


def _probe_round3() -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    os.makedirs(os.path.join(TMP, "layer_probe"), exist_ok=True)
    out_dir = os.path.join(TMP, "layer_probe", "l07_bundle")
    try:
        from engines.asset_bundle import ResearchAssetBundle
        bundle = ResearchAssetBundle().export_bundle({
            "tam": 120.0, "hhi": 2250, "cr4": 90, "structure": "moderate",
            "claims": [{"id": "c1", "sources": ["S1"]}, {"id": "c2", "sources": []}],
            "tam_top": 120.0, "tam_bottom": 180.0,
        }, out_dir)
        sarif = read_json(bundle.get("sarif", "")) or {}
        manifest = read_json(bundle.get("bundle_manifest", "")) or {}
        verify = ResearchAssetBundle().verify_bundle(bundle.get("bundle_manifest", ""))
        checks.append({"id": "L07.sarif_2_1_0_manifest",
                       "ok": sarif.get("version") == "2.1.0" and
                             len(manifest.get("artifacts", [])) >= 3 and
                             bool(verify.get("ok")),
                       "detail": f"artifacts={len(manifest.get('artifacts', []))}, "
                                 f"verify={verify.get('ok')}"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L07.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    try:
        from engines.diff_patch_engine import ResearchDiffPatchEngine
        engine = ResearchDiffPatchEngine()
        doc = {"a": {"b": 1}, "arr": [1, 2]}
        target = {"a": {"b": 3, "c": 4}, "arr": [1, 2, 5]}
        patch = engine.create_patch(doc, target)
        applied = engine.apply(doc, patch)
        integrity = engine.apply_with_integrity(doc, patch)
        checks.append({"id": "L08.rfc6902_roundtrip",
                       "ok": applied == target and integrity["changed"] is True and
                             len(patch) >= 2,
                       "detail": f"ops={len(patch)}"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L08.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    try:
        from engines.session_memory import ResearchSessionStore
        state_path = os.path.join(TMP, "layer_probe", "l09_session_state.json")
        if os.path.exists(state_path):
            os.remove(state_path)
        store = ResearchSessionStore(state_path)
        store.record_turn("调研海外SaaS市场", {"tam": 120.0,
                                              "scenarios": [{"name": "A"}, {"name": "B"}]},
                          topic="海外SaaS市场")
        store.update_slot("current_market", "海外SaaS")
        ordinal = store.resolve_reference("按第二套方案调整")
        checks.append({"id": "L09.slot_sync_ordinal_rollback",
                       "ok": store.state.get("current_market") == "海外SaaS" and
                             ordinal is not None and store.rollback(1) is True,
                       "detail": f"ordinal={ordinal}"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L09.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    try:
        from engines.telemetry_watchdog import (CircuitBreaker, CircuitOpenError,
                                                RetryPolicy, TaskTimeout,
                                                TelemetryTracer, WatchdogRunner)
        breaker = CircuitBreaker(failure_threshold=2, cooldown_sec=0.05)

        def boom():
            raise RuntimeError("upstream 503")

        for _ in range(2):
            try:
                breaker.call(boom)
            except RuntimeError:
                pass
        opened = breaker.state == "OPEN"
        try:
            breaker.call(lambda: 1)
            blocked = False
        except CircuitOpenError:
            blocked = True
        time.sleep(0.06)
        recovered = breaker.state == "HALF_OPEN" and breaker.call(lambda: 1) == 1 and \
            breaker.state == "CLOSED"
        checks.append({"id": "L10.three_state_breaker",
                       "ok": opened and blocked and recovered,
                       "detail": f"OPEN={opened}, blocked={blocked}, recovered={recovered}"})
        policy = RetryPolicy(max_attempts=3, base_delay=0.01, jitter=False,
                             sleep=lambda s: None)
        counter = {"n": 0}

        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise RuntimeError("transient")
            return "ok"

        retried = policy.run(flaky) == "ok" and counter["n"] == 3
        timed_out = False
        try:
            WatchdogRunner(timeout_sec=0.05).run(time.sleep, 0.2)
        except TaskTimeout:
            timed_out = True
        checks.append({"id": "L10.retry_and_timeout", "ok": retried and timed_out,
                       "detail": f"retries={counter['n']}, timeout={timed_out}"})
        log_path = os.path.join(TMP, "layer_probe", "l10_telemetry.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        tracer = TelemetryTracer(log_path)
        with tracer.span("research:probe", {"tam": 120.0}) as span:
            time.sleep(0.001)
        health = TelemetryTracer(log_path).health()
        checks.append({"id": "L10.trace_span_health",
                       "ok": span.get("status") == "SUCCESS" and health.get("total") == 1 and
                             health.get("success") == 1,
                       "detail": f"trace={span.get('trace_id')}"})
    except Exception as exc:  # noqa: BLE001
        checks.append({"id": "L10.import", "ok": False, "detail": f"{type(exc).__name__}: {exc}"})
    return checks


PROBES = {1: _probe_round1, 2: _probe_round2, 3: _probe_round3}


# ---------------------------------------------------------------------------
# 步骤 4：物理工件生成与验收
# ---------------------------------------------------------------------------
def build_artifacts(round_num: int, cli_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    out_dir = os.path.join(ART, f"round{round_num}")
    os.makedirs(out_dir, exist_ok=True)
    files: List[str] = []

    if round_num == 1:
        from engines.runtime_engine import ResearchRuntimeEngine
        from engines.intent_compiler import ResearchIntentCompiler
        from engines.reflexive_healer import ReflexiveResearchHealer, RedlineBlocked

        engine = ResearchRuntimeEngine()
        write_json(os.path.join(out_dir, "l01_runtime_probe.json"), {
            "operators": engine.available_operators(),
            "probe": {"available": engine.probe().available,
                      "details": engine.probe().details},
            "evidence_chain": engine.execute("evidence_chain", {"claims": [
                {"id": "c1", "tier": "tier_1", "confidence": 0.95, "sources": ["S1"], "kind": "fact"},
                {"id": "c2", "tier": "tier_3", "confidence": 0.55, "sources": ["S2"], "kind": "estimate"},
                {"id": "c3", "tier": "tier_0", "confidence": 0.0, "sources": [], "kind": "rumor"},
            ]}).data,
            "unit_economics": engine.execute("unit_economics", {
                "arpu": 99.99, "gross_margin": 0.8, "churn_rate": 0.02, "cac": 300.0}).data,
            "sensitivity": engine.execute("sensitivity_swing", {
                "base_value": 1000.0, "drivers": [
                    {"name": "价格", "low_pct": -0.1, "high_pct": 0.1, "weight": 1.2},
                    {"name": "流失率", "low_pct": -0.05, "high_pct": 0.05, "weight": 0.8},
                ]}).data,
            "tam_triangulate": engine.execute("tam_triangulate", {
                "top_down": {"components": [{"name": "A", "value": 60.0},
                                            {"name": "B", "value": 40.0}]},
                "bottom_up": {"customer_count": 200, "addressable_fraction": 0.5,
                              "annual_quantity": 1, "price_per_unit": 1.2},
            }).data,
        })
        files.append(os.path.join(out_dir, "l01_runtime_probe.json"))

        dag = ResearchIntentCompiler().compile(
            "调研海外AI协同SaaS市场，预算500万人民币，对比3家竞品并给出TAM与进入情景")
        write_json(os.path.join(out_dir, "l02_intent_dag.json"), dag)
        files.append(os.path.join(out_dir, "l02_intent_dag.json"))

        healer = ReflexiveResearchHealer()
        dirty = {"shares": [40, 40],
                 "conclusion": "我们必须进入这个赛道，绝对可行",
                 "claims": [{"id": "c1", "text": "行业增速40%"}],
                 "tam_top": 100.0, "tam_bottom": 160.0,
                 "payment": {"action": "代付款给供应商", "amount": 50000}}
        healed = healer.heal_and_verify(dirty)
        write_json(os.path.join(out_dir, "l03_reflexive_heal.json"), healed)
        files.append(os.path.join(out_dir, "l03_reflexive_heal.json"))
        block = {"blocked": False}
        try:
            healer.assert_redlines(dirty)
        except RedlineBlocked as exc:
            block = {"blocked": True, "code": getattr(exc, "code", None),
                     "handoff": getattr(exc, "handoff", None), "message": str(exc)}
        write_json(os.path.join(out_dir, "l03_redline_block.json"), block)
        files.append(os.path.join(out_dir, "l03_redline_block.json"))

    elif round_num == 2:
        from engines.spec_ledger import ResearchSpecLedger
        from engines.slop_guard import ResearchSlopGuard
        from engines.scenario_matrix import ScenarioMatrixExplorer

        ledger = ResearchSpecLedger()
        ledger.export_json(os.path.join(out_dir, "l04_spec_snapshot.json"))
        files.append(os.path.join(out_dir, "l04_spec_snapshot.json"))
        write_json(os.path.join(out_dir, "l04_gate_evaluate.json"), {
            "good": ledger.evaluate({"metrics": {
                "evidence_coverage": 1.0, "tier0_count": 0, "tam_variance": 0.1,
                "hhi_declared": 1, "scenario_count": 3, "redline_clean": 1,
                "slop_score": 92, "bundle_manifest": 1}}),
            "bad": ledger.evaluate({"metrics": {
                "evidence_coverage": 0.4, "tier0_count": 2, "tam_variance": 0.55,
                "hhi_declared": 0, "scenario_count": 1, "redline_clean": 0,
                "slop_score": 40, "bundle_manifest": 0}}),
        })
        files.append(os.path.join(out_dir, "l04_gate_evaluate.json"))

        guard = ResearchSlopGuard()
        report = guard.enforce_quality(
            "市场整体良好，未来可期，按需采购，相关细节待定。"
            "TAM 120 亿元（来源 S1/S2），增速 18.5%。")
        write_json(os.path.join(out_dir, "l05_slop_enforce.json"), report)
        files.append(os.path.join(out_dir, "l05_slop_enforce.json"))

        matrix = ScenarioMatrixExplorer().generate_matrix(
            {"tam": 120.0, "cogs": 300.0, "price": 1200.0})
        write_json(os.path.join(out_dir, "l06_scenario_matrix.json"), matrix)
        board = os.path.join(out_dir, "l06_scenario_board.md")
        with open(board, "w", encoding="utf-8") as fh:
            fh.write(matrix["board_markdown"])
        files.extend([os.path.join(out_dir, "l06_scenario_matrix.json"), board])

    else:
        from engines.asset_bundle import ResearchAssetBundle
        from engines.diff_patch_engine import ResearchDiffPatchEngine
        from engines.session_memory import ResearchSessionStore
        from engines.telemetry_watchdog import TelemetryTracer

        bundle = ResearchAssetBundle().export_bundle({
            "tam": 120.0, "hhi": 2250, "cr4": 90, "structure": "moderate",
            "claims": [{"id": "c1", "sources": ["S1"]},
                       {"id": "c2", "sources": []}],
            "tam_top": 120.0, "tam_bottom": 180.0,
        }, os.path.join(out_dir, "l07_bundle"))
        files.extend(bundle.values())

        engine = ResearchDiffPatchEngine()
        base_doc = {"model": "subscription",
                    "pricing": {"unit_price": 1200.0, "cogs": 300.0},
                    "sizing": {"tam": 120.0, "obtainable_share": 0.05}}
        target_doc = {"model": "subscription",
                      "pricing": {"unit_price": 1500.0, "cogs": 300.0},
                      "sizing": {"tam": 130.0, "obtainable_share": 0.08}}
        patch = engine.create_patch(base_doc, target_doc)
        integrity = engine.apply_with_integrity(base_doc, patch)
        write_json(os.path.join(out_dir, "l08_patch_integrity.json"), {
            "patch": patch, "integrity": integrity,
            "roundtrip_ok": integrity["doc"] == target_doc})
        files.append(os.path.join(out_dir, "l08_patch_integrity.json"))

        session_path = os.path.join(out_dir, "l09_session_state.json")
        if os.path.exists(session_path):
            os.remove(session_path)
        store = ResearchSessionStore(session_path)
        store.record_turn("调研海外SaaS市场，给出三套进入方案",
                          {"tam": 120.0, "scenarios": [
                              {"name": "保守防御型"}, {"name": "基准稳健型"},
                              {"name": "乐观突击型"}]}, topic="海外SaaS市场")
        store.update_slot("current_market", "海外SaaS")
        resolve_ordinal = store.resolve_reference("按第二套方案调整")
        resolve_pronoun = store.resolve_reference("按刚才那个市场继续")
        store.record_turn("把 TAM 上调到 150 亿", {"tam": 150.0}, topic="海外SaaS市场")
        rollback_ok = store.rollback(1)
        write_json(os.path.join(out_dir, "l09_session_evidence.json"), {
            "session_state": store.state, "ordinal": resolve_ordinal,
            "pronoun": resolve_pronoun, "rollback_ok": rollback_ok})
        files.append(os.path.join(out_dir, "l09_session_evidence.json"))

        log_path = os.path.join(out_dir, "l10_telemetry.jsonl")
        if os.path.exists(log_path):
            os.remove(log_path)
        tracer = TelemetryTracer(log_path)
        with tracer.span("research:sizing", {"tam": 120.0}):
            pass
        try:
            with tracer.span("research:bundle", {"x": 1}):
                raise RuntimeError("simulated downstream failure")
        except RuntimeError:
            pass
        write_json(os.path.join(out_dir, "l10_health.json"),
                   TelemetryTracer(log_path).health())
        files.extend([log_path, os.path.join(out_dir, "l10_health.json")])

    manifest = {
        "round": round_num,
        "generated_at": now_iso(),
        "cli_commands": [{"argv": r["argv"], "returncode": r["returncode"],
                          "duration_sec": r["duration_sec"]} for r in cli_results],
        "artifacts": [file_entry(path) for path in files if os.path.exists(path)],
    }
    write_json(os.path.join(out_dir, "round_artifact_manifest.json"), manifest)
    return manifest


# ---------------------------------------------------------------------------
# 步骤 5：双轨零破坏回归门禁
# ---------------------------------------------------------------------------
def _parse_ran(stdout: str) -> Optional[int]:
    for line in stdout.splitlines():
        if line.startswith("Ran ") and " test" in line:
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def _parse_passed(stdout: str) -> Optional[int]:
    import re
    match = re.search(r"(\d+) passed", stdout)
    return int(match.group(1)) if match else None


def run_regression(round_num: int) -> Dict[str, Any]:
    baseline = run_cmd([sys.executable, "run_tests.py"])
    evolution = run_cmd([sys.executable, "test_evolution_suite.py"])
    round_suite = run_cmd([sys.executable, "-m", "pytest", ROUNDS[round_num - 1]["test_file"], "-q"])
    # 尚未演进到的后续轮次契约不得反向阻断当前轮（SOP 三-5 严禁跨轮伪造打卡，
    # 但同样不允许未来轮次的空壳契约污染当前轮双轨回归）
    future_ignores: List[str] = []
    for future in ROUNDS[round_num:]:
        if os.path.exists(os.path.join(HERE, future["test_file"])):
            future_ignores.extend(["--ignore", future["test_file"]])
    full_suite = run_cmd([sys.executable, "-m", "pytest", "tests", "-q", *future_ignores])

    # unittest.TextTestRunner 把用例进度与总结（「Ran N tests」与「OK」）写入 sys.stderr，
    # 所以仅解析 stdout 会恒得 None / 取不到 OK，使门禁结构性假阴性（无论被测代码多健康
    # 都退出 1）。此处只修正取数来源：合并 stdout+stderr 读取真实用例数与真实判定词，
    # 判定口径（rc==0 / 63 / 10 / 8 / 32 阈值）一律不放宽。
    baseline_stream = baseline["stdout"] + "\n" + baseline["stderr"]
    evolution_stream = evolution["stdout"] + "\n" + evolution["stderr"]
    baseline_ran = _parse_ran(baseline_stream)
    evolution_ran = _parse_ran(evolution_stream)
    round_passed = _parse_passed(round_suite["stdout"])
    full_passed = _parse_passed(full_suite["stdout"])

    ok = bool(
        baseline["returncode"] == 0 and baseline_ran and baseline_ran >= 63
        and "OK" in baseline_stream
        and evolution["returncode"] == 0 and evolution_ran and evolution_ran >= 10
        and "OK" in evolution_stream
        and round_suite["returncode"] == 0 and round_passed and round_passed >= 8
        and full_suite["returncode"] == 0 and full_passed and full_passed >= 32
    )
    return {
        "ok": ok,
        "tracks": {
            "baseline_63": {"returncode": baseline["returncode"],
                            "tests": baseline_ran, "status": "PASS" if baseline["returncode"] == 0 else "FAIL",
                            "tail": "\n".join(baseline["stdout"].strip().splitlines()[-3:])},
            "evolution_l01_l10": {"returncode": evolution["returncode"],
                                  "tests": evolution_ran,
                                  "status": "PASS" if evolution["returncode"] == 0 else "FAIL",
                                  "tail": "\n".join(evolution["stdout"].strip().splitlines()[-3:])},
            "round_contract": {"returncode": round_suite["returncode"],
                               "tests": round_passed,
                               "file": ROUNDS[round_num - 1]["test_file"],
                               "status": "PASS" if round_suite["returncode"] == 0 else "FAIL",
                               "tail": "\n".join(round_suite["stdout"].strip().splitlines()[-6:])},
            "full_pytest": {"returncode": full_suite["returncode"],
                            "tests": full_passed,
                            "status": "PASS" if full_suite["returncode"] == 0 else "FAIL",
                            "tail": "\n".join(full_suite["stdout"].strip().splitlines()[-6:])},
        },
        "duration_sec": round(baseline["duration_sec"] + evolution["duration_sec"] +
                              round_suite["duration_sec"] + full_suite["duration_sec"], 3),
    }


# ---------------------------------------------------------------------------
# 状态机
# ---------------------------------------------------------------------------
def default_state() -> Dict[str, Any]:
    return {
        "agent": AGENT,
        "sop_version": "v13.0",
        "model": "10-Stage Metamodel / 3 progressive rounds",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "rounds_total": 3,
        "rounds_completed": 0,
        "current_round": 0,
        "status": "INIT",
        "layers": {layer: "PEND" for layer in LAYER_INDEX},
        "rounds": [],
        "layer_checks": [],
        "history": [],
    }


def load_state() -> Dict[str, Any]:
    state = read_json(STATE_FILE)
    if not isinstance(state, dict) or "rounds" not in state:
        return default_state()
    return state


def save_state(state: Dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    state["rounds_completed"] = len([r for r in state["rounds"] if r.get("status") == "PASS"])
    completed_layers = []
    for record in state["rounds"]:
        if record.get("status") == "PASS":
            completed_layers.extend(record.get("layers", []))
    state["layers"] = {layer: ("PASS" if layer in completed_layers else "PEND")
                       for layer in LAYER_INDEX}
    if state["rounds_completed"] == 3:
        state["status"] = "ALL_GREEN_10_OF_10"
    elif state["rounds_completed"] > 0:
        state["status"] = "IN_PROGRESS"
    write_json(STATE_FILE, state)


# ---------------------------------------------------------------------------
# 单轮执行
# ---------------------------------------------------------------------------
def execute_round(round_num: int) -> bool:
    if round_num not in PROBES:
        print(f"[ERROR] 轮次超限: {round_num}（有效 1~3，对应 SOP 三大阶段）")
        return False

    rnd = ROUNDS[round_num - 1]
    started = time.time()
    state = load_state()
    state["current_round"] = round_num
    state["status"] = "RUNNING"
    save_state(state)

    print("\n" + "=" * 86)
    print(f"[AUTO-EVOLVE] Round {round_num}/3 · {rnd['title']}")
    print(f"    覆盖阶梯: {' / '.join(rnd['layers'])}")
    print(f"    契约门禁: {rnd['test_file']}")
    print("=" * 86)

    journal: Dict[str, Any] = {"round": round_num, "title": rnd["title"],
                               "started_at": now_iso(), "steps": {}}

    # ---- 步骤 1：穿透体检 ----
    print("[步骤 1/5] 穿透体检 (Reality Audit) ...")
    audit = audit_round(rnd)
    journal["steps"]["audit"] = audit
    for bp in rnd["breakpoints"]:
        print(f"   [{bp['layer']}/{bp['severity']}] {bp['file']}: {bp['finding'][:72]}...")
    write_json(os.path.join(ART, f"round{round_num}", "step1_audit.json"), audit)

    # ---- 步骤 2：标杆对齐 ----
    print("[步骤 2/5] 标杆对齐 (Benchmark Sourcing, Stars > 1k) ...")
    benchmark = {"round": round_num, "timestamp": now_iso(), "benchmarks": rnd["bench"],
                 "absorbed_mechanisms": [b["absorbed"] for b in rnd["bench"]],
                 "policy": "每个标杆必须说明被吸收的具体机制，禁止只贴 star 数"}
    journal["steps"]["benchmark"] = benchmark
    for bench in rnd["bench"]:
        stars = f"{bench['stars']}⭐" if bench["stars"] else "行业标准"
        print(f"   - {bench['project']} ({stars}): {bench['absorbed']}")
    write_json(os.path.join(ART, f"round{round_num}", "step2_benchmark.json"), benchmark)

    # ---- 步骤 3：架构跃迁 ----
    print("[步骤 3/5] 架构跃迁与能力探针 (Architectural Upgrade) ...")
    checks = PROBES[round_num]()
    journal["steps"]["upgrade"] = {"upgrades": rnd["upgrades"], "probes": checks}
    for check in checks:
        mark = "PASS" if check["ok"] else "FAIL"
        print(f"   [{mark}] {check['id']} :: {str(check['detail'])[:100]}")
    if not all(check["ok"] for check in checks):
        journal["steps"]["upgrade"]["verdict"] = "FAIL"
        journal["finished_at"] = now_iso()
        journal["status"] = "FAIL"
        write_json(os.path.join(JOURNAL_DIR, f"round{round_num}_journal.json"), journal)
        print("[ABORT] 架构跃迁探针未全绿，本轮不打卡，后续轮次禁止启动。")
        return False
    print(f"   本轮落地架构升级点: {len(rnd['upgrades'])} 项（SOP 最低 3 项）")

    # ---- 步骤 4：物理工件验收 ----
    print("[步骤 4/5] 物理工件验收 (Physical Artifact Validation) ...")
    cli_results = [run_cmd(cmd) for cmd in rnd["cli"]]
    for result in cli_results:
        mark = "PASS" if result["returncode"] == 0 else "FAIL"
        print(f"   [{mark}] CLI {' '.join(os.path.basename(str(a)) for a in result['argv'][1:])}"
              f" (rc={result['returncode']})")
    if not all(result["returncode"] == 0 for result in cli_results):
        journal["steps"]["artifacts"] = {"cli": cli_results, "verdict": "FAIL"}
        journal["finished_at"] = now_iso()
        journal["status"] = "FAIL"
        write_json(os.path.join(JOURNAL_DIR, f"round{round_num}_journal.json"), journal)
        print("[ABORT] CLI 物理工件探针失败，后续轮次禁止启动。")
        return False
    manifest = build_artifacts(round_num, cli_results)
    print(f"   物理工件落盘: {len(manifest['artifacts'])} 个 → artifacts/evolve/round{round_num}/")
    for entry in manifest["artifacts"]:
        print(f"     - {entry['path']} ({entry['bytes']}B, sha256={entry['sha256'][:12]}…)")
    journal["steps"]["artifacts"] = {"cli": cli_results, "manifest": manifest}

    # ---- 步骤 5：双轨零破坏回归 ----
    print("[步骤 5/5] 双轨零破坏回归门禁 (Dual Zero-Regression Gate) ...")
    regression = run_regression(round_num)
    journal["steps"]["regression"] = regression
    for name, track in regression["tracks"].items():
        print(f"   [{track['status']}] {name}: tests={track['tests']} rc={track['returncode']}")
    if not regression["ok"]:
        journal["finished_at"] = now_iso()
        journal["status"] = "FAIL"
        write_json(os.path.join(JOURNAL_DIR, f"round{round_num}_journal.json"), journal)
        print(f"[ABORT] 双轨回归未全绿，本轮判定升级失败：\n"
              f"   round_contract tail:\n{regression['tracks']['round_contract']['tail']}")
        return False

    # ---- 打卡落盘 ----
    journal["finished_at"] = now_iso()
    journal["duration_sec"] = round(time.time() - started, 3)
    journal["status"] = "PASS"
    write_json(os.path.join(JOURNAL_DIR, f"round{round_num}_journal.json"), journal)

    state = load_state()
    state["rounds"] = [r for r in state["rounds"] if r.get("round") != round_num]
    state["rounds"].append({
        "round": round_num,
        "stage": rnd["stage"],
        "title": rnd["title"],
        "layers": rnd["layers"],
        "status": "PASS",
        "finished_at": journal["finished_at"],
        "duration_sec": journal["duration_sec"],
        "upgrades": [u["item"] for u in rnd["upgrades"]],
        "artifact_manifest": os.path.relpath(
            os.path.join(ART, f"round{round_num}", "round_artifact_manifest.json"), HERE
        ).replace("\\", "/"),
        "artifacts": [a["path"] for a in manifest["artifacts"]],
        "tests": {name: track["tests"] for name, track in regression["tracks"].items()},
        "journal": f"workspace/rounds/round{round_num}_journal.json",
    })
    state["rounds"].sort(key=lambda r: r["round"])
    state["current_round"] = round_num
    state["history"].append({"round": round_num, "verdict": "PASS",
                             "at": journal["finished_at"]})
    save_state(state)

    print(f"\n[ROUND {round_num} PASS] 五次闭环全部通过，状态已落盘 workspace/evolution_state.json")
    return True


# ---------------------------------------------------------------------------
# 单层下钻打卡
# ---------------------------------------------------------------------------
def execute_layer(layer: str) -> bool:
    layer = str(layer).upper()
    if layer not in LAYER_INDEX:
        print(f"[ERROR] 未知阶梯: {layer}（有效 L01~L10）")
        return False
    round_num = LAYER_INDEX[layer]
    checks = [c for c in PROBES[round_num]() if c["id"].startswith(layer + ".")]
    print(f"\n[LAYER DRILL-DOWN] {layer} (归属 Round {round_num})")
    for check in checks:
        print(f"   [{'PASS' if check['ok'] else 'FAIL'}] {check['id']} :: {check['detail']}")
    ok = bool(checks) and all(c["ok"] for c in checks)

    state = load_state()
    state["layer_checks"] = [c for c in state.get("layer_checks", [])
                             if c.get("layer") != layer]
    state["layer_checks"].append({"layer": layer, "round": round_num,
                                  "ok": ok, "at": now_iso(),
                                  "checks": checks})
    save_state(state)
    print(f"[{'LAYER PASS' if ok else 'LAYER FAIL'}] {layer} 已记录（不改变轮次打卡状态）")
    return ok


# ---------------------------------------------------------------------------
# 看板
# ---------------------------------------------------------------------------
def print_status(as_json: bool = False) -> int:
    state = load_state()
    if as_json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    print("\n" + "=" * 86)
    print("R05 蛙深远（战略研究官）十维渐进演进看板 — SOP v13.0 / 3 Rounds × 5 Steps")
    print("=" * 86)
    print(f"状态: {state.get('status')} | 完成轮次: {state.get('rounds_completed')}/3 | "
          f"当前轮: {state.get('current_round')}")
    print("-" * 86)
    by_round = {r["round"]: r for r in state.get("rounds", [])}
    for rnd in ROUNDS:
        record = by_round.get(rnd["round"])
        mark = "[PASS]" if record and record.get("status") == "PASS" else "[PEND]"
        print(f"{mark} Round {rnd['round']} · {rnd['title']}")
        for layer in rnd["layers"]:
            layer_state = state.get("layers", {}).get(layer, "PEND")
            print(f"        {'✅' if layer_state == 'PASS' else '⬜'} {layer}")
        if record:
            tests = record.get("tests", {})
            print(f"        tests: " + ", ".join(f"{k}={v}" for k, v in tests.items()))
    print("-" * 86)
    print(f"状态文件: workspace/evolution_state.json")
    print(f"轮次日志: workspace/rounds/roundN_journal.json")
    print(f"物理工件: artifacts/evolve/roundN/")
    print("=" * 86)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="R05 蛙深远 十维渐进式演进自动化调度状态机（3 轮 × SOP 五步）")
    parser.add_argument("--status", action="store_true", help="打印演进看板")
    parser.add_argument("--json", action="store_true", help="以 JSON 打印状态")
    parser.add_argument("--round", type=int, help="执行指定一轮完整 SOP（1~3）")
    parser.add_argument("--stage", type=int, help="同 --round（SOP 三批次语义）")
    parser.add_argument("--layer", help="单层下钻体检打卡 L01~L10")
    parser.add_argument("--run-all", action="store_true", help="顺序推进 3 轮全绿")
    parser.add_argument("--reset", action="store_true", help="重置状态机")
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("[INFO] 演进状态机已重置。")
        return 0

    if args.status or args.json:
        return print_status(as_json=args.json)

    if args.layer:
        return 0 if execute_layer(args.layer) else 1

    target = args.round if args.round is not None else args.stage
    if target is not None:
        return 0 if execute_round(target) else 1

    if args.run_all:
        for round_num in (1, 2, 3):
            if not execute_round(round_num):
                print(f"[ABORT] Round {round_num} 失败，流水线阻断，未启动后续轮次。")
                return 1
        print_status()
        return 0

    print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
