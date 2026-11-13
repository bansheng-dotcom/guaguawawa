#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R11 蛙点题 · 内容主笔 —— 本地可运行 Agent（八技能调度器）。

把 8 个能力域各自做成一个独立技能模块（skills/s01..s08），本文件只做三件事：
    1. 注册 8 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    topic + audience  →  content_draft + publish_list

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py copy article --input examples/article.json
    python agent.py seo audit --input examples/audit.json
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_AGENTS = _os.path.dirname(_HERE)
_ROOT = _os.path.dirname(_AGENTS)
for _p in (_HERE, _AGENTS, _ROOT):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import argparse
import hashlib
import json
import os
import sys
try:
    from agents.shared.chat_cli import add_chat_parser, handle_chat
except ImportError:
    try:
        from shared.chat_cli import add_chat_parser, handle_chat
    except ImportError:
        def add_chat_parser(p): pass
        def handle_chat(args): pass
try:
    from agents.shared import role_runtime
except ImportError:
    try:
        from shared import role_runtime
    except ImportError:
        role_runtime = None
import time
from typing import Any, Dict, List, Optional
from core import protocol, registry, workspace  # noqa: E402
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402
from skills import SKILLS, _common as c  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402

ROLE = "r11"
CAPABILITY_STATUS = {"default": "real", "reason": "本地文本格式、字数与长度检查", "external_actions": "simulated"}
WORKSPACE_ROOT = workspace.default_root()
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
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
    data.setdefault("capability_status", "real")
    data.setdefault("capability_evidence", "local text inspected")
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R11 蛙点题 · 内容主笔")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    sp.add_parser("demo", help="生成示例内容工件")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)
    add_clarify_parser(sp)

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)
    _register_evolve(sp)
    la = sp.add_parser("local-text-check", help="本地文本格式、字数与平台长度检查")
    la.add_argument("--text", required=True)
    la.add_argument("--platform", default="")
    la.add_argument("--min-chars", type=int, default=1)

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：16 内容门禁 + probe")
    ha = h.add_subparsers(dest="hcmd", required=True)
    for name, help_txt in {
        "brief": "选题卡门禁", "plan_topic": "内容规划门禁",
        "keyword": "关键词表门禁", "audit": "AEO 就绪度审计门禁",
        "hook": "钩子标题门禁", "outline": "提纲立场门禁",
        "article": "文案终稿门禁", "script": "脚本类门禁",
        "guide": "品牌语调指南门禁", "edit": "清洁终稿门禁",
        "ad": "广告文案门禁", "press": "新闻稿门禁",
        "adapt": "多平台改写门禁", "publish": "发布清单门禁",
        "term": "术语表门禁", "review_localize": "审校记录门禁",
    }.items():
        pa = ha.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    pr = ha.add_parser("probe", help="重依赖能力探测（localize）")
    pr.add_argument("--skill", required=True)
    pl = ha.add_parser("plan", help="内容计划门禁（plan_schema）")
    pl.add_argument("--input", required=True)
    rl = ha.add_parser("runlog", help="运行可观测性：最近 N 次运行记录")
    rl.add_argument("--n", type=int, default=10)


def _run_harness(args) -> Dict[str, Any]:
    if args.hcmd == "probe":
        return harness.probe(args.skill)
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


def _register_evolve(sp) -> None:
    ev_p = sp.add_parser("evolve", help="十维演进元模型核心引擎调度 (L01~L10)")
    ev_sub = ev_p.add_subparsers(dest="subcmd", required=True)
    ev_sub.add_parser("probe", help="L01: 探测文案运行时引擎健康状态与计算沙箱")

    dec_p = ev_sub.add_parser("decompile", help="L02: 意图解构与 Kahn 拓扑 DAG 编排")
    dec_p.add_argument("--query", required=True, help="文案或运营需求自然语言")

    heal_p = ev_sub.add_parser("heal", help="L03: 自愈反思与红线审判")
    heal_p.add_argument("--type", default="article", help="工件类型 (article/copy/ad)")
    heal_p.add_argument("--input", required=True, help="待检测内容 JSON 文件")

    spec_p = ev_sub.add_parser("spec", help="L04: 领域规格账本加载与合规校验")
    spec_p.add_argument("--channel", default="微信公众号", help="分发渠道")
    spec_p.add_argument("--input", default=None, help="文案 JSON 或留空加载 Spec")

    slop_p = ev_sub.add_parser("slop", help="L05: 质感去劣化与 Anti-Slop 物理精修")
    slop_p.add_argument("--text", default=None, help="待审查文本")
    slop_p.add_argument("--input", default=None, help="包含文本的 JSON 文件")

    sc_p = ev_sub.add_parser("scenario", help="L06: 多维风格情景决策看板裂变")
    sc_p.add_argument("--topic", default="内容复利与自动化运营", help="核心主题")

    b_p = ev_sub.add_parser("bundle", help="L07: 伴生消费资产包与 SARIF 导出")
    b_p.add_argument("--run-id", default="demo_run_01", help="运行标识")
    b_p.add_argument("--input", default=None, help="文案工件 JSON")

    p_p = ev_sub.add_parser("patch", help="L08: RFC 6902 局部差量补丁与热修")
    p_p.add_argument("--old", required=True, help="旧状态 JSON")
    p_p.add_argument("--new", required=True, help="新状态 JSON")

    mem_p = ev_sub.add_parser("memory", help="L09: 会话记忆与代词消歧测试")
    mem_p.add_argument("--query", required=True, help="自然语言查询")

    ev_sub.add_parser("watchdog", help="L10: 看门狗熔断器与遥测探测")



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
    result.setdefault("capability_evidence", "local text inspected")
    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    outputs: List[protocol.Port] = []
    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs.append(protocol.Port(f"{skill_name}.json", "data"))

    ports = role_runtime.emit(
        role=ROLE, name="蛙点题", title="内容主笔",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="content_report")
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
    # 关键词未命中：交给共享 L02 内核；不再静默落到 copy.article。
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
    for name in ("article", "audit", "brief", "ad"):
        src = os.path.join(_HERE, "examples", f"{name}.json")
        dst = os.path.join(artifacts_dir, f"{name}.json")
        c.write_json(dst, c.load_json(src))
        out[name] = dst
    return out


