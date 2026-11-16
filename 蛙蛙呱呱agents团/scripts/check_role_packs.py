# -*- coding: utf-8 -*-
"""校验 20 个角色领域包：书、方法、指标、决策、远见、误判、章节。

拦八类问题：
1. 角色数不是 20，或 r01—r20 缺失；
2. 每个角色书 <5，或没有中/英文书；
3. 方法 <6，或方法没有公式/算法（只有名词）；
4. 指标 <6、决策 <4、远见 <3、误判 <4、报告章节 <6；
5. 关键词 <3（无法做业务线匹配）；
6. 书缺作者/年份/概念/动作；
7. 角色 domain 为空或重复；
8. JSON schema 不是 dsh.role_domain/v1。

用法：python scripts/check_role_packs.py [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
ROLES = ROOT / "knowledge" / "roles"
EXPECT = [f"r{i:02d}" for i in range(1, 21)]
REQ = ("role", "name", "title", "domain", "keywords", "books", "methods",
       "kpis", "decisions", "foresight", "failure_modes", "report_sections")


def check_one(p: Path) -> Dict:
    errs: List[str] = []
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        return {"file": p.name, "ok": False, "errors": [f"JSON 解析失败: {e}"]}
    if d.get("schema") != "dsh.role_domain/v1":
        errs.append(f"schema 非法: {d.get('schema')}")
    for k in REQ:
        if not d.get(k):
            errs.append(f"缺字段 {k}")
    if errs:
        return {"file": p.name, "ok": False, "errors": errs}

    books = d["books"]
    if len(books) < 5:
        errs.append(f"书 {len(books)} 本 <5")
    langs = {b.get("lang") for b in books}
    if "zh" not in langs or "en" not in langs:
        errs.append("书单缺中文或英文来源")
    for i, b in enumerate(books):
        for k in ("title", "author", "year", "concept", "move"):
            if not b.get(k):
                errs.append(f"books[{i}] 缺 {k}")
        if not isinstance(b.get("year"), int):
            errs.append(f"books[{i}] year 不是整数")

    methods = d["methods"]
    if len(methods) < 6:
        errs.append(f"方法 {len(methods)} 条 <6")
    for i, m in enumerate(methods):
        for k in ("name", "formula", "when"):
            if not m.get(k):
                errs.append(f"methods[{i}] 缺 {k}")
        if len(str(m.get("formula") or "")) < 8:
            errs.append(f"methods[{i}] formula 太短（像名词不像算法）")

    for k, n in (("kpis", 6), ("decisions", 4), ("foresight", 3),
                 ("failure_modes", 4), ("report_sections", 6), ("keywords", 3)):
        if len(d.get(k) or []) < n:
            errs.append(f"{k} {len(d.get(k) or [])} < {n}")
    return {"file": p.name, "role": d.get("role"), "domain": d.get("domain"),
            "books": len(books), "methods": len(methods),
            "ok": not errs, "errors": errs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_role_packs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    files = sorted(ROLES.glob("r*.json"))
    results = [check_one(p) for p in files]
    present = {r.get("role") for r in results}
    missing = [r for r in EXPECT if r not in present]
    domains: Dict[str, str] = {}
    for r in results:
        d = r.get("domain")
        if d and d in domains:
            r["ok"] = False
            r["errors"].append(f"domain 与 {domains[d]} 重复")
        domains[d] = r.get("file", "")
    bad = [r for r in results if not r["ok"]]
    if a.json:
        print(json.dumps({"missing": missing, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"{mark}  {r['file']:<10} {r.get('role', '-'):<4} "
                  f"{r.get('domain', ''):<14} 书 {r.get('books', 0)} 方法 {r.get('methods', 0)}")
            for e in r["errors"]:
                print(f"      - {e}")
        if missing:
            print(f"缺角色: {', '.join(missing)}")
        print(f"\n{len(results) - len(bad)}/{len(results)} PASS；"
              f"角色 {len(present)}/20；书 {sum(r.get('books', 0) for r in results)} 本；"
              f"方法 {sum(r.get('methods', 0) for r in results)} 条")
    return 0 if not bad and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
