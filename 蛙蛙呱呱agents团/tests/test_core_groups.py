# -*- coding: utf-8 -*-
"""test_core_groups —— core 的逻辑分组入口（物理不动）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core  # noqa: E402


def test_group_attributes_exist():
    for g in ("pipeline", "intent", "experts", "data", "cards",
              "semantic", "narrative", "render", "gates", "coordination"):
        assert hasattr(core, g), g
        assert len(dir(getattr(core, g))) > 0, g


def test_group_resolves_to_same_module():
    assert core.gates.quality_gate is core.quality_gate
    assert core.pipeline.report_flow is core.report_flow
    assert core.semantic.report_ir is core.report_ir
    assert core.cards.card_issue is core.card_issue
    assert core.narrative.claims_v4 is core.claims_v4


def test_group_member_is_lazy_then_cached():
    # 访问前不在 sys.modules 里（可能已被别的测试导入，所以只验证访问后能拿到）
    m1 = core.experts.roster
    m2 = core.experts.roster
    assert m1 is m2


def test_unknown_member_raises():
    try:
        core.gates.not_a_module  # noqa: B018
    except AttributeError as exc:
        assert "not_a_module" in str(exc)
    else:
        raise AssertionError("应当抛 AttributeError")


def test_charts_package_aggregates_chart_modules():
    from core.charts import chart_grammar, chart_lib
    assert chart_grammar is core.chart_grammar
    assert chart_lib is __import__("core.charts.chart_lib", fromlist=["x"])


def test_render_group_points_at_report_theme():
    assert core.render.report_theme is core.report_theme


def test_group_repr():
    assert "modules" in repr(core.gates)
