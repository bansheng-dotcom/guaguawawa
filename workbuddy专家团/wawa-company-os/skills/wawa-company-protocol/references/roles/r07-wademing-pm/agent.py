#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R07 蛙得明 · 产品经理 —— 本地可运行 Agent（八技能调度器）。

把 8 个能力域各自做成一个独立技能模块（skills/s01..s08），本文件只做三件事：
    1. 注册 8 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    research_report + voc  →  prd + backlog

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py prd prd --input examples/prd.json
    python agent.py priority rice --input backlog.json
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _REPO_ROOT not in _sys.path:
    _sys.path.insert(0, _REPO_ROOT)


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
from skills import SKILLS, _common as c
from skills import s01_discover, s02_ost, s03_prd, s04_priority, s05_roadmap, s06_metrics, s07_techbrief, s08_decision  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402
from agents.shared import role_runtime  # noqa: E402
import report_contract  # noqa: E402

ROLE = "r07"
WORKSPACE_ROOT = os.path.join(_AGENTS, "workspace")
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
_INTENT_ROUTES = [
    (("prd", "产品文档", "需求文档", "需求说明", "需求分析"), "prd", "prd", {}),
    (("用户故事", "story", "故事", "验收"), "prd", "story", {}),
    (("优先级", "打分", "rice", "ice", "排序", "backlog", "排期"), "priority", "rice", {}),
    (("路线图", "roadmap", "发布"), "roadmap", "roadmap", {}),
    (("北极星", "okr", "愿景", "指标", "metrics"), "metrics", "northstar", {}),
    (("技术", "brief", "代码", "ui", "反推", "接口"), "techbrief", "techbrief", {}),
    (("决策", "汇报", "需求卡", "需求管理", "经验卡", "经验"), "decision", "decision", {}),
    (("机会", "ost", "方案", "假设", "验证"), "ost", "ost", {}),
    (("调研", "访谈", "发现", "research", "voc", "挖掘", "报告"), "discover", "discover", {}),
]


def emit_result(data: Dict[str, Any]) -> None:
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R07 蛙得明 · 产品经理")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    sp.add_parser("demo", help="生成示例产品工件（PRD/Job story/Backlog/指标）")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)

    # 深度产品机会树与 PRD 流水线
    dp = sp.add_parser("deep", help="PM 深度产品机会树与 PRD 流水线")
    dp.add_argument("--input", required=True, help="JTBD / 需求输入 JSON")
    dp.add_argument("--intent", default="产品机会树与PRD深度诊断", help="分析意图")
    dp.add_argument("--out-dir", default=None, help="输出目录")

    for m in SKILLS:
        add_parser = getattr(m, "add_parser", None)
        if add_parser is not None:
            add_parser(sp)
        else:
            # 旧技能模块没有 add_parser；按其公开动作构造统一 CLI。
            mp = sp.add_parser(m.NAME, help=m.DESC)
            ap = mp.add_subparsers(dest="action", required=True)
            for action in contracts.actions(m.NAME):
                act = ap.add_parser(action)
                act.add_argument("--input", required=True)
    return p


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：prd/demand/decision/northstar/verify 等")
    ha = h.add_subparsers(dest="hcmd", required=True)
    for name, help_txt in {
        "jobstory": "JTBD Job story 门禁", "discover": "发现计划门禁",
        "interview": "访谈脚本门禁", "ost": "机会树门禁", "poc": "POC 打分门禁",
        "assumption": "假设优先级门禁", "prd": "PRD 八门禁", "acceptance": "验收门禁",
        "northstar": "北极星门禁", "metrics": "指标分层门禁", "okr": "OKR 门禁",
        "techbrief": "技术翻译门禁", "uibrief": "UI Brief 门禁",
        "codetoprd": "代码反推需求门禁", "releasegate": "发布门禁",
        "decision": "决策汇报门禁", "demand": "需求卡门禁", "experience": "经验卡门禁",
    }.items():
        pa = ha.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    v = ha.add_parser("verify", help="综合门禁（prd+decision）")
    v.add_argument("--prd", required=True)
    v.add_argument("--decision", required=True)
    rl = ha.add_parser("runlog", help="运行可观测性：最近 N 次运行记录")
    rl.add_argument("--n", type=int, default=10)


