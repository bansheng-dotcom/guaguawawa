# -*- coding: utf-8 -*-
"""方法参数（P1-7）：缺省走中性默认，项目文件覆盖；不内置任何业务线口径。"""
from __future__ import annotations

import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from core import method_params, analysis_desk, analysis_methods  # noqa: E402


def teardown_function(_):
    method_params.reset()


def test_default_is_neutral():
    p = method_params.load(None)
    assert p["missing"] is True
    assert p["loss_default"] == 0.0 and p["cold_default"] == 0.0
    assert p["freight"] == 0.0 and p["categories"] == []
    assert "未提供 method_params" in method_params.footnote(p)


def test_project_file_overrides(tmp_path):
    (tmp_path / "method_params.yaml").write_text(
        "schema: dsh.method_params/v1\n"
        "price_unit: 元/件\n"
        "unit_scales: {公斤: 0.5}\n"
        "freight: 0.3\n"
        "categories:\n  - {key: 甲, loss: 0.02, cold: 0.1, shelf: 3}\n",
        encoding="utf-8")
    p = method_params.configure(tmp_path)
    assert p["missing"] is False and p["price_unit"] == "元/件"
    assert analysis_methods.rule_of("甲类")["loss"] == 0.02
    assert analysis_methods.cat_key("甲类") == "甲"
    # 单位换算来自项目参数
    assert analysis_desk._unit_scale("元/公斤") == (0.5, "元/件")


def test_missing_params_do_not_apply_business_defaults():
    method_params.reset()
    assert method_params.current()["missing"] is True
    assert analysis_desk._unit_scale("元/公斤") == (1.0, "元/公斤")
    assert analysis_methods.rule_of("任意品类")["loss"] == 0.0


def test_validate_catches_bad_values(tmp_path):
    bad = {"schema": "dsh.method_params/v1", "freight": -1,
           "unit_scales": {"公斤": "x"}, "categories": [{}]}
    errs = method_params.validate(bad)
    assert len(errs) >= 3
