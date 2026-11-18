# -*- coding: utf-8 -*-
"""报告模型审计的回归测试（v12）。

v12 删掉了 v9 的静态语义层（report_framework 的 23 个维度 + question_library 的
固定题库）：调研要查什么由 `core/research_protocol.plan()` 按任务动态生成，
不再有一份固定清单可以「悬空」或「漏挂」。

所以审计的三类断言（问题挂空维度 / 维度挂未知方法 / 方法未被维度引用）随工件一起删除，
留下的是仍然存在、也仍然会退化的三项：图型配置是否被读、图型是否进配置、角色章节有无图型规则。
"""
from __future__ import annotations

from core import report_model


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
