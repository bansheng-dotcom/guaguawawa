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
    """P4 唯一入口：问题树 → coverage → v9 → 报告。"""
    from core import report_build
    try:
        res = report_build.build(
            intent=args.intent, project_dir=args.dir, out_dir=args.out,
            lens=args.lens, quote_mode=args.quote_mode,
            min_coverage=args.min_coverage, theme=args.theme,
            pdf=args.pdf, audience=args.audience,
            record_outcomes=getattr(args, "record_outcomes", False),
            outcome_deadline=getattr(args, "outcome_deadline", None))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def _deprecated(name: str) -> None:
    print(f"[deprecated] report {name} 已下线；请用 report build（v10）",
          file=sys.stderr)


def cmd_produce_alias(args) -> int:
    """兼容别名：produce --thesis → build --lens。"""
    from core import report_build, report_thesis
    _deprecated("produce")
    lens = report_thesis.LEGACY_LENS.get(args.thesis or "", None)
    res = report_build.build(
        intent=args.intent or "经营分析", project_dir=args.dir, out_dir=args.out,
        lens=lens, quote_mode=args.quote_mode, theme=args.theme, pdf=args.pdf,
        audience=getattr(args, "audience", "业务负责人"))
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_pack_alias(args) -> int:
    """兼容别名：pack 仍产出证据包 + brief。"""
    from core import evidence_pack
    _deprecated("pack")
    try:
        pack = evidence_pack.build(args.dir)
    except FileNotFoundError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2
    files = evidence_pack.write(pack, args.out)
    print(json.dumps({"ok": True, "counts": pack["counts"], **files},
                     ensure_ascii=False))
    return 0


def cmd_research_alias(args) -> int:
    """兼容别名：research → build --lens market。"""
    from core import report_build
    _deprecated("research")
    res = report_build.build(
        intent=args.topic, project_dir=args.dir, out_dir=args.out,
        lens="market", quote_mode="warn", theme=args.theme, pdf=args.pdf)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_run_alias(args) -> int:
    """兼容别名：run 只在显式给 evidence+draft 时可用。"""
    from core import report_flow
    _deprecated("run")
    if not (args.evidence and args.draft):
        print(json.dumps({"ok": False,
                          "error": "run 已下线；请用 report build --intent … --dir … --out …"},
                         ensure_ascii=False))
        return 2
    draft = json.loads(Path(args.draft).read_text(encoding="utf-8-sig"))
    res = report_flow.run(intent=args.intent, out_dir=args.out, draft=draft,
                          evidence=args.evidence, theme=args.theme,
                          pdf=args.pdf, quote_mode=args.quote_mode)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res.get("ok") else 1


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
    from core import report_thesis as _thesis
    ap = argparse.ArgumentParser(prog="guagua report",
                                 description="唯一报告产线：R01 出具，角色只交 result")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build",
                       help="P4 唯一入口：问题树 → coverage → v9 → 报告")
    b.add_argument("--intent", required=True)
    b.add_argument("--dir", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--lens", choices=("market", "ops", "chain", "fix"), default=None)
    b.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="strict")
    b.add_argument("--min-coverage", type=float, default=0.8)
    b.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    b.add_argument("--pdf", action="store_true")
    b.add_argument("--audience", default="业务负责人")
    b.add_argument("--record-outcomes", action="store_true",
                   help="把 findings 登记进结果台账（默认 90 天到期）")
    b.add_argument("--outcome-deadline", default=None, help="YYYY-MM-DD；默认 +90 天")
    b.set_defaults(func=cmd_build)

    # P9：兼容别名（隐藏）。至少保留一个版本，旧脚本不炸。
    pr = sub.add_parser("produce", help="[deprecated] produce → build")
    pr.add_argument("--intent", default=None)
    pr.add_argument("--profile", default=None)
    pr.add_argument("--dir", required=True)
    pr.add_argument("--out", required=True)
    pr.add_argument("--thesis", default=None,
                    choices=list(_thesis.THESES) + list(_thesis.LEGACY_LENS))
    pr.add_argument("--draft", default=None)
    pr.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    pr.add_argument("--pdf", action="store_true")
    pr.add_argument("--audience", default="业务负责人")
    pr.add_argument("--require-contract", action="store_true")
    pr.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="warn")
    pr.set_defaults(func=cmd_produce_alias)

    pk = sub.add_parser("pack", help="[deprecated] pack → 证据包")
    pk.add_argument("--dir", required=True)
    pk.add_argument("--out", required=True)
    pk.set_defaults(func=cmd_pack_alias)

    rs = sub.add_parser("research", help="[deprecated] research → build --lens market")
    rs.add_argument("--topic", required=True)
    rs.add_argument("--dir", required=True)
    rs.add_argument("--out", required=True)
    rs.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    rs.add_argument("--pdf", action="store_true")
    rs.set_defaults(func=cmd_research_alias)

    r = sub.add_parser("run", help="[deprecated] run 仅兼容 evidence+draft")
    r.add_argument("--intent", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--evidence", default=None)
    r.add_argument("--draft", default=None)
    r.add_argument("--results", nargs="*", default=[])
    r.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    r.add_argument("--pdf", action="store_true")
    r.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="warn")
    r.set_defaults(func=cmd_run_alias)

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

    g = sub.add_parser("gaps", help="看项目的 quote gap 清单（不产报告）")
    g.add_argument("--project", required=True)
    g.set_defaults(func=cmd_gaps)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
