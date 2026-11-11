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


from agents.shared import role_runtime
import argparse  # 统一元命令/报告
import json
import os
from core.workspace import role_workspace  # noqa: E402

import sys
from agents.shared.chat_cli import add_chat_parser, handle_chat
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills import SKILLS  # noqa: E402
from skills import _common as c  # noqa: E402
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402

ROLE = "r03"


def manifest() -> Dict[str, Any]:
    """Machine-readable manifest; keeps the legacy skill/action CLI intact."""
    try:
        from core import registry
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
    return parser

def _register_deep(sub) -> None:
    dp = sub.add_parser("deep", help="CFO 深度财务流水线 (Runway Deep Dive)")
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


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _meta = role_runtime.handle_meta_command(argv, ROLE)
    if _meta is not None:
        return _meta
    if argv == ["manifest"]:
        emit_manifest()
        return 0
    parser = _register_parsers()
    args = parser.parse_args(argv)
    if getattr(args, "skill", None) == "clarify":
        return clarify_cli(ROLE, args.intent)
    if getattr(args, "skill", None) == "case":
        return _run_case_cli(args)
    if getattr(args, "skill", None) == "deep":
        from deep_analysis import run_deep_analysis
        from agents.shared.report_generator import generate_professional_report
        from agents.shared.role_profiles import get as get_profile
        
        out_dir = getattr(args, "out_dir", None) or os.path.join(role_workspace(os.path.dirname(__file__)), "deep_report")
        res = run_deep_analysis(args.input)
        
        profile = get_profile(ROLE)
        spec = {
            "role_id": ROLE,
            "agent_name": profile["name"],
            "report_title": f"{profile['name']} · {args.intent}",
            "executive_summary": res["decision"]["summary"],
            "decision_directive": res["decision"]["directive"],
            "kpi_metrics": [
                {"label": "现金耗尽月", "value": f"{res['simulation'].get('cash_out_month', '—')} 个月", "status": "red"},
                {"label": "烧钱倍数", "value": f"{res['simulation'].get('burn_multiple', '—')}x", "status": "red" if res['simulation'].get('burn_multiple', 0) > 2.0 else "green"},
                {"label": "门禁通过", "value": f"{len([c for c in res['checks'] if c.get('ok')])}/{len(res['checks'])}", "status": "normal"},
            ],
            "analysis_sections": [
                {"title": "1. 预算基线校验与滚动调节 (Rollforward)", "content": f"资产负债表与预算基线门禁核验完成，发现平衡差额 {res['base'].get('broken', [{}])[0].get('diff', 0) if res['base'].get('broken') else 0}。"},
                {"title": "2. 现金流仿真与跑道预测 (Runway Simulation)", "content": f"模拟期现金预计于第 {res['simulation'].get('cash_out_month', '—')} 个月耗尽，触发预警项 {len(res['simulation'].get('triggers', []))} 个。"},
                {"title": "3. 单位经济模型压力测试 (Unit Economics)", "content": f"对获客成本 (CAC) 与生命周期价值 (LTV) 做压力测试，安全边际面临收窄。"},
            ],
            "figures": [],
            "guardrails": profile["guardrails"],
            "rollout_plan": profile["rollout"],
            "next_steps": profile["next_steps"],
            "rca": res["decision"]["rca"],
            "provenance": {"input": args.input, "tokens": res["tokens_in"] + res["tokens_out"]},
        }
        files = generate_professional_report(out_dir=out_dir, report_slug="cfo_deep_report", **spec)
        c.emit({"ok": True, "report_html": files["html"], "report_md": files["md"]})
        return 0
    out = dispatch(args.skill, args.action, args.input)
    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
