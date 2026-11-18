# -*- coding: utf-8 -*-
"""单一模型（语义层）审计的回归测试。

P4 起这张审计表从「记录债」变成「守债」：
    旧断言写的是 `chart_config_read_by_code is False`（测试保证了死配置永远死）。
    现在改成「必须为 True 且六项债全部为 0」，任何回退都会红。
"""
from __future__ import annotations

from core import report_model


def test_model_nodes_exist_and_are_nonempty():
    m = report_model.build()
    n = m["nodes"]
    assert n["questions"] >= 50
    assert n["dimensions"] >= 10
    assert n["methods"] >= 20
    assert n["charts"] == 48
    assert n["roles"] == 20
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
    # v11 / P4：选图配置必须真的被 core/decision.py 读
    assert i["chart_config_read_by_code"] is True


def test_audit_is_clean():
    """六项债必须全为 0。这一条是「不许回退」的硬断言。"""
    m = report_model.audit()
    assert set(m["issues"]) == {
        "问题挂空维度", "维度挂未知方法", "方法未被维度引用",
        "图型配置未被代码读取", "图型未进配置", "角色章节无图型规则",
    }
    bad = {k: v for k, v in m["issues"].items() if v}
    assert not bad, f"语义层出现悬空边：{bad}"
    assert m["ok"] is True
