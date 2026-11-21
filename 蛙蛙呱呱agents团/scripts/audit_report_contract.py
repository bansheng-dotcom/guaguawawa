#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按报告契约审计一份 contract.json：段落、主判断、图单位、决策纸、标题。

不替代 check_report_flow（那是成品门禁）；这里查的是「结构契约」，
能在渲染前发现问题，避免又用补丁把稿子凑过门禁。

用法：
    python scripts/audit_report_contract.py --contract projects/x/out/contract.json
退出码：0 = 无硬伤；1 = 有硬伤；2 = 文件读不了。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import report_contract  # noqa: E402


def audit(c: dict) -> dict:
    cfg = report_contract.load()
    hard, warn = [], []
    secs = [s for s in (c.get("sections") or []) if not s.get("appendix")]
    # 1) 段落
    limit = int(cfg.get("paragraph_hard_max_chars") or 330)
    for s in secs:
        for j, r in enumerate(s.get("reading") or [], 1):
            n = len(str(r.get("text") or ""))
            if n > limit:
                hard.append(f"节「{str(s.get('title'))[:16]}」解读{j} {n} 字 > {limit}")
    # 2) 主判断
    main_max = int(cfg.get("main_claims_max") or 7)
    if len(secs) > main_max:
        warn.append(f"正文 {len(secs)} 节 > 主判断上限 {main_max}；第 {main_max + 1} 节起应进附录")
    if cfg.get("decision_fields_required"):
        for s in secs:
            tag = str(s.get("title"))[:16]
            if s.get("decision_rank") is None:
                hard.append(f"节「{tag}」缺 decision_rank（禁止渲染层猜主判断顺序）")
            if not str(s.get("headline") or "").strip() and not str(s.get("headline_ref") or "").strip():
                hard.append(f"节「{tag}」缺 headline/headline_ref（决策数字必须作者给）")
    # 3) 图单位 / 点数
    for s in secs:
        ch = s.get("chart") or {}
        if not ch:
            continue
        items = ch.get("bars") or ch.get("items") or ch.get("points") or []
        units = {str(x.get("unit")) for x in items if isinstance(x, dict) and x.get("unit")}
        if len(units) > 1:
            hard.append(f"节「{str(s.get('title'))[:16]}」图混单位：{sorted(units)[:3]}")
        if not ch.get("unit_meta") and not units:
            hard.append(f"节「{str(s.get('title'))[:16]}」图缺 unit_meta")
        rows = ch.get("rows") or []
        if rows and len(items) != len(rows):
            hard.append(f"节「{str(s.get('title'))[:16]}」图点数 {len(items)} ≠ slice {len(rows)}")
    # 4) 决策纸
    dec = c.get("decision") or {}
    ditems = dec.get("items") or []
    if cfg.get("decision_page"):
        if not ditems:
            hard.append("缺决策纸（decision.items 为空）")
        elif not (3 <= len(ditems) <= int(cfg.get("decision_items_max") or 5)):
            warn.append(f"决策纸 {len(ditems)} 条，建议 3–{cfg.get('decision_items_max') or 5} 条")
        for it in ditems:
            if not it.get("number"):
                warn.append(f"决策项「{str(it.get('claim'))[:16]}」缺数字")
            if not it.get("action") or it.get("action") == "待验证":
                warn.append(f"决策项「{str(it.get('claim'))[:16]}」缺动作")
    # 5) 标题
    tmax = int(cfg.get("title_max_chars") or 20)
    long_titles = [s for s in secs if len(str(s.get("title") or "")) > tmax]
    if long_titles:
        warn.append(f"{len(long_titles)} 个节标题 > {tmax} 字（例如「{str(long_titles[0].get('title'))[:24]}」）")
    # 6) 封面指标去重
    vals = [m.get("value") for m in (c.get("metric_strip") or [])]
    if len(vals) != len(set(vals)):
        warn.append("封面指标有重复值")
    return {"hard": hard, "warn": warn,
            "counts": {"sections": len(secs), "decision": len(ditems),
                       "charts": sum(1 for s in secs if s.get("chart"))}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="audit_report_contract")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    p = Path(a.contract)
    if not p.is_file():
        print(f"读不到 {p}", file=sys.stderr)
        return 2
    c = json.loads(p.read_text(encoding="utf-8-sig"))
    res = audit(c)
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 1 if res["hard"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
