#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R01 蛙全局 · CEO 主理人 / 编排器 —— 本地可运行 Agent（七技能调度器 + 编排器）。

两层职责：
  1. 七个能力域技能（skills/s01..s07）：意图分级 / 跨部门拆解 / 硬决策 /
     反方质询 / 公司OS与治理 / 决策留痕 / 高层汇报——各自确定性校验。
  2. 编排器本体（plan/status/run）：把意图拆成公司级任务卡，指派 20 角色，
     按依赖调度执行并独立验收（Orchestrator + Shared-State 模式）。

协作契约（inputs → outputs）：
    intent + decision_memo  →  task_cards + decision_log + board_report

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py intent brief --input examples/brief.json
    python agent.py decide card --input examples/decision_card.json
    python agent.py plan --intent "分析订单数据趋势"
    python agent.py run --all
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
import time
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.dirname(_HERE)
for _p in (_HERE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import protocol, registry, runner, workspace  # noqa: E402
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402
from agents.shared import role_runtime  # REP-001 报告引擎
from skills import SKILLS, _common as c  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402
import knowledge  # noqa: E402

ROLE = "r01"
WORKSPACE_ROOT = workspace.default_root()
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。具体关键词靠前，_route 小写不区分大小写匹配。
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
# 编排器：意图路由 → 任务卡（与 S02 decompose 共用同一张 20 角色矩阵）
# --------------------------------------------------------------------------- #
from skills.s02_decompose import ROUTE_MATRIX, keyword_hits  # noqa: E402

ROUTING: Dict[str, List[str]] = {rid: list(kws) for kws, rid in ROUTE_MATRIX}


def route(intent: str) -> List[str]:
    hits = [(sum(1 for k in kws if keyword_hits(intent, k)), rid)
            for rid, kws in ROUTING.items()]
    hits = [h for h in hits if h[0] > 0]
    hits.sort(key=lambda x: -x[0])
    return [rid for _, rid in hits]


def _acceptance_for(role_id: str) -> List[str]:
    return {
        "r06": [
            "产物目录存在 analysis_report.md",
            "趋势 JSON 的 total 数值可复算",
            "数据清洗后无整行重复",
        ],
    }.get(role_id, [f"{registry.by_id(role_id)['name']} 交付物可按端口验收"])


# TEAM.md「营收最大化」四段链的场景编排。
# 命中场景信号时按固定主责链建卡（而不是把 20 角色平铺成一条长链）；
# 每段给独立意图，保证各角色能确定性路由到对应技能；
# fixture 仅作为可运行的示例输入，真实执行时应替换为业务输入。
_SCENARIO_CHAINS = [
    {
        "signals": (("营收", "收入", "利润", "gmv"), ("最大", "优化", "提升")),
        "stages": [
            ("r07", "产出定价/套餐/时段/会员策略假设（机会与验证）",
             "examples/ost.json"),
            ("r06", "用历史订单数据验证策略假设（趋势与渠道拆解）", None),
            ("r08", "组装 HTML 方案报告（落地页形态）", "examples/landing.json"),
            ("r04", "验收评审，输出 pass/fail 门禁结论",
             "examples/criteria_review.json"),
        ],
    },
]


def _scenario_stages(intent: str):
    low = intent.lower()
    for sc in _SCENARIO_CHAINS:
        if all(any(k in low for k in group) for group in sc["signals"]):
            return sc["stages"]
    return []


def _make_tasks(intent: str) -> List[protocol.Task]:
    stages = _scenario_stages(intent)
    if stages:
        return _scenario_tasks(stages)

    role_ids = route(intent)
    if not role_ids:
        return []
    tasks: List[protocol.Task] = []
    prev_id: str | None = None
    for rid in role_ids:
        r = registry.by_id(rid)
        t = protocol.Task(
            title=f"{r['name']}｜{intent[:24]}",
            owner=rid,
            intent=intent,
            acceptance=_acceptance_for(rid),
        )
        if prev_id:
            t.deps = [prev_id]
        # 数据类角色：接入默认示例数据 + 端口参数
        if rid == "r06":
            demo = os.path.join(WORKSPACE_ROOT, "artifacts", "orders.csv")
            t.inputs = [protocol.Port(
                "dataset", "data", media_type="text/csv",
                note=f"input={demo},date=date,value=amount,stage=status,group=channel")]
            t.outputs = [protocol.Port("analysis_report.md", "report", "text/markdown",
                                       note="趋势 + 漏斗 + 报告")]
        else:
            t.outputs = [protocol.Port(o, "artifact") for o in r["outputs"]]
        tasks.append(t)
        prev_id = t.task_id
    return tasks


def _scenario_tasks(stages) -> List[protocol.Task]:
    tasks: List[protocol.Task] = []
    prev_id: str | None = None
    for rid, stage_intent, fixture in stages:
        r = registry.by_id(rid)
        t = protocol.Task(
            title=f"{r['name']}｜{stage_intent}",
            owner=rid,
            intent=stage_intent,
            acceptance=_acceptance_for(rid),
        )
        if prev_id:
            t.deps = [prev_id]
        if rid == "r06":
            demo = os.path.join(WORKSPACE_ROOT, "artifacts", "orders.csv")
            t.inputs = [protocol.Port(
                "dataset", "data", media_type="text/csv",
                note=f"input={demo},date=date,value=amount,stage=status,group=channel")]
            t.outputs = [protocol.Port("analysis_report.md", "report", "text/markdown",
                                       note="趋势 + 漏斗 + 报告")]
        else:
            if fixture:
                path = os.path.join(_AGENTS, r["dir"], fixture)
                if os.path.exists(path):
                    t.inputs = [protocol.Port(path, "data")]
            t.outputs = [protocol.Port(o, "artifact") for o in r["outputs"]]
        tasks.append(t)
        prev_id = t.task_id
    return tasks


# --------------------------------------------------------------------------- #
# 编排器：按依赖执行所有待办任务，执行后独立验收
# --------------------------------------------------------------------------- #
def verify_task(task: protocol.Task) -> bool:
    out_dir = ws.artifact(task.task_id)
    ok = any(os.path.exists(os.path.join(out_dir, p.name))
             for p in task.outputs)
    ws.emit(protocol.Event.now(ROLE, "verify", task.task_id,
                               {"passed": ok, "criteria": task.acceptance}))
    return ok


_MEDIA = {".json": "application/json", ".md": "text/markdown",
          ".html": "text/html", ".csv": "text/csv", ".txt": "text/plain"}


def _artifact_dirs(task_id: str) -> List[str]:
    """角色产物目录存在两种历史约定：artifacts/{id} 与 artifacts/run-{id}。"""
    return [ws.artifact(task_id), ws.artifact(f"run-{task_id}")]


def _artifact_files(task_id: str) -> List[str]:
    out: List[str] = []
    for d in _artifact_dirs(task_id):
        if not os.path.isdir(d):
            continue
        for root, _, names in os.walk(d):
            for n in names:
                ext = os.path.splitext(n)[1].lower()
                if ext in _MEDIA:
                    out.append(os.path.join(root, n))
    # JSON 优先：多数角色技能直接 load_json，避免先拿到 md/html 解析失败。
    return sorted(out, key=lambda p: (os.path.splitext(p)[1].lower() != ".json", p))


def _hydrate_inputs(task: protocol.Task) -> protocol.Task:
    """把已完成上游任务的产物接进本任务 inputs（Shared-State 自动交接）。

    任务卡已用 `note="input=<path>"` 显式钉住输入时不再自动追加：
    各角色按“第一个存在的文件”取输入，追加会抢在显式输入前面。
    """
    if any("input=" in (p.note or "") for p in task.inputs):
        return task
    known = {p.name for p in task.inputs}
    added: List[protocol.Port] = []
    for dep_id in task.deps:
        dep = ws.read_task(dep_id)
        if dep is None or dep.status != "done":
            continue
        for path in _artifact_files(dep_id):
            if path in known:
                continue
            ext = os.path.splitext(path)[1].lower()
            added.append(protocol.Port(path, "data", _MEDIA[ext]))
            known.add(path)
    if not added:
        return task
    ports = [p.to_dict() for p in task.inputs] + [p.to_dict() for p in added]
    ws.update_task(task.task_id, {"inputs": ports})
    return ws.read_task(task.task_id) or task


def run_all(limit: int = 30) -> Dict[str, Any]:
    done_ids = {t.task_id for t in ws.list_tasks("done")}
    report = {"executed": [], "verified": [], "failed": [], "notes": []}

    for _ in range(limit):
        pending = ws.list_tasks("pending")
        ready = [t for t in pending if set(t.deps) <= done_ids]
        if not ready:
            break
        implemented = {r["id"] for r in registry.implemented()}
        progressed = False
        for t in ready:
            t = _hydrate_inputs(t)
            if t.owner not in implemented:
                ws.set_status(t.task_id, "skipped")
                report["notes"].append(f"{t.owner} 未实现，跳过 {t.task_id}")
                done_ids.add(t.task_id)
                progressed = True
                continue
            ws.set_status(t.task_id, "assigned")
            r = runner.invoke(t.owner, ["run", "--task", t.task_id])
            current = ws.read_task(t.task_id)
            # 子进程退出码不可靠：部分角色在“缺输入/需澄清”时仍返回 0，
            # 以任务卡最终状态为准，避免把 failed 记成 executed。
            if r.get("exit_code") == 0 and (current is None or current.status != "failed"):
                done_ids.add(t.task_id)
                report["executed"].append(t.task_id)
            else:
                ws.set_status(t.task_id, "failed")
                report["failed"].append({"task": t.task_id,
                                         "stderr": r.get("stderr", "")[:200]})
            progressed = True
        if not progressed:
            break

    for t in ws.list_tasks("done"):
        if verify_task(t):
            report["verified"].append(t.task_id)

    emit_result(report)
    return report


def status() -> Dict[str, Any]:
    tasks = ws.list_tasks()
    lines = [f"{t.task_id}  {t.status:<8}  {t.owner}  {t.title}  deps={t.deps}"
             for t in tasks]
    emit_result({"task_count": len(tasks), "tasks": lines})
    return {"tasks": lines}


# --------------------------------------------------------------------------- #
# 协作入口：owner=r01 的任务卡按意图路由到技能
# --------------------------------------------------------------------------- #
def run_task(task_id: str) -> Dict[str, Any]:
    task = ws.read_task(task_id)
    if task is None:
        return {"error": f"任务不存在: {task_id}"}
    task = _hydrate_inputs(task)

    # 编排器转发：owner 不是 r01 的任务交给对应角色执行
    if task.owner != ROLE:
        r = runner.invoke(task.owner, ["run", "--task", task_id])
        current = ws.read_task(task_id)
        status = current.status if current else "unknown"
        exit_code = r.get("exit_code")
        if status == "failed":
            exit_code = exit_code or 2
        return {"forwarded_to": task.owner, "status": status,
                "exit_code": exit_code,
                "stdout": r.get("stdout", "")[:2000]}

    ws.set_status(task_id, "running")
    ws.emit(protocol.Event.now(ROLE, "task_started", task_id))

    params = _parse_port_params(task.inputs)
    in_file = _first_input_file(task.inputs) or params.get("input")
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

    if in_file and os.path.exists(in_file):
        merged = dict(defaults)
        merged.update(params)
        merged["action"] = action
        merged["input"] = in_file
        result = mod.run(_mkns(**merged))
    else:
        # 无输入文件：意图分级路由也算真实产出（编排判断）
        result = _intent_result(intent)

    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs = [protocol.Port(f"{skill_name}.json", "data")]

    ports = role_runtime.emit(
        role=ROLE, name="蛙全局", title="CEO 主理人 / 编排器",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="ceo_report")
    outputs.extend(ports)

    ws.update_task(task_id, {"outputs": [p.to_dict() for p in outputs],
                             "status": "done"})
    ws.emit(protocol.Event.now(ROLE, "task_finished", task_id,
                               {"outputs": [p.name for p in outputs]}))
    return result


def _intent_result(intent: str) -> Dict[str, Any]:
    """无输入文件时的兜底：意图分级（triage）真实执行。"""
    from skills import s02_decompose
    triage = SKILL_BY_NAME["intent"].run(
        _mkns(action="triage", input=_tmp_intent_json(intent)))
    routing = s02_decompose._route({"intent": intent})
    return {"ok": bool(triage.get("ok") and routing.get("ok")),
            "intent": intent,
            "triage": {k: triage.get(k) for k in ("level", "domains", "boardroom", "next")},
            "routing": {k: routing.get(k) for k in ("roles", "boardroom", "next")},
            "checks": triage.get("checks", []) + routing.get("checks", [])}


def _tmp_intent_json(intent: str) -> str:
    import tempfile
    fd, p = tempfile.mkstemp(prefix="r01_intent_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"intent": intent}, f, ensure_ascii=False)
    return p


def _write_report(result: Dict[str, Any], title: str, path: str) -> None:
    lines = [f"# {title}", ""]
    for k, v in result.items():
        if k in ("checks",):
            continue
        lines += [f"## {k}", "", "```json",
                  json.dumps(v, ensure_ascii=False, indent=2), "```", ""]
    lines += ["## 门禁", "", "```json",
              json.dumps(result.get("checks", []), ensure_ascii=False, indent=2),
              "```"]
    c.write_text(path, "\n".join(lines))


def _route(intent: str):
    low = intent.lower()
    for kws, skill, action, defaults in _INTENT_ROUTES:
        if any(k.lower() in low for k in kws):
            return skill, action, defaults
    # 关键词未命中：交给共享 L02 内核；不再静默落到 intent.brief。
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


def _mkns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


# --------------------------------------------------------------------------- #
# 示例工件 / manifest
# --------------------------------------------------------------------------- #
def make_demo(artifacts_dir: str) -> Dict[str, str]:
    os.makedirs(artifacts_dir, exist_ok=True)
    out: Dict[str, str] = {}
    for name in ("brief", "taskcard", "decision_card", "redteam",
                 "companyos", "decisionlog", "board"):
        src = os.path.join(_HERE, "examples", f"{name}.json")
        if os.path.exists(src):
            dst = os.path.join(artifacts_dir, f"r01_{name}.json")
            c.write_json(dst, c.load_json(src))
            out[name] = dst
    return out


def manifest() -> Dict[str, Any]:
    r = registry.by_id(ROLE)
    return {"role": r["id"], "name": r["name"], "title": r["title"],
            "capabilities": r["capabilities"],
            "inputs": r["inputs"], "outputs": r["outputs"],
            "skills": [{"skill": getattr(m, "NAME", ""), "description": getattr(m, "DESC", "")} for m in SKILLS],
            "capability_status": {"local_orchestration": "real",
                                  "external_delegation": "blocked"},
            "orchestrator": ["plan", "status", "run --all",
                             "run --task（owner≠r01 时转发对应角色）"]}


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py",
                                description="R01 蛙全局 · CEO 主理人/编排器")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力/技能)")
    sp.add_parser("demo", help="生成示例决策工件（简报/决策卡/红队/OS/日志/汇报）")

    # LLM 知识注入模式
    chat_p = sp.add_parser("chat", help="LLM 对话模式：注入知识基座后返回 system prompt")
    chat_p.add_argument("--intent", required=True, help="用户意图描述")
    chat_p.add_argument("--domains", default=None,
                        help="要注入的知识域（逗号分隔，如 decide,redteam），默认自动推断")
    chat_p.add_argument("--output", default=None,
                        help="输出 system prompt 到文件（默认打印到 stdout）")

    run_p = sp.add_parser("run", help="协作入口：执行任务卡 / 按依赖执行全部")
    run_p.add_argument("--task", default=None)
    run_p.add_argument("--all", action="store_true")
    run_p.add_argument("--limit", type=int, default=30)
    add_clarify_parser(sp)

    # 编排器命令
    pl = sp.add_parser("plan", help="把意图拆成公司级任务卡")
    pl.add_argument("--intent", required=True)
    sp.add_parser("status", help="查看工作区任务状态")

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)
    _register_evolution(sp)

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：brief/card/crosseval/freeze 等")
    ha = h.add_subparsers(dest="hcmd", required=True)
    for name in harness._VALIDATORS:
        pa = ha.add_parser(name, help=f"{name} 门禁")
        pa.add_argument("--input", required=True)
    v = ha.add_parser("verify", help="综合门禁（brief+card）")
    v.add_argument("--brief", required=True)
    v.add_argument("--card", required=True)
    rl = ha.add_parser("runlog", help="运行可观测性：最近 N 次运行记录")
    rl.add_argument("--n", type=int, default=10)


