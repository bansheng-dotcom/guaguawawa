#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R20 蛙值守 · 可靠性与恢复官 —— 本地可运行 Agent（七技能调度器）。

把 7 个能力域各自做成一个独立技能模块（skills/s01..s07），本文件只做三件事：
    1. 注册 7 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    topology + asset_list  →  monitor_config + backup_repo

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py monitor monitor --input examples/monitor.json
    python agent.py backup backup   --input examples/backup.json
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（SOP v13.0 §5.9 动态防爆探测）---
# 本目录 + agents 集合目录 + 仓库根同时入 sys.path，且在导入 agents/shared 之前完成。
# 修掉「三层 dirname 误当仓库根 + 路径注入晚于 chat_cli 导入」导致本目录
# `python agent.py` 直接起不来的历史故障（R20 L01 体检断点 #1）。
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

ROLE = "r20"
WORKSPACE_ROOT = workspace.default_root()
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
# 「删除快照/灾难切换」等不可逆词必须排在通用词之前，避免误路由到普通动作。
def _load_intent_routes():
    """意图路由唯一出处：prompt_profile.json 的 intent_routes（勿在代码里再写一份）。"""
    import json as _json
    _here = os.path.dirname(os.path.abspath(__file__))
    _p = os.path.join(_here, "prompt_profile.json")
    try:
        with open(_p, encoding="utf-8") as _f:
            _data = _json.load(_f)
    except (OSError, ValueError):
        return []
    def _defaults(d):
        out = {}
        for k, v in (d or {}).items():
            if isinstance(v, dict) and "__path__" in v:
                out[k] = os.path.join(_here, *str(v["__path__"]).split("/"))
            else:
                out[k] = v
        return out
    return [(tuple(r.get("when") or []), str(r.get("skill") or ""),
             str(r.get("action") or ""), _defaults(r.get("defaults")))
            for r in (_data.get("intent_routes") or [])]


_INTENT_ROUTES = _load_intent_routes()


def emit_result(data: Dict[str, Any]) -> None:
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R20 蛙值守 · 可靠性与恢复官")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    local = sp.add_parser("local", help="本地备份 hash 与临时目录恢复演练")
    local.add_argument("--input", required=True)
    local.add_argument("--output", required=True)
    sp.add_parser("demo", help="生成示例可靠性工件")
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


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：14 可靠性门禁 + runlog")
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
    p = sp.add_parser("review", help="对抗评审：对可靠性工件做确定性挑战")
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
        role=ROLE, name="蛙值守", title="可靠性与恢复官",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="reliability_report")
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
# SOP v13.0 十维演进入口（L01~L10）
# --------------------------------------------------------------------------- #
def _register_evolve(sp) -> None:
    ev = sp.add_parser("evolve", help="SOP v13.0 十维演进探针（L01~L10）")
    ea = ev.add_subparsers(dest="ecmd", required=True)

    p = ea.add_parser("probe", help="L01 可靠性精算沙箱体检")
    p.add_argument("--out", default=None)

    p = ea.add_parser("decompile", help="L02 复合故障诉求 → 5 阶段恢复 DAG")
    p.add_argument("--text", required=True)
    p.add_argument("--deadline", type=float, default=0.0)
    p.add_argument("--out", default=None)
    p.add_argument("--md", default=None)

    p = ea.add_parser("heal", help="L03 告警归一 + Reflexion + 五条红线")
    p.add_argument("--action", default="")
    p.add_argument("--artifact", default="")
    p.add_argument("--out", default=None)

    p = ea.add_parser("spec", help="L04 SRE_SPEC 账本 + 8 维发布门禁")
    p.add_argument("--artifact", default="")
    p.add_argument("--artifact-type", default="release")
    p.add_argument("--export-dir", default="")
    p.add_argument("--out", default=None)

    p = ea.add_parser("slop", help="L05 假大空清洗 + 量化证据 + 行动力")
    p.add_argument("--text", required=True)
    p.add_argument("--out", default=None)

    p = ea.add_parser("scenario", help="L06 三维处置方案 + MCDA 权衡")
    p.add_argument("--service", default="核心服务")
    p.add_argument("--severity", default="major")
    p.add_argument("--out", default=None)
    p.add_argument("--md", default=None)

    p = ea.add_parser("bundle", help="L07 Bundle / SARIF / Vega-Lite")
    p.add_argument("--run-id", default="L07")
    p.add_argument("--out-dir", default="")
    p.add_argument("--out", default=None)

    p = ea.add_parser("patch", help="L08 RFC6902 差量热修 + 不变量复核")
    p.add_argument("--base", default="")
    p.add_argument("--new", default="")
    p.add_argument("--out", default=None)

    p = ea.add_parser("memory", help="L09 持久记忆 + 代词消歧 + 回滚")
    p.add_argument("--query", default="")
    p.add_argument("--out", default=None)

    p = ea.add_parser("watchdog", help="L10 熔断 / 退避 / 全链路遥测")
    p.add_argument("--out", default=None)


