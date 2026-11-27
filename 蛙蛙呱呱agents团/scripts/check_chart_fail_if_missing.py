# -*- coding: utf-8 -*-
"""scripts/check_chart_fail_if_missing.py —— 图表必绘门禁。

判据：
  1. 每张图绑定一条 claim_id；
  2. required_series 全部出现（series_completeness.ratio == 1）；
  3. 起止/差值标注齐全，且声明避让与最小间距；
  4. fail_if_missing 明确包含 required_series 与 annotation_start_end；
  5. 给了 --report 时，图中每个 chart_id 必须进入正文图注。

用法：
    python scripts/check_chart_fail_if_missing.py --spec <chart_spec_pack.json> [--report <html>]
"""
from __future__ import annotations

import argparse
import json
import os


def _selftest() -> int:
    spec = {"charts": [{
        "chart_id": "CH1", "claim_id": "C1", "type": "hbar",
        "series_completeness": {"required": 1, "present": 1, "ratio": 1, "missing": []},
        "annotation_plan": {"start": 1, "end": 2, "delta": 1,
                            "min_spacing_px": 12, "avoid_overlap": True},
        "fail_if_missing": ["required_series", "annotation_start_end",
                            "series_completeness"],
        "payload": {"bars": [{"label": "A", "value": 1}]},
    }]}
    bad = json.loads(json.dumps(spec))
    bad["charts"][0]["series_completeness"] = {"required": 1, "present": 0,
                                              "ratio": 0, "missing": ["A"]}
    ok1 = _check_obj(spec) == []
    ok2 = bool(_check_obj(bad))
    print(f"[{'PASS' if ok1 and ok2 else 'FAIL'}] chart_fail_if_missing selftest "
          f"good={ok1} bad_rejected={ok2}")
    return 0 if (ok1 and ok2) else 1


def _check_obj(data) -> list:
    errs = []
    charts = data.get("charts") or []
    if not charts:
        errs.append("图表数为 0")
    for c in charts:
        cid = c.get("chart_id", "?")
        if not c.get("claim_id"):
            errs.append(f"{cid} 未绑定 claim")
        comp = c.get("series_completeness") or {}
        if comp.get("ratio") != 1 or comp.get("missing"):
            errs.append(f"{cid} 必绘系列缺失 {comp.get('missing')}")
        ap_ = c.get("annotation_plan") or {}
        if not all(ap_.get(k) is not None for k in ("start", "end", "delta")):
            errs.append(f"{cid} 缺起止/差值标注")
        if ap_.get("avoid_overlap") is not True or not isinstance(ap_.get("min_spacing_px"), (int, float)):
            errs.append(f"{cid} 缺标注避让/最小间距")
        fim = c.get("fail_if_missing") or []
        if "required_series" not in fim or "annotation_start_end" not in fim:
            errs.append(f"{cid} fail_if_missing 不全")
        if not c.get("payload"):
            errs.append(f"{cid} 缺渲染 payload")
    return errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_chart_fail_if_missing")
    ap.add_argument("--spec", default=None, help="chart_spec_pack.json")
    ap.add_argument("--report", default=None, help="可选：报告 HTML，检查图注是否齐全")
    ap.add_argument("--selftest", action="store_true", help="内置正反例自测")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not a.spec:
        print("[FAIL] 需要 --spec（或 --selftest）")
        return 1
    if not os.path.exists(a.spec):
        print(f"[FAIL] 缺少图表规格包 {a.spec}")
        return 1
    data = json.load(open(a.spec, encoding="utf-8"))
    charts = data.get("charts") or []
    errs = _check_obj(data)
    if a.report:
        if not os.path.exists(a.report):
            errs.append(f"报告不存在 {a.report}")
        else:
            html = open(a.report, encoding="utf-8", errors="replace").read()
            for c in charts:
                cid = c.get("chart_id", "?")
                if f"图 {cid}" not in html:
                    errs.append(f"{cid} 未进入正文图注")
    out = {"ok": not errs, "charts": len(charts), "errors": errs}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"[{'PASS' if out['ok'] else 'FAIL'}] 图表 {len(charts)} 张；"
              f"错误 {len(errs)} 项 {errs[:6]}")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
