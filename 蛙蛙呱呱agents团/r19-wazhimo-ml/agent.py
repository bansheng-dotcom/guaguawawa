#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R19 蛙智模 · 模型工程与 AI 评估官 —— 本地可运行 Agent（七技能调度器）。

把 7 个能力域各自做成一个独立技能模块（skills/s01..s07），本文件只做三件事：
    1. 注册 7 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    需求 + 数据集 + 服务集成 → 可复现实验/评估报告/模型版本/发布证据

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py tracking experiment --input examples/tracking_experiment.json
    python agent.py release candidate --input examples/release_candidate.json
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3 / SOP v13.0 §5.9） ---
# 动态防爆探测：本目录 + agents 集合目录 + 仓库根同时入 sys.path。
# 修掉「异构 cwd 下 `ModuleNotFoundError: No module named 'agents'`」历史故障
# （原实现把三层 dirname 算成仓库根、且在 chat_cli 导入之后才注入 agents 根，
# 导致 `python agent.py` 在本目录直接起不来 —— R19 L01 体检断点 #1）。
import os as _os
import sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_AGENTS = _os.path.dirname(_HERE)
_REPO_ROOT = _os.path.dirname(_AGENTS)
for _p in (_HERE, _AGENTS, _REPO_ROOT):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)


import argparse
import hashlib
import json
import os
import sys
from agents.shared.chat_cli import add_chat_parser, handle_chat
import time
from typing import Any, Dict, List, Optional

from core import protocol, registry, workspace  # noqa: E402
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402
from agents.shared import role_runtime  # noqa: E402
from skills import SKILLS, _common as c  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402
import local_exec  # noqa: E402

ROLE = "r19"
WORKSPACE_ROOT = os.path.join(_AGENTS, "workspace")
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
# 注意「发布/上线/裁决」(release) 必须排在「注册」(registry) 之前——发布候选
# 的候选 ID 里可能含「版本」字样，不能误路由到 registry（R19 猜坑：发布裁决
# vs 版本登记动作错配）。「评估」(evaluation) 要排在「追踪」(tracking) 之前，
# 因为评估任务常同时提到「实验」。
_INTENT_ROUTES = [
    (("发布", "上线", "放行", "裁决", "回归", "回退", "阻断", "release",
      "candidate", "block"), "release", "candidate", {}),
    (("回归测试", "fail-before", "pass-after", "新旧版本", "根因", "诊断层"),
     "release", "regression", {}),
    (("评估", "评测", "评分", "打分", "scorer", "judge", "指标对比", "evaluation"),
     "evaluation", "scorer", {}),
    (("评估集", "数据集准备", "ground truth", "expectations", "评测集", "标注集"),
     "evaluation", "dataset", {}),
    (("追踪", "实验", "运行记录", "参数", "指标记录", "tracking", "run"),
     "tracking", "run", {}),
    (("实验登记", "实验创建", "实验元数据", "tracking_uri", "experiment"), "tracking",
     "experiment", {}),
    (("注册", "模型版本", "模型入库", "阶段", "staging", "production产出",
      "registry"), "registry", "register", {}),
    (("版本清单", "版本列表", "多版本", "版本历史"), "registry", "version", {}),
    (("trace", "跨度", "span", "链路", "错误定位", "调试", "追踪分析"), "trace",
     "analyze", {}),
    (("检索", "过滤", "搜索trace", "拉取trace", "retrieval", "filter"), "trace",
     "retrieval", {}),
    (("监控", "指标查询", "聚合", "趋势", "metric", "monitor"), "monitor", "metrics", {}),
    (("漂移", "告警阈值", "drift", "数据漂移", "模型漂移"), "monitor", "drift", {}),
    (("模型卡", "用途", "限制", "风险分层", "许可", "model card", "modelcard"), "modelcard",
     "card", {}),
    (("资产", "产物", "artifact", "模型文件", "评估报告文件"), "modelcard", "asset", {}),
]

_DEFAULT_ROUTE = ("evaluation", "scorer", {})


