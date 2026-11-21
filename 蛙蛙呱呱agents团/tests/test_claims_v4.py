# -*- coding: utf-8 -*-
"""claims_v4 自测：检测器 / 编码 / 校验 / 迁移。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import claims_v4 as c4  # noqa: E402

OK, FAIL = [], []


def check(name, cond, msg=""):
    (OK if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" :: {msg}" if msg and not cond else ""))


def main() -> int:
    rows = [{"label": "社区自雇", "value": 5.85}, {"label": "社区雇人", "value": 8.97},
            {"label": "前置仓", "value": 46.81}, {"label": "商场店", "value": 26.81}]
    fs = c4.detect(rows, " 万元")
    types = {f["type"] for f in fs}
    check("detect_extreme", "extreme" in types)
    check("detect_gap", "gap" in types)
    check("detect_concentration", "concentration" in types)

    claim = {"id": "C1", "claim": "10 万预算只有社区自雇店能打平",
             "decision_rank": 1,
             "headline": "社区自雇 5.85 万元/月",
             "table": {"columns": ["形态", "平衡点"], "rows": [["社区自雇", 5.85]]},
             "action": "先做社区自雇店，不做前置仓",
             "falsifier": "若平衡点超过 8 万元/月则本节作废",
             "rows": rows, "encoding": {"mark": "bar", "y": "label"},
             "unit": "万元", "refs": ["N1", "N2", "N3", "N4"],
             "findings": fs, "warrant": "平衡点=固定成本÷(毛利率-变动费用率)",
             "tier": "main"}
    ch = c4.encoding_to_chart(claim)
    check("chart_bar", ch["type"] == "hbar" and len(ch["items"]) == 4, ch)
    check("chart_unit", ch["unit_meta"] == "万元")
    check("chart_refs", ch["refs"] == ["N1", "N2", "N3", "N4"])

    check("validate_ok", c4.validate_v4([claim]) == [], c4.validate_v4([claim]))
    bad = dict(claim, findings=[], warrant="")
    errs = c4.validate_v4([bad])
    check("validate_catches_missing", any("findings" in e for e in errs) and any("warrant" in e for e in errs), errs)

    sec = c4.claim_to_section(claim, 1)
    check("section_five_blocks", len(sec["reading"]) >= 2 and sec["chart"] and sec["boundary"] == "")
    check("section_title_claim", sec["title"] == claim["claim"])

    sup = dict(claim, id="C2", tier="support")
    secs = c4.build_sections({"claims": [sup, claim]})
    check("support_to_appendix", secs[-1].get("appendix") is True and secs[0].get("appendix") is not True)

    print(f"\n{len(OK)}/{len(OK)+len(FAIL)} passed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
