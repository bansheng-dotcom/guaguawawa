# -*- coding: utf-8 -*-
"""报告契约 / 图表单位 / 决策纸 / 80 图例 —— 升级后的硬约束回归。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import chart_units, claims_v4, report_contract  # noqa: E402
from scripts.audit_report_contract import audit as audit_contract  # noqa: E402


def test_contract_is_single_source():
    c = report_contract.load()
    assert c["paragraph_max_chars"] == 300
    assert c["paragraph_hard_max_chars"] == 330
    assert c["main_claims_max"] == 0
    assert c["decision_page"] is True
    assert c["chart_unit_strict"] is True


def test_prose_policy_matches_flow_standard():
    import yaml
    raw = yaml.safe_load((ROOT / "configs" / "report_prose.yaml").read_text(encoding="utf-8"))
    assert raw["prose"]["chars_per_section"] == [1000, 1600]
    assert raw["prose"]["chars_hard_min"] == 800


def test_chart_units_drop_mixed_units():
    pack = {"numbers": [
        {"id": "r1", "name": "月营收", "value": 12, "unit": "万元"},
        {"id": "r2", "name": "门店数", "value": 3, "unit": "家"},
        {"id": "r3", "name": "月租金", "value": 2, "unit": "万元"},
    ]}
    chart = {"type": "hbar", "items": [
        {"label": "月营收", "value": 12, "ref": "r1"},
        {"label": "门店数", "value": 3, "ref": "r2"},
        {"label": "月租金", "value": 2, "ref": "r3"},
    ]}
    out = chart_units.sanitize(chart, pack)
    assert out is not None
    assert out["unit_meta"] == "万元"
    assert len(out["items"]) == 2
    assert {i["unit"] for i in out["items"]} == {"万元"}


def test_claims_section_count_is_adaptive():
    claims = []
    for i in range(9):
        claims.append({
            "id": f"J{i}", "claim": f"判断{i}", "tier": "main",
            "rows": [{"label": "a", "value": 1, "unit": "%"},
                     {"label": "b", "value": 2, "unit": "%"}],
            "encoding": {"mark": "bar"},
            "findings": [{"type": "extreme", "text": "x"}],
            "warrant": "w", "action": "a", "falsifier": "f",
            "table": {"columns": ["a"], "rows": [["1"]]},
        })
    secs = claims_v4.build_sections({"claims": claims})
    assert sum(1 for s in secs if not s.get("appendix")) == 9
    assert sum(1 for s in secs if s.get("appendix")) == 0


def test_validate_rejects_mixed_unit_and_missing_table():
    c = {
        "id": "J1", "claim": "混单位", "tier": "main",
        "decision_rank": 1, "headline": "1%",
        "rows": [{"label": "a", "value": 1, "unit": "元"},
                 {"label": "b", "value": 2, "unit": "家"}],
        "encoding": {"mark": "bar"},
        "findings": [{"type": "extreme", "text": "x"}],
        "warrant": "w", "action": "a", "falsifier": "f",
    }
    errs = claims_v4.validate_v4([c])
    assert any("混单位" in e for e in errs)
    assert any("缺 table" in e for e in errs)


def test_audit_contract_finds_mixed_units_and_long_paragraph():
    c = {
        "decision": {"items": [{"claim": "x", "number": "1", "action": "a", "stop": "s"}]},
        "sections": [{
            "title": "测试节", "refs": ["N1"],
            "reading": [{"text": "长" * 400}],
            "chart": {"type": "hbar", "unit_meta": "%", "items": [
                {"label": "a", "value": 1, "unit": "%"},
                {"label": "b", "value": 2, "unit": "元"},
            ]},
        }],
    }
    res = audit_contract(c)
    assert res["hard"]
    assert any("图混单位" in x for x in res["hard"])
    assert any("400 字" in x for x in res["hard"])


def test_chart_gallery_has_80_examples():
    p = ROOT / "docs" / "chart-gallery.json"
    assert p.is_file(), "先跑 python scripts/gen_chart_gallery.py"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert len(data) == 80
    assert all(x.get("type") for x in data)


def test_compile_infers_block_labels():
    from scripts.compile_agent_report import _infer_strong, _strip_label
    assert _infer_strong("【事实】数字是 1") == "事实\u3000"
    assert _infer_strong("【机理】因为成本刚性") == "机理\u3000"
    assert _infer_strong("【反例】若毛利 60% 则不成立") == "反例\u3000"
    assert _strip_label("【机理】因为成本刚性") == "因为成本刚性"


def test_chart_type_follows_relation():
    from core.report_flow import _chart_for_metric, _short_label
    assert _chart_for_metric("盈亏平衡") == "dot"
    assert _chart_for_metric("份额") == "share_bar"
    assert _chart_for_metric("增速") == "vbar"
    assert "模型·" not in _short_label("模型·前置仓盈亏平衡月销")


def test_appendix_is_split_into_sources_support_caliber():
    from core.report_theme.pages import _sources_page, _support_page
    c = {"sections": [], "sources": [{"id": f"S{i}", "title": f"来源{i}"}
                                     for i in range(30)],
         "boundaries": ["条件 A", "条件 B"]}
    src = _sources_page(c, 19, 21)
    assert 'id="s-A1"' in src and "附录 A" in src
    assert all(f"S{i}" in src for i in range(30))  # 来源全部在一页
    sup = _support_page(c, 20, 21, support=[{"title": "支撑判断 A"}])
    assert 'id="s-B1"' in sup and "附录 B" in sup
    assert "事实" not in sup  # 附录不套五块模板


def test_structure_profiles_are_module_sets():
    from core import report_structure
    assert report_structure.profile_for("决策简报") == "decision"
    assert report_structure.profile_for("一页纸") == "brief"
    mods = report_structure.modules({"structure_profile": "decision"})
    assert "decision" in mods and "support" not in mods
    assert "sources" in mods and "caliber" in mods


def test_first_line_indent_is_typographic():
    for p in (ROOT / "core" / "report_theme" / "kit.py",
              ROOT / "core" / "report_theme" / "consulting.css"):
        assert "text-indent:2em" in p.read_text(encoding="utf-8")


def _mk_claim(i: int, rank: int, headline: str = "") -> dict:
    return {
        "id": f"J{i}", "claim": f"判断{i}", "tier": "main", "decision_rank": rank,
        "headline": headline or f"{i}%",
        "rows": [{"label": "a", "value": i, "unit": "%"},
                 {"label": "b", "value": i + 1, "unit": "%"}],
        "encoding": {"mark": "bar"},
        "findings": [{"type": "extreme", "text": "x"}],
        "warrant": "w", "action": "a", "falsifier": "f",
        "table": {"columns": ["a"], "rows": [["1"]]},
    }


def test_decision_rank_controls_order_and_cap():
    claims = [_mk_claim(i, rank=i) for i in range(1, 10)]
    secs = claims_v4.build_sections({"claims": claims})
    assert [s["title"] for s in secs[:3]] == ["判断1", "判断2", "判断3"]
    assert sum(1 for s in secs if not s.get("appendix")) == 9


def test_headline_is_authored_not_guessed():
    c = _mk_claim(1, 1)
    c["headline"] = "5.85 万元/月（模型值）"
    dec = claims_v4.build_decision({"claims": [c]})
    assert dec["items"][0]["number"] == "5.85 万元/月（模型值）"


def test_chart_relation_adapter_guards_payload():
    from core import chart_relation as cr
    items = [{"label": "a", "value": 10}, {"label": "b", "value": 8},
             {"label": "c", "value": 5}]
    assert cr.adapt("flow", items)["type"] == "funnel"
    assert cr.adapt("composition", items)["type"] == "share_bar"
    assert cr.adapt("change_over_time", items)["type"] == "dot"  # 没有期次
    assert cr.adapt("spatial", items) is None  # 没有地理标签
    geo = [{"label": "北京", "value": 10}, {"label": "上海", "value": 8}]
    assert cr.adapt("spatial", geo)["type"] == "choropleth"
    link = {"nodes": ["a", "b"], "links": [[0, 1, 5]]}
    assert cr.adapt("flow", items, payload=link)["type"] == "sankey"
    assert cr.adapt("network", items, payload={"nodes": ["a", "b"],
                                               "edges": [["a", "b", 0.5]]})["type"] == "network"
    assert cr.adapt("correlation", items, payload={"points": [
        {"x": 1, "y": 2}, {"x": 2, "y": 4}]})["type"] == "scatter"




