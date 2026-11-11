#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R15 蛙供应 · ERP 与供应链运营官 —— 本地可运行 Agent（七技能调度器）。

把 7 个能力域各自做成一个独立技能模块（skills/s01..s07），本文件只做三件事：
    1. 注册 7 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    order + sop  →  purchase_order + inventory_ledger

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py procurement purchase_order --input examples/purchase_order.json
    python agent.py inventory bin --input examples/bin.json
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_AGENTS = _os.path.dirname(_HERE)
_REPO_ROOT = _os.path.dirname(_AGENTS)
for _p in (_HERE, _AGENTS, _REPO_ROOT):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)


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
from core.prompt_kernel import add_clarify_parser, clarify_cli, fallback_route  # noqa: E402
from agents.shared import role_runtime  # noqa: E402
from skills import SKILLS, _common as c  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402
import local_exec  # noqa: E402
import csv as _csv
import tempfile as _tempfile

ROLE = "r15"
WORKSPACE_ROOT = workspace.default_root()
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
# 注意「报价」(quotation) 必须排在「询价」(rfq) 之前、「收货」(receipt) 排在
# 「采购订单」(purchase_order) 之前，否则动作错配导致门禁选错（R14 踩坑同理）。
_INTENT_ROUTES = [
    (("tco", "总拥有成本", "采购成本对比", "报价对比", "landed"), "tco", "compare", {}),
    (("报价", "供应商报价", "quotation", "sq", "比价结果"),
     "procurement", "quotation", {}),
    (("询价", "rfq", "request for quotation", "询比价"),
     "procurement", "rfq", {}),
    (("收货", "到货", "采购入库", "purchase receipt", "入库单"),
     "procurement", "receipt", {}),
    (("采购", "采购订单", "下单采购", "purchase order", "po", "买"),
     "procurement", "purchase_order", {}),
    (("供应商", "supplier", "供方"),
     "procurement", "supplier", {}),
    (("bom", "物料清单", "配方", "生产一件", "成品的料"),
     "production", "bom", {}),
    (("物料请求", "material request", "缺料", "请购", "补料"),
     "production", "material_request", {}),
    (("发票", "invoice", "应收", "应付", "开票"),
     "finance", "invoice", {}),
    (("付款", "payment", "付款单", "打款"),
     "finance", "payment", {}),
    (("权限", "permission", "职责分离", "角色", "授权矩阵", "sod"),
     "masterdata", "permission", {}),
    (("主数据", "编码", "物料主数据", "master data", "数据字典"),
     "masterdata", "master_data", {}),
    (("报表", "运营报表", "report", "kpi", "台账"),
     "report", "report", {}),
    (("发货", "delivery", "履约", "交付"),
     "fulfillment", "delivery", {}),
    (("销售订单", "sales order", "so", "订单承诺"),
     "fulfillment", "sales_order", {}),
    (("库存", "库存明细", "bin", "库存台账", "现值"),
     "inventory", "bin", {}),
    (("出入库", "库存交易", "stock entry", "调拨", "盘点"),
     "inventory", "stock_entry", {}),
    (("仓库", "warehouse", "库房"),
     "inventory", "warehouse", {}),
    (("物料", "item", "sku", "品号"),
     "inventory", "item", {}),
]


def emit_result(data: Dict[str, Any]) -> None:
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R15 蛙供应 · ERP 与供应链运营官")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    local = sp.add_parser("local", help="本地库存台账核验")
    local.add_argument("--input", required=True)
    local.add_argument("--output", required=True)
    sp.add_parser("demo", help="生成示例 ERP 工件")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)
    add_clarify_parser(sp)

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)
    _register_evolve(sp)

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：18 ERP 门禁 + runlog")
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
    p = sp.add_parser("review", help="对抗评审：对 ERP 供应链工件做确定性挑战")
    p.add_argument("--result", required=True)
    p.add_argument("--skill", required=True, dest="review_skill")
    p.add_argument("--action", required=True, dest="review_action")
    p.add_argument("--run-id", default="")