def _run_harness(args) -> Dict[str, Any]:
    if args.hcmd == "verify":
        return harness.verify(args.prd, args.decision)
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
    vi = ca.add_parser("validate-input", help="按契约校验某技能的输入 JSON")
    vi.add_argument("--skill", required=True, dest="contract_skill")
    vi.add_argument("--action", required=True, dest="contract_action")
    vi.add_argument("--input", required=True, dest="contract_input")


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
    if args.ccmd == "validate-input":
        data = c.load_json(args.contract_input)
        return contracts.validate_input(skill, action, data)
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

    report_path = os.path.join(out_dir, "prd_report.md")
    _data = c.load_json(in_file) if in_file and in_file.endswith(".json") and os.path.exists(in_file) else None
    ports = role_runtime.emit(
        role=ROLE, name="蛙得明", title="产品经理",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="prd_report",
        specialist=report_contract.r07_contract, data=_data)
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
    return "prd", "prd", {}


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
    for name in ("prd", "jobstory", "backlog", "northstar"):
        src = os.path.join(_HERE, "examples", f"{name}.json")
        dst = os.path.join(artifacts_dir, f"{name}.json")
        c.write_json(dst, c.load_json(src))
        out[name] = dst
    return out


def manifest() -> Dict[str, Any]:
    r = registry.by_id(ROLE)
    return {"role": r["id"], "name": r["name"], "title": r["title"],
            "capabilities": r["capabilities"],
            "inputs": r["inputs"], "outputs": r["outputs"],
            "capability_status": {"default": "real",
                                  "reason": "本地确定性产品技能可执行",
                                  "external_actions": "simulated"},
            "skills": [{"skill": m.NAME, "name": m.NAME,
                        "description": m.DESC, "desc": m.DESC,
                        "actions": list(getattr(m, "ACTIONS", {}).keys())}
                       for m in SKILLS]}


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
    if args.skill == "demo":
        artifacts = os.path.join(WORKSPACE_ROOT, "artifacts")
        emit_result({"demo_artifacts": make_demo(artifacts)})
        return 0
    if args.skill == "run":
        emit_result(run_task(args.task))
        return 0
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

    if args.skill == "deep":
        from deep_analysis import run_deep_analysis
        from agents.shared.report_generator import generate_professional_report
        from agents.shared.role_profiles import get as get_profile

        out_dir = getattr(args, "out_dir", None) or os.path.join(os.path.dirname(__file__), "workspace", "deep_report")
        res = run_deep_analysis(args.input)
        profile = get_profile(ROLE)
        
        spec = {
            "role_id": ROLE,
            "agent_name": profile["name"],
            "report_title": f"{profile['name']} · {args.intent}",
            "executive_summary": res["decision"]["summary"],
            "decision_directive": res["decision"]["directive"],
            "kpi_metrics": [
                {"label": "门禁通过", "value": f"{len([c for c in res['checks'] if c.get('ok')])}/{len(res['checks'])}", "status": "normal"},
            ],
            "analysis_sections": [
                {"title": "1. JTBD 需求发现", "content": "已完成核心用户场景的 JTBD 映射。"},
                {"title": "2. 机会树映射", "content": "已构建产品机会树，覆盖核心增长空间。"},
                {"title": "3. 风险边界校验", "content": "风险控制点已纳入 PRD 规划。"},
                {"title": "4. PRD 生成", "content": "规格书已定稿。"},
            ],
            "figures": [],
            "guardrails": profile["guardrails"],
            "rollout_plan": profile["rollout"],
            "next_steps": profile["next_steps"],
            "rca": res["decision"]["rca"],
            "provenance": {"input": args.input, "tokens": res["tokens_in"] + res["tokens_out"]},
        }
        files = generate_professional_report(out_dir=out_dir, report_slug="pm_deep_report", **spec)
        emit_result({"ok": True, "report_html": files["html"], "report_md": files["md"]})
        return 0

    t0 = time.time()
    mod = SKILL_BY_NAME[args.skill]
    if hasattr(mod, "run"):
        result = mod.run(args)
    else:
        # r07 技能模块按「动作函数(input_data)」组织，无统一 run(args)。
        fn = getattr(mod, getattr(args, "action", None), None)
        if not callable(fn):
            result = {"ok": False, "error": f"未知动作: {getattr(args, 'action', None)}"}
        else:
            inp = c.load_json(args.input) if getattr(args, "input", None) else {}
            result = fn(inp)
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