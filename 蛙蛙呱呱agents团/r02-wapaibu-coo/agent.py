# -*- coding: utf-8 -*-
"""R02 蛙排布（COO / 首席运营官）角色 Agent。

职责（能力全景 R02 七个能力域）：工作拆解与排期 / 容量与委派 / 交接与验收追踪 /
复盘与事故分析 / 流程与 SOP / 知识运营 / 项目群与 Agent 编排。

用法：
  python agent.py manifest
  python agent.py demo
  python agent.py skills
  python agent.py <skill> <action> --input <json>
  python agent.py contract list|<skill>|validate <skill> <action> --input <json>
  python agent.py review --skill <s> --action <a> --input <json>
  python agent.py case list|validate|get <case_id>
  python agent.py harness <validator> --input <json>
  python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_AGENT_DIR = _os.path.dirname(_os.path.abspath(__file__))
_AGENTS = _os.path.dirname(_AGENT_DIR)
_REPO_ROOT = _os.path.dirname(_AGENTS)
for _p in [_AGENT_DIR, _AGENTS, _REPO_ROOT]:
    if _p not in _sys.path:
        _sys.path.insert(0, _p)


import argparse
import json
import os
import sys
from agents.shared.chat_cli import add_chat_parser, handle_chat
from typing import Any, Dict, List

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(AGENT_DIR)
sys.path.insert(0, AGENTS)

from core import workspace
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route
from agents.shared import role_runtime  # REP-001 报告引擎
from core import protocol
from skills import SKILLS

ROLE = "r02"
WORKSPACE_ROOT = os.path.join(AGENTS, "workspace")
ws = workspace.Workspace(WORKSPACE_ROOT)


# --------------------------------------------------------------------------- #
# manifest
# --------------------------------------------------------------------------- #
def manifest() -> Dict[str, Any]:
    from core import registry

    role = registry.by_id(ROLE)
    skills = [{"skill": s.NAME, "name": s.NAME, "description": s.DESC,
               "desc": s.DESC, "actions": _actions(s)} for s in SKILLS]
    return {"role": role["id"], "name": "蛙排布 · COO",
            "title": role["title"],
            "desc": "首席运营官：排期 / 容量 / 交接验收 / 复盘 / SOP / 知识 / 项目群编排",
            "capabilities": role["capabilities"], "inputs": role["inputs"],
            "outputs": role["outputs"],
            "capability_status": {"default": "real",
                                  "reason": "本地确定性技能可执行；外部系统操作不代执行",
                                  "external_actions": "simulated"},
            "skills": skills}


def _actions(s) -> List[str]:
    if s.NAME == "schedule":
        return ["wbs", "sprint", "critpath"]
    if s.NAME == "capacity":
        return ["check", "delegate", "split"]
    if s.NAME == "handoff":
        return ["package", "accept", "trace"]
    if s.NAME == "retro":
        return ["postmortem", "grade", "action"]
    if s.NAME == "process":
        return ["sop", "waste", "meeting"]
    if s.NAME == "knowledge":
        return ["digest", "entry", "search"]
    return ["status", "plan", "graph"]


# --------------------------------------------------------------------------- #
# demo：复制 7 份示例工件
# --------------------------------------------------------------------------- #
_DEMO_ASSETS = ["wbs.json", "capacity.json", "delegation.json", "handoff.json",
                "incident.json", "sop.json", "portfolio.json"]


def make_demo(ws) -> Dict[str, Any]:
    demo_dir = os.path.join(ws.artifacts_dir, "demo")
    os.makedirs(demo_dir, exist_ok=True)
    made: List[str] = []
    for f in _DEMO_ASSETS:
        src = os.path.join(AGENT_DIR, "examples", f)
        if os.path.isfile(src):
            with open(src, encoding="utf-8") as fh:
                data = json.load(fh)
            with open(os.path.join(demo_dir, f), "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            made.append(os.path.join("demo", f))
    return {"ok": True, "demo_artifacts": made,
            "count": len(made),
            "note": "7 能力域示例工件已就绪，供第一次运行 smoke"}


# --------------------------------------------------------------------------- #
# CLI 调度
# --------------------------------------------------------------------------- #
def run_cli(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="r02-agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    sub.add_parser("demo")
    sub.add_parser("skills")
    for s in SKILLS:
        s.add_parser(sub)
    c_sub = sub.add_parser("contract", help="输出契约：list / validate")
    cc = c_sub.add_subparsers(dest="contract_cmd", required=True)
    cc.add_parser("list")
    cs = cc.add_parser("skill", help="契约详情")
    cs.add_argument("skill")
    cv = cc.add_parser("validate", help="校验 --data-json 或 stdin")
    cv.add_argument("skill")
    cv.add_argument("action")
    cv.add_argument("--data-json")
    r_sub = sub.add_parser("review", help="对抗性评审")
    r_sub.add_argument("--skill")
    r_sub.add_argument("--action")
    r_sub.add_argument("--input")
    r_sub.add_argument("--result-json", help="直接给 result（默认读 __AGENT_RESULT__ 包裹的输入文件）")
    case_sub = sub.add_parser("case", help="案例库：list / validate / get")
    casec = case_sub.add_subparsers(dest="case_cmd", required=True)
    casec.add_parser("list")
    cvv = casec.add_parser("validate")
    cvv.add_argument("case_id")
    cg = casec.add_parser("get")
    cg.add_argument("case_id")
    h_sub = sub.add_parser("harness", help="确定性验证器（21 项）")
    h_sub.add_argument("validator", choices=[
        "wbs", "sprint", "critpath", "check", "delegate", "split", "package",
        "accept", "trace", "postmortem", "grade", "action", "sop", "waste",
        "meeting", "digest", "entry", "search", "status", "plan", "graph",
        "verify", "runlog"])
    h_sub.add_argument("--input")
    run_sub = sub.add_parser("run", help="处理路由给我的任务")
    run_sub.add_argument("--task")
    add_clarify_parser(sub)
    args = ap.parse_args(argv)


    if args.cmd == "chat":
        return handle_chat(args, role_id="r02")
    if args.cmd == "manifest":
        print("__AGENT_RESULT__ " + json.dumps(manifest(), ensure_ascii=False))
        return 0
    if args.cmd == "demo":
        print(json.dumps(make_demo(ws), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "skills":
        print(json.dumps([s.NAME for s in SKILLS], ensure_ascii=False))
        return 0
    if args.cmd == "run":
        return run_task(args, ws)
    if args.cmd == "clarify":
        return clarify_cli(ROLE, args.intent)
    for s in SKILLS:
        if args.cmd == s.NAME:
            result = s.run(args)
            ws.log_run(f"{ROLE}-{s.NAME}-{args.action}",
                       {"role": ROLE, "skill": s.NAME, "action": args.action,
                        "ok": result.get("ok", False)})
            print("__AGENT_RESULT__ " + json.dumps(result, ensure_ascii=False))
            return 0 if result.get("ok") else 1
    if args.cmd == "contract":
        import contracts
        if args.contract_cmd == "list":
            print(json.dumps({"skills": contracts.list_skills(),
                              "actions": {s: contracts.list_actions(s)
                                          for s in contracts.list_skills()}},
                             ensure_ascii=False, indent=2))
            return 0
        if args.contract_cmd == "skill":
            sc = contracts.CONTRACTS.get(args.skill, {})
            print(json.dumps(sc, ensure_ascii=False, indent=2))
            return 0
        if args.contract_cmd == "validate":
            if args.data_json:
                import json as _json
                data = _json.loads(args.data_json)
            else:
                data = json.loads(sys.stdin.read())
            errs = contracts.validate_output(args.skill, args.action, data)
            print(json.dumps({"valid": not errs, "errors": errs},
                             ensure_ascii=False))
            return 0 if not errs else 1
    if args.cmd == "review":
        import review as review_mod
        from skills import _common as c
        packet: Dict[str, Any] = {"skill": args.skill, "action": args.action}
        if args.result_json:
            with open(args.result_json, encoding="utf-8") as fh:
                packet["result"] = json.load(fh)
        elif args.input:
            raw = c.load_text(args.input)
            marker = "__AGENT_RESULT__ "
            i = raw.rfind(marker)
            packet["result"] = json.loads(raw[i + len(marker):] if i >= 0
                                          else raw)
        out = review_mod.review_packet(packet)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("verdict") == "PASS" else 1
    if args.cmd == "case":
        import cases as cases_mod
        if args.case_cmd == "list":
            print(json.dumps(cases_mod.list_cases(), ensure_ascii=False,
                             indent=2))
            return 0
        if args.case_cmd == "validate":
            out = cases_mod.validate_case(args.case_id)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("ok") else 1
        out = cases_mod.get_case(args.case_id)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "harness":
        import harness as harness_mod
        if args.validator == "runlog":
            runs = ws.runlog(5)
            print(json.dumps({"runs": runs}, ensure_ascii=False, indent=2))
            return 0
        if args.validator == "verify":
            from skills import _common as c
            data = c.load_json(args.input)
            out = harness_mod.verify(data)
            print(json.dumps({"ok": out["ok"], "sprint_end": out["sprint_end"],
                              "overloaded": out["overloaded"]},
                             ensure_ascii=False))
            return 0 if out["ok"] else 1
        if not args.input:
            print(json.dumps({"ok": False, "error": "--input 必填"},
                             ensure_ascii=False))
            return 1
        out = harness_mod.run_validator(args.validator, args.input)
        compact = {k: v for k, v in out.items() if k != "harness_result"}
        print(json.dumps(compact, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    ap.print_help()
    return 2


# --------------------------------------------------------------------------- #
# run_task：处理路由给 r02 的任务
# --------------------------------------------------------------------------- #
# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
_INTENT_ROUTES = [
    (("wbs", "工作分解", "拆工作"), "schedule", "wbs", {}),
    (("排期", "冲刺", "sprint", "工期", "排产"), "schedule", "sprint", {}),
    (("容量", "过载", "负载", "人日"), "capacity", "check", {}),
    (("交接", "handoff", "交接包", "工单"), "handoff", "package", {}),
    (("复盘", "事故", "postmortem", "根因"), "retro", "postmortem", {}),
    (("流程", "sop", "标准化", "固化"), "process", "sop", {}),
    (("项目群", "编排", "状态汇总", "portfolio"), "portfolio", "status", {}),
]


def _route(intent: str):
    t = intent.lower()
    for kws, skill, action, defaults in _INTENT_ROUTES:
        if any(k.lower() in t for k in kws):
            return skill, action, defaults
    # 关键词未命中：交给共享 L02 内核；不再静默落到 portfolio.status。
    return fallback_route(ROLE, intent)


_ACTION_HINT = {
    "schedule": ("排期排产", "按能力域 1 拆解排期"),
    "capacity": ("容量委派", "按能力域 2 检查容量与派工"),
    "handoff": ("交接验收", "按能力域 3 打交接包走验收"),
    "retro": ("复盘闭环", "按能力域 4 复盘与行动项闭环"),
    "process": ("流程固化", "按能力域 5 固化为 SOP"),
    "knowledge": ("知识沉淀", "按能力域 6 沉淀进知识库"),
    "portfolio": ("项目群编排", "按能力域 7 编排与状态汇总"),
}


def run_task(args, ws) -> int:
    if not args.task:
        print(json.dumps({"error": "--task 必填"}, ensure_ascii=False))
        return 1
    t = ws.read_task(args.task)
    if t is None:
        print(json.dumps({"error": f"任务 {args.task} 不存在"}, ensure_ascii=False))
        return 1
    if t.owner != ROLE:
        print(json.dumps({"error": f"任务 owner={t.owner} 非 {ROLE}"},
                         ensure_ascii=False))
        return 1
    skill, action, defaults = _route(t.intent)
    if skill == "__clarify__":
        ws.set_status(args.task, "failed")
        payload = {"error": "needs_clarification",
                   "questions": defaults.get("questions", []),
                   "assumptions": defaults.get("assumptions", []),
                   "plan": defaults.get("plan")}
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    title, note = _ACTION_HINT[skill]
    out_dir = os.path.join(ws.artifacts_dir, ROLE, t.task_id)
    os.makedirs(out_dir, exist_ok=True)

    # 真实运行该技能动作，把 result 交给共享报告桥渲染（而非手搓 md）
    result: Dict[str, Any] = {"ok": True, "skill": skill,
                              "intent": t.intent, "note": note}
    mod = None
    for s in SKILLS:
        if s.NAME == skill:
            mod = s
            break
    if mod is not None:
        try:
            ns = argparse.Namespace(action=action, input=None, task=t.task_id)
            out = mod.run(ns)
            if isinstance(out, dict):
                result = out
                result.setdefault("skill", skill)
                result.setdefault("action", action)
        except Exception as e:  # noqa: BLE001  技能缺参时降级为编排记录
            result = {"ok": False, "skill": skill, "action": action,
                      "error": f"{type(e).__name__}: {e}",
                      "conclusion": f"技能 {skill} 未执行（缺参数），已记录路由与闭环。"}

    in_file = None
    if t.inputs:
        for inp in t.inputs:
            if isinstance(inp, protocol.Port) and inp.path:
                in_file = inp.path
                break
            elif isinstance(inp, dict) and inp.get("path"):
                in_file = inp["path"]
                break

    result["task_id"] = t.task_id
    ports: List[protocol.Port] = []
    ports.extend(role_runtime.emit(
        role=ROLE, name="蛙排布", title="首席运营官（COO）",
        result=result, skill=skill, action=result.get("action", "run"),
        intent=t.intent, out_dir=out_dir, input_path=in_file, md_name="coo_report"))
    # 补一份机器可读 result，便于下游消费
    result_path = os.path.join(out_dir, f"{skill}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    ports.append(protocol.Port(f"{skill}.json", "data"))

    ws.update_task(args.task, {
        "outputs": [p.to_dict() for p in ports],
        "output": f"artifacts/{ROLE}/{t.task_id}/coo_report.md",
        "status": "done", "record": result})
    ws.log_run(f"{ROLE}-run-{args.task}",
               {"role": ROLE, "skill": skill, "action": "run_task",
                "ok": bool(result.get("ok", True)), "task": t.task_id})
    print(json.dumps({"task": t.task_id, "owner": ROLE, "skill": skill,
                      "artifact": f"artifacts/{ROLE}/{t.task_id}/coo_report.md",
                      "ok": bool(result.get("ok", True))}, ensure_ascii=False))
    return 0


def main() -> int:
    _meta = role_runtime.handle_meta_command(sys.argv[1:], ROLE)
    if _meta is not None:
        return _meta

    try:
        return run_cli(sys.argv[1:])
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
