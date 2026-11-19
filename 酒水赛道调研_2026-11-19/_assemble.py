#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收卡 + 重排 + 定封面/导语，产出 claims_merged.json（之后交给 report --claims 渲染）。

用法：python _assemble.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
PROJ = Path(r"D:\蛙蛙呱呱\酒水赛道调研_2026-11-19")
sys.path.insert(0, str(ROOT))

from core import dispatch  # noqa: E402

ORDER = ["r01", "r05", "r06", "r02", "r15", "r12", "r03"]

TITLE = "中国酒水赛道全景：缩量、集中与价格倒挂下的进入判断"

# 同一来源在不同卡里被打了不同等级，合并时按 URL 归一（协会报告全文转载记 B）
GRADE_BY_URL = {
    "http://www.tyjzk.com/article/56052.html": "B",
    "https://fsc.foodmate.net/show.php?itemid=735279": "B",
}


def main() -> int:
    merged, problems = dispatch.collect(str(PROJ))
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, ensure_ascii=False, indent=1))
    if not merged.get("sections"):
        print(json.dumps({"ok": False, "error": "没有任何一节"}, ensure_ascii=False))
        return 2

    def role_of(sec):
        r = str(sec.get("refs", [""])[0]).split(":")[0] if sec.get("refs") else ""
        return r or str(sec.get("_role") or "")

    buckets = {r: [] for r in ORDER}
    other = []
    for s in merged["sections"]:
        r = role_of(s)
        (buckets[r] if r in buckets else other).append(s)
    ordered = [s for r in ORDER for s in buckets[r]] + other

    merged["sections"] = ordered
    merged["meta"] = {
        "title": TITLE,
        "doc_type": "调研报告",
        "profile": "research",
        "intent": "中国酒水赛道全景研究",
        "audience": "决定是否进入酒水赛道的业务负责人",
        "title_lines": [TITLE, f"{len(ordered)} 节 · 六路专家调研稿 · 2026-11"],
    }
    merged["metrics"] = [
        {"label": "白酒产量", "value": "354.9 万千升",
         "note": "2025 年，同比 -12.1%", "status": "watch"},
        {"label": "行业 CR6 利润占比", "value": "86%",
         "note": "2024 年，2014 年为 55%", "status": "critical"},
        {"label": "飞天散瓶批价", "value": "1485 元/瓶",
         "note": "2025 年 12 月", "status": "watch"},
        {"label": "存货周转天数", "value": "900 天",
         "note": "2024 年行业均值", "status": "critical"},
    ]
    merged["standfirst"] = str(ordered[0].get("title") or "")
    merged.pop("meta_auto", None)

    for src in merged.get("sources") or []:
        g = GRADE_BY_URL.get(str(src.get("url") or ""))
        if g:
            src["grade"] = g

    out = PROJ / "out"
    out.mkdir(parents=True, exist_ok=True)
    p = out / "claims_merged.json"
    p.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": True, "sections": len(ordered),
        "numbers": len(merged["numbers"]), "sources": len(merged["sources"]),
        "order": [role_of(s) for s in ordered],
        "titles": [s.get("title") for s in ordered],
        "out": str(p),
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