def emit_result(data: Dict[str, Any]) -> None:
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py",
                                description="R19 蛙智模 · 模型工程与 AI 评估官")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    local = sp.add_parser("local", help="本地评估集评分与模型卡，不发布")
    local.add_argument("--input", required=True)
    sp.add_parser("demo", help="生成示例工件")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)
    add_clarify_parser(sp)

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)
    _register_evolve(sp)

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_evolve(sp) -> None:
    """十维演进元模型核心引擎调度（L01~L10），供 auto_evolve_runner 物理验收。"""
    ev = sp.add_parser("evolve", help="十维演进元模型核心引擎调度 (L01~L10)")
    sub = ev.add_subparsers(dest="evolve_cmd", required=True)

    p1 = sub.add_parser("probe", help="L01: 真实评估精算沙箱健康探测")
    p1.add_argument("--out", default="")

    p2 = sub.add_parser("decompile", help="L02: 复合诉求 → 5 阶段 Kahn DAG")
    p2.add_argument("--text", required=True)
    p2.add_argument("--out", default="")
    p2.add_argument("--md", default="")

    p3 = sub.add_parser("heal", help="L03: 红线审判与 Reflexion 自愈")
    p3.add_argument("--action", default="")
    p3.add_argument("--artifact", default="")
    p3.add_argument("--out", default="")

    p4 = sub.add_parser("spec", help="L04: ML_SPEC 账本加载与 8 维门禁")
    p4.add_argument("--artifact", default="")
    p4.add_argument("--artifact-type", default="release")
    p4.add_argument("--export-dir", default="")
    p4.add_argument("--out", default="")

    p5 = sub.add_parser("slop", help="L05: 质感去劣化与假大空清洗")
    p5.add_argument("--text", required=True)
    p5.add_argument("--out", default="")

    p6 = sub.add_parser("scenario", help="L06: 三维发布方案与 MCDA 矩阵")
    p6.add_argument("--model-name", default="客服助手")
    p6.add_argument("--dataset-size", type=int, default=500)
    p6.add_argument("--out", default="")
    p6.add_argument("--md", default="")

    p7 = sub.add_parser("bundle", help="L07: 伴生资产包 (Bundle/SARIF/Vega)")
    p7.add_argument("--run-id", default="L07")
    p7.add_argument("--out-dir", default="")
    p7.add_argument("--out", default="")

    p8 = sub.add_parser("patch", help="L08: RFC 6902 差量热修")
    p8.add_argument("--base", default="")
    p8.add_argument("--new", default="")
    p8.add_argument("--out", default="")

    p9 = sub.add_parser("memory", help="L09: 会话记忆与代词消歧")
    p9.add_argument("--query", default="")
    p9.add_argument("--out", default="")

    p10 = sub.add_parser("watchdog", help="L10: 看门狗熔断与遥测")
    p10.add_argument("--out", default="")

    # ---- Cycle 2 深度探针 ----
    q1 = sub.add_parser("probe2", help="L01[C2]: 多分类指标 + kappa/MCC")
    q1.add_argument("--out", default="")

    q2 = sub.add_parser("dag2", help="L02[C2]: CPM 浮时 + 截止期赶工裁决")
    q2.add_argument("--text", required=True)
    q2.add_argument("--deadline", type=float, default=0.0)
    q2.add_argument("--out", default="")

    q3 = sub.add_parser("heal2", help="L03[C2]: 修复计划 + 红线语料 + 幂等")
    q3.add_argument("--out", default="")

    q4 = sub.add_parser("spec2", help="L04[C2]: 账本 diff + Lint")
    q4.add_argument("--out", default="")

    q5 = sub.add_parser("slop2", help="L05[C2]: 正则族 + 证据密度")
    q5.add_argument("--text", required=True)
    q5.add_argument("--out", default="")

    q6 = sub.add_parser("scenario2", help="L06[C2]: TOPSIS/Pareto/MinimaxRegret")
    q6.add_argument("--model-name", default="客服助手")
    q6.add_argument("--dataset-size", type=int, default=500)
    q6.add_argument("--out", default="")

    q7 = sub.add_parser("bundle2", help="L07[C2]: SARIF/JUnit/Merkle/schema")
    q7.add_argument("--run-id", default="C2")
    q7.add_argument("--out-dir", default="")
    q7.add_argument("--out", default="")

    q8 = sub.add_parser("patch2", help="L08[C2]: 逆Patch/冲突/压缩")
    q8.add_argument("--out", default="")

    q9 = sub.add_parser("memory2", help="L09[C2]: 快照diff/多轮消解/TTL/LRU")
    q9.add_argument("--out", default="")

    q10 = sub.add_parser("watchdog2", help="L10[C2]: 滑窗熔断/遥测聚合/Trace")
    q10.add_argument("--out", default="")


