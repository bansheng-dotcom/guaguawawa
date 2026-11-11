#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R10 蛙成美 · 视觉设计官 —— 本地可运行 Agent（八技能调度器）。

把 8 个能力域各自做成一个独立技能模块（skills/s01..s08），本文件只做三件事：
    1. 注册 8 个技能子命令 + manifest/demo/run；
    2. 把 CLI 分发到对应技能模块；
    3. 提供协作入口 run_task：读任务卡 → 按意图路由到技能 → 产物写回工作区。

协作契约（inputs → outputs）：
    brand_brief + content  →  visual_assets + vi

本地运行示例：
    python agent.py manifest
    python agent.py demo
    python agent.py logo logo --input examples/logo.json
    python agent.py imagegen prompt --input examples/prompt.json
    python agent.py run --task <task_id>
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

ROLE = "r10"
CAPABILITY_STATUS = {"default": "real", "reason": "本地输入的结构与文件属性检查", "external_actions": "simulated"}
WORKSPACE_ROOT = workspace.default_root()
ws = workspace.Workspace(WORKSPACE_ROOT)
SKILL_BY_NAME = {m.NAME: m for m in SKILLS}

# 意图 → (技能, 动作, 默认参数)。供 run_task 把任务卡意图确定性路由到技能。
# 顺序即优先级：更具体的关键词靠前，_route 用小写不区分大小写匹配。
_INTENT_ROUTES = [
    (("品牌一致性", "vi 检查", "品牌检查"), "brandcheck", "check", {}),
    (("缩放", "裁剪", "加水印", "图片补边", "resize"), "imgops", "info", {}),
    (("设计系统", "design system", "design.md", "风格库", "品牌风格", "参考风格"), "designsys", "list", {}),
    (("风格推荐", "推荐风格", "style recommend"), "designsys", "recommend", {}),
    (("视频提示词", "分镜", "h3", "t2va", "i2va", "fl2va", "l2va", "ref2va", "脚本转视频"), "h3prompt", "build", {}),
    (("真实生图", "真实生成图片", "nano banana", "nanobanana", "aihive", "ai hive", "文生图接口", "图片编辑接口"), "aihive", "probe", {}),
    (("logo", "标志", "logotype", "图标", "favicon", "app icon", "品牌标"), "logo", "logo", {}),
    (("生图", "插画", "主视觉", "imagegen", "图片", "生图提示词"), "imagegen", "generate", {}),
    (("海报", "物料", "banner", "卖点图", "poster", "宣传图"), "imagegen", "generate", {}),
    (("设计令牌", "token", "令牌", "design token"), "brand", "token", {}),
    (("视觉身份", "stylescape", "品牌vi", "vi", "品牌视觉", "色彩", "字体搭配"), "brand", "vi", {}),
    (("动效", "motion", "lottie", "微交互", "动画", "缓动"), "motion", "motion", {}),
    (("原型", "交互", "可点击", "prototype"), "motion", "prototype", {}),
    (("屏幕", "界面", "ui", "ux", "组件库", "无障碍", "可用性"), "uiux", "screen", {}),
    (("转写", "字幕", "whisper", "语音转文字"), "transcribe", "transcribe", {}),
    (("视频", "音频", "转码", "剪辑", "ffmpeg", "封装"), "media", "media", {}),
    (("抠图", "修图", "图片处理", "批量", "压缩", "pillow", "背景去除"), "imaging", "edit", {}),
    (("矢量稿", "版式稿", "svg", "主题色板", "矢量渲染", "theme"), "render", "poster", {}),
]


def emit_result(data: Dict[str, Any]) -> None:
    data.setdefault("capability_status", "real")
    data.setdefault("capability_evidence", "local input inspected")
    c.emit(data)


