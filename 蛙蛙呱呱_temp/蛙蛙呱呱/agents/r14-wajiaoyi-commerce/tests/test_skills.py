# -*- coding: utf-8 -*-
"""技能实跑测试：代表性动作必须真实产出 ok 与门禁 checks。"""
import argparse
import json
import os

SKILL = "order"
ACTION = "order"
EXAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "examples", "order.json")


def _dispatch():
    from skills import SKILLS
    mod = next(m for m in SKILLS if m.NAME == SKILL)
    if hasattr(mod, "run"):
        return mod.run(argparse.Namespace(action=ACTION, input=EXAMPLE))
    fn = getattr(mod, ACTION)
    with open(EXAMPLE, encoding="utf-8-sig") as f:
        return fn(json.load(f))


def test_example_input_exists():
    assert os.path.isfile(EXAMPLE), f"缺少示例输入 {EXAMPLE}"


def test_skill_runs_deterministically():
    first = _dispatch()
    second = _dispatch()
    assert isinstance(first, dict)
    assert "ok" in first, "技能必须返回 ok 字段"
    assert first.get("checks"), "技能必须返回逐项门禁 checks（用于 L1 真实性归因）"
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True), "同一输入必须可复现"