def _write_json_out(path: str, data: Any) -> None:
    if not path:
        return
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _write_text_out(path: str, text: str) -> None:
    if not path:
        return
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _run_evolve(args) -> Dict[str, Any]:
    """L01~L10 引擎探针分发：真实执行 + 物理工件落盘。"""
    from engines import (R19RuntimeEngine, R19IntentCompiler, R19ReflexiveHealer,
                         R19SpecLedger, MLSlopGuard, R19ScenarioMatrix,
                         R19AssetBundle, R19DiffPatchEngine, R19SessionMemory,
                         R19TelemetryWatchdog)

    cmd = args.evolve_cmd
    out: Dict[str, Any]
    if cmd == "probe":
        out = R19RuntimeEngine().probe_health()
        out["demo_metrics"] = R19RuntimeEngine().compute_classification_metrics(
            [{"expected": "pass", "predicted": "pass"},
             {"expected": "fail", "predicted": "fail"}])
    elif cmd == "decompile":
        comp = R19IntentCompiler()
        out = comp.compile_request(args.text)
        _write_text_out(args.md, comp.render_markdown(out))
    elif cmd == "heal":
        healer = R19ReflexiveHealer()
        healed = None
        if args.artifact and os.path.exists(args.artifact):
            healed = healer.heal_artifact(c.load_json(args.artifact))
        audit = healer.audit_redlines(args.action,
                                      healed["healed"] if healed else None)
        # 探针语义：红线被成功检出 = 审计链路可用（成功），不是探针崩溃。
        # blocked 作为证据写入产物，供门禁/评审消费。
        out = {"ok": True,
               "probe_outcome": "REDLINE_BLOCKED" if audit["blocked"] else "CLEAN",
               "engine": healer.ENGINE, "layer": healer.LAYER,
               "redline_audit": audit, "heal": healed,
               "capabilities": list(healer.CAPABILITIES)}
    elif cmd == "spec":
        ledger = R19SpecLedger()
        spec = ledger.load_spec()
        out = {"ok": spec["gates_count"] == 8, "engine": ledger.ENGINE,
               "layer": ledger.LAYER, "spec": spec,
               "capabilities": list(ledger.CAPABILITIES)}
        if args.export_dir:
            out["export"] = ledger.export_gates(args.export_dir)
        if args.artifact and os.path.exists(args.artifact):
            comp_res = ledger.verify_gate_compliance(args.artifact_type,
                                                     c.load_json(args.artifact))
            out["compliance"] = comp_res
            out["ok"] = out["ok"] and comp_res["ok"]
    elif cmd == "slop":
        guard = MLSlopGuard()
        audit = guard.audit(args.text)
        # 探针语义：假大空被成功检出 = 清洗链路可用（成功），不是探针崩溃。
        out = dict(audit)
        out["probe_outcome"] = "SLOP_DETECTED" if audit["has_slop"] else "CLEAN"
        out["ok"] = True
    elif cmd == "scenario":
        eng = R19ScenarioMatrix()
        out = eng.compile_matrix(args.model_name, args.dataset_size)
        _write_text_out(args.md, eng.render_markdown(out))
    elif cmd == "bundle":
        out_dir = args.out_dir or os.path.join(WORKSPACE_ROOT, "bundles")
        built = R19AssetBundle(out_dir=out_dir).build(args.run_id)
        out = {"ok": built["ok"], "engine": built["engine"], "layer": built["layer"],
               "run_id": built["run_id"], "files": built["files"],
               "paths": built["paths"],
               "sarif_version": built["sarif"]["version"],
               "vega_schema": built["vega"]["$schema"],
               "bundle_schema": built["bundle"]["schema"]}
    elif cmd == "patch":
        eng = R19DiffPatchEngine()
        old = c.load_json(args.base) if args.base and os.path.exists(args.base) else None
        new = c.load_json(args.new) if args.new and os.path.exists(args.new) else None
        if old is None or new is None:
            old = {"n": 4, "confusion": {"tp": 1, "fp": 1, "tn": 1, "fn": 1},
                   "accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5}
            new = {"n": 4, "confusion": {"tp": 2, "fp": 0, "tn": 1, "fn": 1},
                   "accuracy": 0.75}
        out = eng.diff_evaluation(old, new)
    elif cmd == "memory":
        mem = R19SessionMemory()
        out = mem.disambiguate_query(args.query) if args.query else mem.demo()
    elif cmd == "watchdog":
        wd = R19TelemetryWatchdog()
        out = wd.probe_health()
        out["resilience_demo"] = {
            k: v for k, v in wd.execute_with_resilience(
                "evolve.healthcheck", lambda: {"status": "ok"}).items()
            if k != "result"}
    elif cmd == "probe2":
        rt = R19RuntimeEngine()
        records = [
            {"expected": "positive", "predicted": "positive"},
            {"expected": "positive", "predicted": "positive"},
            {"expected": "positive", "predicted": "negative"},
            {"expected": "negative", "predicted": "negative"},
            {"expected": "negative", "predicted": "negative"},
            {"expected": "negative", "predicted": "positive"},
            {"expected": "neutral", "predicted": "neutral"},
            {"expected": "neutral", "predicted": "neutral"},
            {"expected": "neutral", "predicted": "positive"},
        ]
        multi = rt.compute_multiclass_metrics(records)
        binary = rt.compute_classification_metrics([
            {"expected": "pass", "predicted": "pass"},
            {"expected": "pass", "predicted": "fail"},
            {"expected": "fail", "predicted": "fail"},
            {"expected": "fail", "predicted": "pass"}])
        agree = rt.compute_agreement_metrics(binary)
        out = {"ok": bool(multi.get("ok") and agree.get("ok")
                          and multi["conservation"]["delta"] == 0),
               "engine": rt.ENGINE, "layer": rt.LAYER,
               "multiclass": multi, "binary": binary, "agreement": agree,
               "capabilities": list(rt.CAPABILITIES)}
    elif cmd == "dag2":
        comp = R19IntentCompiler()
        compiled = comp.compile_request(args.text)
        stages = compiled.get("stages") or []
        cpm = comp.compute_cpm(stages)
        deadline_hours = args.deadline or float(
            (compiled.get("entities") or {}).get("deadline_hours") or 0) or None
        deadline = comp.assess_deadline(stages, deadline_hours)
        out = {"ok": bool(cpm.get("ok") and deadline.get("ok")),
               "engine": comp.ENGINE, "layer": comp.LAYER,
               "compile_ok": compiled.get("ok"), "cpm": cpm,
               "deadline": deadline, "capabilities": list(comp.CAPABILITIES)}
    elif cmd == "heal2":
        healer = R19ReflexiveHealer()
        dirty = {"verdict": "pass", "stage": "prod", "feedback_source": "judge",
                 "records": [{"ground_truth": "pass", "prediction": "pass"},
                             {"ground_truth": "fail", "prediction": "pass"}]}
        healed = healer.heal_artifact(dirty)
        plan = healer.build_repair_plan(None, healed)
        corpus = healer.evaluate_redline_corpus()
        idem = healer.verify_idempotent(dirty)
        out = {"ok": bool(corpus.get("ok") and idem.get("ok")),
               "engine": healer.ENGINE, "layer": healer.LAYER,
               "heal_notes": healed.get("notes", []),
               "repair_plan": plan, "corpus": corpus, "idempotency": idem,
               "capabilities": list(healer.CAPABILITIES)}
    elif cmd == "spec2":
        ledger = R19SpecLedger()
        spec = ledger.load_spec()
        lint = ledger.lint_spec(spec)
        baseline_path = os.path.join(_HERE, "workspace", "bundles", "ml_gates.json")
        baseline = None
        if os.path.exists(baseline_path):
            raw = c.load_json(baseline_path)
            baseline = raw.get("spec") if isinstance(raw, dict) and "spec" in raw else raw
        diff = ledger.diff_snapshots(baseline or spec, spec)
        out = {"ok": bool(lint.get("ok") and diff.get("ok")),
               "engine": ledger.ENGINE, "layer": ledger.LAYER,
               "lint": lint, "diff": diff,
               "baseline_used": baseline_path if baseline else "(same-spec)",
               "capabilities": list(ledger.CAPABILITIES)}
    elif cmd == "slop2":
        guard = MLSlopGuard()
        dirty = guard.audit_extended(args.text)
        clean = guard.audit_extended("准确率 0.91，P95 180ms，样本 500 条，回归 ID REG-19。")
        out = {"ok": bool(dirty["regex_count"] > 0
                          and clean["status_extended"] == "PASS"),
               "engine": guard.ENGINE, "layer": guard.LAYER,
               "dirty_audit": dirty, "clean_audit": clean,
               "capabilities": list(guard.CAPABILITIES)}
    elif cmd == "scenario2":
        eng = R19ScenarioMatrix()
        matrix = eng.compile_matrix(args.model_name, args.dataset_size)
        out = {"ok": bool(matrix.get("ok") and matrix["topsis"]["winner"]
                          and matrix["minimax_regret"]["winner"]),
               "engine": eng.ENGINE, "layer": eng.LAYER,
               "recommended": matrix["recommended"],
               "topsis": matrix["topsis"], "pareto": matrix["pareto"],
               "minimax_regret": matrix["minimax_regret"],
               "capabilities": list(eng.CAPABILITIES)}
    elif cmd == "bundle2":
        out_dir = args.out_dir or os.path.join(WORKSPACE_ROOT, "bundles", "cycle2")
        built = R19AssetBundle(out_dir=out_dir).build(args.run_id)
        rules = built["sarif"]["runs"][0]["tool"]["driver"]["rules"]
        out = {"ok": bool(built["ok"] and built["schema_check"]["ok"]
                          and built["merkle_root"]),
               "engine": built["engine"], "layer": built["layer"],
               "run_id": built["run_id"], "paths": built["paths"],
               "sarif": {"version": built["sarif"]["version"],
                         "rule_count": len(rules),
                         "rule_help_ok": all("help" in r for r in rules),
                         "baseline_states": [x.get("baselineState")
                                             for x in built["sarif"]["runs"][0]["results"]]},
               "junit": {"tests": built["bundle"]["junit"]["tests"],
                         "failures": built["bundle"]["junit"]["failures"],
                         "head": built["junit"].splitlines()[:2]},
               "merkle_root": built["merkle_root"],
               "schema_check": built["schema_check"],
               "capabilities": list(built["capabilities"])}
    elif cmd == "patch2":
        eng = R19DiffPatchEngine()
        old = {"n": 4, "confusion": {"tp": 1, "fp": 1, "tn": 1, "fn": 1},
               "accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5}
        new = {"n": 4, "confusion": {"tp": 2, "fp": 0, "tn": 1, "fn": 1},
               "accuracy": 0.75}
        core = eng.diff_evaluation(old, new)
        drift = eng.detect_conflicts(old, [
            {"op": "replace", "path": "/missing_field", "value": 1},
            {"op": "test", "path": "/n", "value": 999}])
        compacted = eng.compact_patch([
            {"op": "replace", "path": "/accuracy", "value": 0.6},
            {"op": "replace", "path": "/accuracy", "value": 0.75},
            {"op": "test", "path": "/n", "value": 4},
            {"op": "remove", "path": "/precision"}])
        out = {"ok": bool(core.get("ok") and core.get("rollback_ok")
                          and core.get("inverse_count", 0) > 0),
               "engine": eng.ENGINE, "layer": eng.LAYER,
               "diff": core, "drift_conflicts": drift, "compacted": compacted,
               "capabilities": list(eng.CAPABILITIES)}
    elif cmd == "memory2":
        state_path = os.path.join(_HERE, "workspace", "rounds", "cycle2", "session_state.json")
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        if os.path.exists(state_path):
            os.remove(state_path)
        mem = R19SessionMemory(state_path=state_path)
        mem.update_slot("current_model", "客服助手")
        mem.update_slot("threshold", 0.80)
        before = mem.record_snapshot("before", {"current_model": "客服助手",
                                                "threshold": 0.80})
        mem.update_slot("threshold", 0.85)
        mem.update_slot("current_dataset", "golden_set_v2")
        after = mem.record_snapshot("after", {"current_model": "客服助手",
                                              "threshold": 0.85,
                                              "current_dataset": "golden_set_v2"})
        diff = mem.diff_snapshots(before, after)
        multi = mem.resolve_multi_turn([
            "按第一套方案调整",
            "把阈值调高0.05",
            "把阈值调低0.02"])
        for i in range(7):
            mem.record_snapshot(f"bulk_{i}", {"threshold": 0.8 + i / 100})
        compact = mem.compact_snapshots(keep=3)
        mem.set_ttl("temp_slot", -1)
        purge = mem.purge_expired()
        out = {"ok": bool(diff["change_count"] > 0 and multi["conflict_count"] > 0
                          and compact["pruned_count"] > 0 and purge["expired_count"] > 0),
               "engine": mem.ENGINE, "layer": mem.LAYER,
               "snapshot_diff": diff, "multi_turn": multi,
               "compaction": compact, "ttl_purge": purge,
               "capabilities": list(mem.CAPABILITIES)}
    elif cmd == "watchdog2":
        from engines.telemetry_watchdog import SlidingWindowBreaker
        wd = R19TelemetryWatchdog()
        health = wd.probe_health()
        demo = wd.execute_with_resilience("evolve.c2.probe", lambda: {"status": "ok"})
        now = [0.0]
        br = SlidingWindowBreaker(window_sec=60, failure_rate_threshold=0.5,
                                  min_samples=6, recovery_timeout_sec=1.0,
                                  clock=lambda: now[0])
        for _ in range(3):
            br.record_success()
        for _ in range(3):
            br.record_failure()
        opened = br.state
        can_before_recovery = br.can_execute()
        now[0] = 1.0
        half_open = br.can_execute()
        br.record_failure()
        reopened = br.state
        rows = wd.read_telemetry(200)
        synthetic = [{"name": "gate.check", "duration_ms": float(v),
                      "status": "OK"} for v in range(10, 101, 10)]
        aggregate = wd.aggregate_telemetry(synthetic)
        real_telemetry = wd.aggregate_telemetry(rows)
        traces = wd.reconstruct_traces(rows)
        out = {"ok": bool(health.get("ok") and opened == "OPEN"
                          and can_before_recovery is False and half_open is True
                          and reopened == "OPEN" and aggregate["total_spans"] == 10
                          and aggregate["by_name"]["gate.check"]["p50"] == 55.0
                          and aggregate["by_name"]["gate.check"]["p95"] == 95.5),
               "engine": wd.ENGINE, "layer": wd.LAYER,
               "health": {k: health.get(k) for k in ("ok", "breaker_state")},
               "resilience": {k: demo.get(k) for k in ("ok", "attempts", "breaker_state")},
               "sliding_window": {"opened": opened,
                                  "can_before_recovery": can_before_recovery,
                                  "half_open_allowed": half_open,
                                  "reopened": reopened,
                                  "transitions": br.transitions},
               "telemetry": aggregate, "real_telemetry": real_telemetry,
               "traces": traces, "capabilities": list(wd.CAPABILITIES)}
    else:  # pragma: no cover - argparse 已限制
        out = {"ok": False, "error": f"未知 evolve 命令: {cmd}"}

    out.setdefault("engine_layer", out.get("layer", ""))
    _write_json_out(args.out, out)
    return out


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：14 门禁 + runlog")
    ha = h.add_subparsers(dest="hcmd", required=True)
    for name, help_txt in harness._GATE_HELP.items():
        pa = ha.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    rl = ha.add_parser("runlog", help="运行可观测性：最近 N 次运行记录")
    rl.add_argument("--n", type=int, default=10)


def _run_harness(args) -> Dict[str, Any]:
    if args.hcmd == "runlog":
        return {"runlog": ws.runlog(args.n)}
    return harness.run_validator(args.hcmd, args.input)


def _mkns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


def _register_contract(sp) -> None:
    cp = sp.add_parser("contract", help="技能契约：list/get/validate")
    ca = cp.add_subparsers(dest="ccmd", required=True)
    ca.add_parser("list", help="列出所有技能及其契约动作")
    g = ca.add_parser("get", help="输出某技能某动作的契约 schema")
    g.add_argument("--skill", required=True, dest="contract_skill")
    g.add_argument("--action", default=None, dest="contract_action")
    v = ca.add_parser("validate", help="按契约校验某技能的产出 JSON")
    v.add_argument("--skill", required=True, dest="contract_skill")
    v.add_argument("--action", required=True, dest="contract_action")
    v.add_argument("--output", required=True)


def _register_case(sp) -> None:
    cp = sp.add_parser("case", help="案例库：list/get/validate")
    ca = cp.add_subparsers(dest="ccmd", required=True)
    ca.add_parser("list", help="列出所有案例")
    g = ca.add_parser("get", help="加载某案例（含语义层）")
    g.add_argument("--case", required=True, dest="case_id")
    v = ca.add_parser("validate", help="案例结构门禁")
    v.add_argument("--case", required=True, dest="case_id")


def _run_case(args) -> Dict[str, Any]:
    if args.ccmd == "list":
        return {"cases": cases.list_cases()}
    if args.ccmd == "get":
        return cases.load_case(args.case_id)
    if args.ccmd == "validate":
        return cases.validate_case(args.case_id)
    return {"error": f"未知 case 命令: {args.ccmd}"}


def _register_review(sp) -> None:
    p = sp.add_parser("review", help="对抗评审：对模型工程工件做确定性挑战")
    p.add_argument("--result", required=True)
    p.add_argument("--skill", required=True, dest="review_skill")
    p.add_argument("--action", required=True, dest="review_action")
    p.add_argument("--run-id", default="")


def _run_review(args) -> Dict[str, Any]:
    result = c.load_json(args.result)
    packet = {"run_id": args.run_id, "skill": args.review_skill,
              "action": args.review_action, "result": result}
    out = review.review_packet(packet)
    out["exit_code"] = 0 if out["verdict"] == "PASS" else 1
    return out


def _run_contract(args) -> Dict[str, Any]:
    skill = getattr(args, "contract_skill", None)
    action = getattr(args, "contract_action", None)
    if args.ccmd == "list":
        return {"contracts": [
            {"skill": s, "desc": contracts.get(s)["desc"],
             "actions": contracts.actions(s)}
            for s in contracts.skill_names()]}
    if args.ccmd == "get":
        entry = contracts.get(skill)
        if not entry:
            return {"error": f"未知技能: {skill}"}
        if action:
            return {"skill": skill, "action": action,
                    "output_schema": entry.get("output", {}).get(action)}
        return {"skill": skill, "desc": entry["desc"],
                "input": entry["input"], "output_actions": list(entry["output"])}
    if args.ccmd == "validate":
        result = c.load_json(args.output)
        return contracts.validate_output(skill, action, result)
    return {"error": f"未知 contract 命令: {args.ccmd}"}


# --------------------------------------------------------------------------- #
# 协作入口
# --------------------------------------------------------------------------- #
def run_task(task_id: str) -> Dict[str, Any]:
    task = ws.read_task(task_id)
    if task is None:
        return {"error": f"任务不存在: {task_id}"}
    if task.owner != ROLE:
        return {"error": f"任务 {task_id} 归属 {task.owner}，非本角色 {ROLE}"}

    ws.set_status(task_id, "running")
    ws.emit(protocol.Event.now(ROLE, "task_started", task_id))

    params = _parse_port_params(task.inputs)
    in_file = _first_input_file(task.inputs) or params.get("input")
    if not in_file or not os.path.exists(in_file):
        ws.set_status(task_id, "failed")
        ws.emit(protocol.Event.now(ROLE, "task_failed", task_id, {"reason": "缺少输入文件"}))
        return {"error": "缺少输入文件"}

    intent = task.intent + " " + " ".join(params.values())
    skill_name, action, defaults = _route(intent)
    if skill_name == "__clarify__":
        ws.set_status(task_id, "failed")
        ws.emit(protocol.Event.now(ROLE, "task_failed", task_id,
                                   {"reason": "needs_clarification",
                                    "questions": defaults.get("questions", [])}))
        return {"error": "needs_clarification",
                "questions": defaults.get("questions", []),
                "assumptions": defaults.get("assumptions", []),
                "plan": defaults.get("plan")}
    mod = SKILL_BY_NAME[skill_name]

    out_dir = ws.artifact(task_id)
    os.makedirs(out_dir, exist_ok=True)

    merged = dict(defaults)
    merged.update(params)
    merged["action"] = action
    merged["input"] = in_file

    result = mod.run(_mkns(**merged))
    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    outputs: List[protocol.Port] = []
    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs.append(protocol.Port(f"{skill_name}.json", "data"))

    ports = role_runtime.emit(
        role=ROLE, name="蛙智模", title="模型工程与 AI 评估官",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="model_report")
    outputs.extend(ports)

    ws.update_task(task_id, {"outputs": [p.to_dict() for p in outputs],
                             "status": "done"})
    ws.emit(protocol.Event.now(ROLE, "task_finished", task_id,
                               {"outputs": [p.name for p in outputs]}))
    return result


def _write_report(result: Dict[str, Any], title: str, path: str) -> None:
    lines = [f"# {title}", ""]
    for k, v in result.items():
        if k in ("checks",):
            continue
        lines += [f"## {k}", "", "```json",
                  json.dumps(v, ensure_ascii=False, indent=2), "```", ""]
    lines += ["## 门禁", "", "```json",
              json.dumps(result.get("checks", []), ensure_ascii=False, indent=2), "```"]
    c.write_text(path, "\n".join(lines))


def _route(intent: str):
    low = intent.lower()
    for kws, skill, action, defaults in _INTENT_ROUTES:
        if any(k.lower() in low for k in kws):
            return skill, action, defaults
    # 关键词未命中：交给共享 L02 内核；不再静默落到默认动作。
    return fallback_route(ROLE, intent)


def _parse_port_params(ports: List[protocol.Port]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for p in ports:
        if p.note:
            for part in p.note.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k.strip()] = v.strip()
    return params


def _first_input_file(ports: List[protocol.Port]) -> Optional[str]:
    for p in ports:
        if p.kind == "data" and os.path.exists(p.name):
            return p.name
    return None


# --------------------------------------------------------------------------- #
# 示例工件 / manifest
# --------------------------------------------------------------------------- #
def make_demo(artifacts_dir: str) -> Dict[str, str]:
    os.makedirs(artifacts_dir, exist_ok=True)
    out: Dict[str, str] = {}
    for name in ("tracking_experiment", "tracking_run", "registry_register",
                 "registry_version", "evaluation_dataset", "evaluation_scorer",
                 "trace_analyze", "trace_retrieval", "release_regression",
                 "release_candidate", "monitor_metrics", "monitor_drift",
                 "modelcard_card", "modelcard_asset"):
        src = os.path.join(_HERE, "examples", f"{name}.json")
        if os.path.exists(src):
            dst = os.path.join(artifacts_dir, f"{name}.json")
            c.write_json(dst, c.load_json(src))
            out[name] = dst
    return out


def manifest() -> Dict[str, Any]:
    r = registry.by_id(ROLE)
    return {"role": r["id"], "name": r["name"], "title": r["title"],
            "capabilities": r["capabilities"],
            "inputs": r["inputs"], "outputs": r["outputs"],
            "skills": [(m.NAME, m.DESC) for m in SKILLS],
            "capability_status": {"local_evaluation_model_card": "real", "model_publication": "blocked"}}


def _input_hash(args) -> str:
    p = getattr(args, "input", None)
    if p and os.path.exists(p):
        h = hashlib.md5()
        with open(p, "rb") as f:
            h.update(f.read())
        return h.hexdigest()[:12]
    return ""


def main() -> int:
    _meta = role_runtime.handle_meta_command(sys.argv[1:], ROLE)
    if _meta is not None:
        return _meta

    args = build_parser().parse_args()

    if args.skill == "manifest":
        emit_result(manifest())
        return 0
    if args.skill == "local":
        out = local_exec.execute(c.load_json(args.input)); emit_result(out)
        return 0 if out["ok"] else 1
    if args.skill == "demo":
        artifacts = os.path.join(WORKSPACE_ROOT, "artifacts")
        emit_result({"demo_artifacts": make_demo(artifacts)})
        return 0
    if args.skill == "run":
        emit_result(run_task(args.task))
        return 0
    if args.skill == "clarify":
        return clarify_cli(ROLE, args.intent)
    if args.skill == "harness":
        out = _run_harness(args)
        emit_result(out)
        return 0 if out.get("ok", True) else 1
    if args.skill == "contract":
        out = _run_contract(args)
        emit_result(out)
        return 0 if out.get("ok", True) else 1
    if args.skill == "case":
        out = _run_case(args)
        emit_result(out)
        return 0 if args.ccmd != "validate" else (0 if out["ok"] else 1)
    if args.skill == "review":
        out = _run_review(args)
        emit_result(out)
        return 0 if out["verdict"] == "PASS" else 1
    if args.skill == "evolve":
        out = _run_evolve(args)
        emit_result(out)
        return 0 if out.get("ok", True) else 1

    t0 = time.time()
    result = SKILL_BY_NAME[args.skill].run(args)
    elapsed = int((time.time() - t0) * 1000)
    result = {"result": result} if not isinstance(result, dict) else result
    result.setdefault("capability_status", "real")
    result.setdefault("report", {"capability_status": result["capability_status"]})
    ok = bool(result.get("ok", True))
    ws.log_run(ROLE, {"skill": args.skill,
                      "action": getattr(args, "action", None),
                      "input_hash": _input_hash(args),
                      "elapsed_ms": elapsed, "exit_code": 0 if ok else 1})
    result.setdefault("runtime_ms", elapsed)
    emit_result(result)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