# --------------------------------------------------------------------------- #
# CLI 与分发
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent.py", description="R10 蛙成美 · 视觉设计官")
    sp = p.add_subparsers(dest="skill", required=True)

    sp.add_parser("manifest", help="打印协作契约(端口/能力)")
    sp.add_parser("demo", help="生成示例设计工件（logo/prompt/vi/screen）")
    run_p = sp.add_parser("run", help="协作入口：执行任务卡")
    run_p.add_argument("--task", required=True)
    add_clarify_parser(sp)

    _register_harness(sp)
    _register_contract(sp)
    _register_case(sp)
    _register_review(sp)
    la = sp.add_parser("local-media-check", help="本地媒体文件存在性/MIME/尺寸检查")
    la.add_argument("--input", required=True)

    ev_p = sp.add_parser("evolve", help="十维演进元模型引擎调度 (L01~L10)")
    ev_sub = ev_p.add_subparsers(dest="subcmd", required=True)
    ev_sub.add_parser("probe", help="L01: 探测引擎健康状态")
    dec_p = ev_sub.add_parser("decompile", help="L02: 意图解构与DAG编排")
    dec_p.add_argument("--query", required=True, help="设计诉求自然语言")
    heal_p = ev_sub.add_parser("heal", help="L03: 自愈反思与红线审判")
    heal_p.add_argument("--type", default="prompt", dest="heal_type")
    heal_p.add_argument("--input", required=True)
    spec_p = ev_sub.add_parser("spec-tokens", help="L04: 领域规格与令牌导出")
    spec_p.add_argument("--format", default="css", choices=["css", "flutter", "json"])
    slop_p = ev_sub.add_parser("slopguard", help="L05: 质感去劣与占位驱除")
    slop_p.add_argument("--text", required=True)
    scen_p = ev_sub.add_parser("scenario", help="L06: 裂变横向决策看板")
    scen_p.add_argument("--concept", default="商业宣传主视觉")
    bun_p = ev_sub.add_parser("bundle", help="L07: 导出下游伴生消费资产包")
    bun_p.add_argument("--id", default="r10_evolve_bundle")
    pat_p = ev_sub.add_parser("patch", help="L08: 局部差量补丁与Inpaint")
    pat_p.add_argument("--doc", default='{"theme": {"primary": "#0F172A"}}')
    mem_p = ev_sub.add_parser("memory", help="L09: 会话记忆与代词消歧")
    mem_p.add_argument("--query", required=True)
    tel_p = ev_sub.add_parser("telemetry", help="L10: 工业容灾与遥测记录")
    tel_p.add_argument("--name", default="r10_cli_trace")

    for m in SKILLS:
        m.add_parser(sp)
    return p


def _register_harness(sp) -> None:
    h = sp.add_parser("harness", help="确定性验证器：logo/vi/screen/motion 等 + probe")
    ha = h.add_subparsers(dest="hcmd", required=True)
    for name, help_txt in {
        "prompt": "生图提示词门禁", "style": "风格探索门禁",
        "logo": "Logo 设计门禁", "favicon": "图标变体门禁",
        "screen": "屏幕设计门禁", "ux": "可用性评估门禁",
        "vi": "品牌视觉身份门禁", "token": "设计令牌门禁",
        "motion": "动效规格门禁", "prototype": "交互原型门禁",
        "edit": "图像工程任务单门禁", "media": "媒体处理任务单门禁",
        "transcribe": "转写任务单门禁", "poster": "宣传图契约门禁",
    }.items():
        pa = ha.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    pr = ha.add_parser("probe", help="重依赖能力探测（imaging/media/transcribe）")
    pr.add_argument("--skill", required=True)
    v = ha.add_parser("verify", help="综合门禁（logo+vi）")
    v.add_argument("--logo", default=None)
    v.add_argument("--vi", default=None)
    rl = ha.add_parser("runlog", help="运行可观测性：最近 N 次运行记录")
    rl.add_argument("--n", type=int, default=10)


