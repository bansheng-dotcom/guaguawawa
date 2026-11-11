#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R08 蛙建成 · 产品实现官(MVP) —— 本地可运行 Agent（七技能调度器）。

把 7 个能力域各自做成一个独立技能模块（skills/s01..s07），本文件只做三件事：
    1. 注册 7 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    prd + ui_brief  →  mvp + page_assets

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py slice mvp --input examples/slice.json
    python agent.py landing landing --input examples/landing.json
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：统一安全引导，注入 sys.path 与 utf-8 编码 ---
import os as _os
import sys as _sys

if hasattr(_sys.stdout, "reconfigure"):
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(_sys.stderr, "reconfigure"):
    try:
        _sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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

ROLE = "r08"
CAPABILITY_STATUS = {
    "default": "real",
    "reason": "仅读取并校验本地输入，未调用外部系统",
    "external_actions": "simulated",
}
WORKSPACE_ROOT = os.path.join(_AGENTS, "workspace")
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
_INTENT_ROUTES = [
    (("幻灯片", "ppt", "deck", "演示文稿", "汇报材料"), "deck", "plan", {}),
    (("html 报告", "网页报告", "报告页", "研究报告页"), "htmlreport", "plan", {}),
    (("小程序", "miniapp", "taro", "weapp"), "miniapp", "plan", {}),
    (("landing", "落地页", "h5", "收集邮箱", "单页"), "landing", "landing", {}),
    (("prototype", "flutter", "跨端", "移动", "app原型", "原型"), "prototype", "prototype", {}),
    (("email", "邮件", "模板", "退订"), "saas", "email", {}),
    (("saas", "多页", "脚手架"), "saas", "saas", {}),
    (("slice", "切片", "最小", "形态"), "slice", "slice", {}),
    (("mvp", "最小可行", "五门禁", "假设"), "slice", "mvp", {}),
    (("scaffold", "spec", "仓库", "脚手架", "骨架", "目录树"), "scaffold", "scaffold", {}),
    (("设计系统", "设计", "组件", "token", "令牌", "设计稿"), "design", "design", {}),
    (("qa", "验证", "交接", "测试", "截图", "无障碍", "handoff", "门禁"), "qa", "qa", {}),
]


def _with_capability(data: Dict[str, Any], status: str = "real") -> Dict[str, Any]:
    data.setdefault("capability_status", status)
    data.setdefault("capability_evidence", "local input inspected" if status == "real" else "external system not connected")
    return data


def emit_result(data: Dict[str, Any]) -> None:
    c.emit(_with_capability(data))


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R08 蛙建成 · 产品实现官")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    sp.add_parser("demo", help="生成示例实现工件（slice/scaffold/landing/prototype）")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)
    add_clarify_parser(sp)

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)
    la = sp.add_parser("local-check", help="本地项目文件/骨架验收")
    la.add_argument("--input", required=True)

    ev_p = sp.add_parser("evolve", help="十维演进元模型引擎调度 (L01~L10)")
    ev_sub = ev_p.add_subparsers(dest="subcmd", required=True)
    ev_sub.add_parser("probe", help="L01: 探测引擎健康状态")
    dec_p = ev_sub.add_parser("decompile", help="L02: 意图解构与DAG编排")
    dec_p.add_argument("--query", required=True, help="交付诉求自然语言")
    heal_p = ev_sub.add_parser("heal", help="L03: 自愈反思与红线审判")
    heal_p.add_argument("--type", default="mvp", dest="heal_type")
    heal_p.add_argument("--input", required=True)
    spec_p = ev_sub.add_parser("spec-tokens", help="L04: 领域规格与令牌导出")
    spec_p.add_argument("--format", default="css", choices=["css", "flutter", "json"])
    slop_p = ev_sub.add_parser("slopguard", help="L05: 原型质感去劣与占位驱除")
    slop_p.add_argument("--text", required=True)
    scen_p = ev_sub.add_parser("scenario", help="L06: 裂变横向决策看板")
    scen_p.add_argument("--project", default="MVP交付项目")

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：slice/mvp/scaffold/landing/verify 等")
    ha = h.add_subparsers(dest="hcmd", required=True)
    for name, help_txt in {
        "slice": "产品切片门禁", "mvp": "MVP 设计门禁",
        "scaffold": "仓库脚手架门禁", "spec": "工程 Spec 门禁",
        "landing": "落地页门禁", "form": "表单门禁",
        "saas": "SaaS 脚手架门禁", "email": "邮件脚手架门禁",
        "prototype": "跨平台原型门禁", "screen": "单屏门禁",
        "design": "设计系统门禁", "token": "Token 门禁",
        "qa": "质量验证门禁", "handoff": "交接门禁",
    }.items():
        pa = ha.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    v = ha.add_parser("verify", help="综合门禁（mvp+qa）")
    v.add_argument("--mvp", required=True)
    v.add_argument("--qa", required=True)
    pl = ha.add_parser("plan", help="实现计划门禁（plan_schema）")
    pl.add_argument("--input", required=True)
    rl = ha.add_parser("runlog", help="运行可观测性：最近 N 次运行记录")
    rl.add_argument("--n", type=int, default=10)


