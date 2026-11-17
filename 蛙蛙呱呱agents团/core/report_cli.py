# -*- coding: utf-8 -*-
"""report CLI —— 唯一产线入口（2026-11-15 收敛后）。

    意图 → R01 路由（A 单角色 / B 跨角色）→ 收集 result → R01 解读
         → core/report_renderer 渲染 → 一份报告 + manifest

命令只有三个：
    report run     跑产线，出一份报告
    report check   验一份成品报告（结论带数、数字有源、边界、禁用词）
    report charts  48 型图表能力盘点（能力自检，不产报告）

历史入口（build/audit/dispatch/seal/diff/one/project/analysis/blueprint/
modules/write）已于 2026-11-15 删除；旧产物归档在 workspace/_archive/。
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


def cmd_research(args) -> int:
    """新业务研究：quote 回抓校验 → r05 台账 → market_entry 报告。"""
    from core import research_intake
    try:
        res = research_intake.run(
            topic=args.topic, project=args.dir, out_dir=args.out,
            thesis=args.thesis, theme=args.theme, pdf=args.pdf,
            skip_verify=args.skip_verify, skip_ledger=args.skip_ledger)
    except Exception as e:  # noqa: BLE001  研究失败要可见
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_run(args) -> int:
    from core import report_flow
    draft = None
    if args.draft:
        draft = json.loads(Path(args.draft).read_text(encoding="utf-8-sig"))
    try:
        res = report_flow.run(
            intent=args.intent, results=args.results, out_dir=args.out,
            roles=[x.strip() for x in (args.roles or "").split(",") if x.strip()] or None,
            draft=draft, theme=args.theme, pdf=args.pdf, md_name=args.md_name,
            evidence=args.evidence, quote_mode=args.quote_mode)
    except report_flow.FlowError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 1


def cmd_produce(args) -> int:
    """v3/v4：画像 → 章节计划 → 技能调度 → 证据图 → 报告 → 评测。

    两种模式：
      --profile market_research        旧的固定画像（保留兼容）
      --intent "…"（不传 profile）      v4 自动纲领：按数据能力选题，再跑方法库
    """
    if args.intent or args.profile in (None, "", "auto"):
        from core import report_compose
        try:
            res = report_compose.build(
                intent=args.intent or "经营分析", project_dir=args.dir,
                out_dir=args.out, thesis=args.thesis, theme=args.theme,
                pdf=args.pdf, audience=getattr(args, "audience", "业务负责人"),
                require_contract=bool(getattr(args, "require_contract", False)),
                quote_mode=getattr(args, "quote_mode", "warn"))
        except Exception as e:  # noqa: BLE001  产线失败要可见
            print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                             ensure_ascii=False))
            return 2
        print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
        return 0 if res.get("ok") else 1
    from core import report_produce
    try:
        res = report_produce.produce(
            profile=args.profile, project_dir=args.dir, out_dir=args.out,
            draft_path=args.draft, theme=args.theme, pdf=args.pdf)
    except Exception as e:  # noqa: BLE001  产线失败要可见
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
    return 0 if res.get("ok") else 1


def cmd_pack(args) -> int:
    """把项目目录里的 JSON/CSV 收成证据包 + 写作简报。"""
    from core import evidence_pack
    try:
        pack = evidence_pack.build(args.dir)
    except FileNotFoundError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 2
    files = evidence_pack.write(pack, args.out)
    print(json.dumps({"ok": True, "counts": pack["counts"], **files},
                     ensure_ascii=False))
    return 0


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


def main(argv=None) -> int:
    from core.report_flow import THEMES, DEFAULT_THEME
    from core import report_thesis as _thesis
    ap = argparse.ArgumentParser(prog="guagua report",
                                 description="唯一报告产线：R01 出具，角色只交 result")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="跑产线，出一份报告")
    r.add_argument("--intent", required=True)
    r.add_argument("--results", nargs="*", default=[],
                   help="执行角色的 result JSON（文件或目录）；空则报错，不接受空报告")
    r.add_argument("--roles", default="", help="显式指定参与角色，逗号分隔（复现时用）")
    r.add_argument("--out", required=True)
    r.add_argument("--draft", default=None, help="判断稿（模型/人写），传入则只校验不代写")
    r.add_argument("--evidence", default=None,
                   help="证据包（report pack 产物）；与 --draft 的 sections 一起用")
    r.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    r.add_argument("--md-name", default="report")
    r.add_argument("--pdf", action="store_true")
    r.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="warn",
                   help="数据 intake：quote 回抓校验模式")
    r.set_defaults(func=cmd_run)

    pk = sub.add_parser("pack", help="证据打包：项目目录 → evidence_pack.json + brief.md")
    pk.add_argument("--dir", required=True, help="项目目录（含 data/、gates/ 等）")
    pk.add_argument("--out", required=True)
    pk.set_defaults(func=cmd_pack)

    pr = sub.add_parser("produce",
                        help="画像/纲领 → 分析方法 → 章节稿 → 报告 → 评测")
    pr.add_argument("--profile", default=None,
                    help="market_research / business_review；留空则按 --intent 自动选纲领")
    pr.add_argument("--intent", default=None,
                    help="v4 自动纲领的意图（不传 --profile 时生效）")
    pr.add_argument("--thesis", default=None, choices=list(_thesis.THESES),
                    help="强制纲领；可选值以 core/report_thesis.THESES 为准")
    pr.add_argument("--dir", required=True, help="项目目录")
    pr.add_argument("--out", required=True)
    pr.add_argument("--draft", default=None, help="可选：覆盖自动章节稿")
    pr.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    pr.add_argument("--pdf", action="store_true")
    pr.add_argument("--audience", default="业务负责人",
                    help="开工前契约：这份报告给谁看（写进 report_ship.json）")
    pr.add_argument("--require-contract", action="store_true",
                    help="契约不成立就中止，不出报告（默认只记录不拦截）")
    pr.add_argument("--quote-mode", choices=("off", "warn", "strict"), default="warn",
                    help="数据 intake：quote 回抓校验模式")
    pr.set_defaults(func=cmd_produce)

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

    rs = sub.add_parser("research", help="新业务研究：quote 回抓校验 + r05 台账 + 可行性报告")
    rs.add_argument("--topic", required=True)
    rs.add_argument("--dir", required=True, help="研究项目目录（含 data/sources.json）")
    rs.add_argument("--out", required=True)
    rs.add_argument("--thesis", default="market_entry")
    rs.add_argument("--theme", choices=list(THEMES), default=DEFAULT_THEME)
    rs.add_argument("--pdf", action="store_true")
    rs.add_argument("--skip-verify", action="store_true")
    rs.add_argument("--skip-ledger", action="store_true")
    rs.set_defaults(func=cmd_research)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