def _run_harness(args) -> Dict[str, Any]:
    if args.hcmd == "verify":
        return harness.verify(args.logo, args.vi)
    if args.hcmd == "probe":
        return harness.probe(args.skill)
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
    # 生图类动作的默认落盘目录固定到任务工件目录，避免污染 workspace 根
    if skill_name == "imagegen" and action == "generate" and not merged.get("output_dir"):
        merged["output_dir"] = out_dir

    result = mod.run(_mkns(**merged))
    result.setdefault("capability_status", "real")
    result.setdefault("capability_evidence", "local input inspected")
    result["task_id"] = task_id
    result["skill"] = skill_name
    result["action"] = action

    outputs: List[protocol.Port] = []
    result_path = os.path.join(out_dir, f"{skill_name}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    outputs.append(protocol.Port(f"{skill_name}.json", "data"))

    # 真实视觉产物也登记为输出端口，供 R08/R11 等下游直接取用
    for art in (result.get("artifacts") or []):
        if isinstance(art, str) and os.path.exists(art):
            outputs.append(protocol.Port(os.path.basename(art), "image"))

    ports = role_runtime.emit(
        role=ROLE, name="蛙成美", title="视觉设计官",
        result=result, skill=skill_name, action=action, intent=intent,
        out_dir=out_dir, input_path=in_file, md_name="design_report")
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
    for name in ("prompt", "logo", "vi", "screen"):
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
    if args.skill == "local-media-check":
        from local_actions import inspect_media
        out = inspect_media(args.input)
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
            VisualRuntimeEngine,
            VisualIntentCompiler,
            VisualReflexiveHealer,
            DesignSpecLedger,
            SlopGuard,
            VisualScenarioMatrix,
            VisualAssetBundle,
            VisualDiffPatchEngine,
            VisualSessionMemory,
            WatchdogBreaker,
            TelemetryTracer,
        )
        if args.subcmd == "probe":
            eng = VisualRuntimeEngine()
            out = eng.probe_health()
            emit_result(out)
            return 0 if out.get("status") == "healthy" else 1
        elif args.subcmd == "decompile":
            comp = VisualIntentCompiler()
            out = comp.decompile(args.query)
            emit_result(out)
            return 0 if out.get("ok") else 1
        elif args.subcmd == "heal":
            healer = VisualReflexiveHealer()
            in_data = c.load_json(args.input)
            out = healer.audit_and_heal(args.heal_type, in_data)
            emit_result(out)
            return 0 if out.get("ok") else 1
        elif args.subcmd == "spec-tokens":
            ledger = DesignSpecLedger()
            if args.format == "css":
                emit_result({"css": ledger.export_css_variables()})
            elif args.format == "flutter":
                emit_result({"flutter": ledger.export_flutter_theme()})
            else:
                emit_result(ledger.load_spec())
            return 0
        elif args.subcmd == "slopguard":
            emit_result(SlopGuard.audit_text(args.text))
            return 0
        elif args.subcmd == "scenario":
            mat = VisualScenarioMatrix()
            emit_result(mat.generate_matrix(args.concept))
            return 0
        elif args.subcmd == "bundle":
            bundle_eng = VisualAssetBundle()
            emit_result(bundle_eng.export_bundle(args.id, {"tokens": {"primary": "#0F172A"}}))
            return 0
        elif args.subcmd == "patch":
            patch_eng = VisualDiffPatchEngine()
            doc1 = json.loads(args.doc)
            doc2 = {"theme": {"primary": "#22D3EE", "radius": "8px"}}
            patch = patch_eng.create_patch(doc1, doc2)
            applied = patch_eng.apply_patch(doc1, patch)
            emit_result({"patch": patch, "applied": applied})
            return 0
        elif args.subcmd == "memory":
            mem = VisualSessionMemory()
            emit_result(mem.resolve_pronouns(args.query))
            return 0
        elif args.subcmd == "telemetry":
            tracer = TelemetryTracer()
            emit_result(tracer.record_span(args.name, 12.0, "SUCCESS"))
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
