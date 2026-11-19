# -*- coding: utf-8 -*-
"""report_prose_gen：结构化证据 -> 论证体。"""
from __future__ import annotations

from core.report_prose_gen import compose


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
