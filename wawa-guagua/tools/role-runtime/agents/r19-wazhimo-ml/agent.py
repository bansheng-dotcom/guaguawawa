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

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)

    for m in SKILLS:
        m.add_parser(sp)
    return p


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
