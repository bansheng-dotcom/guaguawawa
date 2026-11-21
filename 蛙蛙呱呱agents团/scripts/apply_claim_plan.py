#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把作者给的 decision_plan 落到 claims：tier / decision_rank / headline。

系统层工具，不绑定具体项目：
    python scripts/apply_claim_plan.py \
      --claims projects/x/out/claims_merged.json \
      --plan projects/x/decision_plan.json \
      --out projects/x/out/claims_ranked.json

plan 以 1-based 节号索引（也可用 title 前缀），每项：
    {"tier": "main|support", "decision_rank": 1, "headline": "5.85 万元/月"}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def apply(claims: dict, plan: dict) -> dict:
    sections = list(claims.get("sections") or [])
    by_title = {str(s.get("title") or ""): i + 1 for i, s in enumerate(sections)}
    applied = set()
    for key, cfg in (plan.get("sections") or {}).items():
        idx = None
        if str(key).isdigit():
            idx = int(key) - 1
        else:
            for title, i in by_title.items():
                if title.startswith(str(key)):
                    idx = i - 1
                    break
        if idx is None or not (0 <= idx < len(sections)):
            raise SystemExit(f"plan 指向不存在的节：{key}")
        s = sections[idx]
        tier = str(cfg.get("tier") or "support")
        if tier not in ("main", "support"):
            raise SystemExit(f"节 {key} tier 非法：{tier}")
        s["tier"] = tier
        if tier == "main":
            if cfg.get("decision_rank") is None:
                raise SystemExit(f"节 {key} 是 main 但缺 decision_rank")
            if not cfg.get("headline") and not cfg.get("headline_ref"):
                raise SystemExit(f"节 {key} 是 main 但缺 headline/headline_ref")
            s["decision_rank"] = int(cfg.get("decision_rank"))
            if cfg.get("headline"):
                s["headline"] = str(cfg["headline"])
            if cfg.get("action"):
                s["action"] = str(cfg["action"])
            if cfg.get("relation"):
                s["relation"] = str(cfg["relation"])
            if cfg.get("chart"):
                s["chart"] = cfg["chart"]
        else:
            s.pop("decision_rank", None)
            s.pop("headline", None)
            s.pop("action", None)
        applied.add(idx)
    # 没写进 plan 的一律降为 support，避免“忘了标”又混进正文
    for i, s in enumerate(sections):
        if i not in applied:
            s["tier"] = "support"
            s.pop("decision_rank", None)
            s.pop("headline", None)
            s.pop("action", None)
    return claims


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="apply_claim_plan")
    ap.add_argument("--claims", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    claims = json.loads(Path(a.claims).read_text(encoding="utf-8-sig"))
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8-sig"))
    out = apply(claims, plan)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    mains = [s for s in out["sections"] if s.get("tier") == "main"]
    print(json.dumps({"ok": True, "out": a.out, "main": len(mains),
                      "ranks": sorted(s.get("decision_rank") for s in mains)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
