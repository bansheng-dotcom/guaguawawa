# -*- coding: utf-8 -*-
"""v5 接线自测：intake 12 问 / 面板规格 / DoR / 论点与节。"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import intake, panel, dor, synthesis  # noqa: E402

OK, FAIL = [], []


def check(name, cond, msg=""):
    (OK if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" :: {msg}" if msg and not cond else ""))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        r = intake.start(p, "北京宠物用品市场机会")
        check("intake_12", r["questions"] == 12 and r["min_answers"] == 10)
        bad = intake.sign_brief(p)
        check("sign_blocked_without_answers", bad["ok"] is False, bad)
        ans = [f"I{i}=答案{i}" for i in range(1, 11)]
        a = intake.answer(p, ans)
        check("answer_10", a["ok"] is True and a["answered"] == 10, a)
        sg = intake.sign_brief(p)
        check("sign_after_answers", sg["ok"] is True and sg["signed"]["sha"], sg)
        check("signed_reader", intake.signed(p) is not None)

    panels = panel.build("北京宠物用品市场机会", {"asks": []})
    check("panels_three", len(panels) == 3 and all(p["target_rows"] > 0 for p in panels), panels)
    rows = []
    for i, city in enumerate(("朝阳", "海淀", "丰台"), 1):
        rows.append({"metric_name": f"北京{city}零售额", "entity": city, "period": "2025",
                     "value": 10 * i, "unit": "亿元", "row_id": f"R{i}",
                     "number_id": f"r05:N{i}", "value_base": 10 * i * 1e8})
    cov = panel.coverage(rows, panels)
    check("coverage_detects", cov["panels"][0]["filled"] >= 1, cov)

    card = {"question": "北京各品类零售额差距", "primary": "r05", "cells": rows,
            "tier": "must", "metrics": ["retail.sales"], "panel": "P1",
            "acceptance": ["G1"], "deliverable": "rows.json", "depends_on": [],
            "why": "面板切片"}
    d = dor.check(card)
    check("dor_ok", d["ok"] is True, d)
    check("dor_score", dor.score(card) >= 16, dor.score(card))
    empty = dor.check({"question": ""})
    check("dor_blocks_empty", empty["ok"] is False and empty["missing"])

    th = synthesis.theses(rows, panels)
    check("theses_built", len(th) >= 1, th)
    secs = synthesis.sections(th, rows)
    check("sections_built", secs and secs[0]["chart"] and secs[0]["prose_spec"]["signal"], secs)
    check("section_has_refs", bool(secs[0]["refs"]) and secs[0]["refs"][0].startswith("r05:"))

    # 自适应分卡：按问题簇，不按固定张数
    from core import card_plan
    cells = []
    for q in ("Q1", "Q2", "Q3"):
        for i in range(16):
            cells.append({"cell_id": f"{q}.c{i}", "qid": q, "dim": "空间",
                          "measure": "retail_sales"})
    cl = card_plan.cluster(cells)
    check("cluster_by_question", len(cl) == 3, [c["card_id"] for c in cl])
    big = [{"cell_id": f"Q9.c{i}", "qid": "Q9", "dim": "空间", "measure": "retail_sales"}
           for i in range(30)]
    cl2 = card_plan.cluster(big)
    check("cluster_splits_large", len(cl2) == 2 and all(len(c["cells"]) <= 24 for c in cl2),
          [(c["card_id"], len(c["cells"])) for c in cl2])
    cl3, gaps3 = card_plan.assign(cl, {r: {"role": r, "capabilities": ["数据"],
                                           "skills": [], "entitlements": {}}
                                       for r in ("r05", "r06")}, load_cap=2)
    check("load_cap_respected", sum(1 for c in cl3 if c.get("owner") == "r05") <= 2, cl3)

    print(f"\n{len(OK)}/{len(OK)+len(FAIL)} passed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
