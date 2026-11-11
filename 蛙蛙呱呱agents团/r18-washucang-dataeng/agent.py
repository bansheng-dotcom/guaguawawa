#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R18 蛙数仓 · 数据工程与管道官 —— 本地可运行 Agent（七技能调度器）。

把 7 个能力域各自做成一个独立技能模块（skills/s01..s07），本文件只做三件事：
    1. 注册 7 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    source + metrics_spec  →  dataset + data_catalog

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py elt connection --input examples/connection.json
    python agent.py quality check --input examples/quality_check.json
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_HERE_BOOT = _os.path.dirname(_os.path.abspath(__file__))
_AGENTS_BOOT = _os.path.dirname(_HERE_BOOT)
_REPO_ROOT = _os.path.dirname(_AGENTS_BOOT)
# 动态防爆探测（SOP §5.9）：自身目录 / agents 集合目录 / 仓库根同时入 PATH，
# 任何一层写错都不会再退化成 `ModuleNotFoundError: No module named 'agents'`。
for _p in (_HERE_BOOT, _AGENTS_BOOT, _REPO_ROOT):
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

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
for _p in (_HERE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import protocol, registry, workspace  # noqa: E402
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402
from agents.shared import role_runtime  # noqa: E402
from skills import SKILLS, _common as c  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402
import local_exec  # noqa: E402

ROLE = "r18"
WORKSPACE_ROOT = workspace.default_root()
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
# 注意「质量/门禁」(quality) 必须排在「同步/sync」之前——质量口径词里含「数据」
# 相关词时不能误路由到 elt（R18 猜坑：质量门禁 vs 连接同步动作错配）。
# 同样「增量/水位」(incremental) 要排在「调度/管道」(pipeline) 之前。
_INTENT_ROUTES = [
    (("质量", "门禁", "空值", "重复率", "唯一性", "新鲜度", "quality", "fresh",
      "校验数据"), "quality", "check", {}),
    (("新鲜度", "时效", "延迟", "过期", "freshness"), "quality", "fresh", {}),
    (("增量", "水位", "全量", "快照", "cdc", "迟到", "incremental", "watermark"),
     "incremental", "strategy", {}),
    (("回填", "补数", "重跑", "backfill"), "incremental", "backfill", {}),
    (("血缘", "目录", "口径", "字段说明", "lineage", "catalog", "owner"),
     "catalog", "lineage", {}),
    (("目录条目", "字段类型", "登记表", "表结构"), "catalog", "entry", {}),
    (("转换", "模型", "物化", "dbt", "model", "material", "测试声明"),
     "transform", "model", {}),
    (("dbt测试", "通用测试", "accepted_values", "not_null", "unique测试"),
     "transform", "test", {}),
    (("调度", "编排", "dag", "依赖", "任务图", "airflow", "pipeline"), "pipeline", "dag", {}),
    (("运行状态", "任务状态", "失败任务", "重试", "task state"), "pipeline", "run", {}),
    (("连接", "connector", "数据源", "来源", "目的地", "connection"), "elt", "connection", {}),
    (("同步", "sync", "拉取", "抽取", "extract"), "elt", "sync", {}),
    (("审批", "授权", "运维", "高风险", "审批单", "request"), "ops", "request", {}),
    (("告警", "报警", "通知", "阈值告警", "alert"), "ops", "alert", {}),
]


def emit_result(data: Dict[str, Any]) -> None:
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R18 蛙数仓 · 数据工程与管道官")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    local = sp.add_parser("local", help="本地 ELT 清洗与质量门禁")
    local.add_argument("--input", required=True)
    sp.add_parser("demo", help="生成示例数据管道工件")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)
    add_clarify_parser(sp)

    _register_evolve(sp)
    _register_patch(sp)
    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_patch(sp) -> None:
    """L08 主链路入口：局部差量热修（RFC 6902）+ 增量门禁影响面。"""
    p = sp.add_parser("patch", help="局部差量：应用 JSON Patch 并给出受影响门禁")
    p.add_argument("--base", required=True)
    p.add_argument("--patch", required=True)
    p.add_argument("--out", default="")


def _run_patch(args) -> Dict[str, Any]:
    from engines import DataEngDiffPatchEngine
    base = c.load_json(args.base)
    patch = c.load_json(args.patch)
    out = DataEngDiffPatchEngine().apply_and_plan(base, patch)
    if getattr(args, "out", ""):
        c.write_json(args.out, out)
    return out