def _register_evolve(sp) -> None:
    ev_p = sp.add_parser("evolve", help="十维演进元模型核心引擎调度 (L01~L10)")
    ev_sub = ev_p.add_subparsers(dest="subcmd", required=True)
    ev_sub.add_parser("probe", help="L01: 探测 ERP 供应链计算沙箱与健康状态")

    dec_p = ev_sub.add_parser("decompile", help="L02: 意图解构与 Kahn 拓扑 DAG 编排")
    dec_p.add_argument("--query", required=True, help="供应链采购或排产需求自然语言")

    heal_p = ev_sub.add_parser("heal", help="L03: 自愈反思与红线审判")
    heal_p.add_argument("--action", default="代付款", help="待审判的动作或策略")

    spec_p = ev_sub.add_parser("spec", help="L04: 领域规格账本加载与合规校验")
    spec_p.add_argument("--input", default=None, help="供应链数据 JSON 或留空加载 Spec")

    slop_p = ev_sub.add_parser("slop", help="L05: 质感去劣化与 Anti-Slop 显著性校验")
    slop_p.add_argument("--text", default=None, help="待审查文本")

    sc_p = ev_sub.add_parser("scenario", help="L06: 多维供应链补货策略看板裂变")
    sc_p.add_argument("--item-code", default="ITEM_STANDARD", help="物料代码")
    sc_p.add_argument("--demand", type=float, default=1000.0, help="需求总量")

    b_p = ev_sub.add_parser("bundle", help="L07: 伴生消费资产包与 SARIF/Vega 导出")
    b_p.add_argument("--run-id", default="demo_run_01", help="运行标识")
    b_p.add_argument("--input", default=None, help="供应链工件 JSON")

    p_p = ev_sub.add_parser("patch", help="L08: RFC 6902 局部差量补丁与热修")
    p_p.add_argument("--old", required=True, help="旧状态 JSON")
    p_p.add_argument("--new", required=True, help="新状态 JSON")

    mem_p = ev_sub.add_parser("memory", help="L09: 会话记忆与代词消歧测试")
    mem_p.add_argument("--query", required=True, help="自然语言查询")

    ev_sub.add_parser("watchdog", help="L10: 看门狗熔断器与遥测探测")


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
    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    outputs: List[protocol.Port] = []
    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs.append(protocol.Port(f"{skill_name}.json", "data"))

    ports = role_runtime.emit(
        role=ROLE, name="蛙供应", title="ERP 与供应链运营官",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="erp_report")
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
    # 关键词未命中：交给共享 L02 内核；不再静默落到默认动作。
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
    for name in ("purchase_order", "bin", "sales_order", "bom", "invoice"):
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
            "capability_status": {"local_inventory_ledger": "real", "external_erp_mutation": "blocked"}}


def _input_hash(args) -> str:
    p = getattr(args, "input", None)
    if p and os.path.exists(p):
        h = hashlib.md5()
        with open(p, "rb") as f:
            h.update(f.read())
        return h.hexdigest()[:12]
    return ""


def main() -> int:
    # 避让：R15 自身拥有名为 `report` 的技能 (s07_report)。
    # 当 CLI 传入 `report report ...` 时属于 R15 自身技能调用，交由技能解析器处理；
    # 仅当入参为元命令（如 report procurement purchase_order 等）才交由公共 meta_command。
    if not (len(sys.argv) > 2 and sys.argv[1] == "report" and sys.argv[2] == "report"):
        _meta = role_runtime.handle_meta_command(sys.argv[1:], ROLE)
        if _meta is not None:
            return _meta

    args = build_parser().parse_args()

    if args.skill == "manifest":
        emit_result(manifest())
        return 0
    if args.skill == "local":
        out = local_exec.execute(args.input)
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
    if args.skill == "evolve":
        from engines import (
            ERPRuntimeEngine,
            IntentCompiler,
            ReflexiveHealer,
            SpecLedger,
            SupplySlopGuard,
            SupplyScenarioMatrix,
            ERPAssetBundle,
            ERPDiffPatchEngine,
            ERPSessionMemory,
            ERPTelemetryWatchdog,
        )
        if args.subcmd == "probe":
            eng = ERPRuntimeEngine()
            out = eng.probe_health()
            emit_result(out)
            return 0 if out.get("status") == "healthy" else 1
        elif args.subcmd == "decompile":
            comp = IntentCompiler()
            stages = comp.compile_intent(args.query)
            out = {"stages": stages, "summary": comp.get_dag_summary(stages)}
            emit_result(out)
            return 0
        elif args.subcmd == "heal":
            healer = ReflexiveHealer()
            try:
                res = healer.check_redlines(args.action)
                out = {"blocked": False, "action": args.action, "result": res}
            except ValueError as e:
                out = {"blocked": True, "action": args.action, "reason": str(e)}
            emit_result(out)
            return 0
        elif args.subcmd == "spec":
            ledger = SpecLedger()
            out = ledger.load_spec()
            emit_result(out)
            return 0
        elif args.subcmd == "slop":
            guard = SupplySlopGuard()
            raw_text = args.text or "整体良好，按需采购，表现良好，相关细节待定"
            audit_res = guard.audit(raw_text)
            emit_result(audit_res)
            return 0
        elif args.subcmd == "scenario":
            sc = SupplyScenarioMatrix()
            scenarios = sc.generate(item_code=getattr(args, "item_code", "ITEM_STANDARD"), target_demand_qty=getattr(args, "demand", 1000.0))
            out = {"scenarios": scenarios, "markdown_table": sc.render_markdown(scenarios)}
            emit_result(out)
            return 0
        elif args.subcmd == "bundle":
            bundle_eng = ERPAssetBundle()
            input_data = c.load_json(args.input) if getattr(args, "input", None) else None
            paths = bundle_eng.compile_and_save(args.run_id, artifact_data=input_data)
            emit_result({"ok": True, "run_id": args.run_id, "paths": paths})
            return 0
        elif args.subcmd == "patch":
            diff_eng = ERPDiffPatchEngine()
            old_doc = c.load_json(args.old)
            new_doc = c.load_json(args.new)
            patch_ops = diff_eng.create_patch(old_doc, new_doc)
            applied = diff_eng.apply_patch(old_doc, patch_ops)
            emit_result({"patch_ops": patch_ops, "applied": applied})
            return 0
        elif args.subcmd == "memory":
            mem = ERPSessionMemory()
            res = mem.disambiguate_query(args.query)
            emit_result(res)
            return 0
        elif args.subcmd == "watchdog":
            wd = ERPTelemetryWatchdog()
            out = wd.probe_health()
            emit_result(out)
            return 0

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
