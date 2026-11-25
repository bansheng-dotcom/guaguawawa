# -*- coding: utf-8 -*-
"""charts_pro 边界门禁：空数据 / 零域 / 负值 / 长标签 / 超多类别。

`check_charts_pro.py` 只验"能出 svg"；本脚本验"画得对"：
  - 空数据 → 输出空态说明卡，不抛异常
  - 单点 / 全零 → 不抛异常（零域保护）
  - 全负值 hbar → 所有条共用 0 基线，且向左延伸
  - heatmap 负值 → 用发散色阶（蓝），不与 0 同色
  - 长中文标签 → 自动换行，不越界
  - 200 项 → 仍可渲染且体积可控

用法：python scripts/check_chart_edges.py
退出码：0=全部通过，1=有失败。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.report_theme.charts_pro import spec as S  # noqa: E402

RECT = re.compile(r'<rect x="([-\d.]+)" y="[-\d.]+" width="([-\d.]+)"')


def _case(name, fn) -> bool:
    try:
        ok, why = fn()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {name:<26} {type(exc).__name__}: {exc}")
        return False
    print(("PASS " if ok else "FAIL ") + f"{name:<26} {why}")
    return ok


def main() -> int:
    results = []

    results.append(_case("空数据→空态", lambda: (
        "无数据" in S.render({"type": "hbar", "items": []}),
        "输出空态说明卡")))

    results.append(_case("单点折线", lambda: (
        "<svg" in S.render({"type": "line", "points": [{"label": "2026-10", "value": 4.8}]}),
        "零域保护生效")))

    results.append(_case("全零折线", lambda: (
        "<svg" in S.render({"type": "line", "points": [{"label": "a", "value": 0},
                                                       {"label": "b", "value": 0}]}),
        "零域保护生效")))

    results.append(_case("全零饼图", lambda: (
        "无数据" in S.render({"type": "pie", "items": [{"label": "a", "value": 0},
                                                        {"label": "b", "value": 0}]}),
        "输出空态说明卡")))

    def neg_bar():
        svg = S.render({"type": "hbar", "items": [{"label": "A", "value": -5},
                                                  {"label": "B", "value": -9}]})
        rects = [(float(x), float(w)) for x, w in RECT.findall(svg)]
        rights = {round(x + w, 1) for x, w in rects}
        lefts = [x for x, _ in rects]
        ok = len(rects) >= 2 and len(rights) == 1 and min(lefts) < max(rights) - 10
        return ok, f"条数 {len(rects)}｜共用基线 {rights}｜最左 {min(lefts):.1f}"
    results.append(_case("全负值条形向左", neg_bar))

    results.append(_case("热力负值发散色阶", lambda: (
        "2E6F9E" in S.render({"type": "heatmap", "rows": ["a"], "cols": ["c1", "c2"],
                              "matrix": [[-3, 4]]}),
        "负值=蓝、正值=红")))

    def long_label():
        svg = S.render({"type": "hbar", "items": [
            {"label": "电力、热力、燃气及水生产和供应业投资", "value": 12},
            {"label": "固定资产投资（不含农户）", "value": 8}]})
        texts = re.findall(r">([^<>]{2,})</text>", svg)
        longest = max(len(t) for t in texts)
        return longest <= 16, f"最长文本 {longest} 字（换行后）"
    results.append(_case("长标签自动换行", long_label))

    def many_items():
        svg = S.render({"type": "hbar",
                        "items": [{"label": f"I{i}", "value": i} for i in range(200)]})
        return len(svg) < 200_000, f"svg {len(svg)} 字节"
    results.append(_case("200 项不失控", many_items))

    ok = all(results)
    print(f"\n边界门禁：{sum(results)}/{len(results)} 通过")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
