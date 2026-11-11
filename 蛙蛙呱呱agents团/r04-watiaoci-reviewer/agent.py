# -*- coding: utf-8 -*-
"""R04 蛙挑刺（独立评审官）——薄调度器。

子命令：
  manifest / demo / run --task <id> / contract / review / case / harness
  + 7 个技能子命令（artifact/gate/criteria/quality/facts/strengths/human）

设计约定（对齐 r02/r03/r07）：
- 技能只做确定性计算，无 LLM 调用；退出码：ok=true → 0，否则 1。
- run --task 走 agents/core/workspace.py 协议（runlog 写 ../workspace/runlog.jsonl）。
- R04 边界：只评已存在成品、不参与生产、只记录不修复。
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：agents/ 所在根入 sys.path ---
import os as _os
import sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_AGENTS_ROOT = _os.path.dirname(_HERE)
_WORKSPACE_ROOT = _os.path.dirname(_AGENTS_ROOT)
for _p in (_AGENTS_ROOT, _WORKSPACE_ROOT, _HERE):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)



import argparse
import json
import os
import sys
from agents.shared.chat_cli import add_chat_parser, handle_chat
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)          # agents/
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import SKILLS, SKILL_BY_NAME                          # noqa: E402
from skills import _common as c                                    # noqa: E402
import contracts                                                    # noqa: E402
import cases as cases_lib                                           # noqa: E402
import review as review_lib                                        # noqa: E402
import harness as harness_lib                                       # noqa: E402

from core import protocol, workspace                 # noqa: E402
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402
from agents.shared import role_runtime  # REP-001 报告引擎

ws = workspace.Workspace(os.path.join(_ROOT, "workspace"))

ROLE = "r04"
DIRS = os.path.basename(_HERE)

# ---------------------------------------------------------------------------
# 意图路由（R07 踩坑：具体关键词靠前；大小写不敏感；命中即返回）
# 元组：(关键词组, skill, action, extra_args 默认值)
# ---------------------------------------------------------------------------
_INTENT_ROUTES: List[Tuple[Tuple[str, ...], str, str, Dict[str, str]]] = [
    (("三级证据链", "证据链核验", "stub 扫描", "孤岛工件", "artifact verify"),
     "artifact", "verify", {}),
    (("物料核验", "工件清单", "materials", "inventory", "成品清点"),
     "artifact", "inventory", {}),
    (("门禁强度", "门禁审计", "strength", "theatre", "gate audit"),
     "gate", "audit", {}),
    (("跑门禁", "硬门禁", "命令门禁", "gate run"),
     "gate", "run", {}),
    (("判据对照", "复评对照", "criteria delta", "fixed new remaining"),
     "criteria", "delta",
     {"state": os.path.join(_HERE, "examples", "criteria_delta_state.json")}),
    (("外置判据", "验收判据", "判据审查", "acceptance", "criteria review"),
     "criteria", "review", {}),
    (("验收", "评审", "验收评审"),
     "criteria", "review", {}),
    (("收敛", "converge", "不再下降"),
     "quality", "converge",
     {"compare": os.path.join(_HERE, "examples", "quality_converge_v2.json")}),
    (("禁词", "质量批评", "critique", "完成声明", "claims"),
     "quality", "critique", {}),
    (("单数字", "数字回溯", "facts trace"),
     "facts", "trace",
     {"text": os.path.join(_HERE, "examples", "facts_trace_source.txt")}),
    (("事实核查", "数字幻觉", "来源质量", "facts check", "幻觉"),
     "facts", "check", {}),
    (("保留优点", "keep_list", "优点标记", "why_keep"),
     "strengths", "mark", {}),
    (("复评修改", "keep 降级", "recheck", "change 区"),
     "strengths", "recheck",
     {"new": os.path.join(_HERE, "examples", "strengths_recheck_new.json")}),
    (("staged", "复制资产", "human ack", "ack 批次"),
     "human", "ack", {}),
    (("批次校验", "逐字回填", "human ingest", "edits"),
     "human", "ingest", {}),
    (("人工评审", "评审包", "human package", "发起评审"),
     "human", "package", {}),
]
_DEFAULT_ROUTE: Tuple[str, str, Dict[str, str]] = ("criteria", "review", {})


def route_intent(intent: str) -> Tuple[str, str, Dict[str, str]]:
    low = str(intent or "").lower()
    # 最长关键词优先：避免通用词（如「评审」）遮蔽专用词（如「人工评审」）
    best = None
    for keys, skill, action, extra in _INTENT_ROUTES:
        for k in keys:
            kl = k.lower()
            if kl in low and (best is None or len(kl) > best[0]):
                best = (len(kl), skill, action, extra)
    if best is not None:
        return best[1], best[2], best[3]
    # 关键词未命中：交给共享 L02 内核；不再静默落到 criteria.review。
    return fallback_route(ROLE, intent)


# ---------------------------------------------------------------------------
# CLI 组装
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="agent.py", description="R04 蛙挑刺（独立评审官）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("manifest", help="打印角色能力清单")
    sub.add_parser("demo", help="用真实示例跑一组代表性动作")

    rp = sub.add_parser("run", help="按 task 卡执行一次评审任务")
    rp.add_argument("--task", required=True, help="task id（workspace 协议）")
    add_clarify_parser(sub)

    cp = sub.add_parser("contract", help="技能契约登记表")
    csub = cp.add_subparsers(dest="ccmd", required=True)
    csub.add_parser("list", help="列出全部 skill/action")
    cvp = csub.add_parser("validate", help="校验输出是否符合契约")
    cvp.add_argument("--skill", required=True, choices=contracts.skill_names())
    cvp.add_argument("--action", required=True)
    cvp.add_argument("--output", required=True, help="result.json 路径")

    rvp = sub.add_parser("review", help="对抗评审（T7）：对评审产出本身再评审")
    rvp.add_argument("--packet", required=True, help="产出包 JSON（{skill,action,result}）")

    cap = sub.add_parser("case", help="案例库")
    cap.add_argument("case_id", nargs="?", default=None,
                     help="缺省=列出全部；给定 id=展示并校验")

    hp = sub.add_parser("harness", help="确定性验证器")
    hsub = hp.add_subparsers(dest="hcmd", required=True)
    hmp = hsub.add_parser("materials", help="材料门禁（BLOCKED 判定）")
    hmp.add_argument("--input", required=True)
    hvp = hsub.add_parser("verdict", help="评审产出结构门禁")
    hvp.add_argument("--input", required=True)
    hpp = hsub.add_parser("plan", help="分析计划门禁")
    hpp.add_argument("--input", required=True)
    hrp = hsub.add_parser("runlog", help="最近 n 条 runlog")
    hrp.add_argument("--n", type=int, default=5)

    for m in SKILLS:
        m.add_parser(sub)
    return ap


# ---------------------------------------------------------------------------
# manifest / demo
# ---------------------------------------------------------------------------
def make_manifest() -> Dict[str, Any]:
    skills = [{"name": m.NAME, "skill": m.NAME, "desc": m.DESC, "description": m.DESC,
               "actions": [{"action": a, "help": h}
                           for a, h in m.ACTIONS.items()]}
              for m in SKILLS]
    from core import registry
    role = registry.by_id(ROLE)
    return {
        "role": role["id"],
        "dirs": DIRS,
        "name": "蛙挑刺（独立评审官）",
        "title": role["title"],
        "capabilities": role["capabilities"],
        "inputs": role["inputs"],
        "outputs": role["outputs"],
        "capability_status": {"default": "real", "reason": "本地确定性评审可执行", "external_actions": "simulated"},
        "desc": "对已存在成品做独立评审：三级证据链、硬门禁复核、外置判据、质量批评、"
                "事实核查、保留优点复评、人工评审工作流。只记录不修复。",
        "skills": skills,
        "skill_count": len(SKILLS),
        "action_count": sum(len(m.ACTIONS) for m in SKILLS),
        "cases": [r["case_id"] for r in cases_lib.list_cases()],
        "contracts": [f"{s}/{a}" for s in contracts.skill_names()
                      for a in contracts.actions(s)],
        "boundary": {
            "in_scope": ["评已存在成品", "记录 FAIL 与证据", "出 pass/warn/fail 三态"],
            "out_of_scope": ["生产新成品", "修复产品（归 R08/R09）", "替生产方决定"],
            "never": ["评审者==生产者（身份红线）", "评审只记录不修复",
                      "完成声明无证据即 FAIL"],
        },
        "intent_routes": [{"keys": list(k), "skill": s, "action": a}
                          for k, s, a, _ in _INTENT_ROUTES],
    }


def _run_demo() -> int:
    demo_specs = [
        ("criteria", "review", os.path.join(_HERE, "examples", "criteria_review.json"), {}),
        ("quality", "critique", os.path.join(_HERE, "examples", "quality_critique.json"), {}),
        ("gate", "audit", os.path.join(_HERE, "examples", "gate_audit.json"), {}),
    ]
    artifacts_dir = ws.artifact("r04-demo")
    os.makedirs(artifacts_dir, exist_ok=True)
    lines: List[str] = []
    ok_all = True
    for skill, action, path, extra in demo_specs:
        args = argparse.Namespace(cmd=skill, action=action, input=path, **extra)
        out = SKILL_BY_NAME[skill].run(args)
        ok_all = ok_all and bool(out.get("ok"))
        c.write_json(os.path.join(artifacts_dir, f"{skill}-{action}.json"), out)
        verdict = out.get("verdict") or out.get("overall") or ("ok" if out.get("ok") else "FAIL")
        lines.append(f"[demo] {skill} {action} → verdict={verdict} ok={out.get('ok')}")
    lines.append(f"[demo] 产物目录：{artifacts_dir}")
    print("\n".join(lines))
    return 0 if ok_all else 1


# ---------------------------------------------------------------------------
# run --task（workspace 协议）
# ---------------------------------------------------------------------------
def _first_input_file(inputs) -> Optional[str]:
    for p in inputs or []:
        s = getattr(p, "name", "")
        if s and os.path.isfile(str(s)):
            return str(s)
    return None


def _mkns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


def run_task(task_id: str) -> int:
    task = ws.read_task(task_id)
    if task is None:
        print(f"[run] task 不存在：{task_id}", file=sys.stderr)
        return 1
    if task.owner != ROLE:
        print(f"[run] task.owner={task.owner!r} != r04：拒绝执行（越权）",
              file=sys.stderr)
        return 1

    ws.set_status(task_id, "running")
    ws.emit(protocol.Event.now(ROLE, "task_started", task_id))

    intent = str(task.intent or "")
    skill, action, extra = route_intent(intent)
    if skill == "__clarify__":
        ws.set_status(task_id, "failed")
        ws.emit(protocol.Event.now(ROLE, "task_failed", task_id,
                                   {"reason": "needs_clarification",
                                    "questions": extra.get("questions", [])}))
        print(json.dumps({"error": "needs_clarification",
                          "questions": extra.get("questions", []),
                          "assumptions": extra.get("assumptions", []),
                          "plan": extra.get("plan")}, ensure_ascii=False))
        return 2
    input_path = _first_input_file(task.inputs) or extra.get("input") or ""
    if not input_path or not os.path.isfile(input_path):
        ws.set_status(task_id, "failed")
        ws.emit(protocol.Event.now(ROLE, "task_failed", task_id,
                                   {"reason": "缺少输入文件"}))
        print("[run] 缺少输入文件", file=sys.stderr)
        return 1

    mod = SKILL_BY_NAME[skill]
    args = _mkns(action=action, input=input_path,
                 **{k: v for k, v in extra.items() if k != "input"})
    out = mod.run(args)
    ok = bool(out.get("ok"))

    out_dir = ws.artifact(f"run-{task_id}")
    os.makedirs(out_dir, exist_ok=True)
    result_path = os.path.join(out_dir, f"{skill}_{action}_result.json")
    c.write_json(result_path, out)
    ports = role_runtime.emit(
        role=ROLE, name="蛙挑刺", title="独立评审官", result=out,
        skill=skill, action=action, intent=intent, out_dir=out_dir, input_path=input_path,
        md_name="review_report")

    ws.update_task(task_id, {"outputs": [
        protocol.Port(f"run-{task_id}/{skill}_{action}_result.json", "data",
                      "application/json").to_dict(),
        *[protocol.Port(f"run-{task_id}/{p.name}", p.kind, p.media_type).to_dict()
          for p in ports],
    ], "status": "done" if ok else "failed"})
    ws.emit(protocol.Event.now(ROLE, "task_finished", task_id,
                               {"skill": skill, "action": action, "ok": ok}))
    ws.log_run(ROLE, {"skill": f"{skill}/{action}", "task_id": task_id,
                      "ok": ok, "verdict": out.get("verdict")})
    print(f"[run] task={task_id} 路由 {skill}/{action} → {'ok' if ok else 'FAIL'}")
    c.emit(out)
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    _meta = role_runtime.handle_meta_command(list(sys.argv[1:] if argv is None else argv), ROLE)
    if _meta is not None:
        return _meta

    args = build_parser().parse_args(argv)
    cmd = args.cmd
    if cmd == "manifest":
        print(json.dumps(make_manifest(), ensure_ascii=False))
        return 0
    if cmd == "demo":
        return _run_demo()
    if cmd == "run":
        return run_task(args.task)
    if cmd == "clarify":
        return clarify_cli(ROLE, args.intent)
    if cmd == "contract":
        if args.ccmd == "list":
            rows = [f"{s}/{a}" for s in contracts.skill_names()
                    for a in contracts.actions(s)]
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        data = json.load(open(args.output, encoding="utf-8"))
        v = contracts.validate_output(args.skill, args.action, data)
        print(json.dumps(v, ensure_ascii=False, indent=2))
        return 0 if v["ok"] else 1
    if cmd == "review":
        packet = json.load(open(args.packet, encoding="utf-8"))
        out = review_lib.review_packet(packet)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if cmd == "case":
        if not args.case_id:
            print(json.dumps(cases_lib.list_cases(), ensure_ascii=False, indent=2))
            return 0
        try:
            case = cases_lib.load_case(args.case_id)
        except KeyError as exc:
            print(f"[case] {exc}", file=sys.stderr)
            return 1
        v = cases_lib.validate_case(args.case_id)
        print(json.dumps({"case": {k: case.get(k) for k in
                                   ("case_id", "display_name", "description",
                                    "default_question")},
                          "validate": v}, ensure_ascii=False, indent=2))
        return 0 if v["ok"] else 1
    if cmd == "harness":
        try:
            out = (harness_lib.validate_runlog(args.n) if args.hcmd == "runlog"
                   else harness_lib.run_validator(args.hcmd, args.input))
        except FileNotFoundError as e:
            out = {"ok": False, "error": f"input not found: {e.filename or e}"}
        except (KeyError, ValueError, TypeError) as e:
            out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    m = SKILL_BY_NAME.get(cmd)
    if m is None:
        print(f"未知命令：{cmd}", file=sys.stderr)
        return 2
    try:
        out = m.run(args)
    except FileNotFoundError as e:
        out = {"ok": False, "checks": [],
               "error": f"input not found: {e.filename or e}"}
    except (KeyError, ValueError, TypeError) as e:
        out = {"ok": False, "checks": [], "error": f"{type(e).__name__}: {e}"}
    c.emit(out)
    ws.log_run(ROLE, {"skill": f"{m.NAME}/{args.action}", "ok": bool(out.get("ok")),
                      "verdict": out.get("verdict")})
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
