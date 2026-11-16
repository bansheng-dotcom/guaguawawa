# -*- coding: utf-8 -*-
"""图表引擎 v2 覆盖率门禁。

现状（升级前）：chart_lib 有 48 型，charts.v2 只覆盖 18 型，
其余 30 型在 report_renderer.render_chart() 里被**静默**回退到 v1（手写 SVG 的素图）。
这个脚本把"静默"变成"可计数"：

    python scripts/check_chart_v2_coverage.py          # 人看
    python scripts/check_chart_v2_coverage.py --json   # 给 CI / 看板
    python scripts/check_chart_v2_coverage.py --strict # 缺一即失败（P4 起挂进 CI）

退出码：0 = 全量覆盖；1 = 仍有缺口（--strict 时）/ 采集失败。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHART_DIR = ROOT / "core" / "charts"
if str(CHART_DIR) not in sys.path:
    sys.path.insert(0, str(CHART_DIR))


def collect() -> dict:
    import chart_lib  # noqa: E402
    from core.charts.v2 import RENDERERS as V2  # noqa: E402

    v1 = set(chart_lib.RENDERERS)
    v2 = set(V2)
    catalog = {c["key"]: c for c in chart_lib.CHART_INDEX}
    missing = sorted(v1 - v2)
    extra = sorted(v2 - v1)
    # 别名：v2 里两个 key 共用一个实现（lollipop->dot、bridge->waterfall）不算缺陷
    aliases = {}
    seen = {}
    for key, fn in V2.items():
        seen.setdefault(fn.__name__, []).append(key)
    for fn_name, keys in seen.items():
        if len(keys) > 1:
            aliases[fn_name] = keys
    return {
        "v1_count": len(v1),
        "v2_count": len(v2),
        "covered": len(v1 & v2),
        "missing": missing,
        "missing_titles": [catalog.get(k, {}).get("title", "") for k in missing],
        "extra_in_v2": extra,
        "aliases": aliases,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    try:
        r = collect()
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1

    r["ok"] = not r["missing"]
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"v1 {r['v1_count']} 型 / v2 {r['v2_count']} 型 / 覆盖 {r['covered']} / 缺 {len(r['missing'])}")
        if r["missing"]:
            print("未覆盖：")
            for k, t in zip(r["missing"], r["missing_titles"]):
                print(f"  - {k:<14} {t}")
        if r["extra_in_v2"]:
            print("v2 多出（v1 无此型）：", ", ".join(r["extra_in_v2"]))
        if r["aliases"]:
            print("共用实现：", "; ".join(f"{k} <- {','.join(v)}" for k, v in r["aliases"].items()))
    return 0 if (r["ok"] or not a.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
