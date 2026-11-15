# -*- coding: utf-8 -*-
"""report CLI：L1×N → L2 → L3 的端到端构建。

用法（经 guagua.py 转发）：
  python guagua.py report build --project demo_2026q4
  python guagua.py report audit --project demo_2026q4
  python guagua.py report seal  --project demo_2026q4 --by 张三
  python guagua.py report one --role r07 --result r.json --input in.json \
      --skill prd --action prd --out workspace/out     # 默认 core
  python guagua.py report one ... --path single        # 明确要旧路径才用
  python guagua.py report project --dir <项目目录>      # 项目级单份报告（contract → core）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import report_bridge, report_renderer  # noqa: E402
from core.report_kernel import aggregate, guard, layers, spec as kspec  # noqa: E402
from core.report_kernel.structure import writing_errors  # noqa: E402

PROJECTS = ROOT / "projects"
CACHE = ROOT / ".cache" / "report_contracts"


def _load_inputs(pid: str) -> list[dict]:
    d = PROJECTS / pid / "inputs"
    out = []
    for p in sorted(d.glob("*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def cmd_build(args) -> int:
    pid = args.project
    pdir = PROJECTS / pid
    inputs = _load_inputs(pid)
    if not inputs:
        print(f"没有输入: {pdir/'inputs'}")
        return 1

    cache = guard.ContractCache(CACHE)
    items, spec_errors = [], {}
    outdir = pdir / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    for item in inputs:
        role = item["role"]
        res = item.get("result", {})
        ds = item.get("dataset")
        s = kspec.load(role)
        key = cache.key(role, res, ds, s)
        hit = cache.get(key)
        if hit:
            contract, fid = hit["contract"], hit["fid"]
        else:
            contract, fid = layers.build_contract(
                role, item.get("name", role), item.get("title", "任务"),
                res, s, item.get("skill", ""), item.get("action", ""), item.get("intent", ""),
                dataset=ds)
            cache.put(key, {"contract": contract, "fid": fid})
        if getattr(args, "theme", None):
            contract["theme"] = args.theme

        errs = layers.spec_compliance(contract, s)
        spec_errors[role] = errs
        items.append({"role": role, "title": item.get("title", role),
                      "contract": contract, "fid": fid, "spec_errors": errs})

        html_p = outdir / f"{role}_report.html"
        md_p = outdir / f"{role}_report.md"
        report_renderer.render(contract) if False else None
        report_bridge.render_html(contract, str(html_p))
        report_bridge.write_markdown(contract, str(md_p))
        print(f"  L1 {role}: sections={len(contract['sections'])} "
              f"retention={fid.get('retention')} spec_errs={len(errs)}")

    l2 = aggregate.build_l2(pid, items)
    report_bridge.render_html(l2, str(outdir / "L2_report.html"))
    report_bridge.write_markdown(l2, str(outdir / "L2_report.md"))
    print("  L2 汇总完成")

    l3 = aggregate.build_l3(pid, l2, spec_errors)
    report_bridge.render_html(l3, str(outdir / "L3_review.html"))
    report_bridge.write_markdown(l3, str(outdir / "L3_review.md"))
    print("  L3 评审完成")

    man = {
        "project": pid,
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "l1": [{"role": i["role"], "fid": i["fid"], "spec_errors": i["spec_errors"]} for i in items],
        "cache": cache.stats(),
        "l2_hash": _hash(json.dumps(l2, ensure_ascii=False, sort_keys=True)),
        "l3_hash": _hash(json.dumps(l3, ensure_ascii=False, sort_keys=True)),
    }
    (pdir / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    # 出厂自检：新项目默认必须过版式检查
    from scripts.check_report_layout import check_html
    bad = []
    for h in sorted(outdir.glob("*.html")):
        r = check_html(h)
        if not r["ok"]:
            bad.append((h.name, r["violations"]))
    if bad:
        print("版式自检不通过：")
        for name, vs in bad:
            print(f"  - {name}: {'；'.join(vs)}")
    else:
        print("版式自检：PASS（末节口径与分数 / 附录折叠 / 无重复章节）")

    # 写作自检：格式对但内容空（R5 指标带业务化 / R6 每节带数字判断 / R7 结论带数字）
    wbad = []
    for it in items:
        werrs = writing_errors(it["contract"])
        if werrs:
            wbad.append((it["role"], werrs))
    if wbad:
        print("写作自检（不阻断，待各角色 specialist 就位后转硬门禁）：")
        for role, errs in wbad:
            print(f"  - {role}: {len(errs)} 项 → {errs[0]}")
    else:
        print("写作自检：PASS（指标带无执行元数据 / 每节带数字判断 / 结论带数字）")

    print(json.dumps({"l1": len(items), "cache": man["cache"],
                      "spec_fail": sum(1 for v in spec_errors.values() if v)}, ensure_ascii=False))
    return 0


def cmd_dispatch(args) -> int:
    """由真实任务卡触发：dispatch → 收结果 → L1 → L2 → L3。"""
    import subprocess
    ids = [x.strip() for x in args.tasks.split(",") if x.strip()]
    for tid in ids:
        subprocess.run([sys.executable, "guagua.py", "dispatch", "--task", tid],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"  dispatched {tid}")

    jl = ROOT / "workspace" / "artifacts" / "r01" / "dispatch_results.jsonl"
    lines = []
    if jl.exists():
        lines = [json.loads(x) for x in jl.read_text(encoding="utf-8").splitlines() if x.strip()]
    picked = {}
    for rec in lines:
        if rec["task_id"] in ids:
            picked[rec["task_id"]] = rec
    if not picked:
        print("没有拿到任务结果（角色未输出 __AGENT_RESULT__）")
        return 1

    pdir = PROJECTS / args.project
    outdir = pdir / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    items, spec_errors = [], {}
    for tid, rec in picked.items():
        role = rec["owner"]
        s = kspec.load(role)
        contract, fid = layers.build_contract(
            role, role, f"任务 {tid}", rec["result"], s, "task", tid, f"任务卡 {tid}")
        errs = layers.spec_compliance(contract, s)
        spec_errors[role] = errs
        items.append({"role": role, "title": f"任务 {tid}", "contract": contract,
                      "fid": fid, "spec_errors": errs})
        report_bridge.render_html(contract, str(outdir / f"{role}_{tid}.html"))
        print(f"  L1 {role} ({tid}) sections={len(contract['sections'])} spec_errs={len(errs)}")

    l2 = aggregate.build_l2(args.project, items)
    report_bridge.render_html(l2, str(outdir / "L2_report.html"))
    l3 = aggregate.build_l3(args.project, l2, spec_errors)
    report_bridge.render_html(l3, str(outdir / "L3_review.html"))
    print(json.dumps({"tasks": len(items), "spec_fail": sum(1 for v in spec_errors.values() if v)},
                     ensure_ascii=False))
    return 0


def cmd_audit(args) -> int:
    man = json.loads((PROJECTS / args.project / "manifest.json").read_text(encoding="utf-8"))
    rows = [f'{i["role"]:<4} retention={i["fid"].get("retention")} trace={i["fid"].get("trace")} '
            f'errs={len(i["spec_errors"])}' for i in man["l1"]]
    print("\n".join(rows))
    print(json.dumps({"cache": man["cache"], "spec_fail": sum(1 for i in man["l1"] if i["spec_errors"])},
                     ensure_ascii=False))
    return 0


def cmd_seal(args) -> int:
    pdir = PROJECTS / args.project
    man = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
    h = _hash(man["l2_hash"] + man["l3_hash"])
    dest = pdir / "sealed" / f'{man["built_at"].replace(":", "").replace(" ", "-")}-{h}'
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(pdir / "out", dest)
    man["sealed_by"] = args.by or "unknown"
    man["sealed_hash"] = h
    (dest / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sealed": str(dest), "hash": h}, ensure_ascii=False))
    return 0


def cmd_diff(args) -> int:
    pdir = PROJECTS / args.project
    seals = sorted((pdir / "sealed").glob("*"))
    if len(seals) < 1:
        print("没有 sealed 版本")
        return 1
    a = json.loads((seals[0] / "manifest.json").read_text(encoding="utf-8"))
    b = json.loads((seals[-1] / "manifest.json").read_text(encoding="utf-8"))
    print(json.dumps({"from": a.get("sealed_hash"), "to": b.get("sealed_hash"),
                      "changed_l1": [x["role"] for x, y in zip(a["l1"], b["l1"])
                                     if x["fid"] != y["fid"]]}, ensure_ascii=False))
    return 0


def cmd_one(args) -> int:
    """单角色报告：默认 core（L1+manifest），--path single 才走旧路径。"""
    from shared import role_runtime
    result = json.loads(Path(args.result).read_text(encoding="utf-8-sig"))
    data = (json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
            if args.input else None)
    dataset = (json.loads(Path(args.dataset).read_text(encoding="utf-8-sig"))
               if args.dataset else None)
    if args.path == "single":
        os.environ["GUAGUA_REPORT_PATH"] = "single"
    else:
        os.environ.pop("GUAGUA_REPORT_PATH", None)
    ports = role_runtime.emit(
        role=args.role, name=args.name or args.role, title=args.title or "",
        result=result, skill=args.skill, action=args.action, intent=args.intent,
        out_dir=args.out, md_name=args.md_name, data=data, dataset=dataset)
    man = Path(args.out) / "manifest.json"
    print(json.dumps({
        "engine": "single" if args.path == "single" else "core",
        "ports": [p.name for p in ports],
        "manifest": str(man) if man.exists() else None,
    }, ensure_ascii=False))
    return 0


def cmd_project(args) -> int:
    """项目级单份报告：contract → core 渲染 + manifest。"""
    from core.report_project import build_project
    res = build_project(args.dir, out_dir=args.out, theme=args.theme,
                        pdf=args.pdf, md_name=args.md_name)
    print(json.dumps({
        "ok": res["ok"],
        "counts": res["counts"],
        "checks": res["checks"],
        "files": res["files"],
        "manifest": res["manifest"],
    }, ensure_ascii=False))
    return 0 if res["ok"] else 1


def cmd_analysis(args) -> int:
    """问题驱动分析报告：analysis_pack → core 渲染 + manifest。"""
    from core.report_analysis import build_from_pack
    res = build_from_pack(args.pack, args.out, args.md_name,
                          theme=args.theme, pdf=args.pdf)
    print(json.dumps({
        "ok": res["ok"], "counts": res["counts"], "checks": res["checks"],
        "files": res["files"], "manifest": res["manifest"],
    }, ensure_ascii=False))
    return 0 if res["ok"] else 1


def cmd_blueprint(args) -> int:
    """通用报告蓝图：角色 × 对象 × 层级 × 领域 → 骨架。"""
    import json as _json
    from core.report_blueprint import build_outline, to_markdown
    domains = [x.strip() for x in (args.domains or "").split(",") if x.strip()] or None
    o = build_outline(args.role, args.tier, domains, args.object, args.external)
    print(_json.dumps(o, ensure_ascii=False, indent=2) if args.json else to_markdown(o))
    return 0


def cmd_modules(args) -> int:
    """通用模块报告：M0—M9 + 领域模块 → core 渲染。"""
    from core.report_modules import build_from_modules
    res = build_from_modules(args.pack, args.out, args.md_name,
                             theme=args.theme, pdf=args.pdf)
    print(json.dumps({"ok": res["ok"], "counts": res["counts"], "checks": res["checks"],
                      "files": res["files"], "manifest": res["manifest"]},
                     ensure_ascii=False))
    return 0 if res["ok"] else 1


def cmd_charts(args) -> int:
    from core.chart_capabilities import check, CATALOG
    r = check()
    if args.json:
        print(json.dumps({"ok": r["ok"], "count": r["count"], "items": CATALOG}, ensure_ascii=False, indent=2))
    else:
        print(f"图表能力：{r['count']}/48，渲染器 {r['renderers']}/48，ok={r['ok']}")
        for c in CATALOG:
            print(f"{c['id']:>6}  {c['key']:<14} {c['title']:<8} {c.get('use_when','')}")
    return 0 if r["ok"] else 1


def cmd_write(args) -> int:
    """证据包 → 核心 writer 扩写 → 模块报告。"""
    from core.report_writer import write_and_render
    res = write_and_render(args.evidence, args.out, args.md_name,
                           theme=args.theme, pdf=args.pdf)
    print(json.dumps({"ok": res["ok"], "counts": res["counts"], "checks": res["checks"],
                      "files": res["files"], "written_pack": res["written_pack"]},
                     ensure_ascii=False))
    return 0 if res["ok"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="guagua report")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--project", required=True)
    b.add_argument("--theme", choices=["sticker", "paper", "editorial", "mono", "annual", "swiss", "slate", "noir"], default=None)
    b.set_defaults(func=cmd_build)
    a = sub.add_parser("audit"); a.add_argument("--project", required=True); a.set_defaults(func=cmd_audit)
    ds = sub.add_parser("dispatch"); ds.add_argument("--project", required=True)
    ds.add_argument("--tasks", required=True); ds.set_defaults(func=cmd_dispatch)
    s = sub.add_parser("seal"); s.add_argument("--project", required=True)
    s.add_argument("--by", default=None); s.set_defaults(func=cmd_seal)
    d = sub.add_parser("diff"); d.add_argument("--project", required=True); d.set_defaults(func=cmd_diff)
    one = sub.add_parser("one", help="单角色报告：默认 core，--path single 才走旧路径")
    one.add_argument("--role", required=True)
    one.add_argument("--result", required=True)
    one.add_argument("--input", default=None)
    one.add_argument("--dataset", default=None)
    one.add_argument("--skill", required=True)
    one.add_argument("--action", required=True)
    one.add_argument("--intent", default="")
    one.add_argument("--out", required=True)
    one.add_argument("--md-name", default="role_report")
    one.add_argument("--name", default="")
    one.add_argument("--title", default="")
    one.add_argument("--path", choices=["core", "single"], default="core")
    one.set_defaults(func=cmd_one)
    proj = sub.add_parser("project", help="项目级单份报告：contract → core 渲染 + manifest")
    proj.add_argument("--dir", required=True, help="项目目录（含 data/report.contract.json）")
    proj.add_argument("--out", default=None, help="输出目录，默认 <dir>/out")
    proj.add_argument("--md-name", default="report", help="产物前缀")
    proj.add_argument("--theme", choices=["sticker", "paper", "editorial", "mono",
                                          "annual", "swiss", "slate", "noir"], default=None)
    proj.add_argument("--pdf", dest="pdf", action="store_true", default=True,
                      help="导出 PDF（默认开启）")
    proj.add_argument("--no-pdf", dest="pdf", action="store_false", help="只出 HTML，不出 PDF")
    proj.set_defaults(func=cmd_project)
    ana = sub.add_parser("analysis", help="问题驱动分析报告：analysis_pack → core")
    ana.add_argument("--pack", required=True, help="analysis_pack.json")
    ana.add_argument("--out", required=True)
    ana.add_argument("--md-name", default="report")
    ana.add_argument("--theme", choices=["sticker", "paper", "editorial", "mono",
                                         "annual", "swiss", "slate", "noir"], default=None)
    ana.add_argument("--pdf", action="store_true")
    ana.set_defaults(func=cmd_analysis)
    bp = sub.add_parser("blueprint", help="通用报告蓝图：角色 × 对象 × 层级 × 领域")
    bp.add_argument("--role", required=True, help="r01—r20")
    bp.add_argument("--tier", default="L3", choices=["L1", "L2", "L3"])
    bp.add_argument("--domains", default="", help="逗号分隔：market,customer,product,operations,finance,organization,technology,risk,transaction,data,model")
    bp.add_argument("--object", default=None, help="覆盖角色默认报告对象")
    bp.add_argument("--external", action="store_true", help="已有外部市场/竞品数据")
    bp.add_argument("--json", action="store_true")
    bp.set_defaults(func=cmd_blueprint)
    mod = sub.add_parser("modules", help="通用模块报告：M0—M9 + 领域模块 → core")
    mod.add_argument("--pack", required=True)
    mod.add_argument("--out", required=True)
    mod.add_argument("--md-name", default="report")
    mod.add_argument("--theme", default=None)
    mod.add_argument("--pdf", action="store_true")
    mod.set_defaults(func=cmd_modules)
    wr = sub.add_parser("write", help="证据包 → core writer 扩写 → 模块报告")
    wr.add_argument("--evidence", required=True)
    wr.add_argument("--out", required=True)
    wr.add_argument("--md-name", default="report")
    wr.add_argument("--theme", default=None)
    wr.add_argument("--pdf", action="store_true")
    wr.set_defaults(func=cmd_write)
    ch = sub.add_parser("charts", help="列出核心 48 型图表能力")
    ch.add_argument("--json", action="store_true")
    ch.set_defaults(func=cmd_charts)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
