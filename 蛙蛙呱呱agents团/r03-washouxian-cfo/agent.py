# -*- coding: utf-8 -*-
"""R03 蛙守线（CFO / 财务合规官）调度器。

结构对齐 r01/r02 样板：
  skills/         8 个能力域技能模块（financial/cfo/tax/contract/privacy/
                  aigov/audit/risk，各 3 动作，共 24 动作）
  contracts.py    24 动作的确定性 JSON Schema 输入契约（T6）
  review.py       T7 双向评审（挑战漏洞 / 挑战建议：契约、持牌边界、空话、
                  授权、量化）
  cases.py        T8 内嵌案例（month-end-close / kyc-onboarding）
  harness.py      运行入口
  experience/     T9 阈值与计划模式外置
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

if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(_sys.stderr, "reconfigure"):
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from shared import role_runtime
import argparse  # 统一元命令/报告
import json
import os
from core.base.workspace import role_workspace  # noqa: E402

import sys
from shared.chat_cli import add_chat_parser, handle_chat
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills import SKILLS  # noqa: E402
from skills import _common as c  # noqa: E402
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402

ROLE = "r03"


def manifest() -> Dict[str, Any]:
    """Machine-readable manifest; keeps the legacy skill/action CLI intact."""
    try:
        from core.base import registry
        role = registry.by_id(ROLE)
    except (ImportError, KeyError):
        role = {"id": ROLE, "name": "蛙守线", "title": "财务合规官 / 红线负责人",
                "capabilities": [], "inputs": [], "outputs": []}
    return {
        "role": role["id"], "name": role["name"], "title": role["title"],
        "capabilities": role["capabilities"], "inputs": role["inputs"],
        "outputs": role["outputs"],
        "capability_status": {"default": "real", "reason": "本地确定性技能可执行",
                              "external_actions": "simulated"},
        "skills": [{"skill": m.NAME, "name": m.NAME, "description": m.DESC,
                    "desc": m.DESC} for m in SKILLS],
    }


def emit_manifest() -> None:
    print("__AGENT_RESULT__ " + json.dumps(manifest(), ensure_ascii=False))

TOOL_PATH = os.path.abspath(__file__)

# 意图 → (技能, 动作, 默认参数)。供 probe/run_task 把意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，route 用小写不区分大小写匹配。
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


def route(text: str):
    """意图路由（确定性关键词匹配）：中文/英文关键词 → (技能, 动作, 默认参数)。

    旧实现未命中即静默落到 financial；现在未命中交给共享 L02 内核澄清。
    """
    t = (text or "").lower()
    for kws, skill, action, defaults in _INTENT_ROUTES:
        if any(k in t for k in kws):
            return skill, action, defaults
    return fallback_route(ROLE, text)


def dispatch(skill: str, action: str, input_path: str) -> Dict[str, Any]:
    mod = next((m for m in SKILLS if m.NAME == skill), None)
    if mod is None:
        return {"ok": False, "error": f"unknown skill: {skill}"}
    if not os.path.exists(input_path):
        return {"ok": False, "error": f"input not found: {input_path}"}
    try:
        return mod.run(argparse.Namespace(action=action,
                                          input=input_path))
    except (KeyError, ValueError, TypeError) as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def agent_description() -> Dict[str, Any]:
    return {
        "role": "R03 蛙守线（CFO / 财务合规官）",
        "desc": "报表月结 / CFO 经营诊断 / 税务边界 / 合同政策 / "
                "隐私数据安全 / AI 治理 / 审计留痕 / 广告-KYC-AML 风控",
        "tools": [{"path": TOOL_PATH,
                   "cli": f"python {TOOL_PATH} <skill> <action> --input X"}],
        "skills": [{"name": m.NAME, "desc": m.DESC} for m in SKILLS],
    }


def _register_parsers() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="r03-washouxian-cfo")
    sub = parser.add_subparsers(dest="skill", required=True)
    add_clarify_parser(sub)
    for m in SKILLS:
        m.add_parser(sub)
    _register_case(sub)
    _register_deep(sub)
    _register_run(sub)
    return parser

def _register_deep(sub) -> None:
    dp = sub.add_parser("deep", help="已下线：CFO 深度财务流水线（Runway Deep Dive）")
    dp.add_argument("--input", required=True, help="财务数据输入 JSON")
    dp.add_argument("--intent", default="现金流跑道与财务深度诊断", help="分析意图")
    dp.add_argument("--out-dir", default=None, help="输出目录")



# --------------------------------------------------------------------------- #
# 案例库（T8）：cases/<case_id>/ 的结构门禁
#   对齐 R01/R02/R07/R14/R20 的 case 语义：case.json + semantic_layer.json +
#   experience/{good_summaries.md, priority_rules.md, thresholds.json}。
#   R03 的案例此前只有内嵌 CASES 列表、没有 CLI，是 META-001 Stage 1 体检出的
#   「资产存在但不可校验」缺口，这里补齐。
# --------------------------------------------------------------------------- #
_CASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")
_CASE_META = ["case_id", "display_name", "description", "default_question"]
_CASE_SEMANTIC = ["artifact_type", "terms", "gates", "boundary"]
_CASE_FILES = ["good_summaries.md", "priority_rules.md", "thresholds.json"]


def _register_case(sub) -> None:
    cp = sub.add_parser("case", help="案例库：list / get / validate")
    ca = cp.add_subparsers(dest="case_cmd", required=True)
    ca.add_parser("list", help="列出全部案例")
    g = ca.add_parser("get", help="加载案例（含语义层与经验包）")
    g.add_argument("case_id")
    v = ca.add_parser("validate", help="案例结构门禁")
    v.add_argument("case_id")


def _case_dir(case_id: str) -> str:
    return os.path.join(_CASE_DIR, case_id)


def _list_cases() -> list:
    out = []
    if not os.path.isdir(_CASE_DIR):
        return out
    for name in sorted(os.listdir(_CASE_DIR)):
        p = os.path.join(_CASE_DIR, name, "case.json")
        if os.path.isfile(p):
            d = c.load_json(p)
            out.append({"case_id": d.get("case_id", name),
                        "display_name": d.get("display_name", name),
                        "default_question": d.get("default_question", "")})
    return out


def _validate_case(case_id: str) -> Dict[str, Any]:
    def chk(ok: bool, msg: str, dim: str, sev: str = "OK") -> Dict[str, Any]:
        return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else sev}

    d = _case_dir(case_id)
    checks: list = []
    if not os.path.isdir(d):
        return {"ok": False, "case_id": case_id, "grade": "FAIL",
                "checks": [chk(False, f"案例目录不存在 {case_id}", "existence", "CRITICAL")]}
    case = c.load_json(os.path.join(d, "case.json"))
    for k in _CASE_META:
        checks.append(chk(bool(case.get(k)), f"case.json 含 {k}", "structure", "CRITICAL"))
    sem_path = os.path.join(d, case.get("semantic_layer", "semantic_layer.json"))
    sem = c.load_json(sem_path) if os.path.isfile(sem_path) else {}
    for k in _CASE_SEMANTIC:
        present = bool(sem.get(k))
        checks.append(chk(present, f"semantic_layer.{k}",
                          "structure", "HIGH"))
    exp = os.path.join(d, case.get("experience_dir", "experience"))
    for f in _CASE_FILES:
        checks.append(chk(os.path.isfile(os.path.join(exp, f)),
                          f"experience/{f}", "structure", "HIGH"))
    ok = all(x["ok"] for x in checks)
    grade = ("PASS" if ok else
             "FAIL" if any(x["sev"] == "CRITICAL" and not x["ok"] for x in checks)
             else "WARN")
    return {"ok": ok, "case_id": case.get("case_id", case_id),
            "grade": grade, "checks": checks}


def _run_case_cli(args) -> int:
    if args.case_cmd == "list":
        c.emit({"cases": _list_cases()})
        return 0
    if args.case_cmd == "get":
        d = _case_dir(args.case_id)
        if not os.path.isdir(d):
            c.emit({"ok": False, "error": f"案例不存在: {args.case_id}"})
            return 1
        case = c.load_json(os.path.join(d, "case.json"))
        sem_path = os.path.join(d, case.get("semantic_layer", "semantic_layer.json"))
        c.emit({"case_id": args.case_id, **case,
                "semantic_layer": c.load_json(sem_path) if os.path.isfile(sem_path) else {}})
        return 0
    out = _validate_case(args.case_id)
    c.emit(out)
    return 0 if out["ok"] else 1


def _register_run(sub) -> None:
    rp = sub.add_parser("run", help="协作入口：执行编排器下发的一张任务卡")
    rp.add_argument("--task", required=True, help="任务卡 ID（workspace/tasks/<id>.json）")
    rp.add_argument("--all", action="store_true",
                    help="兼容参数；R03 由编排器逐卡派发，本参数不做事")


def _task_input(task) -> str:
    """任务卡输入端口里第一个真实存在的文件。"""
    for port in getattr(task, "inputs", []) or []:
        name = str(getattr(port, "name", "") or "")
        if name and os.path.exists(name):
            return name
    return ""


def run_task(task_id: str) -> Dict[str, Any]:
    """执行一张任务卡：路由 → 跑技能 → 落 result/evidence → 更新状态。

    R03 之前是唯一没有 `run --task` 的执行角色，导致 R01 把合规/税务/审计类
    任务派给 R03 时必然失败（PROTOCOL.md 的「合规闭环」pattern 跑不起来）。
    """
    from core.base import protocol, workspace as _ws
    ws = _ws.Workspace(_ws.default_root())
    task = ws.read_task(task_id)
    if task is None:
        return {"ok": False, "error": f"任务不存在: {task_id}"}
    if task.owner != ROLE:
        return {"ok": False, "error": f"任务 {task_id} 归属 {task.owner}，非本角色 {ROLE}"}

    ws.set_status(task_id, "running")
    ws.emit(protocol.Event.now(ROLE, "task_started", task_id))

    intent = " ".join([task.title or "", task.intent or ""] +
                      [str(getattr(p, "note", "") or "") for p in (task.inputs or [])])
    skill, action, _defaults = route(intent)
    if skill == "__clarify__" or not skill:
        ws.set_status(task_id, "failed")
        ws.emit(protocol.Event.now(ROLE, "task_failed", task_id,
                                   {"reason": "needs_clarification"}))
        return {"ok": False, "error": "needs_clarification",
                "questions": _defaults.get("questions", []) if isinstance(_defaults, dict) else []}

    in_file = _task_input(task)
    if not in_file:
        ws.set_status(task_id, "failed")
        ws.emit(protocol.Event.now(ROLE, "task_failed", task_id,
                                   {"reason": "缺少输入文件"}))
        return {"ok": False, "error": "缺少输入文件（任务卡 inputs 里没有可读路径）"}

    out = dispatch(skill, action, in_file)
    if not isinstance(out, dict):
        out = {"ok": False, "error": "技能返回非结构化结果"}
    out.setdefault("task_id", task_id)
    out.setdefault("input", in_file)

    out_dir = ws.artifact(task_id)
    os.makedirs(out_dir, exist_ok=True)
    from core.base import registry as _registry
    role = _registry.by_id(ROLE)
    role_runtime.emit(role=ROLE, name=role["name"], title=role["title"],
                      result=out, skill=skill, action=action, intent=task.intent or "",
                      out_dir=out_dir, input_path=in_file)

    status = "done" if out.get("ok") else "failed"
    ws.set_status(task_id, status)
    ws.emit(protocol.Event.now(ROLE, "task_finished" if status == "done" else "task_failed",
                               task_id, {"skill": skill, "action": action}))
    return {"ok": bool(out.get("ok")), "task_id": task_id, "status": status,
            "skill": skill, "action": action, "artifact": out_dir}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _meta = role_runtime.handle_meta_command(argv, ROLE)
    if _meta is not None:
        return _meta
    if argv == ["manifest"]:
        emit_manifest()
        return 0
    if argv == ["demo"]:
        # demo = 用示例输入真实跑一次技能（不是伪造结果）
        argv = ["aigov", "aiclassify", "--input", "examples/aigov_aiclassify.json"]
    parser = _register_parsers()
    args = parser.parse_args(argv)
    if getattr(args, "skill", None) == "clarify":
        return clarify_cli(ROLE, args.intent)
    if getattr(args, "skill", None) == "case":
        return _run_case_cli(args)
    if getattr(args, "skill", None) == "run":
        out = run_task(args.task)
        c.emit(out)
        return 0 if out.get("ok") else 1
    # 2026-11-15 产线收敛：深度报告支线已删除。报告由 R01 统一出具。
    if getattr(args, "skill", None) in ("deep", "depth"):
        out = {"ok": False,
               "message": "deep/depth 支线已下线（报告产线收敛为 R01 唯一出口）",
               "next": "python guagua.py report run-line --intent <意图> --dir <项目> --out <目录>"}
        try:
            c.emit(out)
        except NameError:
            emit_result(out)
        return 1
    out = dispatch(args.skill, args.action, args.input)
    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