def _run_harness(args) -> Dict[str, Any]:
    if args.hcmd == "verify":
        return harness.verify(args.mvp, args.qa)
    if args.hcmd == "plan":
        return harness.validate_plan(args.input)
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
    p = sp.add_parser("review", help="对抗评审：对技能产出做确定性挑战")
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
    result.setdefault("capability_status", "real")
    result.setdefault("capability_evidence", "local input inspected")
    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    outputs: List[protocol.Port] = []
    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs.append(protocol.Port(f"{skill_name}.json", "data"))

    ports = role_runtime.emit(
        role=ROLE, name="蛙建成", title="产品实现官 (MVP)",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="mvp_report")
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
    for name in ("slice", "scaffold", "landing", "prototype"):
        src = os.path.join(_HERE, "examples", f"{name}.json")
        dst = os.path.join(artifacts_dir, f"{name}.json")
        c.write_json(dst, c.load_json(src))
        out[name] = dst
    return out


def manifest() -> Dict[str, Any]:
    r = registry.by_id(ROLE)
    skills = [{"name": m.NAME, "desc": m.DESC,
               "actions": contracts.actions(m.NAME)}
              for m in SKILLS]
    return {"role": r["id"], "capability_status": CAPABILITY_STATUS, "title": r["title"],
            "capabilities": r["capabilities"],
            "inputs": r["inputs"], "outputs": r["outputs"],
            "skills": skills,
            "skill_count": len(SKILLS),
            "action_count": sum(len(s["actions"]) for s in skills),
            "cases": [row["case_id"] for row in cases.list_cases()],
            "contracts": [f"{s}/{a}" for s in contracts.skill_names()
                          for a in contracts.actions(s)],
            "boundary": {
                "in_scope": ["产品切片与 MVP 设计", "脚手架/落地页/邮件/SaaS 骨架",
                             "跨平台原型与设计 token", "质量门禁与交接包"],
                "out_of_scope": ["生产级工程与可靠性（归 R09/R20）",
                                 "数据分析结论（归 R06）", "策略与研究结论（归 R05）"],
                "never": ["空泛/占位产出（待定/TODO/占位）",
                          "越界做生产工程而不声明 handoff",
                          "无具体交付物的叙述性输出"],
            },
            "intent_routes": [{"keys": list(k), "skill": s, "action": a}
                              for k, s, a, _ in _INTENT_ROUTES]}


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

    if args.skill == "local-check":
        from local_actions import inspect_scaffold
        source = c.load_json(args.input)
        out = inspect_scaffold(source, os.path.dirname(os.path.abspath(args.input)))
        emit_result(out)
        return 0 if out["ok"] else 1
    if args.skill == "manifest":
        emit_result(manifest())
        return 0
    if args.skill == "demo":
        artifacts = os.path.join(WORKSPACE_ROOT, "artifacts")
        emit_result({"demo_artifacts": make_demo(artifacts)})
        return 0
    if args.skill == "run":
        emit_result(run_task(args.task))
        return 0
    if args.skill == "clarify":
        return clarify_cli(ROLE, args.intent)
    if args.skill == "local-check":
        from local_actions import inspect_scaffold
        source = c.load_json(args.input)
        out = inspect_scaffold(source, os.path.dirname(os.path.abspath(args.input)))
        emit_result(out)
        return 0 if out["ok"] else 1
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
        from engines import (
            PrototypeRuntimeEngine,
            IntentCompiler,
            PrototypeReflexiveHealer,
        )
        if args.subcmd == "probe":
            eng = PrototypeRuntimeEngine()
            out = eng.probe_health()
            emit_result(out)
            return 0 if out.get("status") == "healthy" else 1
        elif args.subcmd == "decompile":
            comp = IntentCompiler()
            out = comp.decompile(args.query)
            emit_result(out)
            return 0 if out.get("ok") else 1
        elif args.subcmd == "heal":
            healer = PrototypeReflexiveHealer()
            in_data = c.load_json(args.input)
            out = healer.audit_and_heal(args.heal_type, in_data)
            emit_result(out)
            return 0 if out.get("ok") else 1
        elif args.subcmd == "spec-tokens":
            from engines.tech_spec_ledger import TechSpecLedger
            ledger = TechSpecLedger()
            if args.format == "css":
                emit_result({"css": ledger.export_css_variables()})
            elif args.format == "flutter":
                emit_result({"flutter": ledger.export_flutter_theme()})
            else:
                emit_result(ledger.load_spec())
            return 0
        elif args.subcmd == "slopguard":
            from engines.prototype_slop_guard import PrototypeSlopGuard
            guard = PrototypeSlopGuard()
            emit_result(guard.audit_text(args.text))
            return 0
        elif args.subcmd == "scenario":
            from engines.scenario_matrix import ScenarioMatrix
            mat = ScenarioMatrix()
            emit_result(mat.generate_matrix(args.project))
            return 0

    t0 = time.time()
    result = SKILL_BY_NAME[args.skill].run(args)
    elapsed = int((time.time() - t0) * 1000)
    result = {"result": result} if not isinstance(result, dict) else result
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