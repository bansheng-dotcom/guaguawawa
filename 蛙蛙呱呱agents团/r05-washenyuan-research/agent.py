# -*- coding: utf-8 -*-
"""R05 蛙深远（战略研究官）——薄调度器。

子命令：
  manifest / demo / run --task <id> / contract / review / case / harness
  + 7 个技能子命令（research/industry/competitor/business/sizing/scenario/auto）

设计约定（对齐 r02/r03/r04/r07）：
- 技能只做确定性计算，无 LLM 调用；退出码：ok=true → 0，否则 1。
- run --task 走 agents/core/workspace.py 协议（runlog 写 ../workspace/runlog.jsonl）。
- R05 边界：只做研究呈现证据与选项，不替你拍板。
"""
from __future__ import annotations

# --- 运行时引导（META-001 Stage 3）：仓库根入 sys.path，修掉异构 cwd 下 ---
# --- `ModuleNotFoundError: No module named 'agents'` 的历史故障 ---
import os as _os
import sys as _sys
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _REPO_ROOT not in _sys.path:
    _sys.path.insert(0, _REPO_ROOT)


import argparse
import json
import os
import sys
import time
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

ROLE = "r05"
DIRS = os.path.basename(_HERE)

# ---------------------------------------------------------------------------
# 意图路由（具体关键词靠前；大小写不敏感；命中即返回）
# 元组：(关键词组, skill, action, extra_args 默认值)
# ---------------------------------------------------------------------------
_INTENT_ROUTES: List[Tuple[Tuple[str, ...], str, str, Dict[str, str]]] = [
    (("证据台账", "研究台账", "来源登记", "evidence ledger", "claims ledger"),
     "research", "ledger", {}),
    (("研究报告", "引用覆盖", "研究汇报", "research report"),
     "research", "report", {}),
    (("行业地图", "产业链", "价值链", "行业扫描", "landscape"),
     "industry", "landscape", {}),
    (("市场集中度", "HHI", "CR4", "集中度", "concentration"),
     "industry", "concentration", {}),
    (("竞品矩阵", "功能对比", "feature matrix", "竞品对比"),
     "competitor", "matrix", {}),
    (("战斗卡", "对位卡", "battlecard", "竞品威胁"),
     "competitor", "battlecard", {}),
    (("商业画布", "九宫格", "business canvas", "商业模式"),
     "business", "canvas", {}),
    (("变现", "定价", "单位经济", "ltv", "monetize"),
     "business", "monetize", {}),
    (("市场规模", "TAM", "SAM", "SOM", "market sizing"),
     "sizing", "size", {}),
    (("敏感性", "关键驱动", "sensitivity"),
     "sizing", "sensitivity", {}),
    (("宏观分析", "PESTEL", "政策环境"),
     "scenario", "pestel", {}),
    (("事前尸检", "失效推演", "pre-mortem", "premortem"),
     "scenario", "premortem", {}),
    (("研究计划", "research plan", "调研计划"),
     "auto", "plan", {}),
    (("研究追踪", "运行追踪", "调研进度", "research track"),
     "auto", "track", {}),
]
_DEFAULT_ROUTE: Tuple[str, str, Dict[str, str]] = ("research", "ledger", {})


def route_intent(intent: str) -> Tuple[str, str, Dict[str, str]]:
    low = str(intent or "").lower()
    for keys, skill, action, extra in _INTENT_ROUTES:
        for k in keys:
            if k.lower() in low:
                return skill, action, extra
    # 关键词未命中：交给共享 L02 内核；不再静默落到默认动作。
    return fallback_route(ROLE, intent)


