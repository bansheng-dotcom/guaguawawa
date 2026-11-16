# -*- coding: utf-8 -*-
"""图表回退门禁：48 型画廊必须全部由 v2 出图，不允许静默回退 v1。

    python scripts/check_chart_fallback.py [theme]
退出码：0 = 无回退；1 = 有回退 / 有渲染异常。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import chart_gallery_v2 as G  # noqa: E402
from core.charts.v2 import render as v2_render  # noqa: E402
from core.report_renderer import chart_stats, render_chart  # noqa: E402


def main() -> int:
    theme = sys.argv[1] if len(sys.argv) > 1 else "paper"
    fallbacks, errors = [], []
    for key, spec in G.SAMPLES.items():
        payload = {**spec, "_embed": True}
        try:
            direct = v2_render(dict(payload), theme)
        except Exception as exc:  # noqa: BLE001
            direct = None
            errors.append(f"{key}: {type(exc).__name__}: {exc}")
        out = render_chart(dict(payload), theme, engine="v2")
        if not direct:
            fallbacks.append(key)
            continue
        if out != direct:
            fallbacks.append(key)

    print(f"样本 {len(G.SAMPLES)} 型 · 回退 {len(fallbacks)} · 异常 {len(errors)}")
    if fallbacks:
        print("回退：", ", ".join(fallbacks))
    for e in errors:
        print("异常：", e)
    print("计数：", chart_stats())
    return 0 if not fallbacks and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
