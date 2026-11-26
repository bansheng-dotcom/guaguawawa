# -*- coding: utf-8 -*-
"""report_render 域测试（合并自 11 个文件）。

源文件：
    test_report_ir.py —— test_report_ir —— S0 富 IR 校验器 + 关系推断单测。
    test_report_kernel.py —— report_kernel 单元测试：契约、规格、一致性、序列、交付门禁。
    test_ir_adapters.py —— test_ir_adapters —— S2 claims 前端单测。
    test_ir_to_contract.py —— test_ir_to_contract —— IR → contract 转换器单测。
    test_facts_frontend.py —— test_facts_frontend —— S4 声明式 facts.yaml→IR 前端单测。
    test_decision_frontend.py —— test_decision_frontend —— S3 decision→IR 前端单测。
    test_flow_renderer.py —— flow renderer：HTML 一条流，页脚小签名。
    test_design_systems.py —— 设计系统库集成测试（R10 ↔ R08）。
    test_prose_gen.py —— report_prose_gen：结构化证据 -> 论证体。
    test_prose_style.py —— prose_style：字数/段块/禁用词/数字密度门禁。
    test_shape_gate.py —— test_shape_gate —— 数据形状门禁（SOP §2.5）。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


from core.report import report_ir
import json
import pytest
from core.report_kernel import consistency, contract as C, gate, series, specs
from core.ir_adapters import claims_to_ir
from core.report.report_ir import validate
from core import ir_to_contract
from core.report import report_renderer
from core.semantic_pipeline import resolve
from core.ir_adapters import facts_to_ir
from core.ir_adapters import decision_to_ir
from core.report_theme.flow import flowify
import os
import subprocess
from shared import design_systems as ds
from core.report.report_prose_gen import compose
from core.prose import prose_style
from core import shape_gate



# ====================================================================
# 合并自 test_report_ir.py：test_report_ir —— S0 富 IR 校验器 + 关系推断单测。
# ====================================================================
# -*- coding: utf-8 -*-


def _valid_ir():
    return {
        "schema": "dsh.report_ir/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人"},
        "facts": [
            {"id": "F1", "metric": "电子配件营收", "entity": "B市",
             "period": "2026-01", "value": 48.2, "unit": "万元", "source": "S01"},
            {"id": "F2", "metric": "电子配件营收", "entity": "A市",
             "period": "2026-01", "value": 40.1, "unit": "万元", "source": "S01",
             "derived_from": []},
        ],
        "sections": [
            {"title": "电子配件 B 市比 A 市高 8.1 万",
             "question": "电子配件两城营收差多大？",
             "outline": "两城对比电子配件营收",
             "chart": {"data_refs": ["F1", "F2"]}},
        ],
    }


def test_valid_ir_passes():
    assert report_ir.validate(_valid_ir()) == []


def test_missing_schema():
    ir = _valid_ir(); ir["schema"] = "x"
    assert any("schema" in e for e in report_ir.validate(ir))


def test_fact_missing_source():
    ir = _valid_ir(); ir["facts"][0].pop("source")
    assert any("source" in e for e in report_ir.validate(ir))


def test_chart_refs_unknown_fact():
    ir = _valid_ir(); ir["sections"][0]["chart"]["data_refs"] = ["NOPE"]
    assert any("不存在的 fact" in e for e in report_ir.validate(ir))


def test_infer_relation_from_question():
    assert report_ir.infer_relation("两地价差多大") == "deviation"
    assert report_ir.infer_relation("哪个产品线最贵") == "ranking"
    assert report_ir.infer_relation("月度营收走势") == "change_over_time"
    assert report_ir.infer_relation("电子配件占比") == "composition"


# ====================================================================
# 合并自 test_report_kernel.py：report_kernel 单元测试：契约、规格、一致性、序列、交付门禁。
# ====================================================================
# -*- coding: utf-8 -*-


PROJECT = ROOT.parent / "内蒙古肉禽蛋调研_2026-11-12"


def _good_contract():
    c = C.template("RPT-TEST-01", "测试报告")
    c.update({
        "decision": "决定是否上线",
        "audience": "创始人",
        "questions": ["问题一", "问题二", "问题三"],
        "data_cutoff": "2026-11-16",
        "owner": "R01",
        "reviewer": "R04",
        "source_count": 30,
        "series_periods": 12,
    })
    return c


def test_contract_requires_six_fields():
    assert C.validate(_good_contract())["ok"]
    bad = _good_contract()
    bad["questions"] = ["只有一个"]
    res = C.validate(bad)
    assert not res["ok"]
    assert any("questions" in e for e in res["errors"])


def test_contract_blocks_trend_without_series():
    c = _good_contract()
    c["trend_required"] = True
    c["series_periods"] = 4
    res = C.validate(c)
    assert not res["ok"]
    assert any("12" in e for e in res["errors"])


def test_contract_blocks_cross_day_without_alignment():
    c = _good_contract()
    c["time_span_days"] = 5
    res = C.validate(c)
    assert not res["ok"]
    c["alignment_note"] = "已按同日对齐，剩余时点差已标注"
    assert C.validate(c)["ok"]


def test_table_specs_units_tone_total():
    tb = {
        "caption": "价格与变化（元/斤）",
        "columns": ["品类", "批发价", "变化率"],
        "rows": [["牛肉", "36.00", "+3.6%"], ["合计", "36.00", "+3.6%"]],
    }
    out, st = specs.infer_table(tb)
    assert out["columns"][1].get("num")
    assert "元/斤" in out["columns"][1]["text"]
    assert out["rows"][0][2].get("tone") == "up"
    assert out.get("total_row")
    assert st["with_unit"] >= 1


def test_chart_specs_fill_ref_and_subtitle():
    ch = {
        "type": "hbar", "title": "牛肉 36.00 元", "unit_meta": "元/斤",
        "source": "测试", "bars": [{"label": "a", "value": 30},
                                  {"label": "b", "value": 40}],
    }
    out, st, errs = specs.complete_chart(ch)
    assert not errs
    assert out["ref"]["value"] == 35
    assert out["subtitle"]
    assert st["ref_added"] == 1


def test_chart_specs_reject_title_without_number():
    ch = {"type": "hbar", "title": "牛肉价格", "unit_meta": "元/斤",
          "source": "测试", "bars": [{"label": "a", "value": 1}]}
    _, _, errs = specs.complete_chart(ch)
    assert any("数字" in e for e in errs)


def test_consistency_detects_conflict():
    reg = {"metrics": [
        {"id": "markup", "value": 4.0, "unit": "倍"},
        {"id": "markup", "value": 11.3, "unit": "倍"},
    ]}
    res = consistency.check_registry(reg)
    assert not res["ok"]
    assert any("markup" in e for e in res["errors"])


def test_series_blocks_short_trend():
    c = _good_contract()
    c["sections"] = [{"title": "趋势：未来两个月 +7%"}]
    c["series_periods"] = 4
    assert not series.check_series(c)["ok"]


@pytest.mark.skipif(not (PROJECT / "报告质量根因分析_2026-11-16.html").exists(),
                    reason="缺少根因报告交付件")
def test_gate_positive_on_delivered_report():
    html = PROJECT / "报告质量根因分析_2026-11-16.html"
    if not html.with_suffix(".ship.json").exists():
        pytest.skip("缺少 ship 契约")
    res = gate.run_gate(html)
    assert res["ok"], res["errors"]
    assert res["level"] == "L4"


@pytest.mark.skipif(not (PROJECT / "_archive_2026-11-12").exists(),
                    reason="缺少归档旧版")
def test_gate_negative_on_old_report():
    old = PROJECT / "_archive_2026-11-12" / "内蒙古肉禽蛋市场调研与数据分析报告.html"
    if not old.exists():
        pytest.skip("缺少旧版文件")
    res = gate.run_gate(old, strict=False)
    assert not res["ok"]
    failed = {c["id"] for c in res["checks"] if not c["ok"]}
    assert {"C2_level", "C4_figures", "C5_table_units"}.issubset(failed)


# ====================================================================
# 合并自 test_ir_adapters.py：test_ir_adapters —— S2 claims 前端单测。
# ====================================================================
# -*- coding: utf-8 -*-


def _claims():
    return {
        "meta": {"title": "t", "audience": "a"},
        "numbers": [
            {"id": "N1", "name": "包头价", "value": 9.0, "unit": "元/公斤",
             "source_file": "S1"},
            {"id": "N2", "name": "呼市价", "value": 16.0, "unit": "元/公斤",
             "source_file": "S1"},
        ],
        "sources": [{"file": "S1", "title": "s", "org": "o", "url": "u"}],
        "sections": [{
            "title": "价差 7 元", "question": "两地价差多大",
            "reading": [{"strong": "事实　", "text": "9 vs 16", "refs": ["N1", "N2"]}],
            "boundary": "b", "falsifier": "f",
            "chart": {"type": "dumbbell", "refs": ["N1", "N2"]},
        }],
    }


def test_claims_to_ir_valid():
    ir, _ = claims_to_ir(_claims())
    assert validate(ir) == []


def test_facts_and_sources_count():
    ir, _ = claims_to_ir(_claims())
    assert len(ir["facts"]) == 2
    assert len(ir["sources"]) == 1
    assert len(ir["sections"]) == 1


def test_relation_inferred_from_question():
    ir, _ = claims_to_ir(_claims())
    assert ir["sections"][0]["chart"]["relation"] == "deviation"


def test_outline_degradation_recorded():
    _, degraded = claims_to_ir(_claims())
    assert any("outline" in d["field"] for d in degraded)


# ====================================================================
# 合并自 test_ir_to_contract.py：test_ir_to_contract —— IR → contract 转换器单测。
# ====================================================================
# -*- coding: utf-8 -*-


def _model():
    ir = {
        "schema": "dsh.report_ir/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人",
                 "subtitle": "三个月", "standfirst": "电子配件最高"},
        "facts": [
            {"id": "F1", "metric": "电子配件", "entity": "B市", "period": "2026-01",
             "value": 48.2, "unit": "万元", "source": "S1"},
            {"id": "F2", "metric": "食品饮料", "entity": "B市", "period": "2026-01",
             "value": 32.5, "unit": "万元", "source": "S1"},
            {"id": "F3", "metric": "运动旅行", "entity": "B市", "period": "2026-01",
             "value": 12.1, "unit": "万元", "source": "S1"},
        ],
        "sources": [{"file": "S1", "title": "交易数据", "org": "本地", "url": ""}],
        "sections": [{
            "title": "电子配件 48.2 万最高", "question": "哪个品类最高",
            "outline": "品类排名",
            "readings": [{"strong": "事实　", "text": "电子配件 48.2 万", "refs": ["F1"]}],
            "boundary": "b", "falsifier": "f",
            "chart": {"relation": "ranking", "chosen": "hbar",
                      "data_refs": ["F1", "F2", "F3"],
                      "dims": [{"name": "entity", "type": "categorical"}]},
        }],
    }
    return resolve(ir)


def test_contract_valid():
    c = ir_to_contract.build(_model())
    assert report_renderer.validate_contract(c) == []


def test_title_and_summary():
    c = ir_to_contract.build(_model())
    assert c["title_lines"][0] == "超市销售"
    assert c["summary"][0]["text"] == "电子配件最高"


def test_section_and_chart():
    c = ir_to_contract.build(_model())
    assert len(c["sections"]) == 1
    ch = c["sections"][0]["chart"]
    assert ch["type"] == "hbar"
    assert len(ch["items"]) == 3
    assert ch["unit_meta"] == "万元"


def test_metric_strip():
    c = ir_to_contract.build(_model())
    assert len(c["metric_strip"]) == 3
    assert all("label" in m and "value" in m and "note" in m for m in c["metric_strip"])


# ====================================================================
# 合并自 test_facts_frontend.py：test_facts_frontend —— S4 声明式 facts.yaml→IR 前端单测。
# ====================================================================
# -*- coding: utf-8 -*-


def _facts():
    return {
        "schema": "dsh.facts_authoring/v1",
        "meta": {"title": "超市销售", "audience": "业务负责人", "one_thing": "先拆电子配件"},
        "facts": [
            {"id": "F1", "metric": "电子配件营收", "entity": "B市",
             "period": "2026-01", "value": 48.2, "unit": "万元", "source": "S1"},
            {"id": "F2", "metric": "电子配件营收", "entity": "A市",
             "period": "2026-01", "value": 40.1, "unit": "万元", "source": "S1"},
        ],
        "sources": [{"file": "S1", "title": "sales", "org": "o", "url": "u"}],
        "sections": [{
            "title": "电子配件 B 市比 A 市高 8.1 万",
            "question": "两地价差多大",
            "outline": "两城对比电子配件营收",
            "actions": ["拆电子配件 B 市溢价"],
            "chart": {"data_refs": ["F1", "F2"]},
        }],
    }


def test_facts_to_ir_valid():
    ir, _ = facts_to_ir(_facts())
    assert validate(ir) == []


def test_relation_inferred_when_absent():
    ir, _ = facts_to_ir(_facts())
    assert ir["sections"][0]["chart"]["relation"] == "deviation"


def test_relation_explicit_overrides():
    f = _facts(); f["sections"][0]["chart"]["relation"] = "ranking"
    ir, _ = facts_to_ir(f)
    assert ir["sections"][0]["chart"]["relation"] == "ranking"


def test_dims_from_facts():
    ir, _ = facts_to_ir(_facts())
    names = {d["name"] for d in ir["sections"][0]["chart"]["dims"]}
    assert names == {"entity", "period"}


def test_actions_passthrough():
    ir, _ = facts_to_ir(_facts())
    assert ir["sections"][0]["actions"] == ["拆电子配件 B 市溢价"]


# ====================================================================
# 合并自 test_decision_frontend.py：test_decision_frontend —— S3 decision→IR 前端单测。
# ====================================================================
# -*- coding: utf-8 -*-


def _draft_pack():
    draft = {
        "title_lines": ["超市销售分析"], "intent": "超市销售",
        "standfirst": "s",
        "sections": [{
            "title": "电子配件 48.2 万最高", "question": "哪个产品线最高",
            "reading": [{"strong": "事实　", "text": "电子配件 48.2",
                         "refs": ["csv:r:电子配件:last"]}],
            "boundary": "b", "falsifier": "f",
            "chart": {"type": "hbar", "refs": ["csv:r:电子配件:last"]},
        }],
    }
    pack = {
        "numbers": [
            {"id": "csv:r:电子配件:last", "name": "电子配件(last)",
             "value": 48.2, "unit": "万元", "period": "", "region": "B市",
             "source_file": "data/sales.csv", "inputs": ""},
        ],
        "sources": [{"file": "data/sales.csv", "title": "sales", "org": "o", "url": "u"}],
    }
    return draft, pack


def test_decision_to_ir_valid():
    ir, _ = decision_to_ir(*_draft_pack())
    assert validate(ir) == []


def test_region_mapped_to_entity():
    ir, _ = decision_to_ir(*_draft_pack())
    assert ir["facts"][0]["entity"] == "B市"


def test_derived_from_from_inputs():
    d, p = _draft_pack()
    p["numbers"][0]["inputs"] = "csv:r:营收:sum"
    ir, _ = decision_to_ir(d, p)
    assert ir["facts"][0]["derived_from"] == ["csv:r:营收:sum"]


def test_relation_inferred_from_question():
    ir, _ = decision_to_ir(*_draft_pack())
    assert ir["sections"][0]["chart"]["relation"] == "ranking"


# ====================================================================
# 合并自 test_flow_renderer.py：flow renderer：HTML 一条流，页脚小签名。
# ====================================================================
# -*- coding: utf-8 -*-


def _pages_like() -> str:
    return (
        '<!doctype html><html><head></head><body>'
        '<div class="page cover"><div class="inner"><h1>标题</h1></div></div>'
        '<section class="page sec" id="s1"><div class="rh">眉</div>'
        '<div class="head"><h2>01</h2></div><p>正文</p>'
        '<div class="rf">脚</div></section>'
        '<section class="page back" id="back"><div class="inner"><img src="x.png"></div></section>'
        '</body></html>'
    )


def test_flowify_removes_page_wrappers():
    html = flowify(_pages_like())
    assert "flow-cover" in html
    assert "flow-block" in html
    assert 'class="page ' not in html
    assert "flow-footer" in html


def test_flowify_strips_header_footer():
    html = flowify(_pages_like())
    assert ">眉<" not in html
    assert ">脚<" not in html


def test_flowify_keeps_body():
    html = flowify(_pages_like())
    assert "正文" in html
    assert "标题" in html


def test_flowify_compact_sources():
    html = _pages_like().replace(
        '</body>',
        '<section class="page appendix" id="appendix"><table><tr><td>old</td></tr></table></section></body>')
    out = flowify(html, [("S01", "来源一", "2024"), ("S02", "来源二", "2025")])
    assert "src-grid" in out
    assert "来源一" in out
    assert "old" not in out


def test_footer_html():
    from core.report_theme.blocks import footer_html
    assert "flow-footer" in footer_html()
    assert "蛙蛙呱呱专家团" in footer_html()


def test_flowify_is_responsive():
    html = flowify(_pages_like())
    assert 'name="viewport"' in html
    assert "max-width:900px" in html
    assert "width:100%" in html


# ====================================================================
# 合并自 test_design_systems.py：设计系统库集成测试（R10 ↔ R08）。
# ====================================================================
# -*- coding: utf-8 -*-


R08_DIR = os.path.join(ROOT, "r08-wajiancheng-mvp")


def test_library_has_31_systems():
    systems = ds.available()
    assert len(systems) == 31, f"期望 31 个设计系统，实际 {len(systems)}"
    for slug in systems:
        item = ds.get(slug)
        assert item and item["exists"], f"{slug} 元数据缺失"
        assert ds.read(slug).startswith("# Design System:")


def test_every_system_passes_nine_section_audit():
    failures = []
    for slug in ds.available():
        parsed = ds.parse(ds.read(slug))
        report = ds.audit(parsed, slug)
        if not report["ok"]:
            failures.append((slug, [c["msg"] for c in report["checks"] if not c["ok"]]))
    assert not failures, f"以下设计系统未过门禁：{failures}"


def test_every_project_type_recommends_at_least_three():
    for project in ds.PROJECT_TYPES:
        rec = ds.recommend(project)
        assert rec is not None, f"{project} 无推荐"
        assert len(rec["brands"]) >= 3, f"{project} 推荐不足 3 个：{rec['brands']}"
        assert all(b["exists"] for b in rec["brands"])


def test_tokens_shape_matches_r08_contract():
    bundle = ds.tokens(ds.parse(ds.read("linear.app")), "linear.app")
    tokens = bundle["tokens"]
    for kind in ("color", "typography", "spacing"):
        assert isinstance(tokens[kind], list) and tokens[kind], f"tokens.{kind} 为空"
        for item in tokens[kind]:
            assert str(item.get("name", "")).strip()
            assert str(item.get("value", "")).strip()
    assert isinstance(bundle["components"], list) and bundle["components"]
    for comp in bundle["components"]:
        assert comp["name"] and comp["platform"] and comp["states"]


def test_write_bundle_writes_two_files_and_respects_force(tmp_path):
    out = str(tmp_path / "bundle")
    report = ds.write_bundle("claude", out, force=True)
    assert report["verdict"] == "PASS"
    assert os.path.isfile(os.path.join(out, "DESIGN.md"))
    assert os.path.isfile(os.path.join(out, "design_tokens.json"))
    payload = json.loads(open(os.path.join(out, "design_tokens.json"), encoding="utf-8").read())
    assert payload["design_system"]["slug"] == "claude"

    again = ds.write_bundle("claude", out, force=False)
    assert again["written"] == [] and len(again["skipped"]) == 2


def test_unknown_brand_raises():
    with pytest.raises(FileNotFoundError):
        ds.read("no-such-brand")
    assert ds.get("no-such-brand") is None


def test_r08_from_md_bridge(tmp_path):
    ds.write_bundle("claude", str(tmp_path), force=True)
    design = os.path.join(str(tmp_path), "DESIGN.md")
    tokens = os.path.join(str(tmp_path), "tokens.json")
    proc = subprocess.run(
        [sys.executable, "agent.py", "design", "from-md",
         "--input", design, "--out", tokens, "--brand", "claude"],
        cwd=R08_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120)
    assert proc.returncode == 0, proc.stderr[-500:]
    line = next(l for l in proc.stdout.splitlines() if l.startswith("__AGENT_RESULT__"))
    payload = json.loads(line.split(" ", 1)[1])
    assert payload["ok"] is True, payload
    assert payload["verdict"] == "PASS"
    assert payload["component_count"] >= 1
    assert os.path.isfile(tokens)
    written = json.loads(open(tokens, encoding="utf-8").read())
    assert written["design_system"]["slug"] == "claude"


# ====================================================================
# 合并自 test_prose_gen.py：report_prose_gen：结构化证据 -> 论证体。
# ====================================================================
# -*- coding: utf-8 -*-


def test_compose_has_blocks_and_length():
    s = {"id": "s1", "verdict": "判断：不是 A，而是 B。", "body": "事实：2024 年 6871 亿元。"}
    spec = {
        "fact": "事实：2024 年 6871 亿元、同比 16.0%。",
        "evidence": "证据：比本地社零 4.5% 快 11.5pp。",
        "mechanism": "机理：品类替代。",
        "alternative": "不是总量扩张，而是结构迁移。",
        "signal": "判别：下一期酱油份额是否继续上升。",
        "implication": "含义：先做酱油。",
        "action": "动作：先上 1 个 SKU。",
        "stop": "毛利低于 25%。",
        "boundary": "边界：只覆盖家庭零售。",
    }
    out = compose(s, spec)
    assert "判断" in out and "所以" in out and "边界" in out
    assert "如果" in out or "判别" in out
    assert len(out) > 300


def test_compose_no_new_numbers():
    s = {"id": "s2", "verdict": "判断。", "body": "事实：10 个品类。"}
    out = compose(s, {"fact": "事实：10 个品类。", "boundary": "边界。"})
    assert "10 个品类" in out


def test_prose_spec_requires_11_fields():
    """固定 11 字段：facts 的 verdict/question + spec 的 9 个字段。"""
    from core.prose import prose_spec

    section = {"id": "s1", "verdict": "判断：先做酱油。", "question": "先做哪个品类？"}
    good = {f: "x" * 8 for f in prose_spec.FIELDS}
    assert prose_spec.validate({"s1": good}, [section]) == []

    bad = dict(good)
    bad.pop("mechanism")
    errs = prose_spec.validate({"s1": bad}, [section])
    assert any("mechanism" in e for e in errs)

    no_question = {"id": "s2", "verdict": "判断：先做酱油。", "question": ""}
    errs2 = prose_spec.validate({"s2": good}, [no_question])
    assert any("question" in e for e in errs2)


# ====================================================================
# 合并自 test_prose_style.py：prose_style：字数/段块/禁用词/数字密度门禁。
# ====================================================================
# -*- coding: utf-8 -*-


def _good() -> str:
    body = (
        "结论：这不是需求扩张，而是结构升级。"
        "事实：2024 年规模 6871 亿元，同比 16.0%；本地社零 4.5%，差 11.5 个百分点。"
        "解释：一种解释是品类替代，另一种解释是渠道下沉；判别方法是看下一期酱油份额是否继续上升。"
        "如果份额继续上升，说明替代成立；如果回落，说明只是促销。"
        "所以：先守超市陈列，再做低钠 SKU；毛利低于 25% 就停。"
        "边界：只覆盖家庭零售与餐饮渠道，不含工业原料。"
    )
    extra = ("补充：2022 年 5133 亿元、2023 年 5925 亿元、2024 年 6871 亿元；"
             "渠道费用 15%–25%，账期 60–90 天；如果费用率超过 25%，"
             "毛利低于 25% 就停。")
    return body + extra * 10


def test_good_section_passes():
    r = prose_style.audit_section(_good())
    assert r["score"] >= 85
    assert r["hard"] is False


def test_short_section_fails():
    r = prose_style.audit_section("事实：很短。解释：没有。所以：没有。")
    assert r["hard"] is True
    assert r["score"] < 85


def test_banned_phrase_hard_fails():
    r = prose_style.audit_section(_good() + "这张表回答一切。")
    assert r["hard"] is True


def test_audit_html_sections():
    html = ('<section class="page sec" id="s1">' + _good() + "</section>"
            '<section class="page sec" id="s2">' + _good() + "</section>")
    out = prose_style.audit_html(html)
    assert out["sections"] == 2
    assert out["ok"] is True


# ====================================================================
# 合并自 test_shape_gate.py：test_shape_gate —— 数据形状门禁（SOP §2.5）。
# ====================================================================
# -*- coding: utf-8 -*-


def _rows(per_metric):
    rows = []
    for m, n in per_metric.items():
        for i in range(n):
            rows.append({"metric_id": m, "value": i, "entity": f"e{i}"})
    return rows


def test_pass_when_most_metrics_have_3_rows():
    r = shape_gate.gate(_rows({"a": 3, "b": 4, "c": 3, "d": 1}))
    assert r["ratio"] == 0.75
    assert r["verdict"] == "pass"
    assert r["allowed_charts"] == "2d"


def test_1d_only_in_middle_band():
    r = shape_gate.gate(_rows({"a": 3, "b": 1, "c": 1, "d": 1}))
    assert r["ratio"] == 0.25
    assert r["verdict"] == "fail"
    assert r["allowed_charts"] == "none"


def test_fail_below_floor_and_lists_thin_metrics():
    r = shape_gate.gate(_rows({"a": 1, "b": 1, "c": 2, "d": 1, "e": 1}))
    assert r["verdict"] == "fail"
    assert {t["metric"] for t in r["thin_metrics"]} >= {"a", "b", "d", "e"}


def test_empty_rows_is_fail():
    r = shape_gate.gate([])
    assert r["ratio"] == 0.0
    assert r["verdict"] == "fail"


def test_ratio_boundary_at_half():
    # 2/4 = 0.5 → pass（SOP: ≥0.5 通过）
    r = shape_gate.gate(_rows({"a": 3, "b": 3, "c": 1, "d": 1}))
    assert r["ratio"] == 0.5
    assert r["verdict"] == "pass"


def test_ratio_boundary_at_03():
    # 1/3 ≈ 0.333 → 1d_only
    r = shape_gate.gate(_rows({"a": 3, "b": 1, "c": 1}))
    assert r["verdict"] == "1d_only"
    assert r["allowed_charts"] == "1d"
