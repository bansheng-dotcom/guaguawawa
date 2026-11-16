# -*- coding: utf-8 -*-
"""校验 Move 卡片：让「学习」有可判定的入口。

拦七类问题（任一出现即 FAIL）：
1. 缺来源（书名/作者/年份）——不知道从哪学的，就不是学习；
2. 步骤少于 3 条——书摘不是动作；
3. 没有反例或反例太短——不可证伪的 move 不许入库；
4. 结论等级不在 L0—L4——分不清描述/对照/相关/因果/预测；
5. id 重复或不符合 M-<域>-<序号>；
6. active 卡片的 method / test 路径不存在，或 test 函数找不到；
7. active 卡片没有可判定的验收断言。

用法：
    python scripts/check_move_cards.py
    python scripts/check_move_cards.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
MOVES = ROOT / "knowledge" / "moves"

ID_RE = re.compile(r"^M-[A-Z]{3}-\d{3}$")
VER_RE = re.compile(r"^\d+\.\d+$")
DOMAINS = {"problem_solving", "causal", "statistics", "strategy", "marketing",
           "retail", "supply_chain", "systems", "communication"}
KINDS = {"size", "trend", "gap", "mix", "volume", "unit", "concentration",
         "spread", "coverage", "demand", "channel", "supply", "policy",
         "region", "consistency", "phase"}
LEVELS = {"L0", "L1", "L2", "L3", "L4"}
STATUS = {"draft", "active", "retired"}
REQUIRED = ("id", "name", "version", "status", "domain", "source", "trigger",
            "inputs", "procedure", "output_claim", "counterexample",
            "failure_mode", "landing", "acceptance", "owner", "last_reviewed")


def _defines(path: Path, func: str) -> bool:
    if not path.exists():
        return False
    src = path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(rf"^(?:async\s+)?def\s+{re.escape(func)}\s*\(", src, re.M))


def _check_landing(d: Dict[str, Any], errs: List[str]) -> None:
    landing = d.get("landing") or {}
    method = str(landing.get("method") or "")
    test = str(landing.get("test") or "")
    active = d.get("status") == "active"

    if method and not method.startswith("none"):
        p, _, fn = method.partition("::")
        mp = ROOT / p
        if not mp.exists():
            errs.append(f"landing.method 文件不存在: {p}")
        elif fn and not _defines(mp, fn):
            errs.append(f"landing.method 函数不存在: {p}::{fn}")
    elif active:
        errs.append("active 卡片的 landing.method 不能是 none")

    if test:
        p, _, fn = test.partition("::")
        tp = ROOT / p
        if not tp.exists():
            errs.append(f"landing.test 文件不存在: {p}")
        elif fn and not _defines(tp, fn):
            errs.append(f"landing.test 函数不存在: {p}::{fn}")
    elif active:
        errs.append("active 卡片的 landing.test 不能为空")

    for k in ("gate", "frame", "claim_kind"):
        if not landing.get(k):
            errs.append(f"landing.{k} 为空")

    acc = d.get("acceptance") or {}
    if active and not (acc.get("expected") and acc.get("fixture")):
        errs.append("active 卡片缺验收断言（fixture + expected）")


def check_one(p: Path) -> Dict[str, Any]:
    errs: List[str] = []
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        return {"file": p.name, "ok": False, "errors": [f"JSON 解析失败: {e}"]}
    for k in REQUIRED:
        if k not in d:
            errs.append(f"缺字段 {k}")
    if errs:
        return {"file": p.name, "ok": False, "errors": errs}

    if not ID_RE.match(str(d["id"])):
        errs.append(f"id 不合规: {d['id']}")
    if not VER_RE.match(str(d["version"])):
        errs.append(f"version 不合规: {d['version']}")
    if d.get("status") not in STATUS:
        errs.append(f"status 非法: {d.get('status')}")
    if d.get("domain") not in DOMAINS:
        errs.append(f"domain 非法: {d.get('domain')}")

    src = d.get("source") or {}
    for k in ("book", "author", "concept"):
        if not str(src.get(k) or "").strip():
            errs.append(f"source.{k} 为空")
    if not isinstance(src.get("year"), int) or not (1900 <= src["year"] <= 2100):
        errs.append("source.year 不是合理年份")

    trig = d.get("trigger") or {}
    if not trig.get("decision") or not trig.get("data_shape"):
        errs.append("trigger 缺 decision 或 data_shape")
    if not str(trig.get("min_evidence") or "").strip():
        errs.append("trigger.min_evidence 为空")

    proc = d.get("procedure") or []
    if not isinstance(proc, list) or len(proc) < 3:
        errs.append("procedure 少于 3 步")
    if any(len(str(x).strip()) < 6 for x in proc):
        errs.append("procedure 有步骤太短（<6 字）")

    oc = d.get("output_claim") or {}
    if oc.get("kind") not in KINDS:
        errs.append(f"output_claim.kind 非法: {oc.get('kind')}")
    if oc.get("level") not in LEVELS:
        errs.append(f"output_claim.level 非法: {oc.get('level')}")
    if "{".join(str(oc.get("headline_template") or "").split("{")[1:]).count("}") < 1:
        errs.append("output_claim.headline_template 没有占位符")

    if len(str(d.get("counterexample") or "").strip()) < 15:
        errs.append("counterexample 太短或为空（<15 字）")
    if len(str(d.get("failure_mode") or "").strip()) < 6:
        errs.append("failure_mode 太短或为空")

    _check_landing(d, errs)
    return {"file": p.name, "id": d.get("id"), "name": d.get("name"),
            "status": d.get("status"), "ok": not errs, "errors": errs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_move_cards")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    files = sorted(MOVES.glob("M-*.json"))
    if not files:
        print(f"没有 move 卡片：{MOVES}")
        return 2
    results = [check_one(p) for p in files]
    ids: Dict[str, str] = {}
    for r in results:
        i = r.get("id")
        if i:
            if i in ids:
                r["ok"] = False
                r["errors"].append(f"id 与 {ids[i]} 重复")
            ids[i] = r["file"]
    bad = [r for r in results if not r["ok"]]
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"{mark}  {r['file']:<16} {r.get('status', '-'):<7} "
                  f"{r.get('name', '')}")
            for e in r["errors"]:
                print(f"      - {e}")
        print(f"\n{len(results) - len(bad)}/{len(results)} PASS；"
              f"active {sum(1 for r in results if r.get('status') == 'active')} 张")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
