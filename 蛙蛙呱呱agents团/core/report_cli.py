# -*- coding: utf-8 -*-
"""report CLI —— 唯一报告产线入口（v10）。

主入口：
    report build   问题树 → coverage → v9 → 报告（唯一出报告入口）
    report check   验一份成品报告
    report gaps    看项目的 quote 缺口
    report charts  48 型图表能力盘点
    report capabilities / plan  诊断

兼容别名（P9，至少保留一个版本）：
    run / pack / produce / research → 打印 deprecation 后转到 build 或旧原子能力。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def cmd_capabilities(args) -> int:
    """角色适配层：20 角色 / 195 技能，哪些能进报告、输出什么 claim。"""
    from core import report_roles
    if getattr(args, "graph", False) or getattr(args, "graph_write", None):
        from core import capability_graph
        g = capability_graph.build()
        if getattr(args, "graph_write", None):
            p = capability_graph.write(args.graph_write)
            print(f"graph: {p}")
        if getattr(args, "graph", False):
            print(json.dumps(g["counts"], ensure_ascii=False, indent=1))
        return 0
    cat = report_roles.classify()
    if args.write:
        p = report_roles.write_catalog(cat)
        print(f"catalog: {p}")
    if args.json:
        print(json.dumps(cat, ensure_ascii=False, indent=1)[:12000])
        return 0
    c = cat["counts"]
    print(f"角色 {c['roles']} / 技能 {c['skills']} / 动作 {c['actions']}；"
          f"可进报告 {c['eligible_skills']} 技能 / {c['eligible_actions']} 动作")
    for r in report_roles.coverage_table(cat):
        print(f"  {r['role']} {r['name']:<4} 技能 {r['eligible']:>2}/{r['skills']:<2}"
              f" 动作 {r['eligible_actions']:>2}/{r['actions']:<2} "
              f"{'进报告' if r['enters'] else '不进报告'}")
    return 0


def cmd_plan(args) -> int:
    """只看挂载计划：这个方法会不会被数据挂上、缺哪个能力。"""
    from core import analysis_desk, analysis_methods, methods, report_thesis
    desk = analysis_desk.scan(args.dir)
    views = analysis_methods.build_views(desk)
    prof = analysis_desk.profile(desk)
    th = args.thesis or report_thesis.infer(args.intent or "分析", prof)
    p = methods.plan(desk, views, prof, th)
    p["inferred_thesis"] = th
    print(json.dumps(p, ensure_ascii=False, indent=1)[:12000])
    return 0


def cmd_build(args) -> int:
    """[deprecated] 兼容名：等同 decide。

    v11 起「按报告类型筛方法」的参数已彻底删除（不再是「忽略的参数」，是不存在的参数）。
    build 与 decide 都是 run-line 的过渡别名，P5 删除。
    """
    from core import decision_report
    try:
        res = decision_report.build(
            intent=args.intent, project_dir=args.dir, out_dir=args.out,
            decision_path=None, min_binding=0.8, theme=args.theme,
            pdf=args.pdf, quote_mode=args.quote_mode, audience=args.audience)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_decide(args) -> int:
    """决策优先：3–5 个必答问题 → 方法 → 逐问作答 → 图由对照选型。"""
    from core import decision_report
    try:
        res = decision_report.build(
            intent=args.intent, project_dir=args.dir, out_dir=args.out,
            decision_path=args.decision, min_binding=args.min_binding,
            theme=args.theme, pdf=args.pdf, quote_mode=args.quote_mode,
            audience=args.audience)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_plan_report(args) -> int:
    """一句话 → 专业研究方案（不产报告）：告诉 agent 该查什么、按什么等级收证据。"""
    from core import research_protocol
    p = research_protocol.plan(args.intent, project_dir=getattr(args, "dir", None),
                               has_files=bool(getattr(args, "dir", None)))
    out = getattr(args, "out", None)
    if out:
        from pathlib import Path
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "research_plan.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        (Path(out) / "research_brief.md").write_text(
            research_protocol.to_markdown(p), encoding="utf-8")
    print(json.dumps({"data_lane": p["data_lane"],
                      "what_to_research": p["what_to_research"],
                      "claim_fields": [c["field"] for c in p["claim_contract"]],
                      "report_parts": [s["part"] for s in p["report_shape"]],
                      "out": out or "(仅预览)"}, ensure_ascii=False, indent=1))
    return 0


def cmd_brief(args) -> int:
    """发任务卡：每个可进报告的角色一张，只带契约不带题目。"""
    from core import dispatch
    only = [x.strip() for x in (args.only or "").split(",") if x.strip()] or None
    res = dispatch.write_cards(args.intent, args.out, only)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


def cmd_collect(args) -> int:
    """收卡：验完整性 → 合并 → 编译 → 过闸 → 渲染。"""
    from core import dispatch
    merged, problems = dispatch.collect(args.dir)
    if problems:
        print(json.dumps({"ok": False, "problems": problems[:12]},
                         ensure_ascii=False, indent=1))
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    merged_path = out / "claims_merged.json"
    merged_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    args.claims = str(merged_path)
    args.dir = None
    args.evidence = None
    args.draft = None
    for attr, val in (("intent", "自动汇编报告"), ("audience", None),
                      ("theme", "paper"), ("quote_mode", "warn"),
                      ("min_binding", 0.8), ("input", None),
                      ("research", False)):
        if not hasattr(args, attr):
            setattr(args, attr, val)
    return cmd_run_line(args)


def cmd_run_line(args) -> int:
    """v11 唯一入口（P1：转发实现）：一条命令 + 四种输入。"""
    from core import report_line
    # v12：--claims 一步到位：编译（含交叉质询）→ 过闸 → 渲染。
    # 这样「智能体交一份 claims.json」就是完整交付动作，不用记两个命令。
    claims_path = getattr(args, "claims", None)
    if claims_path:
        import subprocess
        import sys as _sys
        from pathlib import Path as _P
        comp = _P(__file__).resolve().parent.parent / "scripts" / "compile_agent_report.py"
        proc = subprocess.run([_sys.executable, str(comp), str(claims_path),
                               "--out", str(_P(args.out) / "_compiled")],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            print((proc.stdout or proc.stderr or "").strip() or f"compile rc={proc.returncode}")
            return proc.returncode
        args.evidence = str(_P(args.out) / "_compiled" / "evidence_pack.json")
        args.draft = str(_P(args.out) / "_compiled" / "draft_sections.json")
    try:
        res = report_line.build(
            intent=args.intent, project_dir=args.dir, out_dir=args.out,
            input_path=getattr(args, "input", None),
            research=getattr(args, "research", False),
            audience=args.audience, theme=args.theme, pdf=args.pdf,
            quote_mode=args.quote_mode, min_binding=args.min_binding,
            evidence_path=getattr(args, "evidence", None),
            draft_path=getattr(args, "draft", None))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def _deprecated(name: str) -> None:
    print(f"[deprecated] report {name} 已下线；请用 report run-line（v11）",
          file=sys.stderr)


def cmd_check(args) -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_report_flow import check_html
    r = check_html(args.html)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["ok"] else 1


def cmd_charts(args) -> int:
    from core.chart_capabilities import check, CATALOG
    r = check()
    print(json.dumps({"ok": r["ok"], "count": r["count"], "items": CATALOG},
                     ensure_ascii=False) if args.json
          else f"图表能力：{r['count']}/48，渲染器 {r['renderers']}/48，ok={r['ok']}")
    return 0 if r["ok"] else 1


def cmd_gaps(args) -> int:
    """看项目的 quote gap 清单（诊断，不产报告）。"""
    p = Path(args.project) / "data" / "quote_gaps.json"
    if not p.exists():
        print(json.dumps({"ok": False, "error": f"没有 {p}"}, ensure_ascii=False))
        return 2
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    print(json.dumps(data, ensure_ascii=False, indent=2)[:12000])
    return 0 if int(data.get("unverified") or 0) == 0 else 1


def main(argv=None) -> int:
    from core.report_flow import THEMES, DEFAULT_THEME
    ap = argparse.ArgumentParser(prog="guagua report",
                                 description="唯一报告产线：一条命令 + 四种输入（v11）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rl = sub.add_parser("run-line", help="v11 唯一入口（P1 转发）：一条命令 + 四种输入")
    rl.add_argument("--intent", required=True, help="你的指令/问题")
    rl.add_argument("--dir", default=None, help="数据项目目录（数据型）")
    rl.add_argument("--input", default=None, help="单份文档（评审型，P2 接入）")
    rl.add_argument("--research", action="store_true", help="联网采集型（P2/P3 接入）")
    rl.add_argument("--out", required=True)
    rl.add_argument("--audience", default="业务负责人")
    rl.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    rl.add_argument("--pdf", action="store_true")
    rl.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="off")
    rl.add_argument("--min-binding", type=float, default=0.8)
    rl.add_argument("--evidence", default=None, help="证据包 JSON（智能体写稿路径）")
    rl.add_argument("--draft", default=None, help="章节稿 JSON（智能体写稿路径）")
    rl.add_argument("--claims", default=None,
                    help="claims.json：一步完成 编译+交叉质询+过闸+渲染")
    rl.add_argument("--decision", default=None,
                    help="决策契约 JSON；缺省读 <dir>/data/decision.json，再缺省按出场专家起草")
    rl.set_defaults(func=cmd_run_line)

    # v11 / P5：build / decide / produce / pack / research / run 六个名字全部删除。
    # 唯一入口 = `report "指令" --dir … --out …`（也接受 `report run-line …` 写法）。

    c = sub.add_parser("check", help="验一份成品报告")
    c.add_argument("--html", required=True)
    c.set_defaults(func=cmd_check)

    ch = sub.add_parser("charts", help="48 型图表能力盘点")
    ch.add_argument("--json", action="store_true")
    ch.set_defaults(func=cmd_charts)

    cp = sub.add_parser("capabilities", help="角色适配层：20 角色 / 195 技能的入报资格与 claim")
    cp.add_argument("--json", action="store_true")
    cp.add_argument("--write", action="store_true", help="写 configs/report_capabilities.json")
    cp.add_argument("--graph", action="store_true", help="角色 × 问题 × 能力 × 状态图")
    cp.add_argument("--graph-write", default=None, help="把能力图写到指定 JSON")
    cp.set_defaults(func=cmd_capabilities)

    pl = sub.add_parser("plan", help="只看方法挂载计划（不执行、不出报告）")
    pl.add_argument("--dir", required=True)
    pl.add_argument("--intent", default=None)
    pl.add_argument("--thesis", default=None,
                    help="research / operations / remediation / chain / forecast / growth / "
                         "product / support / people / sre / marketing / sku / store")
    pl.set_defaults(func=cmd_plan)

    # v12：一句话 → 专业研究方案。这一步替代「让用户自己定义研究问题」。
    rp = sub.add_parser("research-plan",
                        help="一句话 → 专业研究方案（8 个模块 / 专家 / 数据通道），不产报告")
    rp.add_argument("--intent", required=True)
    rp.add_argument("--dir", default=None, help="已给数据目录则 data_lane=given")
    rp.add_argument("--out", default=None)
    rp.set_defaults(func=cmd_plan_report)

    g = sub.add_parser("gaps", help="看项目的 quote gap 清单（不产报告）")
    g.add_argument("--project", required=True)
    g.set_defaults(func=cmd_gaps)

    bf = sub.add_parser("brief", help="按名册发任务卡（不产报告）")
    bf.add_argument("--intent", required=True)
    bf.add_argument("--out", required=True)
    bf.add_argument("--only", default=None, help="只发给这些角色，逗号分隔")
    bf.set_defaults(func=cmd_brief)

    cl = sub.add_parser("collect", help="收各角色 claims → 合并 → 过闸 → 出报告")
    cl.add_argument("--dir", required=True)
    cl.add_argument("--out", required=True)
    cl.add_argument("--pdf", action="store_true")
    cl.set_defaults(func=cmd_collect)

    argv = list(sys.argv[1:] if argv is None else argv)
    # v11 唯一入口：`report "指令" --dir …` 等价于 `report run-line --intent "指令" …`
    # 判断依据是「第一个 token 不是已注册子命令」——这样不用记子命令名。
    known = {"run-line", "check", "charts", "capabilities", "plan", "gaps",
             "research-plan", "brief", "collect", "-h", "--help"}
    if argv and argv[0] not in known:
        rest = argv
        argv = ["run-line", "--intent", rest[0], *rest[1:]]

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