# ---------------------------------------------------------------------------
# CLI 组装
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="agent.py", description="R05 蛙深远（战略研究官）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("manifest", help="打印角色能力清单")
    sub.add_parser("demo", help="用真实示例跑一组代表性动作")

    rp = sub.add_parser("run", help="按 task 卡执行一次研究任务")
    rp.add_argument("--task", required=True, help="task id（workspace 协议）")
    add_clarify_parser(sub)

    cp = sub.add_parser("contract", help="技能契约登记表")
    csub = cp.add_subparsers(dest="ccmd", required=True)
    csub.add_parser("list", help="列出全部 skill/action")
    cvp = csub.add_parser("validate", help="校验输出是否符合契约")
    cvp.add_argument("--skill", required=True, choices=contracts.skill_names())
    cvp.add_argument("--action", required=True)
    cvp.add_argument("--output", required=True, help="result.json 路径")

    rvp = sub.add_parser("review", help="对抗评审（T7）：对研究产出本身再评审")
    rvp.add_argument("--packet", required=True, help="产出包 JSON（{skill,action,result}）")

    cap = sub.add_parser("case", help="案例库")
    cap.add_argument("case_id", nargs="?", default=None,
                     help="缺省=列出全部；给定 id=展示并校验")

    hp = sub.add_parser("harness", help="确定性验证器")
    hsub = hp.add_subparsers(dest="hcmd", required=True)
    hmp = hsub.add_parser("materials", help="研究物料门禁（BLOCKED 判定）")
    hmp.add_argument("--input", required=True)
    hvp = hsub.add_parser("verdict", help="研究产出结构门禁")
    hvp.add_argument("--input", required=True)
    hpp = hsub.add_parser("plan", help="研究计划门禁")
    hpp.add_argument("--input", required=True)
    hrp = hsub.add_parser("runlog", help="最近 n 条 runlog")
    hrp.add_argument("--n", type=int, default=5)

    _register_evolution(sub)

    for m in SKILLS:
        m.add_parser(sub)
    return ap


def _register_evolution(sub) -> None:
    ep = sub.add_parser("evolution", help="十轮渐进自升级能力接口：probe/prompter/heal/ledger/slopguard/explore/bundle/patch/memory/telemetry")
    ea = ep.add_subparsers(dest="action", required=True)

    # L01: 探针
    ea.add_parser("probe", help="外置物理探针巡检")

    # L02: 动态意图
    p_prompter = ea.add_parser("prompter", help="战略意图解构与 DAG 编译器")
    p_prompter.add_argument("--intent", required=True)

    # L03: 自愈反思
    p_heal = ea.add_parser("heal", help="战略研究 Critic 诊断与 Auto-Heal 自愈")
    p_heal.add_argument("--input", required=True)

    # L04: 规范账本
    ea.add_parser("ledger", help="读取并校验 RESEARCH_SPEC.md 规范账本")

    # L05: 去劣反伪影
    p_slop = ea.add_parser("slopguard", help="假大空套话与未锚定词汇审计精修")
    p_slop.add_argument("--text", required=True)
    p_slop.add_argument("--polish", action="store_true")

    # L06: 三维情景比选
    p_explore = ea.add_parser("explore", help="三维情景规划横向比选看板生成")
    p_explore.add_argument("--input", default=None)
    p_explore.add_argument("--output", default=None)

    # L07: 伴生结构化资产
    p_bundle = ea.add_parser("bundle", help="导出伴生消费规格包与 Vega 图表描述符")
    p_bundle.add_argument("--input", default=None)
    p_bundle.add_argument("--output-dir", default=None)

    # L08: 局部增量编辑
    p_patch = ea.add_parser("patch", help="RFC 6902 差量微调与自然语言指令调优")
    p_patch.add_argument("--input", required=True)
    p_patch.add_argument("--instruction", required=True)

    # L09: 状态记忆
    p_memory = ea.add_parser("memory", help="会话状态工作记忆池操作")
    p_memory.add_argument("--commit", default=None)
    p_memory.add_argument("--rollback", type=int, default=None)
    p_memory.add_argument("--resolve", default=None)

    # L10: 容灾遥测
    ea.add_parser("telemetry", help="容灾看门狗熔断与全链路遥测健康检查")

    # ---- Round 1~3 升级新增探针（公开 CLI，供人与下游直接消费新引擎）----
    # 五阶段 Kahn DAG 编译
    p_compile = ea.add_parser("compile", help="五阶段研究 Kahn DAG 编译与工时预算")
    p_compile.add_argument("--intent", required=True)

    # 深层自愈 + 跨角色硬红线 handoff
    p_heal2 = ea.add_parser("heal2", help="Reflexive 深层自愈与越权红线移交")
    p_heal2.add_argument("--input", required=True)

    # 机器可读 SSOT + 8 维门禁
    p_spec = ea.add_parser("spec", help="机器可读 SSOT 与 8 维发布门禁评估")
    p_spec.add_argument("--metrics", default=None, help="metrics JSON 文件")
    p_spec.add_argument("--export", default=None, help="导出 spec 快照路径")

    # RFC 6902 差量
    p_diff = ea.add_parser("diff", help="RFC 6902 差量生成与应用")
    p_diff.add_argument("--source", required=True)
    p_diff.add_argument("--target", required=True)
    p_diff.add_argument("--output", default=None)

    # 会话槽位 / 指代消歧 / 回滚
    p_session = ea.add_parser("session", help="会话槽位双向同步、指代消歧与回滚")
    p_session.add_argument("--state", default=None)
    p_session.add_argument("--commit", default=None)
    p_session.add_argument("--slot", default=None, help="key=value")
    p_session.add_argument("--topic", default=None)
    p_session.add_argument("--resolve", default=None)
    p_session.add_argument("--rollback", type=int, default=None)

    # 三态熔断探针
    p_breaker = ea.add_parser("breaker", help="三态熔断 CLOSED/OPEN/HALF_OPEN 探针")
    p_breaker.add_argument("--fail", type=int, default=2)


