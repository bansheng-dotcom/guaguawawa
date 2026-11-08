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
from agents.shared import role_runtime  # noqa: E402
from skills import SKILLS, _common as c  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402
import local_exec  # noqa: E402

ROLE = "r20"
WORKSPACE_ROOT = os.path.join(_AGENTS, "workspace")
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
# 「删除快照/灾难切换」等不可逆词必须排在通用词之前，避免误路由到普通动作。
_INTENT_ROUTES = [
    (("删除快照", "删除备份", "清空快照", "灾难切换", "切换生产", "恢复生产"),
     "dr", "rollback", {}),
    (("rpo", "rto", "恢复点", "恢复时间", "灾难恢复", "恢复手册", "dr"),
     "dr", "rpo_rto", {}),
    (("回滚", "rollback", "退路", "撤销切换"), "dr", "rollback", {}),
    (("恢复演练", "演练", "drill", "能否恢复", "恢复验证"), "restore", "drill", {}),
    (("恢复", "restore", "还原"), "restore", "restore", {}),
    (("快照", "snapshot", "存了哪些", "备份了多少"), "backup", "snapshot", {}),
    (("加密", "保留策略", "排除规则", "备份仓", "备份", "restic", "repo", "backup"),
     "backup", "backup", {}),
    (("状态页", "组件状态", "对外状态", "statuspage"), "statuspage", "statuspage", {}),
    (("事件", "故障通报", "事件时间线", "incident"), "statuspage", "incident", {}),
    (("值班升级", "升级链", "escalation", "oncall"), "alert", "escalation", {}),
    (("告警", "报警", "通知渠道", "阈值告警", "alert"), "alert", "alert", {}),
    (("可用率", "uptime", "可用性记录", "在线率"), "monitor", "uptime", {}),
    (("监控", "探测", "心跳", "monitor", "站点"), "monitor", "monitor", {}),
    (("复盘", "故障复盘", "postmortem", "事故分析"), "postmortem", "postmortem", {}),
    (("改进项", "闭环", "整改", "improvement"), "postmortem", "improvement", {}),
]

_DEFAULT_ROUTE = ("monitor", "monitor", {})


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

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)

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
    return _DEFAULT_ROUTE


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
