# -*- coding: utf-8 -*-
"""chart_query 自测：形状 → 图型、数据点、标题、标注。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import chart_query as cq  # noqa: E402

OK, FAIL = [], []


def check(name, cond, msg=""):
    (OK if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" :: {msg}" if msg and not cond else ""))


def row(i, mid, entity, period, value, segment="", unit="亿元"):
    return {"row_id": f"R{i}", "number_id": f"r05:N{i}", "metric_id": mid,
            "metric_name": "北京宠物用品零售额", "entity": entity,
            "period": period, "value": value, "segment": segment, "unit": unit}


def main() -> int:
    # 矩阵：8 区 × 3 品类
    rs = []
    n = 0
    for e in ("朝阳", "海淀", "丰台", "通州", "昌平", "大兴", "顺义", "石景山"):
        for s in ("主粮", "零食", "用品"):
            n += 1
            rs.append(row(n, "m1", e, "2025", 10 + n, s))
    ch = cq.build(rs, "m1")
    check("matrix_heatmap", ch["type"] == "heatmap", ch["type"])
    check("matrix_shape", len(ch["rows"]) == 8 and len(ch["cols"]) == 3, ch)
    check("matrix_cells", sum(1 for r in ch["matrix"] for x in r if x is not None) == 24, ch)
    check("matrix_title_digit", any(c.isdigit() for c in ch["title"]), ch["title"])

    # 趋势：12 期
    tr = [row(i, "m2", "朝阳", f"2025-{i:02d}", 100 + i) for i in range(1, 13)]
    ch = cq.build(tr, "m2")
    check("trend_line", ch["type"] == "line" and len(ch["points"]) == 12, ch.get("type"))

    # 构成：5 项合计 100
    comp = [row(i, "m3", x, "2025", v) for i, (x, v) in
            enumerate([("主粮", 40), ("零食", 25), ("用品", 20), ("医疗", 10), ("服务", 5)], 1)]
    ch = cq.build(comp, "m3")
    check("composition_share", ch["type"] == "share_bar" and len(ch["items"]) == 5, ch.get("type"))

    # 排序：16 个主体 → 只列前 10，并注明
    rank = [row(i, "m4", f"区{i}", "2025", i * 3) for i in range(1, 17)]
    ch = cq.build(rank, "m4")
    check("rank_top10", ch["type"] == "hbar" and len(ch["items"]) == 10, len(ch.get("items") or []))
    check("rank_note", "仅列前 10" in ch.get("accent_note", ""), ch.get("accent_note"))
    check("rank_title_digit", any(c.isdigit() for c in ch["title"]), ch["title"])

    check("no_rows_none", cq.build([], "m1") is None)
    check("plan_matrix", cq.plan(rs, "m1")["kind"] == "matrix")

    print(f"\n{len(OK)}/{len(OK)+len(FAIL)} passed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