def _run_harness(args) -> Dict[str, Any]:
    if args.hcmd == "verify":
        return harness.verify(args.brief, args.card)
    if args.hcmd == "runlog":
        return {"runlog": ws.runlog(args.n)}
    return harness.run_validator(args.hcmd, args.input)


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


def _register_evolution(sp) -> None:
    ep = sp.add_parser("evolution", help="十轮渐进自升级能力接口：probe/prompter/heal/audit/explore/bundle/patch/memory/telemetry")
    ea = ep.add_subparsers(dest="action", required=True)
    
    # R01: 探针
    p_probe = ea.add_parser("probe", help="外置物理探针巡检")
    
    # R02: 动态大脑
    p_brain = ea.add_parser("brain", help="动态战略意图编译器")
    p_brain.add_argument("--intent", required=True)
    
    # R03: 自愈审校
    p_heal = ea.add_parser("heal", help="决策卡 Auto-Heal 自愈反思循环")
    p_heal.add_argument("--input", required=True)
    
    # R04: 规范账本
    p_ledger = ea.add_parser("ledger", help="读取并校验持久化规范账本")
    
    # R05: 去劣反伪影
    p_slop = ea.add_parser("slopguard", help="决策空话套话与伪影审计精修")
    p_slop.add_argument("--text", required=True)
    p_slop.add_argument("--polish", action="store_true")
    
    # R06: 多向探索画廊
    p_explore = ea.add_parser("explore", help="多向战略分支裂变与看板生成")
    p_explore.add_argument("--topic", required=True)
    p_explore.add_argument("--output", default=None)
    
    # R07: 伴生结构化资产
    p_bundle = ea.add_parser("bundle", help="导出伴生结构化治理规格资产包")
    p_bundle.add_argument("--input", required=True)
    p_bundle.add_argument("--output-dir", default=None)
    
    # R08: 局部增量编辑
    p_patch = ea.add_parser("patch", help="自然语言局部差量编辑")
    p_patch.add_argument("--input", required=True)
    p_patch.add_argument("--instruction", required=True)
    
    # R09: 状态记忆
    p_memory = ea.add_parser("memory", help="会话状态工作记忆操作")
    p_memory.add_argument("--commit", default=None)
    p_memory.add_argument("--rollback", type=int, default=None)
    p_memory.add_argument("--resolve", default=None)
    
    # R10: 容灾遥测
    p_telemetry = ea.add_parser("telemetry", help="容灾看门狗与遥测指标检查")


