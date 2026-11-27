# -*- coding: utf-8 -*-
"""report_pipeline 域测试（合并自 7 个文件）。

源文件：
    test_report_contract_v4.py —— 报告契约 / 图表单位 / 决策纸 / 80 图例 —— 升级后的硬约束回归。
    test_report_flow.py —— 唯一报告产线的回归测试（2026-11-15 收敛后）。
    test_report_flow_opt.py —— SOP 优化项的回归测试（2026-11-16）。
    test_report_model.py —— 报告模型审计的回归测试（v12）。
    test_report_sections.py —— 调研级报告（章节稿 + 证据包逐节过账）的回归测试。
    test_decision_report.py —— 决策契约与决策优先产线的单元测试（不跑完整渲染）。
    test_semantic_pipeline.py —— test_semantic_pipeline —— S5a 语义管道单测。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


import json
from core.charts import chart_units
from core.claims import claims as claims_model  # P5-4：映射层已并入 claims
from core.report import report_contract
from scripts.audit_report_contract import audit as audit_contract
from core.report import report_flow
from core.report_kernel import structure
import pytest
import re
from core.data import evidence_pack
from core.report import report_flow, report_renderer
from core.report import report_model
from core.data import evidence_pack
from core.report import report_flow
import os
from core import decision
from core.semantic_pipeline import resolve, panel, apply_decisions



# ====================================================================
# 合并自 test_report_contract_v4.py：报告契约 / 图表单位 / 决策纸 / 80 图例 —— 升级后的硬约束回归。
# ====================================================================
# -*- coding: utf-8 -*-


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
        {"id": "r4", "name": "月水电", "value": 1, "unit": "万元"},
    ]}
    chart = {"type": "hbar", "items": [
        {"label": "月营收", "value": 12, "ref": "r1"},
        {"label": "门店数", "value": 3, "ref": "r2"},
        {"label": "月租金", "value": 2, "ref": "r3"},
        {"label": "月水电", "value": 1, "ref": "r4"},
    ]}
    out = chart_units.sanitize(chart, pack)
    assert out is not None
    assert out["unit_meta"] == "万元"
    # 2026-11-23：门槛提到 ≥3 点，混单位过滤后剩 3 个「万元」点
    assert len(out["items"]) == 3
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
    secs = claims_model.build_sections({"claims": claims})
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
    errs = claims_model.validate_v4([c])
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
    from core.report.report_flow import _chart_for_metric, _short_label
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
    from core.report import report_structure
    assert report_structure.profile_for("决策简报") == "decision"
    assert report_structure.profile_for("一页纸") == "brief"
    mods = report_structure.modules({"structure_profile": "decision"})
    assert "decision" in mods and "support" not in mods
    assert "sources" in mods and "caliber" in mods


def test_body_has_no_first_line_indent():
    # 2026-11-23：正文取消首行缩进（2em）与两端对齐。
    # 原因：2em 缩进让每段左边缘呈锯齿，与左侧 13mm 块标签打架；
    # justify 在中文夹数字/百分号时把字距拉开，同一段每行松紧不一，看上去"换行很丑"。
    # 两条都要在源里锁住，否则改一次主题就会回潮。
    for p in (ROOT / "core" / "report_theme" / "kit.py",
              ROOT / "core" / "report_theme" / "consulting.css"):
        css = p.read_text(encoding="utf-8")
        assert "text-indent:2em" not in css
        assert "text-indent:0" in css


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
    secs = claims_model.build_sections({"claims": claims})
    assert [s["title"] for s in secs[:3]] == ["判断1", "判断2", "判断3"]
    assert sum(1 for s in secs if not s.get("appendix")) == 9


def test_headline_is_authored_not_guessed():
    c = _mk_claim(1, 1)
    c["headline"] = "5.85 万元/月（模型值）"
    dec = claims_model.build_decision({"claims": [c]})
    assert dec["items"][0]["number"] == "5.85 万元/月（模型值）"


def test_chart_relation_adapter_guards_payload():
    from core.charts import chart_relation as cr
    items = [{"label": "a", "value": 10}, {"label": "b", "value": 8},
             {"label": "c", "value": 5}]
    assert cr.adapt("flow", items)["type"] == "funnel"
    assert cr.adapt("composition", items)["type"] == "share_bar"
    assert cr.adapt("change_over_time", items)["type"] == "dot"  # 没有期次
    assert cr.adapt("spatial", items) is None  # 没有地理标签
    geo = [{"label": "北京市", "value": 10}, {"label": "上海市", "value": 8}]
    assert cr.adapt("spatial", geo)["type"] == "choropleth"
    link = {"nodes": ["a", "b"], "links": [[0, 1, 5]]}
    assert cr.adapt("flow", items, payload=link)["type"] == "sankey"
    assert cr.adapt("network", items, payload={"nodes": ["a", "b"],
                                               "edges": [["a", "b", 0.5]]})["type"] == "network"
    assert cr.adapt("correlation", items, payload={"points": [
        {"x": 1, "y": 2}, {"x": 2, "y": 4}]})["type"] == "scatter"


# ====================================================================
# 合并自 test_report_flow.py：唯一报告产线的回归测试（2026-11-15 收敛后）。
# ====================================================================
# -*- coding: utf-8 -*-


for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


GOOD_REPORT = {
    "title": "Q4 复盘",
    "meta": {"audience": "管理层", "purpose": "决定加投"},
    "chapters": [
        {"title": "结论", "summary": "复购是主因", "paragraphs": ["复购 +18%"]},
        {"title": "流量", "summary": "自然升转化降"},
        {"title": "动作", "summary": "先修履约"},
    ],
    "thesis": ["复购 62%", "履约漏点", "只投 ROI>2"],
    "sources": [{"label": "生意参谋"}, {"label": "财务月报"}, {"label": "履约系统"}],
}

FIX = TEAM / "fixtures" / "report_flow"


def test_structure_guard_single_implementation():
    assert structure.guard(GOOD_REPORT)["violations"] == []
    bad = {**GOOD_REPORT, "thesis": ["只有一条"]}
    assert structure.guard(bad)["violations"]


def test_build_contract_shape():
    j = {"headline": "GMV 下降 3.2%",
         "conclusions": [{"text": "GMV 下降 3.2%", "number": "-3.2",
                          "source": "r06/semantics", "kind": "finding"}],
         "drivers": [], "boundary": ["只对本次输入成立"],
         "actions": [{"do": "复算", "condition": "对外时", "stop": "不一致即停"}],
         "gaps": []}
    ev = [{"role": "r06", "skill": "semantics", "action": "validate",
           "source": "x.json", "source_hash": "h"}]
    nums = [{"path": "gmv.delta_pct", "value": -3.2, "text": "-3.2",
             "source": "r06/semantics"}]
    c = report_flow.build_contract(j, "测试诊断", "A", ev, nums,
                                   [{"id": "x", "ok": True}], "rule")
    assert c["title_lines"][0] == "测试诊断"
    assert c["sections"][-1]["title"] == "口径与分数"
    assert c["sections"][-2].get("appendix") is True
    assert structure.layout_errors(c, require_appendix=True) == []


def test_run_requires_evidence_and_draft(tmp_path):
    with pytest.raises(report_flow.FlowError):
        report_flow.run(intent="2月经营诊断", out_dir=str(tmp_path / "b"))


# ====================================================================
# 合并自 test_report_flow_opt.py：SOP 优化项的回归测试（2026-11-16）。
# ====================================================================
# -*- coding: utf-8 -*-


for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _pack(tmp_path) -> dict:
    return {
        "schema": "dsh.evidence_pack/v1", "project": "t", "root": str(tmp_path),
        "numbers": [{"id": "A1", "name": "社零", "value": 1.0, "unit": "亿元"}],
        "sources": [{"file": "obs.json", "kind": "json", "hash": "abc", "numbers": 1}],
        "counts": {"files": 1, "numbers": 1},
    }


def _draft() -> dict:
    return {
        "standfirst": "测试用结论 12",
        "summary": ["测试用结论 12"],
        "sections": [{
            "title": "1 测试节：有数字 12",
            "question": "q",
            "reading": [{"text": "证据 12", "refs": ["A1"]}],
            "chart": {"type": "hbar", "title": "图 12", "unit_meta": "亿元",
                      "source": "obs.json",
                      "bars": [{"label": "a", "value": 1}]},
            "charts": [{"type": "hbar", "title": "第二张 3", "unit_meta": "亿元",
                        "source": "obs.json", "bars": [{"label": "b", "value": 2}]}],
            "intro": [{"text": "导语 12"}],
            "why": "为什么做 12",
            "refs": ["A1"],
        }],
        "boundaries": ["只对样本成立 1", "不含税 2"],
    }


def test_boundaries_reach_final_section(tmp_path):
    contract = report_flow.build_sections_contract(_draft(), _pack(tmp_path))
    tail = contract["sections"][-1]
    assert tail["title"] == "口径与分数"
    joined = " ".join(r.get("text", "") for r in tail["reading"])
    assert "只对样本成立 1" in joined and "不含税 2" in joined


def test_charts_and_section_fields_pass_through(tmp_path):
    contract = report_flow.build_sections_contract(_draft(), _pack(tmp_path))
    sec = contract["sections"][0]
    assert sec["charts"][0]["title"] == "第二张 3"
    assert sec["intro"][0]["text"] == "导语 12"
    assert sec["why"].startswith("为什么做")
    assert sec["refs"] == ["A1"]


def test_gate_blocks_render(tmp_path, monkeypatch):
    monkeypatch.setattr(report_flow, "check_sections",
                        lambda *a, **k: {"ok": True, "sections": 1, "checks": {}})
    monkeypatch.setattr(report_flow, "layout_errors", lambda *a, **k: ["forced"])
    monkeypatch.setattr(evidence_pack, "load", lambda *a, **k: _pack(tmp_path))
    out = tmp_path / "out"
    res = report_flow.run("测试", out_dir=str(out), draft=_draft(), evidence=str(tmp_path))
    assert res["ok"] is False
    assert not (out / "report.html").exists(), "门禁不过时不许落盘"


def test_appendix_ids_unique_and_string_cells(tmp_path):
    contract = report_flow.build_sections_contract(_draft(), _pack(tmp_path))
    # 追加一张表，单元格用裸字符串（手写 draft 的常见写法）
    contract["sections"][0]["table"] = {
        "caption": "表 1", "columns": ["列 A", "列 B"],
        "rows": [["x", "1"], ["y", "2"]],
        "total_row": ["合计", "3"],
    }
    html = report_renderer.render(contract)
    ids = re.findall(r'id="(s-[^"]+)"', html)
    assert len(ids) == len(set(ids)), f"section id 重复: {ids}"
    assert "s-A1" in ids
    assert "<td>x</td>" in html


# ====================================================================
# 合并自 test_report_model.py：报告模型审计的回归测试（v12）。
# ====================================================================
# -*- coding: utf-8 -*-


def test_model_nodes_exist_and_are_nonempty():
    m = report_model.build()
    n = m["nodes"]
    assert n["methods"] >= 20
    assert n["charts"] == 48
    assert n["roles"] == 20
    assert n["chart_config"] >= 1


def test_integrity_shape_is_stable():
    m = report_model.build()
    i = m["integrity"]
    for key in ("chart_types_not_in_config",
                "role_sections_without_chart_rule"):
        assert key in i, key
    # v11 / P4：选图配置必须真的被 core/decision.py 读
    assert i["chart_config_read_by_code"] is True


def test_audit_is_clean():
    """剩余三项债必须全为 0。这一条是「不许回退」的硬断言。"""
    m = report_model.audit()
    assert set(m["issues"]) == {
        "图型配置未被代码读取", "图型未进配置", "角色章节无图型规则",
    }
    bad = {k: v for k, v in m["issues"].items() if v}
    assert not bad, f"图型层出现悬空边：{bad}"


# ====================================================================
# 合并自 test_report_sections.py：调研级报告（章节稿 + 证据包逐节过账）的回归测试。
# ====================================================================
# -*- coding: utf-8 -*-


for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _pack_sec(tmp_path):
    numbers = [
        {"id": "A1", "name": "社零", "value": 5375.5, "unit": "亿元", "period": "2025",
         "source_file": "obs.json", "org": "统计局"},
        {"id": "A2", "name": "上年社零", "value": 5615.3, "unit": "亿元", "period": "2024",
         "source_file": "obs.json", "org": "统计局"},
        {"id": "A3", "name": "今年增速", "value": 0.5, "unit": "%", "period": "2026Q3",
         "source_file": "obs.json", "org": "统计局"},
    ]
    pack = {"schema": "dsh.evidence_pack/v1", "project": "t", "root": str(tmp_path),
            "numbers": numbers,
            "sources": [{"file": "obs.json", "kind": "json", "hash": "abc", "numbers": 3}],
            "counts": {"files": 1, "numbers": 3}}
    p = tmp_path / "evidence_pack.json"
    p.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
    return pack, str(p)


def _draft_sec(bad_number: bool = False):
    x = 9999 if bad_number else 239.8
    return {
        "profile": "market_research",
        "title_lines": ["测试市场：5375.5 亿元的盘子在减速"],
        "standfirst": "2025 年社零 5375.5 亿元，增速掉到 0.5%。",
        "metrics": [{"label": "社零", "value": "5375.5 亿", "note": "A1"}],
        "summary": ["盘子还在，但增速只剩 0.5%。"],
        "boundaries": [
            "只对本次输入的三组社零数据成立，不外推到全国",
            "2025 年口径与 2024 年一致，若口径变了本节作废",
            "增速 0.5% 是同比，不是环比",
            "社零 5375.5 亿元未扣价格因素",
            "若下季度增速超过百分之一，减速判断作废",
        ],
        "sections": [
            {"title": "大盘：社零 5375.5 亿元，比上一年少 239.8 亿元",
             "question": "盘子有多大？",
             "refs": ["A1", "A2"],
             "falsifier": "若社零超过 5615.3 亿元，本节作废",
             "chart": {"type": "hbar", "title": "两年社零：5375.5 vs 5615.3",
                       "unit_meta": "亿元", "source": "A1/A2",
                       "refs": ["A1", "A2"],
                       "bars": [{"label": "2025", "value": 5375.5},
                                {"label": "2024", "value": 5615.3}]},
             "reading": [
                 {"text": "2025 年社零 5375.5 亿元，比上一年多 239.8 亿元的降幅；因为基数 5615.3 亿元更高，所以同比少 239.8 亿元。判别方法：看 2025 与 2024 的绝对额差。",
                  "refs": ["A1", "A2"]},
                 {"text": f"补充口径：{x}；因为口径未变，所以两年可比。判别方法：核对来源与期次。",
                  "refs": ["A1", "A2"]},
             ]},
            {"title": "增速：三季度只有 0.5%", "question": "还在不在增长？",
             "refs": ["A3"],
             "falsifier": "若增速超过 1 个百分点，本节作废",
             "reading": [
                 {"text": "2026 年三季度增速不到一个百分点，基本停住；因为基数高，所以增速掉到不到一个百分点。判别方法：看同比增速是否连续两个季度低于百分之一。",
                  "refs": ["A3"]},
                 {"text": "增速口径是同比，不是环比；因为季调不同，所以不能拿环比替代。判别方法：核对报告期，并核对同比基期与本期口径是否一致，若基期被修订则本节结论只保留方向、不保留点位。",
                  "refs": ["A3"]},
                 {"text": "这一段只交代阅读方式：先看方向，再看幅度，最后看口径；方向由同比给出，幅度由绝对额差给出，口径由来源期次给出，三者缺一就不下结论。",
                  "refs": ["A3"]},
             ]},
            {"title": "判断：先保存量，3 条动作", "question": "做什么？",
             "refs": ["A1"],
             "falsifier": "若存量跌破 5000 亿元，本节作废",
             "reading": [
                 {"text": "盘子 5375.5 亿元，先保存量；因为增量只剩不到一个百分点，所以先守住 5375.5 亿元的存量。判别方法：看季度社零是否守住 5375.5 亿元。",
                  "refs": ["A1"]},
                 {"text": "动作按季度验收；因为回款滞后，所以按季度而不是按月验收。判别方法：看季度回款、看季度库存周转、看季度新增投入是否超过当季增量，三项有一项不达标就停手重排。",
                  "refs": ["A1"]},
                 {"text": "预算先按 5375.5 亿元的不到一个百分点增量安排；因为增量薄，所以不扩新品类。判别方法：看新增品类是否超过 239.8 亿元。",
                  "refs": ["A1", "A2"]},
             ]},
            {"title": "风险：0.5% 增速下的三个停手条件", "question": "什么情况下停？",
             "refs": ["A1", "A3"],
             "falsifier": "若增速回到 1 个百分点以上，本节作废",
             "reading": [
                 {"text": "社零 5375.5 亿元、增速不到一个百分点，先设停手线；因为增速薄，所以任何一个月低于百分之一就停。判别方法：看月度同比。",
                  "refs": ["A1", "A3"]},
                 {"text": "库存周转超过两个月就停；因为 5375.5 亿元的盘子不允许压货。判别方法：看周转天数。",
                  "refs": ["A1"]},
                 {"text": "新增投入超过 239.8 亿元就停；因为增量只有 239.8 亿元，投入不能超过增量。判别方法：看投入/增量比。",
                  "refs": ["A1", "A2"]},
             ]},
        ],
        "boundary": ["只对本次输入成立"],
    }


def test_pack_is_addressable(tmp_path):
    pack, path = _pack_sec(tmp_path)
    assert pack["counts"]["numbers"] == 3
    assert evidence_pack.load(path)["numbers"][0]["id"] == "A1"
    ids = {n["id"] for n in evidence_pack.values(pack)}
    assert ids == {"A1", "A2", "A3"}


def test_sections_validate_and_render(tmp_path):
    _, path = _pack_sec(tmp_path)
    out = tmp_path / "out"
    res = report_flow.run(intent="测试", evidence=path, draft=_draft_sec(),
                          out_dir=str(out), prose_hard=False)
    assert res["ok"], res
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["producer"] == "r01" and man["branch"] == "sections"
    assert man["section_check"]["ok"] is True
    c = json.loads((out / "contract.json").read_text(encoding="utf-8"))
    assert c["sections"][-1]["title"] == "口径与分数"
    assert any(s.get("appendix") for s in c["sections"])
    assert (out / "report.html").stat().st_size > 15000


def test_fabricated_number_is_rejected(tmp_path):
    _, path = _pack_sec(tmp_path)
    with pytest.raises(report_flow.FlowError) as e:
        report_flow.run(intent="测试", evidence=path, draft=_draft_sec(bad_number=True),
                        out_dir=str(tmp_path / "bad"))
    assert "239.8" in str(e.value) or "9999" in str(e.value) or "无法" in str(e.value)


# ====================================================================
# 合并自 test_decision_report.py：决策契约与决策优先产线的单元测试（不跑完整渲染）。
# ====================================================================
# -*- coding: utf-8 -*-


def _q(i=1, finding="structure", kind="compare_categories", ctype="hbar", **kw):
    q = {
        "id": f"dq{i}", "text": f"问题{i}？", "decision": "做一个决定",
        "finding": finding, "falsifier": "方向反转即作废",
        "comparison": {"kind": kind, "left": "A", "right": "B",
                       "metric": "变化率", "unit": "%"},
        "chart": {"type": ctype},
    }
    q.update(kw)
    return q


def _ctr(qs, **kw):
    c = {"schema": decision.SCHEMA, "decision": "决定", "auto": False,
         "questions": qs}
    c.update(kw)
    return c


def test_draft_five_questions_and_unique_comparisons():
    ctr = decision.draft("经营诊断", ["structure", "trajectory", "momentum",
                                      "contribution", "economics", "risk"])
    assert len(ctr["questions"]) == 5
    kinds = [q["comparison"]["kind"] for q in ctr["questions"]]
    assert len(set(kinds)) >= 4, kinds          # 不选五个同型对照
    assert decision.validate(ctr)["ok"]


def test_validate_rejects_too_few_questions():
    r = decision.validate(_ctr([_q(1), _q(2)]))
    assert not r["ok"]
    assert any("3–5" in e for e in r["errors"])


def test_validate_rejects_chart_that_cannot_encode_comparison():
    # 时间趋势不能用横条排名表达
    r = decision.validate(_ctr([_q(1), _q(2, "momentum", "compare_two_points",
                                   "grouped_bar"),
                                _q(3, "trajectory", "change_over_time", "line")]))
    bad = _ctr([_q(1, "structure", "compare_categories", "hbar"),
                _q(2, "trajectory", "change_over_time", "hbar"),
                _q(3, "momentum", "compare_two_points", "grouped_bar")])
    r = decision.validate(bad)
    assert not r["ok"]
    assert any("不能表达 change_over_time" in e for e in r["errors"])


def test_validate_rejects_unknown_chart_type():
    bad = _ctr([_q(1), _q(2, "trajectory", "change_over_time", "line"),
                _q(3, "momentum", "compare_two_points", "nope")])
    r = decision.validate(bad)
    assert not r["ok"]
    assert any("48 型" in e for e in r["errors"])


def test_choose_chart_follows_comparison_and_fills_contract():
    q = _q(1, "structure", "compare_categories", "hbar")
    chart = decision.choose_chart({"bars": [{"label": "a", "value": 1.0},
                                            {"label": "b", "value": -1.0}],
                                   "title": "a 1.0、b -1.0",
                                   "unit_meta": "%", "source": "证据包"}, q)
    assert chart["type"] in decision.CHART_POLICY["compare_categories"]
    assert chart["policy"]["comparison"] == "compare_categories"
    assert decision.chart_contract_ok(chart)["ok"]


def test_choose_chart_adapts_items_to_a_bar():
    """只有 items 的 payload：v11 起会适配成 hbar（画出真数据），而不是拒绝。

    旧行为是「要求 grouped_bar 就只画 grouped_bar」，于是同一份 items 在
    compare_two_points 下被判定「无法编码」而丢图；P4 扩了 allowed 列表后
    应该退到能表达 items 的图型，而不是不画。
    """
    q = _q(1, "momentum", "compare_two_points", "grouped_bar")
    chart = decision.choose_chart({"items": [{"label": "a", "value": 1.0},
                                             {"label": "b", "value": 2.0}],
                                   "title": "a 1.0、b 2.0", "unit_meta": "%",
                                   "source": "证据包"}, q)
    assert chart["type"] == "hbar"
    assert chart["policy"]["fallback"] is True     # 换了图型就要留痕
    assert chart.get("bars")


def test_choose_chart_refuses_when_payload_cannot_be_encoded():
    """连一个数据点都没有 → 不硬画，标 unsupported。"""
    q = _q(1, "momentum", "compare_two_points", "grouped_bar")
    chart = decision.choose_chart({"items": [], "title": "t"}, q)
    assert chart["policy"]["fallback"] is True
    assert chart["policy"]["unsupported"] is True
    assert chart["type"] == ""


def test_bind_counts_declared_not_answered():
    ctr = _ctr([_q(1, "structure"), _q(2, "economics"), _q(3, "headcount")])
    findings = {"structure": object(), "economics": object()}
    plan = {"skipped": [{"key": "headcount", "missing": ["table.headcount"]}]}
    b = decision.bind(ctr, findings, plan)
    assert (b["declared"], b["answered"]) == (3, 2)
    assert b["binding"] == pytest.approx(0.667, abs=1e-3)
    assert b["unanswered"][0]["finding"] == "headcount"
    assert b["unanswered"][0]["reason"] == "no_data"
    assert b["verdict"] == "PARTIAL"


def test_chart_contract_rejects_missing_proof_fields():
    r = decision.chart_contract_ok({"type": "hbar", "title": "t"})
    assert not r["ok"]
    assert any("claim_to_prove" in e for e in r["errors"])


def test_synth_from_table_only_uses_existing_numbers():
    table = {"caption": "c", "columns": [{"text": "品类"}, {"text": "值"}],
             "rows": [[{"text": "a"}, {"text": "1.5 元"}],
                      [{"text": "b"}, {"text": "-2.5 元"}],
                      [{"text": "c"}, {"text": "3.5 元"}]]}
    c = decision.synth_from_table(table)
    assert [i["value"] for i in c["items"]] == [1.5, -2.5, 3.5]
    assert decision.synth_from_table({"rows": []}) is None


@pytest.mark.skipif(os.environ.get("GUAGUA_DECISION_IT") != "1",
                    reason="需要完整项目与 r01 子进程；设 GUAGUA_DECISION_IT=1 才跑")
def test_decision_build_end_to_end(tmp_path):
    from core import decision_report
    proj = os.environ.get("GUAGUA_DECISION_PROJECT")
    if not proj or not os.path.isdir(proj):
        pytest.skip("缺 GUAGUA_DECISION_PROJECT")
    res = decision_report.build("经营诊断", proj, str(tmp_path / "out"))
    assert res["declared"] >= 3
    assert res["binding"] == pytest.approx(res["answered"] / res["declared"], abs=1e-3)
    man = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert man["gates"]["binding"] in ("pass", "block")


# ====================================================================
# 合并自 test_semantic_pipeline.py：test_semantic_pipeline —— S5a 语义管道单测。
# ====================================================================
# -*- coding: utf-8 -*-


def _ir():
    return {
        "schema": "dsh.report_ir/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人"},
        "facts": [
            {"id": "F1", "metric": "电子配件", "entity": "B市",
             "period": "2026-01", "value": 48.2, "unit": "万元", "source": "S1"},
            {"id": "F2", "metric": "电子配件", "entity": "A市",
             "period": "2026-01", "value": 40.1, "unit": "万元", "source": "S1"},
        ],
        "sources": [{"file": "S1", "title": "s", "org": "o", "url": "u"}],
        "sections": [{
            "title": "电子配件两城差 8.1 万", "question": "两地价差多大",
            "outline": "两城对比",
            "chart": {"relation": "deviation", "chosen": "hbar",
                      "data_refs": ["F1", "F2"],
                      "dims": [{"name": "entity", "type": "categorical"}]},
        }],
    }


def test_resolve_valid():
    m = resolve(_ir())
    assert m["ok"] is True
    assert m["schema_errors"] == []


def test_resolve_keeps_chart_validation():
    m = resolve(_ir())
    cv = m["sections"][0]["chart"]["chart_validation"]
    assert cv["ok"] is True


def test_resolve_fills_chosen_when_absent():
    ir = _ir()
    ir["sections"][0]["chart"].pop("chosen")
    m = resolve(ir)
    # deviation 关系下，无 period 维时 area 不可行，首位可读候选是 hbar
    assert m["sections"][0]["chart"]["chosen"] == "hbar"


def test_resolve_fills_relation_from_question():
    ir = _ir()
    ir["sections"][0]["chart"].pop("relation")
    m = resolve(ir)
    assert m["sections"][0]["chart"]["relation"] == "deviation"


def test_resolve_reports_schema_errors():
    ir = _ir()
    ir["facts"][0].pop("unit")
    m = resolve(ir)
    assert m["ok"] is False
    assert any("unit" in e for e in m["schema_errors"])


def test_resolve_author_override():
    ir = _ir()
    # 作者把关系改成 ranking + dumbbell（两值对比），覆盖推断的 deviation
    m = resolve(ir, {"0": {"relation": "ranking", "chosen": "dumbbell"}})
    cv = m["sections"][0]["chart"]["chart_validation"]
    assert m["sections"][0]["chart"]["relation"] == "ranking"
    assert cv["ok"] is True


def _invalid_ir():
    ir = _ir()
    # hbar 不能表达 composition → 面板应列出这一节
    ir["sections"][0]["chart"]["relation"] = "composition"
    ir["sections"][0]["chart"]["chosen"] = "hbar"
    return ir


def test_panel_lists_invalid_only():
    m = resolve(_invalid_ir())
    p = panel(m)
    assert len(p) == 1
    assert p[0]["index"] == 0
    assert p[0]["reason"] is not None
    assert p[0]["candidates"]  # 给了候选


def test_apply_decisions_fixes_invalid():
    ir = _invalid_ir()
    m = apply_decisions(ir, [{"index": 0, "chosen": "treemap"}])
    cv = m["sections"][0]["chart"]["chart_validation"]
    assert m["sections"][0]["chart"]["chosen"] == "treemap"
    assert cv["ok"] is True
