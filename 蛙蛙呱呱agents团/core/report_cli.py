# -*- coding: utf-8 -*-
"""report CLI：L1×N → L2 → L3 的端到端构建。

用法（经 guagua.py 转发）：
  python guagua.py report build --project demo_2026q4
  python guagua.py report audit --project demo_2026q4
  python guagua.py report seal  --project demo_2026q4 --by 张三
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
