# -*- coding: utf-8 -*-
"""scripts/ir_shadow.py —— 影子 IR 生成器（SOP v3.0 S2–S5 的零回归对比基线）。

不改渲染器、不动产线运行路径，只做：作者写法 → IR → 已解析模型 → 图表变更报告。
这是「影子双渲染」的影子侧：先证明三条写法能落到同一 IR 且图型判断正确，
再把渲染器切到 IR（S5b 热路径）时，拿这份报告做零回归对照。

用法：
  python scripts/ir_shadow.py --claims <claims.json> --out <dir>
  python scripts/ir_shadow.py --draft <draft_sections.json> --pack <evidence_pack.json> --out <dir>
  python scripts/ir_shadow.py --facts <facts.yaml> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from core.ir_adapters import claims_to_ir, decision_to_ir, facts_to_ir  # noqa: E402
from core.semantic_pipeline import resolve, panel  # noqa: E402


def _load_json(p: str):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims")
    ap.add_argument("--draft")
    ap.add_argument("--pack")
    ap.add_argument("--facts")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.claims:
        ir, deg = claims_to_ir(_load_json(args.claims))
        src = "claims"
    elif args.draft and args.pack:
        ir, deg = decision_to_ir(_load_json(args.draft), _load_json(args.pack))
        src = "decision"
    elif args.facts:
        f = yaml.safe_load(Path(args.facts).read_text(encoding="utf-8"))
        ir, deg = facts_to_ir(f)
        src = "facts"
    else:
        ap.error("需要 --claims | --draft+--pack | --facts")

    model = resolve(ir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ir.json").write_text(json.dumps(ir, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    (out / "resolved.json").write_text(json.dumps(model, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    changes = []
    for s in model["sections"]:
        cv = s["chart"]["chart_validation"]
        changes.append({
            "title": s["title"][:24],
            "relation": s["chart"]["relation"],
            "chosen": s["chart"]["chosen"],
            "ok": cv.get("ok"),
            "reason": cv.get("reason"),
            "suggest": cv.get("suggest"),
        })
    (out / "chart_report.json").write_text(
        json.dumps(changes, ensure_ascii=False, indent=1), encoding="utf-8")

    # 候选面板：作者决策接口（只列需决策的节 + 决策模板）
    p = panel(model)
    (out / "panel.json").write_text(
        json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "decisions.template.json").write_text(
        json.dumps([{"index": e["index"], "relation": e["relation"],
                     "chosen": (e["candidates"] or [""])[0]}
                    for e in p], ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({
        "src": src, "ok": model["ok"],
        "schema_errors": len(model["schema_errors"]),
        "facts": len(model["facts"]),
        "sections": len(model["sections"]),
        "charts_valid": sum(1 for c in changes if c["ok"]),
        "charts_to_change": sum(1 for c in changes if not c["ok"]),
        "degraded": len(deg),
        "out": str(out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