def _run_evolve(args) -> Dict[str, Any]:
    import json as _json
    from engines import (R20AssetBundle, R20DiffPatchEngine, R20IntentCompiler,
                         R20ReflexiveHealer, R20RuntimeEngine, R20ScenarioMatrix,
                         R20SessionMemory, R20SpecLedger, R20TelemetryWatchdog,
                         SreSlopGuard)

    def _dump(out: Dict[str, Any], path: Optional[str]) -> None:
        if not path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(out, f, ensure_ascii=False, indent=2)

    def _dump_md(text: str, path: Optional[str]) -> None:
        if not path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    local_ws = os.path.join(workspace.role_workspace(_HERE))

    if args.ecmd == "probe":
        out = R20RuntimeEngine().probe_health()
        _dump(out, args.out)
        return out
    if args.ecmd == "decompile":
        comp = R20IntentCompiler()
        out = comp.compile_request(args.text, args.deadline or None)
        _dump(out, args.out)
        _dump_md(comp.render_markdown(out), args.md)
        return out
    if args.ecmd == "heal":
        healer = R20ReflexiveHealer()
        artifact = None
        if args.artifact and os.path.exists(args.artifact):
            with open(args.artifact, encoding="utf-8-sig") as f:
                artifact = _json.load(f)
        if artifact is not None:
            out = healer.reflexive_loop(artifact, args.action)
        else:
            audit = healer.audit_redlines(args.action, None)
            out = {"ok": not audit["blocked"], "audit": audit,
                   "engine": healer.ENGINE, "layer": healer.LAYER}
        _dump(out, args.out)
        return out
    if args.ecmd == "spec":
        ledger = R20SpecLedger()
        spec = ledger.load_spec()
        out: Dict[str, Any] = {"ok": spec["ok"], "engine": ledger.ENGINE,
                               "layer": ledger.LAYER, "spec": spec}
        if args.export_dir:
            out["export"] = ledger.export_gates(args.export_dir)
        if args.artifact and os.path.exists(args.artifact):
            with open(args.artifact, encoding="utf-8-sig") as f:
                art = _json.load(f)
            out["compliance"] = ledger.verify_gate_compliance(args.artifact_type, art)
            out["ok"] = out["ok"] and out["compliance"]["ok"]
        _dump(out, args.out)
        return out
    if args.ecmd == "slop":
        out = SreSlopGuard().clean(args.text)
        _dump(out, args.out)
        return out
    if args.ecmd == "scenario":
        eng = R20ScenarioMatrix()
        out = eng.compile_matrix(args.service, args.severity)
        _dump(out, args.out)
        _dump_md(eng.render_markdown(out), args.md)
        return out
    if args.ecmd == "bundle":
        out_dir = args.out_dir or os.path.join(local_ws, "bundles")
        built = R20AssetBundle(out_dir).build(args.run_id)
        _dump({k: v for k, v in built.items() if k not in ("bundle", "sarif", "vega")}, args.out)
        return built
    if args.ecmd == "patch":
        eng = R20DiffPatchEngine()
        if args.base and args.new:
            with open(args.base, encoding="utf-8-sig") as f:
                old = _json.load(f)
            with open(args.new, encoding="utf-8-sig") as f:
                new = _json.load(f)
            out = eng.patch_with_recheck(old, new)
        else:
            out = eng.demo()
        _dump(out, args.out)
        return out
    if args.ecmd == "memory":
        out = R20SessionMemory(local_ws).demo(args.query)
        _dump(out, args.out)
        return out
    if args.ecmd == "watchdog":
        out = R20TelemetryWatchdog(local_ws).probe_health()
        _dump(out, args.out)
        return out
    raise SystemExit(f"unknown evolve command: {args.ecmd}")


# --------------------------------------------------------------------------- #
# 示例工件 / manifest
# --------------------------------------------------------------------------- #
def make_demo(artifacts_dir: str) -> Dict[str, str]:
    os.makedirs(artifacts_dir, exist_ok=True)
    out: Dict[str, str] = {}
    for name in ("monitor", "uptime", "alert", "escalation",
                 "statuspage", "incident", "backup", "snapshot",
                 "restore", "drill", "rpo_rto", "rollback",
                 "postmortem", "improvement"):
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
            "capability_status": {"local_backup_restore_drill": "real", "production_restore": "blocked"}}


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
        spec = c.load_json(args.input)
        source = spec.get("source", "") if isinstance(spec, dict) else str(spec)
        out = local_exec.execute(source)
        out["result_path"] = args.output
        c.write_json(args.output, out); emit_result(out)
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
        return 0 if out.get("ok", False) else 1

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
