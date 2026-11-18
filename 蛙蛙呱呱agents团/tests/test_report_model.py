# -*- coding: utf-8 -*-
"""单一模型（语义层）审计的回归测试。"""
from __future__ import annotations

from core import report_model


def test_model_nodes_exist_and_are_nonempty():
    m = report_model.build()
    n = m["nodes"]
    assert n["questions"] >= 50
    assert n["dimensions"] >= 10
    assert n["methods"] >= 20
    assert n["charts"] == 48
    assert n["chart_config"] >= 1


def test_integrity_shape_is_stable():
    m = report_model.build()
    i = m["integrity"]
    for key in ("questions_with_bad_dimension",
                "dimensions_with_unknown_method",
                "methods_used_by_no_dimension",
                "chart_types_not_in_config",
                "role_sections_without_chart_rule"):
        assert key in i, key
    # 图型配置目前没有被任何报告代码读取，这条要能被量出来
    assert i["chart_config_read_by_code"] is False


def test_audit_reports_issues_not_crash():
    m = report_model.audit()
    assert set(m["issues"]) == {
        "问题挂空维度", "维度挂未知方法", "方法未被维度引用",
        "图型配置未被代码读取", "图型未进配置", "角色章节无图型规则",
    }
    assert isinstance(m["ok"], bool)
