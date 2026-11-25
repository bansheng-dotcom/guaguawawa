# -*- coding: utf-8 -*-
"""report_kernel CLI：init / spec / registry / ship / self-test。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.report_kernel import consistency, contract as C, gate, series, specs


def _print_checks(res: dict) -> None:
    print(f"{'结果':6s}{'检查':24s}说明")
    for c in res["checks"]:
        mark = "PASS" if c["ok"] else ("WARN" if c["severity"] == "warn" else "FAIL")
        print(f"{mark:6s}{c['id']:24s}{c['detail']}")
    print(f"\n结论：{'PASS' if res['ok'] else 'FAIL'}  "
          f"{res['level']} / 目标 {res['target']}  score {res['score']}")
    if res["errors"]:
        print("阻塞项：")
        for e in res["errors"][:8]:
            print("  -", e)
    if res["warnings"]:
        print("提醒：")
        for w in res["warnings"][:6]:
            print("  -", w)


def cmd_init(a) -> int:
    data = C.template(a.id, a.title)
    data.update({
        "decision": a.decision, "audience": a.audience,
        "questions": a.questions, "data_cutoff": a.cutoff,
        "target_level": a.target, "owner": a.owner, "reviewer": a.reviewer,
        "source_count": a.sources, "series_periods": a.periods,
        "time_span_days": a.span, "cross_market": a.cross_market,
        "alignment_note": a.alignment or "", "trend_required": a.trend,
    })
    v = C.validate(data)
    if not v["ok"]:
        print("契约不完整：")
        for e in v["errors"]:
            print("  -", e)
        return 2
    out = Path(a.html).with_suffix(".ship.json")
    C.save(out, data)
    print(f"OK 写入 {out}")
    return 0


def cmd_spec(a) -> int:
    src = Path(a.contract)
    c = json.loads(src.read_text(encoding="utf-8-sig"))
    res = specs.apply_specs(c)
    out = Path(a.out) if a.out else src.with_suffix(".spec.json")
    out.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"OK 写入 {out}")
    return 0 if res["ok"] else 1


def cmd_registry(a) -> int:
    p = Path(a.path)
    if a.action == "init":
        consistency.save_registry(p, {"schema": "report-metrics/v1", "metrics": []})
        print(f"OK 写入 {p}")
        return 0
    if a.action == "add":
        reg = consistency.load_registry(p)
        reg.setdefault("metrics", []).append({
            "id": a.id, "label": a.label, "value": a.value,
            "unit": a.unit or "", "period": a.period or "",
            "source": a.source or "", "tolerance": a.tolerance,
        })
        consistency.save_registry(p, reg)
        print(f"OK 追加 {a.id}={a.value}")
        return 0
    reg = consistency.load_registry(p)
    res = consistency.check_registry(reg)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["ok"] else 1


def cmd_ship(a) -> int:
    if a.dir:
        globs = a.glob if isinstance(a.glob, list) else [a.glob or "*.html"]
        files = sorted({p for g in globs for p in Path(a.dir).glob(g)})
        if not files:
            print(f"目录下没有 {globs} 文件：{a.dir}")
            return 2
        results = [gate.run_gate(p, ship_path=None, registry_path=a.registry,
                                 peers=a.peer or [], strict=not a.no_strict)
                   for p in files]
        for r in results:
            bad = [c["id"] for c in r["checks"] if not c["ok"]]
            print(f"{'PASS' if r['ok'] else 'FAIL':5s}{r['level']:>3s}/{r['target']:>3s} "
                  f"score={r['score']:>5.1f}  {Path(r['report']).name}  {bad[:3]}")
        ok = all(r["ok"] for r in results)
        out = Path(a.json) if a.json else Path(a.dir) / "ship-result.batch.json"
        out.write_text(json.dumps({"ok": ok, "count": len(results), "reports": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n合计 {len(results)} 份，通过 {sum(1 for r in results if r['ok'])} 份；结果 {out}")
        return 0 if ok else 1

    if not a.html:
        print("请给 html 路径，或用 --dir 批量")
        return 2
    res = gate.run_gate(a.html, ship_path=a.contract, registry_path=a.registry,
                        peers=a.peer or [], strict=not a.no_strict)
    _print_checks(res)
    out = Path(a.json) if a.json else Path(a.html).with_suffix(".ship-result.json")
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果写入 {out}")
    return 0 if res["ok"] else 1


def cmd_self_test(a) -> int:
    errs = []
    c = C.template("RPT-TEST-01", "测试")
    c.update({"decision": "决定", "audience": "读者", "questions": ["q1", "q2", "q3"],
              "data_cutoff": "2026-11-16", "owner": "o", "reviewer": "r"})
    if not C.validate(c)["ok"]:
        errs.append("contract 合法样例未通过")
    bad = dict(c)
    bad["questions"] = ["q1"]
    if C.validate(bad)["ok"]:
        errs.append("contract 缺问题未拦截")

    tb = {"caption": "测试（元/件）", "columns": ["品类", "中间价", "变化率"],
          "rows": [["甲", "36.00", "+3.6%"], ["合计", "36.00", "+3.6%"]]}
    nt, st = specs.infer_table(tb)
    if st["with_unit"] < 1 or not nt.get("total_row"):
        errs.append("table 规格推断未生效")

    ch = {"type": "hbar", "title": "指标 36.00 元", "unit_meta": "元/件",
          "source": "测试", "bars": [{"label": "a", "value": 30}, {"label": "b", "value": 40}]}
    nc, cs, ce = specs.complete_chart(ch)
    if cs["ref_added"] != 1 or ce:
        errs.append("chart 规格补全未生效")

    reg = {"metrics": [{"id": "x", "value": 4, "unit": "倍"},
                       {"id": "x", "value": 11.3, "unit": "倍"}]}
    if consistency.check_registry(reg)["ok"]:
        errs.append("一致性冲突未拦截")

    sc = {"series_periods": 4, "trend_required": True, "sections": []}
    if series.check_series(sc)["ok"]:
        errs.append("序列不足未拦截")

    if errs:
        print("FAIL")
        for e in errs:
            print("  -", e)
        return 1
    print("PASS  6 项内核自检全部通过")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m core.report_kernel")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="生成报告验收契约 <report>.ship.json")
    p.add_argument("html")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--audience", required=True)
    p.add_argument("--questions", nargs="+", required=True)
    p.add_argument("--cutoff", required=True)
    p.add_argument("--target", choices=["L3", "L4"], default="L4")
    p.add_argument("--owner", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--sources", type=int, default=0)
    p.add_argument("--periods", type=int, default=0)
    p.add_argument("--span", type=int, default=0)
    p.add_argument("--cross-market", action="store_true")
    p.add_argument("--alignment", default="")
    p.add_argument("--trend", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("spec", help="对渲染契约补表/图规格")
    p.add_argument("contract")
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_spec)

    p = sub.add_parser("registry", help="数字登记与冲突检查")
    p.add_argument("action", choices=["init", "add", "check"])
    p.add_argument("path")
    p.add_argument("--id", default="")
    p.add_argument("--label", default="")
    p.add_argument("--value", type=float, default=0.0)
    p.add_argument("--unit", default="")
    p.add_argument("--period", default="")
    p.add_argument("--source", default="")
    p.add_argument("--tolerance", type=float, default=0.01)
    p.set_defaults(func=cmd_registry)

    p = sub.add_parser("ship", help="交付门禁")
    p.add_argument("html", nargs="?", default=None)
    p.add_argument("--dir", default=None, help="批量体检目录")
    p.add_argument("--glob", nargs="+", default=["*.html"])
    p.add_argument("--contract", default=None)
    p.add_argument("--registry", default=None)
    p.add_argument("--peer", nargs="*", default=[])
    p.add_argument("--json", default=None)
    p.add_argument("--no-strict", action="store_true",
                   help="无契约时只告警，用于存量报告体检")
    p.set_defaults(func=cmd_ship)

    p = sub.add_parser("self-test", help="内核自检")
    p.set_defaults(func=cmd_self_test)

    a = ap.parse_args(argv)
    return int(a.func(a))


if __name__ == "__main__":
    sys.exit(main())
