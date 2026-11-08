# -*- coding: utf-8 -*-
"""R09 蛙稳码（代码工程官）——薄调度器。

子命令：
  manifest / demo / run --task <id> / contract / review / case / harness
  + 8 个技能子命令（spec/data_api/fullstack/crossplatform/testing/debug/ops/special）

设计约定（对齐 r02/r03/r04/r05/r07/r08）：
- 技能只做确定性计算，无 LLM 调用；退出码：ok=true → 0，否则 1。
- run --task 走 agents/core/workspace.py 协议（runlog 写 ../workspace/runlog.jsonl）。
- R09 边界：不靠跳过测试制造假通过；R20 负责持续监控与备份；不可逆线上操作需授权。
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _REPO_ROOT not in _sys.path:
    _sys.path.insert(0, _REPO_ROOT)


from agents.shared import role_runtime
import argparse  # 统一元命令/报告
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

from core import protocol, workspace                                # noqa: E402

ws = workspace.Workspace(os.path.join(_ROOT, "workspace"))

ROLE = "r09"
CAPABILITY_STATUS = {"default": "real", "reason": "仅在安全入口执行本地 tests/build", "external_actions": "blocked"}
DIRS = os.path.basename(_HERE)

# ---------------------------------------------------------------------------
# 意图路由（具体关键词靠前；大小写不敏感；命中即返回）
# 元组：(关键词组, skill, action, extra_args 默认值)
# ---------------------------------------------------------------------------
_INTENT_ROUTES: List[Tuple[Tuple[str, ...], str, str, Dict[str, str]]] = [
    (("技术规格", "模块边界", "输入输出", "工程约束", "tech spec"),
     "spec", "spec", {}),
    (("架构", "拓扑", "服务连线", "architecture"),
     "spec", "arch", {}),
    (("数据库", "schema", "建表", "索引", "数据模型"),
     "data_api", "schema", {}),
    (("api 契约", "接口", "错误码", "endpoint", "rest"),
     "data_api", "api", {}),
    (("全栈", "端到端", "前端后端", "功能切片", "fullstack"),
     "fullstack", "feature", {}),
    (("认证", "登录", "鉴权", "auth"),
     "fullstack", "auth", {}),
    (("构建", "编译", "打包", "build"),
     "crossplatform", "build", {}),
    (("跨端", "平台差异", "flutter", "状态管理"),
     "crossplatform", "platform", {}),
    (("单元测试", "集成测试", "契约测试", "覆盖率", "test suite"),
     "testing", "suites", {}),
    (("浏览器验证", "e2e", "playwright", "关键路径"),
     "testing", "browser", {}),
    (("调试", "复现", "根因", "bug", "debug"),
     "debug", "debug", {}),
    (("性能", "重构", "热点", "剖析", "refactor"),
     "debug", "refactor", {}),
    (("迁移", "回滚", "migration", "数据迁移"),
     "ops", "migration", {}),
    (("安全审计", "cve", "依赖审计", "密钥", "security"),
     "ops", "security", {}),
    (("mcp", "工具服务"),
     "special", "mcp", {}),
    (("godot", "游戏工程", "可加载脚本"),
     "special", "godot", {}),
]
_DEFAULT_ROUTE: Tuple[str, str, Dict[str, str]] = ("spec", "spec", {})


def route_intent(intent: str) -> Tuple[str, str, Dict[str, str]]:
    low = str(intent or "").lower()
    for keys, skill, action, extra in _INTENT_ROUTES:
        for k in keys:
            if k.lower() in low:
                return skill, action, extra
    return _DEFAULT_ROUTE[0], _DEFAULT_ROUTE[1], _DEFAULT_ROUTE[2]


# ---------------------------------------------------------------------------
# CLI 组装
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="agent.py", description="R09 蛙稳码（代码工程官）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("manifest", help="打印角色能力清单")
    sub.add_parser("demo", help="用真实示例跑一组代表性动作")

    rp = sub.add_parser("run", help="按 task 卡执行一次工程任务")
    rp.add_argument("--task", required=True, help="task id（workspace 协议）")
    lp = sub.add_parser("local-verify", help="在当前项目内运行本地测试/构建；命令为白名单且禁止 shell")
    lp.add_argument("--project", required=True)
    lp.add_argument("--kind", choices=["pytest", "unittest", "build"], required=True)
    lp.add_argument("--command", required=True, help="可执行文件路径/名称")

    cp = sub.add_parser("contract", help="技能契约登记表")
    csub = cp.add_subparsers(dest="ccmd", required=True)
    csub.add_parser("list", help="列出全部 skill/action")
    cvp = csub.add_parser("validate", help="校验输出是否符合契约")
    cvp.add_argument("--skill", required=True, choices=contracts.skill_names())
    cvp.add_argument("--action", required=True)
    cvp.add_argument("--output", required=True, help="result.json 路径")

    rvp = sub.add_parser("review", help="对抗评审（T7）：对工程产出本身再评审")
    rvp.add_argument("--packet", required=True, help="产出包 JSON（{skill,action,result}）")

    cap = sub.add_parser("case", help="案例库")
    cap.add_argument("case_id", nargs="?", default=None,
                     help="缺省=列出全部；给定 id=展示并校验")

    hp = sub.add_parser("harness", help="确定性验证器")
    hsub = hp.add_subparsers(dest="hcmd", required=True)
    hmp = hsub.add_parser("materials", help="工程物料门禁（BLOCKED 判定）")
    hmp.add_argument("--input", required=True)
    htp = hsub.add_parser("testreport", help="测试报告结构门禁")
    htp.add_argument("--input", required=True)
    hpp = hsub.add_parser("plan", help="实现计划门禁")
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
    skills = [{"name": m.NAME, "desc": m.DESC,
               "actions": [{"action": a, "help": h}
                           for a, h in m.ACTIONS.items()]}
              for m in SKILLS]
    from core import registry
    role = registry.by_id(ROLE)
    skills = [{"name": m.NAME, "skill": m.NAME, "desc": m.DESC,
               "description": m.DESC,
               "actions": [{"action": a, "help": h}
                            for a, h in m.ACTIONS.items()]}
              for m in SKILLS]
    return {
        "role": role["id"], "dirs": DIRS,
        "name": "蛙稳码（代码工程官）", "title": role["title"],
        "capabilities": role["capabilities"], "inputs": role["inputs"],
        "outputs": role["outputs"],
        "desc": "从需求到可运行、可测试、可维护、可部署代码的完整工程链路："
                "技术规格架构、数据库API、前后端全栈、跨端生产工程、测试浏览器"
                "验证、调试性能重构、迁移CI/CD安全、特殊技术载体。",
        "capability_status": CAPABILITY_STATUS,
        "skills": skills,
        "skill_count": len(SKILLS),
        "action_count": sum(len(m.ACTIONS) for m in SKILLS),
        "cases": [r["case_id"] for r in cases_lib.list_cases()],
        "contracts": [f"{s}/{a}" for s in contracts.skill_names()
                      for a in contracts.actions(s)],
        "boundary": {
            "in_scope": ["技术规格与架构", "数据库与 API", "前后端全栈",
                         "跨端生产工程", "测试与浏览器验证", "调试性能重构",
                         "迁移 CI/CD 安全", "特殊技术载体（Godot/MCP/工程 Agent）"],
            "out_of_scope": ["持续监控与备份（归 R20）", "可用性告警与恢复（归 R20）",
                             "快速 MVP 原型（归 R08）"],
            "never": ["跳过测试制造假通过", "未授权执行不可逆线上操作",
                      "产出持续监控/备份结论而不移交 R20"],
        },
        "intent_routes": [{"keys": list(k), "skill": s, "action": a}
                          for k, s, a, _ in _INTENT_ROUTES],
    }


def _run_demo() -> int:
    demo_specs = [
        ("spec", "spec", os.path.join(_HERE, "examples", "spec_spec.json"), {}),
        ("testing", "suites", os.path.join(_HERE, "examples", "testing_suites.json"), {}),
        ("ops", "migration", os.path.join(_HERE, "examples", "ops_migration.json"), {}),
    ]
    artifacts_dir = ws.artifact("r09-demo")
    os.makedirs(artifacts_dir, exist_ok=True)
    lines: List[str] = []
    ok_all = True
    for skill, action, path, extra in demo_specs:
        args = argparse.Namespace(cmd=skill, action=action, input=path, **extra)
        out = SKILL_BY_NAME[skill].run(args)
        ok_all = ok_all and bool(out.get("ok"))
        c.write_json(os.path.join(artifacts_dir, f"{skill}-{action}.json"), out)
        verdict = out.get("verdict") or ("ok" if out.get("ok") else "FAIL")
        lines.append(f"[demo] {skill} {action} → verdict={verdict} ok={out.get('ok')}")
    lines.append(f"[demo] 产物目录：{artifacts_dir}")
    print("\n".join(lines))
    return 0 if ok_all else 1


def _run_local_verify(project: str, kind: str, command: str) -> Dict[str, Any]:
    import shlex
    import subprocess
    # `command` 既可只给可执行文件（如 python），也可给完整命令行
    # （如 "python -m unittest discover -s . -p test_*.py"）。后者按空格切分、
    # 禁止 shell=True，并对首段做可执行白名单校验。
    try:
        argv = shlex.split(command, posix=False)
    except ValueError as exc:
        return {"ok": False, "capability_status": "blocked",
                "capability_evidence": "command could not be parsed",
                "verdict": "BLOCKED", "blocked_reason": str(exc)}
    if not argv:
        return {"ok": False, "capability_status": "blocked",
                "capability_evidence": "empty command", "verdict": "BLOCKED",
                "blocked_reason": "command is empty"}
    allowed = {"pytest": {"pytest", "python", "python.exe", "py"},
               "unittest": {"python", "python.exe", "py"},
               "build": {"python", "python.exe", "py", "npm", "node"}}
    exe = os.path.basename(argv[0]).lower()
    if exe not in {x.lower() for x in allowed[kind]}:
        return {"ok": False, "capability_status": "blocked",
                "capability_evidence": "command rejected by local safety allowlist",
                "verdict": "BLOCKED",
                "blocked_reason": f"only safe local {kind} entrypoints are allowed"}
    if not os.path.isdir(project):
        return {"ok": False, "capability_status": "blocked",
                "capability_evidence": "project path unavailable locally",
                "verdict": "BLOCKED", "blocked_reason": "project directory missing"}
    # 只给可执行名时补默认子命令；给了完整 argv 则原样执行。
    if len(argv) == 1:
        argv = [argv[0], "-m", "pytest"] if kind == "pytest" else (
            [argv[0], "-m", "unittest", "discover"] if kind == "unittest" else argv)
    try:
        proc = subprocess.run(argv, cwd=project, capture_output=True, text=True,
                              timeout=120, shell=False)
        return {"ok": proc.returncode == 0, "capability_status": "real",
                "capability_evidence": "local process executed with shell=False",
                "verdict": "PASS" if proc.returncode == 0 else "FAIL",
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "capability_status": "blocked",
                "capability_evidence": "local execution could not start safely",
                "verdict": "BLOCKED", "blocked_reason": str(exc)}


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
        print(f"[run] task.owner={task.owner!r} != r09：拒绝执行（越权）",
              file=sys.stderr)
        return 1

    ws.set_status(task_id, "running")
    ws.emit(protocol.Event.now(ROLE, "task_started", task_id))

    intent = str(task.intent or "")
    skill, action, extra = route_intent(intent)
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
    out.setdefault("capability_status", "real")
    out.setdefault("capability_evidence", "local input inspected")
    ok = bool(out.get("ok"))

    out_dir = ws.artifact(f"run-{task_id}")
    os.makedirs(out_dir, exist_ok=True)
    result_path = os.path.join(out_dir, f"{skill}_{action}_result.json")
    c.write_json(result_path, out)
    report = [
        f"# R09 run --task {task_id}",
        f"- intent: {intent}",
        f"- 路由: {skill}/{action}",
        f"- 输入: {input_path}",
        f"- verdict: {out.get('verdict') or ('PASS' if ok else 'FAIL')}",
        f"- 结论: {out.get('next')}",
    ]
    report_path = os.path.join(out_dir, "engineering_report.md")
    c.write_text(report_path, "\n".join(report) + "\n")

    ws.update_task(task_id, {"outputs": [
        protocol.Port(f"run-{task_id}/{skill}_{action}_result.json", "data",
                      "application/json").to_dict(),
        protocol.Port(f"run-{task_id}/engineering_report.md", "report",
                      "text/markdown").to_dict(),
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
        c.emit(make_manifest())
        return 0
    if cmd == "demo":
        return _run_demo()
    if cmd == "run":
        return run_task(args.task)
    if cmd == "local-verify":
        out = _run_local_verify(args.project, args.kind, args.command)
        c.emit(out)
        return 0 if out.get("ok") else 1
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