def _run_evolution(args) -> Dict[str, Any]:
    from engines.manager import ExecutiveEngineManager
    from engines.prompter import ExecutivePrompter
    from engines.critic import ExecutiveCritic
    from engines.ledger import ExecutiveLedgerParser
    from engines.slop_guard import ExecutiveSlopGuard
    from engines.explorer import ExecutiveStrategyExplorer
    from engines.asset_bundle import ExecutiveAssetBundle
    from engines.patch_editor import ExecutivePatchEditor
    from engines.memory import ExecutiveMemoryPool
    from engines.telemetry import ExecutiveWatchdog, ExecutiveTelemetry

    act = args.action
    if act == "probe":
        mgr = ExecutiveEngineManager()
        probes = mgr.probe_all()
        return {"ok": True, "engines": {k: v.__dict__ for k, v in probes.items()}}
        
    elif act == "brain":
        res = ExecutivePrompter.decompose_strategic_intent(args.intent)
        return {"ok": True, "strategy_spec": res}

    elif act == "heal":
        with open(args.input, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return ExecutiveCritic.auto_heal(data)

    elif act == "ledger":
        spec = ExecutiveLedgerParser.load_spec()
        return {"ok": True, "ledger": spec}

    elif act == "slopguard":
        passed, score, issues = ExecutiveSlopGuard.audit_text(args.text)
        res = {"ok": passed, "slop_score": score, "issues": issues}
        if args.polish:
            res["polished_text"] = ExecutiveSlopGuard.polish_text(args.text)
        return res

    elif act == "explore":
        branches = ExecutiveStrategyExplorer.explore_branches(args.topic, {})
        dashboard = ExecutiveStrategyExplorer.generate_comparison_dashboard(args.topic, branches)
        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(dashboard)
        return {"ok": True, "topic": args.topic, "branches": branches, "dashboard_length": len(dashboard), "output": args.output}

    elif act == "bundle":
        with open(args.input, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        spec = ExecutiveAssetBundle.build_executive_spec(data)
        out_dir = args.output_dir or os.path.join(WORKSPACE_ROOT, "artifacts", "executive")
        out_path = ExecutiveAssetBundle.export_bundle(out_dir, spec)
        return {"ok": True, "spec": spec, "exported_path": out_path}

    elif act == "patch":
        with open(args.input, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        patched, ops = ExecutivePatchEditor.apply_patch(data, args.instruction)
        return {"ok": True, "operations": ops, "patched_card": patched}

    elif act == "memory":
        pool = ExecutiveMemoryPool(os.path.join(WORKSPACE_ROOT, "executive_session_state.json"))
        if args.commit:
            v = pool.commit("manual_commit", {"note": args.commit})
            return {"ok": True, "committed_version": v}
        elif args.rollback is not None:
            s = pool.rollback(args.rollback)
            return {"ok": s is not None, "restored_state": s}
        elif args.resolve:
            r = pool.resolve_reference(args.resolve)
            return {"ok": r is not None, "referenced_state": r}
        return {"ok": True, "current_state": pool.current_state, "history_len": len(pool.history)}

    elif act == "telemetry":
        tel = ExecutiveTelemetry(os.path.join(WORKSPACE_ROOT, "executive_telemetry.jsonl"))
        trace_id = tel.record_trace("telemetry_healthcheck", {"status": "ping"}, "SUCCESS", 1.2)
        res = ExecutiveWatchdog.execute_with_resilience(lambda: "pong")
        return {"ok": True, "trace_id": trace_id, "watchdog": res}

    return {"ok": False, "error": f"Unknown evolution action: {act}"}


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
    if args.skill == "chat":
        domains = (args.domains.split(",") if args.domains
                   else knowledge.get_domain_for_intent(args.intent))
        prompt = knowledge.build_system_prompt(
            domains=domains, task_context=args.intent)
        if args.output:
            c.write_text(args.output, prompt)
            emit_result({"ok": True, "output": args.output,
                         "domains": domains,
                         "prompt_length": len(prompt)})
        else:
            print(prompt)
        return 0
    if args.skill == "plan":
        tasks = _make_tasks(args.intent)
        if not tasks:
            emit_result({"planned": 0, "note": "未匹配到角色，请提供更具体意图"})
            return 0
        ids = [ws.create_task(t) for t in tasks]
        emit_result({"planned": len(ids), "task_ids": ids,
                     "owners": [t.owner for t in tasks]})
        return 0
    if args.skill == "status":
        status()
        return 0
    if args.skill == "run":
        if args.task:
            emit_result(run_task(args.task))
        else:
            run_all(args.limit)
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
    if args.skill == "evolution":
        out = _run_evolution(args)
        emit_result(out)
        return 0 if out.get("ok", True) else 1

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
