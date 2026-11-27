# -*- coding: utf-8 -*-
"""R10 机制单测：设计契约 12 条 + 2 套风格包 + 视觉评审清单。"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import design_contract as dc  # noqa: E402


def test_contract_rules_are_twelve():
    assert [r["id"] for r in dc.RULES] == [f"P{i}" for i in range(1, 13)]
    assert len({r["gate"] for r in dc.RULES}) == 12


def test_goldens_pass_all_rules(tmp_path):
    out = dc.build_goldens(str(tmp_path))
    assert out["ok"] is True
    for name, res in out["goldens"].items():
        assert res["ok"] is True, (name, res["violations"])
        assert res["stats"]["rules_checked"] == 12
    assert set(out["goldens"]) == {"design-editorial.html", "design-internet.html"}


def test_two_style_packs_exist():
    out = dc.style_packs()
    assert out["ok"] is True
    ids = [p["id"] for p in out["packs"]]
    assert ids == ["editorial-evidence-report", "internet-reporting"]
    for p in out["packs"]:
        assert p["files"]["page_style.yaml"] and p["files"]["sample.html"]


def test_visual_review_checklist_complete():
    out = dc.visual_review()
    assert out["ok"] is True, out["missing"]
    assert out["items"] == [f"V{i}" for i in range(1, 11)]


def test_each_rule_can_fail():
    cases = {
        "P1_italic": dict(inject_css="p{font-style:italic}"),
        "P7_measure": dict(drop=("measure",)),
        "P10_table": dict(drop=("drop_thead",)),
        "P12_heading": dict(mutations=("skip_heading",)),
    }
    for gate, kw in cases.items():
        out = dc.check_html(dc.render_delivery("editorial-evidence-report", **kw))
        assert out["ok"] is False, gate
        assert gate in {v["id"] for v in out["violations"]}, (gate, out["violations"])


def test_misuse_cases_are_rejected():
    for name in ("italic-no-measure.json", "skip-heading-no-thead.json"):
        out = dc.check_case(os.path.join(HERE, "misuse", name))
        assert out["rejected"] is True, name
        assert out["as_expected"] is True, (name, out["hit"], out["expect"])