def manifest() -> Dict[str, Any]:
    r = registry.by_id(ROLE)
    return {"role": r["id"], "capability_status": CAPABILITY_STATUS, "name": r["name"], "title": r["title"],
            "capabilities": r["capabilities"],
            "inputs": r["inputs"], "outputs": r["outputs"],
            "skills": [(m.NAME, m.DESC) for m in SKILLS]}


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
    if args.skill == "clarify":
        return clarify_cli(ROLE, args.intent)
    if args.skill == "local-text-check":
        from local_actions import check_text
        out = check_text(args.text, args.platform, args.min_chars)
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
            CopyRuntimeEngine,
            IntentDAGCompiler,
            CopyReflexiveHealer,
            CopySpecLedger,
            CopySlopGuard,
            ScenarioMatrix,
            ContentAssetBundle,
            ContentDiffPatchEngine,
            ContentSessionMemory,
            ContentTelemetryWatchdog,
        )
        if args.subcmd == "probe":
            eng = CopyRuntimeEngine()
            out = eng.probe_health()
            emit_result(out)
            return 0 if out.get("status") == "healthy" else 1
        elif args.subcmd == "decompile":
            comp = IntentDAGCompiler()
            out = comp.decompile_intent(args.query)
            emit_result(out)
            return 0 if out.get("ok") else 1
        elif args.subcmd == "heal":
            healer = CopyReflexiveHealer()
            in_data = c.load_json(args.input)
            out = healer.audit_and_heal(args.type, in_data)
            emit_result(out)
            return 0
        elif args.subcmd == "spec":
            ledger = CopySpecLedger()
            if args.input:
                in_data = c.load_json(args.input)
                content = in_data.get("content", in_data.get("text", ""))
                title = in_data.get("title", "")
                out = ledger.validate_content(content, title, args.channel)
            else:
                out = ledger.load_spec()
            emit_result(out)
            return 0
        elif args.subcmd == "slop":
            guard = CopySlopGuard()
            raw_text = args.text
            if not raw_text and args.input:
                in_data = c.load_json(args.input)
                raw_text = in_data.get("content", in_data.get("text", ""))
            raw_text = raw_text or "总而言之，毫无疑问，随着科技的飞速发展..."
            audit = guard.audit_text(raw_text)
            polished, count = guard.polish(raw_text)
            out = {"audit": audit, "polished": polished, "replacement_count": count}
            emit_result(out)
            return 0
        elif args.subcmd == "scenario":
            sc = ScenarioMatrix()
            out = sc.generate_matrix(args.topic)
            emit_result(out)
            return 0
        elif args.subcmd == "bundle":
            bundle_eng = ContentAssetBundle()
            in_data = c.load_json(args.input) if args.input else {"title": "测试文案", "content": "测试正文"}
            out = bundle_eng.export_bundle(args.run_id, in_data)
            emit_result(out)
            return 0
        elif args.subcmd == "patch":
            diff_eng = ContentDiffPatchEngine()
            old_data = c.load_json(args.old)
            new_data = c.load_json(args.new)
            patches = diff_eng.create_patch(old_data, new_data)
            applied = diff_eng.apply_patch(old_data, patches)
            out = {"patches": patches, "applied": applied}
            emit_result(out)
            return 0
        elif args.subcmd == "memory":
            mem = ContentSessionMemory()
            out = mem.resolve_pronouns(args.query)
            emit_result(out)
            return 0
        elif args.subcmd == "watchdog":
            wd = ContentTelemetryWatchdog()
            st = wd.get_state()
            out = {"status": "ok", "breaker_state": st}
            emit_result(out)
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