def _register_evolve(sp) -> None:
    """十维演进入口：委托自动演进状态机执行器（SOP §七 Golden Standard）。"""
    ev = sp.add_parser("evolve", help="十维演进状态机：--status/--stage/--round/--run-all")
    ev.add_argument("--status", action="store_true", dest="evolve_status")
    ev.add_argument("--stage", type=int, choices=[1, 2, 3], dest="evolve_stage")
    ev.add_argument("--round", type=int, dest="evolve_round")
    ev.add_argument("--run-all", action="store_true", dest="evolve_run_all")


def _run_evolve(args) -> int:
    import auto_evolve_runner as runner
    argv: List[str] = []
    if getattr(args, "evolve_status", False):
        argv.append("--status")
    if getattr(args, "evolve_stage", None):
        argv += ["--stage", str(args.evolve_stage)]
    if getattr(args, "evolve_round", None):
        argv += ["--round", str(args.evolve_round)]
    if getattr(args, "evolve_run_all", False):
        argv.append("--run-all")
    return runner.main(argv)


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：14 数据管道门禁 + runlog")
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
    p = sp.add_parser("review", help="对抗评审：对数据管道工件做确定性挑战")
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

    # --- L10 主链路接入：技能执行过看门狗（重试 + 熔断 + 遥测留痕） ---
    from engines import DataEngTelemetryWatchdog
    watchdog = DataEngTelemetryWatchdog(workspace_dir=os.path.join(workspace.role_workspace(_HERE)))
    outcome = watchdog.execute_with_resilience(
        lambda: mod.run(_mkns(**merged)), retries=2,
        name=f"{skill_name}/{action}")
    if outcome.get("ok"):
        result = outcome["result"] if isinstance(outcome.get("result"), dict) else {}
    else:
        result = {"ok": False, "checks": [],
                  "error": f"技能执行失败：{outcome.get('error')}"}
    result["trace"] = {"trace_id": outcome.get("trace_id"),
                       "attempts": outcome.get("attempts"),
                       "status": outcome.get("status")}
    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    # --- L09 主链路接入：跨轮会话记忆（代词消歧 + 槽位落盘） ---
    from engines import DataEngSessionMemory
    memory = DataEngSessionMemory(
        workspace_dir=os.path.join(workspace.role_workspace(_HERE), "state"),
        session_id="r18-main")
    resolved = memory.disambiguate(intent)
    memory.remember_turn(task.intent, f"{skill_name}/{action}",
                         {"task_id": task_id, "resolved": resolved})
    result["memory"] = {"resolved": resolved.get("resolved"),
                        "kind": resolved.get("kind"),
                        "slots": memory.history_digest()["slots"]}

    # --- L02 主链路接入：把自然语言任务编译成 5 阶段 Kahn 交付 DAG 并落盘 ---
    from engines import (DataEngIntentCompiler, DataEngReflexiveHealer,
                         DataEngScenarioMatrix, DataEngSlopGuard, DataEngSpecLedger)
    dag = DataEngIntentCompiler().compile_intent(intent)
    dag_path = os.path.join(out_dir, "delivery_dag.json")
    c.write_json(dag_path, dag)
    result["delivery_dag"] = {
        "dag_id": dag["intent_id"],
        "stage_count": dag["stage_count"],
        "topological_order": dag["topological_order"],
        "total_effort_h": dag["total_effort_h"],
        "total_man_days": dag["total_man_days"],
        "critical_path_h": dag["critical_path_h"],
        "parallel_levels": dag["parallel_levels"],
        "path": dag_path,
    }

    # --- L04 主链路接入：运行时加载领域账本 SSOT，口径不达标即暴露 ---
    try:
        spec = DataEngSpecLedger().load_spec()
        result["spec_ref"] = {"version": spec["version"],
                              "gates_count": spec["gates_count"],
                              "metrics_count": spec["metrics_count"],
                              "dri": spec["dri"],
                              "thresholds_source": "DATAENG_SPEC.md"}
    except Exception as exc:  # noqa: BLE001 - 账本缺失必须显式暴露，不静默
        result["spec_ref"] = {"error": str(exc)}

    # --- L06 主链路接入：按任务上下文生成三维方案，并落盘供人类横向决策 ---
    ctx = {}
    sla = dag["entities"].get("sla_hours")
    if sla is not None:
        ctx["sla_hours"] = sla
    if any(k in intent for k in ("强一致", "财务", "合规", "对账")):
        ctx["strict_consistency"] = True
    matrix = DataEngScenarioMatrix().generate(ctx)
    matrix_path = os.path.join(out_dir, "scenario_matrix.json")
    c.write_json(matrix_path, matrix)
    result["scenario_matrix"] = {
        "context": ctx,
        "recommended_id": matrix["recommended_id"],
        "recommended_name": matrix["recommended_name"],
        "ranking": [{"id": r["id"], "name": r["name"], "score": r["total_score"],
                     "roi_ratio": r["roi_ratio"]} for r in matrix["scenarios"]],
        "path": matrix_path,
    }

    # --- L05 主链路接入：全部结论键过反套话清洗（不只 narrative） ---
    guard = DataEngSlopGuard()
    measured = result.get("measured") if isinstance(result.get("measured"), dict) else {}
    facts = {"measured": measured} if measured else {}
    slop_audit: Dict[str, Any] = {}
    for key in c.load_thresholds().get("review", {}).get("conclusion_keys", ["narrative"]):
        val = result.get(key)
        if isinstance(val, str) and val:
            cleaned = guard.clean(val, facts=facts)
            result[key] = cleaned["cleaned"]
            slop_audit[key] = {"before": cleaned["before"], "after": cleaned["after"]}
    result["slop_audit"] = slop_audit

    # --- L03 主链路接入：emit 前对结论文本强制过四条红线，命中即硬阻断 ---
    conclusion = " ".join(str(result.get(k, "")) for k in ("narrative", "summary", "next"))
    hits = DataEngReflexiveHealer().scan_redlines(conclusion)
    result["redline_scan"] = {"hits": hits, "blocked": bool(hits),
                              "scanned_keys": ["narrative", "summary", "next"]}
    if hits:
        result["ok"] = False
        result["verdict"] = "FAIL"
        result["redline_blocked"] = hits[0]
        result["next"] = (f"{hits[0]['rule_id']} {hits[0]['name']}：强制移交 "
                          f"{hits[0]['handoff']}；{hits[0]['fix']}")

    # --- L07 主链路接入：伴生导出 SARIF/Vega/血缘 AST/bundle，下游可机器消费 ---
    from engines import DataEngAssetBundle
    gate_passed = bool(result.get("ok", True))
    spec_gates = []
    if isinstance(result.get("spec_ref"), dict) and "gates_count" in result["spec_ref"]:
        try:
            gates = DataEngSpecLedger().load_spec()["gates"]
            spec_gates = [{**g, "ok": gate_passed} for g in gates]
        except Exception:  # noqa: BLE001
            spec_gates = []
    exported = DataEngAssetBundle().export(
        task_id,
        {"pipeline": {"skill": skill_name, "action": action, "intent": intent},
         "gates": spec_gates, "checks": result.get("checks", []),
         "delivery_dag": dag, "artifact_uri": f"{skill_name}.json"},
        out_dir=os.path.join(out_dir, "bundles"))
    bundle_check = DataEngAssetBundle().validate_export(exported)
    result["asset_bundle"] = {
        "dir": exported["bundle"].rsplit(os.sep, 1)[0],
        "bundle": os.path.basename(exported["bundle"]),
        "sarif": os.path.basename(exported["sarif"]),
        "vega": os.path.basename(exported["vega"]),
        "ast": os.path.basename(exported["ast"]),
        "sarif_results": exported["sarif_results"],
        "validation": bundle_check["grade"],
    }

    outputs: List[protocol.Port] = []
    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs.append(protocol.Port(f"{skill_name}.json", "data"))

    ports = role_runtime.emit(
        role=ROLE, name="蛙数仓", title="数据工程与管道官",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="data_report")
    outputs.extend(ports)

    task_ok = bool(result.get("ok", True))
    ws.update_task(task_id, {"outputs": [p.to_dict() for p in outputs],
                             "status": "done" if task_ok else "failed"})
    ws.emit(protocol.Event.now(ROLE, "task_finished" if task_ok else "task_failed",
                               task_id, {"outputs": [p.name for p in outputs],
                                         "redline_blocked": result["redline_scan"]["blocked"]}))
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
    for name in ("connection", "sync", "model", "test", "dag", "run",
                 "quality_check", "quality_fresh", "incremental_strategy",
                 "backfill", "catalog_entry", "lineage", "ops_request", "alert"):
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
            "capability_status": {"local_elt_quality_lineage": "real", "external_connectors": "blocked"}}


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
    if args.skill == "evolve":
        return _run_evolve(args)
    if args.skill == "patch":
        out = _run_patch(args)
        emit_result(out)
        return 0 if out.get("ok") else 1
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
