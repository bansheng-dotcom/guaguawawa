# -*- coding: utf-8 -*-
"""S10 分析链（T8a）：frame → plan → profile → explore → explain → test。

这是 R06 从「统计工具箱」升级为「可审计分析链」的入口：
  - 每个阶段先过自己的确定性门禁，再交给下一段；
  - run 一次产出 6 个工件 + chain_manifest.json；
  - audit 可对已产出链做只读复核（哈希 + 门禁 + 跨段一致）。

角色边界不变：只交分析工件，不写报告（报告归 R01）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from . import _common as c

NAME = "chain"
DESC = "分析链：frame/plan/profile/explore/explain/test/run/audit"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)

    f = act.add_parser("frame", help="第1段：业务问题 → 3–5 个可证伪假设 + 决策用途")
    f.add_argument("--question", required=True, help="业务问题，如“9月利润为什么下滑”")
    f.add_argument("--decision-use", default="", help="这份分析要支持什么决策")
    f.add_argument("--metric", default="", help="指标列名，缺省按问题领域推断")
    f.add_argument("--dimensions", default="", help="逗号分隔的切分维度，如 channel,category")
    f.add_argument("--domain", default="", help="profit/revenue/churn/conversion/growth/generic")
    f.add_argument("--window", default="近90天")
    f.add_argument("--min-impact-pct", type=float, default=3.0)
    f.add_argument("--out", default=None, help="输出 frame.json 路径")

    pl = act.add_parser("plan", help="第2段：frame → 预注册分析计划（先计划后看数）")
    pl.add_argument("--frame", required=True)
    pl.add_argument("--before", required=True, help="窗口开始日 YYYY-MM-DD")
    pl.add_argument("--after", required=True, help="窗口结束日 YYYY-MM-DD")
    pl.add_argument("--split", required=True, help="前后期切分日（<=split 为前期）")
    pl.add_argument("--grain", default="day")
    pl.add_argument("--min-rows", type=int, default=30)
    pl.add_argument("--out", default=None)

    pr = act.add_parser("profile", help="第3段：六维数据质量 + 覆盖 + 偏差")
    pr.add_argument("--input", required=True, help="CSV 数据")
    pr.add_argument("--plan", required=True)
    pr.add_argument("--pk", default=None, help="主键列（去重口径）")
    pr.add_argument("--date", default="date")
    pr.add_argument("--semantic", default=None, help="语义模型 JSON（可选，做防幻觉联动）")
    pr.add_argument("--out", default=None)

    ex = act.add_parser("explore", help="第4段：按预注册分母/分段出发现（只描述不解释）")
    ex.add_argument("--input", required=True)
    ex.add_argument("--plan", required=True)
    ex.add_argument("--date", default="date")
    ex.add_argument("--stage", default=None, help="可选：漏斗阶段列")
    ex.add_argument("--stage-order", default=None, help="漏斗阶段顺序，逗号分隔")
    ex.add_argument("--qty", default=None, help="可选：数量列（供后续量价拆解）")
    ex.add_argument("--cost", default=None, help="可选：成本列（供单位经济）")
    ex.add_argument("--out", default=None)

    ep = act.add_parser("explain", help="第5段：贡献拆解 + 驱动树 + 替代解释 + 反事实")
    ep.add_argument("--input", required=True, help="CSV 数据")
    ep.add_argument("--plan", required=True)
    ep.add_argument("--findings", required=True)
    ep.add_argument("--dim", default=None, help="主拆解维度，缺省取计划第一个维度")
    ep.add_argument("--qty", default=None, help="数量列（拆量价效应）")
    ep.add_argument("--date", default="date")
    ep.add_argument("--out", default=None)

    ts = act.add_parser("test", help="第6段：效应量 + CI + 检验 + 敏感性 + Holm")
    ts.add_argument("--input", required=True)
    ts.add_argument("--plan", required=True)
    ts.add_argument("--findings", required=True)
    ts.add_argument("--date", default="date")
    ts.add_argument("--seed", type=int, default=0)
    ts.add_argument("--min-n", type=int, default=30)
    ts.add_argument("--out", default=None)

    rn = act.add_parser("run", help="一条命令跑完 6 段，产出 6 工件 + chain_manifest")
    rn.add_argument("--question", required=True)
    rn.add_argument("--input", required=True, help="CSV 数据")
    rn.add_argument("--out-dir", default=None)
    rn.add_argument("--before", required=True)
    rn.add_argument("--after", required=True)
    rn.add_argument("--split", required=True)
    rn.add_argument("--decision-use", default="")
    rn.add_argument("--metric", default="")
    rn.add_argument("--dimensions", default="")
    rn.add_argument("--domain", default="")
    rn.add_argument("--date", default="date")
    rn.add_argument("--qty", default=None)
    rn.add_argument("--cost", default=None)
    rn.add_argument("--stage", default=None)
    rn.add_argument("--stage-order", default=None)
    rn.add_argument("--semantic", default=None)
    rn.add_argument("--pk", default=None)
    rn.add_argument("--seed", type=int, default=0)
    rn.add_argument("--min-n", type=int, default=30)
    rn.add_argument("--min-impact-pct", type=float, default=3.0)

    au = act.add_parser("audit", help="只读复核已产出的分析链（哈希/门禁/跨段一致）")
    au.add_argument("--dir", required=True, help="run 的输出目录")

    vf = act.add_parser("verify", help="第7段：CoV 六问 + 回流码 + bounded modules")
    vf.add_argument("--dir", required=True, help="T8a 链条目录")

    ch = act.add_parser("chart", help="第8段：claim-bound 图表规格包 + fail_if_missing")
    ch.add_argument("--dir", required=True, help="T8a 链条目录")

    wr = act.add_parser("write", help="第9段：unit packet → 文字包 → 对抗评审")
    wr.add_argument("--dir", required=True, help="T8a 链条目录")

    dv = act.add_parser("deliver", help="第10段：文图仲裁 + report.html + manifest + 事件")
    dv.add_argument("--dir", required=True, help="T8a 链条目录")
    dv.add_argument("--out-dir", default=None, help="报告输出目录（默认 <dir>/report）")

    rp = act.add_parser("report", help="一条命令跑完 T8a+T8b，产出报告草稿与运行账本")
    rp.add_argument("--question", required=True)
    rp.add_argument("--input", required=True, help="CSV 数据")
    rp.add_argument("--out-dir", default=None)
    rp.add_argument("--before", required=True)
    rp.add_argument("--after", required=True)
    rp.add_argument("--split", required=True)
    rp.add_argument("--decision-use", default="")
    rp.add_argument("--metric", default="")
    rp.add_argument("--dimensions", default="")
    rp.add_argument("--domain", default="")
    rp.add_argument("--date", default="date")
    rp.add_argument("--qty", default=None)
    rp.add_argument("--cost", default=None)
    rp.add_argument("--stage", default=None)
    rp.add_argument("--stage-order", default=None)
    rp.add_argument("--semantic", default=None)
    rp.add_argument("--pk", default=None)
    rp.add_argument("--seed", type=int, default=0)
    rp.add_argument("--min-n", type=int, default=30)
    rp.add_argument("--min-impact-pct", type=float, default=3.0)


def _out_dir() -> str:
    try:
        from core.base.workspace import role_workspace
        base = role_workspace(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:  # noqa: BLE001
        base = os.path.join(os.getcwd(), "workspace")
    d = os.path.join(base, "artifacts", "chain")
    os.makedirs(d, exist_ok=True)
    return d


def _out(args, name: str) -> str:
    return getattr(args, "out", None) or os.path.join(_out_dir(), name)


def _dims(s: str) -> Optional[List[str]]:
    vals = [x.strip() for x in (s or "").split(",") if x.strip()]
    return vals or None


def _emit(artifact: Dict[str, Any], path: str) -> Dict[str, Any]:
    g = artifact.get("gate") or {}
    return {"ok": bool(g.get("ok")), "artifact": artifact.get("artifact"),
            "artifact_path": path, "grade": g.get("grade"),
            "gate": g, "data": artifact}


def run(args) -> Dict[str, Any]:
    from analysis_chain import common, runner

    if args.action == "frame":
        art = frame_build(args)
        path = _out(args, "frame.json")
        c.write_json(path, art)
        return _emit(art, path)
    if args.action == "plan":
        from analysis_chain import plan as plan_mod
        fr = common.load_gate_artifact(args.frame, "frame")
        if "_error" in fr:
            return _err(fr["_error"])
        try:
            art = plan_mod.build(fr, args.before, args.after, args.split,
                                 grain=args.grain, min_rows=args.min_rows)
        except ValueError as exc:
            return _err(str(exc))
        path = _out(args, "analysis_plan.json")
        c.write_json(path, art)
        return _emit(art, path)
    if args.action == "profile":
        from analysis_chain import profile as profile_mod
        pl = common.load_gate_artifact(args.plan, "plan")
        if "_error" in pl:
            return _err(pl["_error"])
        sem = c.load_json(args.semantic) if args.semantic and os.path.exists(args.semantic) else None
        art = profile_mod.profile(args.input, pl, pk=args.pk, date=args.date, semantic=sem)
        path = _out(args, "data_profile.json")
        c.write_json(path, art)
        return _emit(art, path)
    if args.action == "explore":
        from analysis_chain import explore as explore_mod
        pl = common.load_gate_artifact(args.plan, "plan")
        if "_error" in pl:
            return _err(pl["_error"])
        art = explore_mod.build(args.input, pl, date=args.date, stage=args.stage,
                                stage_order=args.stage_order, qty=args.qty, cost=args.cost)
        path = _out(args, "findings.json")
        c.write_json(path, art)
        return _emit(art, path)
    if args.action == "explain":
        from analysis_chain import explain as explain_mod
        pl = common.load_gate_artifact(args.plan, "plan")
        fd = common.load_gate_artifact(args.findings, "findings")
        if "_error" in pl:
            return _err(pl["_error"])
        if "_error" in fd:
            return _err(fd["_error"])
        art = explain_mod.build(args.input, pl, fd, dim=args.dim, qty=args.qty, date=args.date)
        path = _out(args, "explanation.json")
        c.write_json(path, art)
        return _emit(art, path)
    if args.action == "test":
        from analysis_chain import stats_test as stats_mod
        pl = common.load_gate_artifact(args.plan, "plan")
        fd = common.load_gate_artifact(args.findings, "findings")
        if "_error" in pl:
            return _err(pl["_error"])
        if "_error" in fd:
            return _err(fd["_error"])
        art = stats_mod.build(args.input, pl, fd, date=args.date, seed=args.seed, min_n=args.min_n)
        path = _out(args, "stats.json")
        c.write_json(path, art)
        return _emit(art, path)
    if args.action == "run":
        out_dir = args.out_dir or os.path.join(_out_dir(), "run")
        manifest = runner.run(
            args.question, args.input, out_dir, args.before, args.after, args.split,
            decision_use=args.decision_use, metric=args.metric,
            dimensions=_dims(args.dimensions), domain=args.domain or None,
            date=args.date, qty=args.qty, cost=args.cost, stage=args.stage,
            stage_order=args.stage_order, semantic_path=args.semantic, pk=args.pk,
            seed=args.seed, min_n=args.min_n, min_impact_pct=args.min_impact_pct)
        return _emit(manifest, os.path.join(out_dir, "chain_manifest.json"))
    if args.action == "verify":
        from analysis_chain import report_runner
        art = report_runner.stage_verify(args.dir)
        path = os.path.join(args.dir, "verification.json")
        return _emit(art, path)
    if args.action == "chart":
        from analysis_chain import report_runner
        art = report_runner.stage_chart(args.dir)
        path = os.path.join(args.dir, "chart_spec_pack.json")
        return _emit(art, path)
    if args.action == "write":
        from analysis_chain import report_runner
        art = report_runner.stage_write(args.dir)
        path = os.path.join(args.dir, "report_text_pack.json")
        return _emit(art, path)
    if args.action == "deliver":
        from analysis_chain import report_runner
        art = report_runner.stage_deliver(args.dir, args.out_dir)
        path = art.get("report_html") or os.path.join(args.dir, "report", "report.html")
        return _emit(art, path)
    if args.action == "report":
        from analysis_chain import report_runner
        out_dir = args.out_dir or os.path.join(_out_dir(), "report_case")
        art = report_runner.run_all(
            args.question, args.input, out_dir, args.before, args.after, args.split,
            decision_use=args.decision_use, metric=args.metric,
            dimensions=_dims(args.dimensions), domain=args.domain or None,
            date=args.date, qty=args.qty, cost=args.cost, stage=args.stage,
            stage_order=args.stage_order, semantic_path=args.semantic, pk=args.pk,
            seed=args.seed, min_n=args.min_n, min_impact_pct=args.min_impact_pct)
        path = art.get("report_html") or os.path.join(out_dir, "report", "report.html")
        return _emit(art, path)
    if args.action == "audit":
        return audit(args.dir)
    return _err(f"未知动作: {args.action}")


def frame_build(args) -> Dict[str, Any]:
    from analysis_chain import frame as frame_mod
    return frame_mod.build(args.question, decision_use=args.decision_use,
                           metric=args.metric, dimensions=_dims(args.dimensions),
                           domain=args.domain or None, window=args.window,
                           min_impact_pct=args.min_impact_pct)


def audit(dir_path: str) -> Dict[str, Any]:
    """只读复核：文件齐全、哈希一致、门禁 PASS、跨段一致。"""
    from analysis_chain import common
    from analysis_chain.runner import FILES

    checks = []
    manifest_path = os.path.join(dir_path, "chain_manifest.json")
    if not os.path.exists(manifest_path):
        return {"ok": False, "errors": [f"缺少 {manifest_path}"], "stages": []}
    manifest = c.load_json(manifest_path)
    for item in manifest.get("stages", []):
        p = os.path.join(dir_path, item.get("file", ""))
        checks.append(common.ck(os.path.exists(p), f"{item.get('stage')} 文件存在",
                                "existence", "CRITICAL" if not os.path.exists(p) else "OK"))
        if os.path.exists(p):
            checks.append(common.ck(common.sha256_file(p) == item.get("sha256"),
                                    f"{item.get('stage')} 哈希一致", "integrity",
                                    "CRITICAL" if common.sha256_file(p) != item.get("sha256") else "OK"))
    expected = {stage for stage in FILES}
    got = {item.get("stage") for item in manifest.get("stages", [])}
    checks.append(common.ck(expected <= got, f"阶段齐全 {sorted(got)}", "structure",
                            "CRITICAL" if not expected <= got else "OK"))
    checks.append(common.ck(bool(manifest.get("ok")), "manifest 判定为 PASS", "gate",
                            "CRITICAL" if not manifest.get("ok") else "OK"))
    g = common.gate(checks, "audit")
    return {"ok": g["ok"], "grade": g["grade"], "stage": "audit",
            "stages": manifest.get("stages", []), "gate": g,
            "errors": g["errors"], "artifact": "chain_audit"}


def _err(msg: str) -> Dict[str, Any]:
    return {"ok": False, "error": msg, "grade": "FAIL",
            "gate": {"ok": False, "grade": "FAIL", "errors": [msg]}}
