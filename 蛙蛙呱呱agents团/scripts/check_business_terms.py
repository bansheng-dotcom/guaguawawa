# -*- coding: utf-8 -*-
"""scripts/check_business_terms.py —— 业务词隔离门禁（方案 §3.6 / P1-7）。

三层词表，处置不同：
  project_block  项目专属词（具体品类/单位）——**任何位置**出现即失败
  line_block     业务线词（生鲜/母婴/美妆/冷链/损耗率…）——只允许出现在
                 `configs/industries/*`（行业库是显式数据）；code 目录出现即失败
  warn           行业口径词（零售/批发/门店/坪效/SKU…）——**代码里必须为 0**；
                 `configs/industries/*` 是显式行业库，豁免（它本来就要写行业名）

为什么分两层：行业库（`configs/industries`）本来就要写行业名，它是**声明式数据**；
但项目专属词（某个历史业务的品类与单位）连行业库都不该有。

用法：
  python scripts/check_business_terms.py            # 报告
  python scripts/check_business_terms.py --check    # 门禁（任一 block/warn > 0 则 1）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("core", "shared", "configs", "scripts")
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "_archive"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".svg", ".xlsx", ".xls", ".pdf", ".zip",
            ".pyc", ".geojson", ".woff", ".ttf"}

PROJECT_BLOCK = ("下架鸡", "肥牛", "育肥牛", "活牛", "犊牛", "鲜蛋", "鸡白条",
                 "元/斤", "元/公斤", "东瓦窑")
LINE_BLOCK = ("母婴", "美妆", "生鲜", "损耗率", "冷链")
WARN = ("零售", "批发", "产地价", "出场价", "门店", "坪效", "SKU",
        "限额以上", "盟市", "旗县", "规模以上", "采矿业")
INFO = ("同比", "环比", "期次", "客单价")

LINE_BLOCK_ALLOW = ("configs/industries/",)
WARN_ALLOW = ("configs/industries/",)
ALLOW_FILES: Dict[str, str] = {
    # 历史归档：不参与产线，保留原文以便追溯；显式登记而不是静默跳过
    "scripts/_archive/seed_knowledge.py": "历史归档，不参与产线",
    # 词表定义文件本身必须出现这些词，否则无法扫描
    "scripts/check_business_terms.py": "词表定义",
    "scripts/scan_business_terms.py": "词表定义（旧版扫描器）",
}  # noqa: E501


def _files() -> List[Tuple[Path, str]]:
    out: List[Tuple[Path, str]] = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() in SKIP_EXT:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            out.append((p, str(p.relative_to(ROOT)).replace("\\", "/")))
    return out


def scan() -> Dict[str, Dict[str, Dict[str, int]]]:
    res: Dict[str, Dict[str, Dict[str, int]]] = {"project_block": {}, "line_block": {},
                                                 "warn": {}, "info": {}}
    for p, rel in _files():
        if rel in ALLOW_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for tier, words in (("project_block", PROJECT_BLOCK),
                            ("line_block", LINE_BLOCK),
                            ("warn", WARN), ("info", INFO)):
            for w in words:
                n = text.count(w)
                if not n:
                    continue
                if tier == "line_block" and any(rel.startswith(a) for a in LINE_BLOCK_ALLOW):
                    continue
                if tier == "warn" and any(rel.startswith(a) for a in WARN_ALLOW):
                    continue
                res[tier].setdefault(rel, {})[w] = n
    return res


def _totals(d: Dict[str, Dict[str, int]]) -> int:
    return sum(sum(v.values()) for v in d.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    res = scan()
    pb, lb, wn = _totals(res["project_block"]), _totals(res["line_block"]), _totals(res["warn"])
    print(f"project_block {pb} 次 / {len(res['project_block'])} 文件"
          f"｜line_block {lb} 次 / {len(res['line_block'])} 文件"
          f"｜warn {wn} 次 / {len(res['warn'])} 文件（info {_totals(res['info'])} 只统计）")

    def show(tier: str, top: int = 8) -> None:
        rows = sorted(res[tier].items(), key=lambda kv: -sum(kv[1].values()))[:top]
        if not rows:
            return
        print(f"\n[{tier}]")
        for f, ws in rows:
            words = "、".join(f"{k}×{v}" for k, v in
                             sorted(ws.items(), key=lambda kv: -kv[1])[:4])
            print(f"  {sum(ws.values()):>4}  {f}  ← {words}")

    show("project_block")
    show("line_block")
    show("warn")

    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"\n明细：{a.json}")

    fails = pb or lb or wn
    if a.check:
        print(f"\n=== {'FAIL' if fails else 'PASS'} ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
