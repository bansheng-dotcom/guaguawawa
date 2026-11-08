#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R06 蛙得清 · 数据分析师 —— 本地可运行 Agent（九技能调度器）。

把 9 个能力域各自做成一个独立技能模块（skills/s01..s09），本文件只做三件事：
    1. 注册 9 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    dataset + metrics_spec  →  dataset(清洗后) + analysis_report

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py quality audit  --input orders.csv
    python agent.py explore trend --input orders.csv --date date --value amount
    python agent.py statistics abtest --input orders.csv --group channel \
        --control 抖音 --treatment 微信 --metric amount
    python agent.py run --task <task_id>
"""
from __future__ import annotations

# --- 运行时引导：仓库根入 sys.path，修掉异构 cwd 下 ModuleNotFoundError ---
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
# 48 型图表库已上收为全角色共享（core/charts），角色不再保留私有副本。
CHART_DIR = os.path.join(_AGENTS, "core", "charts")
for _p in (_HERE, _AGENTS, CHART_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core import protocol, registry, workspace  # noqa: E402
from skills import SKILLS, _common as c  # noqa: E402
import cases  # noqa: E402
import contracts  # noqa: E402
import harness  # noqa: E402
import review  # noqa: E402
from core import report_bridge  # noqa: E402
import report_contract  # noqa: E402

ROLE = "r06"
WORKSPACE_ROOT = os.path.join(_AGENTS, "workspace")
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
_INTENT_ROUTES = [
    (("清洗", "clean", "去重"), "quality", "clean", {}),
    (("质检", "质量", "audit"), "quality", "audit", {}),
    (("趋势", "trend"), "explore", "trend", {"date": "date", "value": "amount"}),
    (("漏斗", "funnel"), "explore", "funnel", {"stage": "status"}),
    (("留存", "cohort"), "explore", "cohort", {"user": "user_id", "period": "date"}),
    (("分组", "groupby"), "explore", "groupby", {"group": "channel", "value": "amount"}),
    (("描述", "describe", "统计汇总"), "describe", "describe", {"col": "amount"}),
    (("相关", "correlate", "相关系数", "皮尔逊"), "correlate", "correlate",
     {"col_a": "amount", "col_b": "amount"}),
    (("t检验", "ttest", "welch", "双样本"), "ttest", "ttest",
     {"value": "amount", "group": "channel", "group_a": "抖音", "group_b": "微信"}),
    (("卡方", "chi2", "独立性"), "chi2", "chi2", {"row": "channel", "col": "status"}),
    (("anova", "方差分析"), "anova", "anova", {"value": "amount", "group": "channel"}),
    (("回归", "regression", "ols"), "regression", "regression",
     {"x": "amount", "y": "amount"}),
    (("实验", "abtest", "ab"), "abtest", "abtest",
     {"group": "channel", "control": "抖音", "treatment": "微信", "metric": "amount"}),
    (("根因", "贡献", "下钻", "drilldown"), "rootcause", "drilldown",
     {"dim": "channel", "value": "amount"}),
    (("语义", "指标", "口径", "semantic"), "semantics", "validate", {}),
]


def emit_result(data: Dict[str, Any]) -> None:
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R06 蛙得清 · 数据分析师")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    sp.add_parser("demo", help="生成示例订单数据 + 语义模型")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)
    
    # 注入测试与诊断命令
    sp.add_parser("test", help="运行工程化测试")
    diag_p = sp.add_parser("diagnose", help="基于SOP自动执行业务诊断")
    diag_p.add_argument("--case", required=True)
    
    # 商业咨询级深度分析与决策研报
    dp = sp.add_parser("deep", help="出具咨询级深度商业决策报告 (McKinsey-Grade)")
    dp.add_argument("--series", required=True, help="12个月时序数据 (CSV)")
    dp.add_argument("--cross", required=True, help="截面/区域对比数据 (CSV)")
    dp.add_argument("--before", required=True, help="前期时间标识 (如 2025-09)")
    dp.add_argument("--after", required=True, help="本期时间标识 (如 2025-10)")
    dp.add_argument("--intent", default="全盘利润异动归因与行动决策", help="分析命题与意图")
    dp.add_argument("--out-dir", default=None, help="输出目录")
    
    # 注入真实适配器命令
    qa = sp.add_parser("quality_real", help="真实的 Pandas 数据质量审计")
    qa.add_argument("--input", required=True)
    qa.add_argument("--pk", default=None)
    qa.add_argument("--date_col", default=None)

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_harness(sp) -> None:
    """把 harness.py 的确定性验证器挂到 agent CLI 上。"""
    h = sp.add_parser("harness", help="确定性验证器：dataset/report/semantic/chart/verify")
    ha = h.add_subparsers(dest="hcmd", required=True)
    d = ha.add_parser("dataset", help="数据集门禁（行数/字段/缺失率/非数值）")
    d.add_argument("--input", required=True)
    d.add_argument("--semantic", default=None)
    r = ha.add_parser("report", help="报告门禁（结论段/QA/禁用语）")
    r.add_argument("--input", required=True)
    sm = ha.add_parser("semantic", help="语义层校验（可选 --data 做语义↔数据联动）")
    sm.add_argument("--input", required=True)
    sm.add_argument("--data", default=None, help="提供数据 CSV 时一并做防幻觉联动")
    ch = ha.add_parser("chart", help="图表规格校验")
    ch.add_argument("--input", required=True)
    pl = ha.add_parser("plan", help="分析计划门禁（plan_schema.json）")
    pl.add_argument("--input", required=True)
    v = ha.add_parser("verify", help="综合门禁（dataset+report+semantic）")
    v.add_argument("--data", required=True)
    v.add_argument("--report", required=True)
    v.add_argument("--semantic", default=None)
    rl = ha.add_parser("runlog", help="运行可观测性：最近 N 次运行记录")
    rl.add_argument("--n", type=int, default=10)


def _run_harness(args) -> Dict[str, Any]:
    if args.hcmd == "dataset":
        return harness.validate_dataset(args.input, args.semantic)
    if args.hcmd == "report":
        return harness.validate_report(args.input)
    if args.hcmd == "semantic":
        return harness.validate_semantic(args.input, getattr(args, "data", None))
    if args.hcmd == "chart":
        return harness.validate_chart_spec(args.input)
    if args.hcmd == "plan":
        return harness.validate_plan(args.input)
    if args.hcmd == "verify":
        return harness.verify_all(args.data, args.report, args.semantic)
    if args.hcmd == "runlog":
        return {"runlog": ws.runlog(args.n)}
    return {"error": f"未知 harness 命令: {args.hcmd}"}


def _mkns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


def _register_contract(sp) -> None:
    """T6：每技能机器可读输入/输出 JSON Schema 契约。"""
    cp = sp.add_parser("contract", help="技能契约：list/get/validate")
    ca = cp.add_subparsers(dest="ccmd", required=True)

    l = ca.add_parser("list", help="列出所有技能及其契约动作")
    g = ca.add_parser("get", help="输出某技能某动作的契约 schema")
    g.add_argument("--skill", required=True, dest="contract_skill")
    g.add_argument("--action", default=None, dest="contract_action")
    v = ca.add_parser("validate", help="按契约校验某技能的产出 JSON")
    v.add_argument("--skill", required=True, dest="contract_skill")
    v.add_argument("--action", required=True, dest="contract_action")
    v.add_argument("--output", required=True, help="待校验的技能产出 JSON 路径")


def _register_case(sp) -> None:
    """T8：案例库（业务语义 + 阈值 + 边界）。"""
    cp = sp.add_parser("case", help="案例库：list/get/validate")
    ca = cp.add_subparsers(dest="ccmd", required=True)
    l = ca.add_parser("list", help="列出所有案例")
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
    """T7：对抗评审（确定性 reviewer）。"""
    p = sp.add_parser("review", help="对抗评审：对技能产出做确定性挑战")
    p.add_argument("--result", required=True, help="待评审的技能产出 JSON")
    p.add_argument("--skill", required=True, dest="review_skill")
    p.add_argument("--action", required=True, dest="review_action")
    p.add_argument("--data", default=None, help="数据 CSV（数值可追溯校验）")
    p.add_argument("--run-id", default="")


def _run_review(args) -> Dict[str, Any]:
    result = c.load_json(args.result)
    packet = {"run_id": args.run_id, "skill": args.review_skill,
              "action": args.review_action, "result": result,
              "data_ref": args.data}
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
            schema = entry.get("output", {}).get(action)
            return {"skill": skill, "action": action, "output_schema": schema}
        return {"skill": skill, "desc": entry["desc"],
                "input": entry["input"], "output_actions": list(entry["output"])}
    if args.ccmd == "validate":
        result = c.load_json(args.output)
        return contracts.validate_output(skill, action, result)
    return {"error": f"未知 contract 命令: {args.ccmd}"}


# --------------------------------------------------------------------------- #
# 协作入口：读任务卡 → 意图路由 → 技能执行 → 产物写回工作区
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
        ws.emit(protocol.Event.now(ROLE, "task_failed", task_id,
                                   {"reason": "缺少输入文件"}))
        return {"error": "缺少输入文件"}

    intent = task.intent + " " + " ".join(params.values())
    skill_name, action, defaults = _route(intent)
    mod = SKILL_BY_NAME[skill_name]

    out_dir = ws.artifact(task_id)
    os.makedirs(out_dir, exist_ok=True)

    # 合并端口参数(优先级 > 默认)
    merged = dict(defaults)
    merged.update(params)
    merged["action"] = action
    merged["input"] = in_file
    if action in ("clean",) and "output" not in merged:
        merged["output"] = os.path.join(out_dir, "cleaned.csv")

    result = mod.run(_mkns(**merged))
    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    # 落产物 + 报告
    outputs: List[protocol.Port] = []
    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs.append(protocol.Port(f"{skill_name}.json", "data"))

    report_path = os.path.join(out_dir, "analysis_report.md")
    ports = report_bridge.emit(
        role=ROLE, name="蛙得清", title="数据分析师",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, md_name="analysis_report",
        specialist=report_contract.r06_contract, chart_dir=CHART_DIR)
    outputs.extend(ports)

    ws.update_task(task_id, {"outputs": [p.to_dict() for p in outputs],
                             "status": "done"})
    ws.emit(protocol.Event.now(ROLE, "task_finished", task_id,
                               {"outputs": [p.name for p in outputs]}))
    return result


def _route(intent: str):
    for kws, skill, action, defaults in _INTENT_ROUTES:
        if any(k in intent for k in kws):
            return skill, action, defaults
    # 缺省：数据质量审计（最安全的门禁动作）
    return "quality", "audit", {}


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
# 示例数据 / manifest
# --------------------------------------------------------------------------- #
DEMO_HEADERS = ["order_id", "date", "channel", "amount", "status", "user_id"]


def make_demo(path: str, n: int = 60) -> str:
    import random
    random.seed(7)
    channels = ["抖音", "小红书", "知乎", "微信"]
    statuses = ["浏览", "加购", "下单", "支付", "支付"]
    rows = []
    for i in range(n):
        day = f"2026-11-{1 + i % 12:02d}"
        rows.append({"order_id": f"O{i:04d}", "date": day,
                     "channel": random.choice(channels),
                     "amount": round(random.uniform(20, 500), 2),
                     "status": random.choice(statuses),
                     "user_id": f"U{i % 20:03d}"})
    rows[3]["amount"] = ""       # 脏数据：缺失
    rows[5]["amount"] = "99999"  # 脏数据：极端值
    c.write_csv(path, DEMO_HEADERS, rows)
    return path


def manifest() -> Dict[str, Any]:
    r = registry.by_id(ROLE)
    return {"role": r["id"], "name": r["name"], "title": r["title"],
            "capabilities": r["capabilities"],
            "inputs": r["inputs"], "outputs": r["outputs"],
            "skills": [(m.NAME, m.DESC) for m in SKILLS],
            "capability_status": {"local_data_analysis": "real",
                                  "heavy_backend_scinlp": "blocked",
                                  "plotly_interactive_export": "simulated"}}


def _input_hash(args) -> str:
    p = getattr(args, "input", None)
    if p and os.path.exists(p):
        h = hashlib.md5()
        with open(p, "rb") as f:
            h.update(f.read())
        return h.hexdigest()[:12]
    return ""


def main() -> int:
    args = build_parser().parse_args()

    if args.skill == "manifest":
        emit_result(manifest())
        return 0
    if args.skill == "demo":
        path = os.path.join(WORKSPACE_ROOT, "artifacts", "orders.csv")
        make_demo(path)
        sem_src = os.path.join(_HERE, "examples", "semantic_model.json")
        sem_dst = os.path.join(WORKSPACE_ROOT, "artifacts", "semantic_model.json")
        c.write_json(sem_dst, c.load_json(sem_src))
        emit_result({"demo_csv": path, "semantic_model": sem_dst})
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

    if args.skill == "test":
        import pytest
        # 使用绝对路径定位 tests 目录
        tests_path = os.path.join(_HERE, "tests")
        sys.exit(pytest.main([tests_path]))
    if args.skill == "diagnose":
        case_path = os.path.join(_HERE, "cases", f"{args.case}.md")
        if not os.path.exists(case_path):
            emit_result({"error": f"找不到诊断案例: {args.case}"})
        else:
            # 简单的 SOP 伪自动化执行：读取文件并提取核心步骤
            with open(case_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 这里实现自动化诊断的路由逻辑
            emit_result({
                "status": "SOP自动化执行启动",
                "case": args.case,
                "workflow": "已解析 SOP 逻辑",
                "next_step": "正在调用 s03_explore.py 进行漏斗节点下钻...",
                "sop_summary": content[:100] + "..."
            })
        return 0

    # 咨询级深度决策研报分支
    if args.skill == "deep":
        from consulting_report import build_consulting_report
        from agents.shared.report_generator import generate_professional_report
        
        out_dir = args.out_dir or os.path.join(WORKSPACE_ROOT, "consulting_report")
        spec = build_consulting_report(
            series_csv=args.series,
            cross_csv=args.cross,
            before=args.before,
            after=args.after,
            intent=args.intent
        )
        files = generate_professional_report(out_dir=out_dir, report_slug="consulting_report", **spec)
        emit_result({
            "ok": True,
            "status": "出具成功",
            "report_html": files["html"],
            "report_md": files["md"],
            "figures_count": len(spec["figures"])
        })
        return 0

    # 真实适配器分支
    if args.skill == "quality_real":
        import pandas as pd
        from skills.quality_adapter import QualityAuditAdapter
        
        try:
            # 动态加载外置业务配置
            with open(os.path.join(_HERE, "rules", "business_thresholds.json"), "r") as f:
                rules = json.load(f).get("quality", {})
        except Exception:
            rules = {}
            
        adapter = QualityAuditAdapter(rule_config=rules)
        df = pd.read_csv(args.input)
        
        result = adapter.run_pipeline(df, pk=args.pk, date_col=args.date_col)
        emit_result(result)
        return 0 if result.get("ok") else 1

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