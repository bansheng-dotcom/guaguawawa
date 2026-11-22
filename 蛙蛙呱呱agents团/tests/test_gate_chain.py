# -*- coding: utf-8 -*-
"""test_gate_chain —— 四层门禁链单测。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import gate_chain  # noqa: E402


def _w(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _project(tmp_path: Path):
    proj = tmp_path / "proj"
    _w(proj / "plan" / "pre_issue_gates.json",
       {"ok": True, "passed": 13, "total": 13})
    _w(proj / "plan" / "post_gates.json",
       {"ok": True, "passed": 25, "total": 25, "checks": []})
    _w(proj / "contract.json", {"sections": [
        {"index": 1, "title": "页一", "chart": {"chart_validation": {"ok": True}}},
        {"index": 2, "title": "页二", "chart": {"chart_validation": {"ok": True}}},
    ]})
    _w(proj / "ir_shadow.json", {"sections": [
        {"title": "页一"}, {"title": "页二"},
    ]})
    return proj


def test_chain_all_ok(tmp_path):
    proj = _project(tmp_path)
    r = gate_chain.run(str(proj))
    assert r["ok"] is True
    assert r["failures"] == []
    assert r["layers"]["L1"]["detail"]["post_passed"] == "25/25"


def test_l1_fails_when_post_gates_fail(tmp_path):
    proj = _project(tmp_path)
    _w(proj / "plan" / "post_gates.json",
       {"ok": False, "passed": 19, "total": 25,
        "checks": [{"id": "G1", "ok": False}]})
    r = gate_chain.run(str(proj))
    assert r["ok"] is False
    assert "L1" in r["failures"]
    assert "G1" in r["layers"]["L1"]["detail"]["post_fail"]


def test_l2_fails_on_title_mismatch(tmp_path):
    proj = _project(tmp_path)
    _w(proj / "ir_shadow.json", {"sections": [{"title": "页一"}, {"title": "页三"}]})
    r = gate_chain.run(str(proj))
    assert "L2" in r["failures"]


def test_l2_fails_without_shadow(tmp_path):
    proj = _project(tmp_path)
    (proj / "ir_shadow.json").unlink()
    r = gate_chain.run(str(proj))
    assert "L2" in r["failures"]


def test_l3_fails_on_bad_chart(tmp_path):
    proj = _project(tmp_path)
    _w(proj / "contract.json", {"sections": [
        {"index": 1, "title": "页一",
         "chart": {"chart_validation": {"ok": False, "reason": "hbar 不能表达 composition"}}},
    ]})
    _w(proj / "ir_shadow.json", {"sections": [{"title": "页一"}]})
    r = gate_chain.run(str(proj))
    assert "L3" in r["failures"]


def test_l4_skipped_without_html(tmp_path):
    proj = _project(tmp_path)
    r = gate_chain.run(str(proj), html_path=None)
    assert r["layers"]["L4"]["ok"] is True
    assert r["layers"]["L4"]["detail"].get("skipped")