def _run_evolution(args) -> Dict[str, Any]:
    from engines import (
        ResearchEngineManager,
        ResearchPrompter,
        ResearchCritic,
        ResearchLedgerParser,
        ResearchSlopGuard,
        ScenarioMatrixExplorer,
        ResearchAssetBundle,
        ResearchPatchEditor,
        SessionMemoryPool,
        WatchdogCircuitBreaker,
        ProductionTelemetry,
        # Round 1 执行基石新增实体
        ResearchRuntimeEngine,
        ResearchIntentCompiler,
        ReflexiveResearchHealer,
        # Round 2 专业深度新增实体
        ResearchSpecLedger,
        # Round 3 工业交付新增实体
        ResearchDiffPatchEngine,
        ResearchSessionStore,
        CircuitBreaker,
        CircuitOpenError,
    )

    act = args.action
    if act == "probe":
        mgr = ResearchEngineManager()
        probes = mgr.probe_all()
        return {"ok": probes.get("all_healthy", False), "details": probes}

    elif act == "prompter":
        prompter = ResearchPrompter()
        res = prompter.compile_intent(args.intent)
        return {"ok": True, "dag": res}

    elif act == "heal":
        with open(args.input, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        critic = ResearchCritic()
        ok, issues = critic.audit_findings(data)
        if ok:
            return {"ok": True, "status": "clean", "data": data}
        healed = critic.heal_payload(data, issues)
        return {"ok": True, "status": "healed", "issues": issues, "data": healed}

    elif act == "ledger":
        parser = ResearchLedgerParser()
        spec = parser.parse()
        return {"ok": spec.get("rules_loaded", False), "ledger": spec}

    elif act == "slopguard":
        guard = ResearchSlopGuard()
        audit = guard.audit_text(args.text)
        res = {"ok": audit.get("is_clean", False), "score": audit.get("score", 0), "audit": audit}
        if args.polish:
            polished, count = guard.polish(args.text)
            enforcement = guard.enforce_quality(args.text)
            res["polished_text"] = polished
            res["replaced_count"] = count
            res["quality_ok"] = enforcement["ok"]
            res["blocking_issues"] = enforcement["blocking_issues"]
            res["dri"] = enforcement["dri"]
            # 精修是「产出修复稿」动作：只要成功生成精修文本即退出 0；
            # 质量是否达标由 quality_ok / blocking_issues 表达，避免门禁结论
            # 混同为进程故障（审计模式仍以 is_clean 作为退出码）。
            res["ok"] = True
        return res

    elif act == "explore":
        explorer = ScenarioMatrixExplorer()
        inputs = {}
        if args.input and os.path.exists(args.input):
            with open(args.input, "r", encoding="utf-8-sig") as f:
                inputs = json.load(f)
        else:
            inputs = {"tam": 120.0, "cogs": 300.0, "price": 1200.0}
        matrix = explorer.generate_matrix(inputs)
        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(matrix["board_markdown"])
        return {"ok": True, "matrix": matrix, "output": args.output}

    elif act == "bundle":
        exporter = ResearchAssetBundle()
        inputs = {}
        if args.input and os.path.exists(args.input):
            with open(args.input, "r", encoding="utf-8-sig") as f:
                inputs = json.load(f)
        else:
            inputs = {
                "tam": 120.0,
                "hhi": 2250,
                "cr4": 90,
                "structure": "moderate",
                "claims": [{"id": "c1", "sources": ["S1"]}]
            }
        out_dir = args.output_dir or os.path.join(_HERE, "artifacts")
        bundle = exporter.export_bundle(inputs, out_dir)
        return {"ok": True, "bundle": bundle}

    elif act == "patch":
        with open(args.input, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        editor = ResearchPatchEditor()
        patched, logs = editor.patch_by_instruction(data, args.instruction)
        return {"ok": True, "patched": patched, "patch_logs": logs}

    elif act == "memory":
        state_path = os.path.join(_HERE, "session_state.json")
        pool = SessionMemoryPool(state_path)
        if args.commit:
            ver = pool.record_turn(args.commit, {"status": "manual_commit"}, topic="人工提交快照")
            return {"ok": True, "version": ver}
        elif args.rollback is not None:
            ok = pool.rollback(args.rollback)
            return {"ok": ok, "current_version": pool.state.get("version")}
        elif args.resolve:
            res = pool.resolve_reference(args.resolve)
            return {"ok": True, "resolved": res}
        return {"ok": True, "state": pool.state}

    elif act == "telemetry":
        watchdog = WatchdogCircuitBreaker(timeout_sec=2.0)
        res = watchdog.execute_with_guard(lambda: "pong")
        tel_file = os.path.join(_HERE, "telemetry.jsonl")
        tel = ProductionTelemetry(tel_file)
        span = tel.record_span("r05:healthcheck", {"res": res}, latency_ms=1.0)
        return {"ok": True, "watchdog": res, "span": span}

    elif act == "compile":
        dag = ResearchIntentCompiler().compile(args.intent)
        return {"ok": True, "dag": dag}

    elif act == "heal2":
        with open(args.input, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        result = ReflexiveResearchHealer().heal_and_verify(data)
        return {"ok": True, "status": "healed" if result["reflections"] else "clean", **result}

    elif act == "spec":
        ledger = ResearchSpecLedger()
        spec = ledger.load()
        metrics: Dict[str, Any] = {}
        if args.metrics and os.path.exists(args.metrics):
            payload = json.load(open(args.metrics, encoding="utf-8-sig"))
            metrics = payload.get("metrics", payload)
        evaluation = ledger.evaluate(metrics)
        if args.export:
            os.makedirs(os.path.dirname(os.path.abspath(args.export)), exist_ok=True)
            ledger.export_json(args.export)
        return {"ok": bool(evaluation["passed"]), "spec_version": spec.get("version"),
                "gate_count": len(ledger.gates()), "evaluation": evaluation,
                "export": args.export}

    elif act == "diff":
        engine = ResearchDiffPatchEngine()
        with open(args.source, "r", encoding="utf-8-sig") as f:
            source_doc = json.load(f)
        with open(args.target, "r", encoding="utf-8-sig") as f:
            target_doc = json.load(f)
        patch = engine.create_patch(source_doc, target_doc)
        applied = engine.apply(source_doc, patch)
        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(patch, f, ensure_ascii=False, indent=2)
        return {"ok": applied == target_doc, "patch": patch,
                "ops_count": len(patch), "output": args.output}

    elif act == "session":
        state_path = args.state or os.path.join(_HERE, "workspace", "session_state_v2.json")
        store = ResearchSessionStore(state_path)
        if args.slot:
            key, _, value = args.slot.partition("=")
            store.update_slot(key.strip(), value.strip())
        if args.commit:
            store.record_turn(args.commit, {"status": "manual_commit"}, topic=args.topic)
        resolved = store.resolve_reference(args.resolve) if args.resolve else None
        rolled = store.rollback(args.rollback) if args.rollback is not None else None
        return {"ok": True, "state_path": state_path, "resolved": resolved,
                "rollback": rolled, "state": store.state}

    elif act == "breaker":
        breaker = CircuitBreaker(failure_threshold=max(1, args.fail), cooldown_sec=0.05)
        states = [breaker.state]

        def _boom():
            raise RuntimeError("simulated upstream failure")

        for _ in range(max(1, args.fail)):
            try:
                breaker.call(_boom)
            except RuntimeError:
                states.append(breaker.state)
        blocked = False
        try:
            breaker.call(lambda: "should-not-run")
        except CircuitOpenError:
            blocked = True
        time.sleep(0.06)
        recovered = breaker.state == "HALF_OPEN" and breaker.call(lambda: "pong") == "pong"
        return {"ok": blocked and recovered, "states": states, "blocked": blocked,
                "final_state": breaker.state}

    return {"ok": False, "error": f"Unknown evolution action: {act}"}


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
    skills = [{"name": m.NAME, "skill": m.NAME, "desc": m.DESC, "description": m.DESC,
               "actions": [{"action": a, "help": h} for a, h in m.ACTIONS.items()]}
              for m in SKILLS]
    return {
        "role": role["id"], "dirs": DIRS, "name": "蛙深远（战略研究官）",
        "title": role["title"], "capabilities": role["capabilities"],
        "inputs": role["inputs"], "outputs": role["outputs"],
        "capability_status": {"default": "real", "reason": "本地确定性研究可执行", "external_actions": "simulated"},
        "desc": "战略研究：证据台账、行业扫描、竞品情报、商业模式、市场规模、"
                "情景推演、研究自动化。只呈现证据与选项，不替你拍板。",
        "skills": skills,
        "skill_count": len(SKILLS),
        "action_count": sum(len(m.ACTIONS) for m in SKILLS),
        "cases": [r["case_id"] for r in cases_lib.list_cases()],
        "contracts": [f"{s}/{a}" for s in contracts.skill_names()
                      for a in contracts.actions(s)],
        "boundary": {
            "in_scope": ["行业/市场/竞品研究", "市场规模测算", "情景推演",
                         "证据台账与研究报告"],
            "out_of_scope": ["数据分析结论（归 R06）", "正式财务/法律判断（归 R03）",
                             "替老板决策（只呈现证据与选项）"],
            "never": ["无源断言（claims 必须挂来源）", "替你拍板（决策权在老板）",
                      "结论文本含推测措辞"],
        },
        "intent_routes": [{"keys": list(k), "skill": s, "action": a}
                          for k, s, a, _ in _INTENT_ROUTES],
    }


def _run_demo() -> int:
    demo_specs = [
        ("research", "ledger", os.path.join(_HERE, "examples", "research_ledger.json"), {}),
        ("sizing", "size", os.path.join(_HERE, "examples", "sizing_size.json"), {}),
        ("scenario", "premortem", os.path.join(_HERE, "examples", "scenario_premortem.json"), {}),
    ]
    artifacts_dir = ws.artifact("r05-demo")
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
        print(f"[run] task.owner={task.owner!r} != r05：拒绝执行（越权）",
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
                          "plan": extra.get("plan")}, ensure_ascii=False, indent=2))
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
        role=ROLE, name="蛙深远", title="战略研究官", result=out,
        skill=skill, action=action, intent=intent, out_dir=out_dir, input_path=input_path,
        md_name="research_report")

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
        c.emit(make_manifest())
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
    if cmd == "evolution":
        out = _run_evolution(args)
        c.emit(out)
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
