# -*- coding: utf-8 -*-
"""R03 厚度样本回归：golden 成品存在 + misuse 被具名门禁拦下。

golden/*.html 由 golden/build_golden.py 调用真实技能生成；
misuse/*.json 故意违反一个具名门禁，本测试断言它一定被拒。
"""
from __future__ import annotations

import os
import sys
import unittest
from argparse import Namespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE_DIR = os.path.dirname(HERE)
if ROLE_DIR not in sys.path:
    sys.path.insert(0, ROLE_DIR)

from skills import SKILLS  # noqa: E402

GOLDEN = os.path.join(ROLE_DIR, "golden")
MISUSE = [
    ("rollforward_unbalanced.json", "financial", "rollforward", "balance"),
    ("policy_missing_owner.json", "contract", "policy", "policy_field"),
]


def _run(skill, action, path):
    mod = next(m for m in SKILLS if m.NAME == skill)
    return mod.run(Namespace(action=action, input=path))


def collect_problems():
    problems = []
    if not os.path.isdir(GOLDEN):
        return ["golden/ 目录不存在"]
    golden = sorted(f for f in os.listdir(GOLDEN) if f.endswith(".html"))
    if len(golden) < 2:
        problems.append(f"golden HTML 少于 2 份（实际 {len(golden)}）")
    for f in golden:
        p = os.path.join(GOLDEN, f)
        if os.path.getsize(p) < 1024:
            problems.append(f"golden/{f} 为空或过小")
            continue
        text = open(p, encoding="utf-8").read()
        for token in ('data-theme="light"', "@page", "<thead>", "<th>"):
            if token not in text:
                problems.append(f"golden/{f} 缺 {token}")
    for fname, skill, action, gate in MISUSE:
        p = os.path.join(ROLE_DIR, "misuse", fname)
        if not os.path.exists(p):
            problems.append(f"misuse/{fname} 不存在")
            continue
        out = _run(skill, action, p)
        if out.get("ok"):
            problems.append(f"misuse/{fname} 未被拦下")
        dims = [str(c.get("dim", "")) for c in out.get("checks", []) if not c.get("ok")]
        if not any(gate in d for d in dims):
            problems.append(f"misuse/{fname} 未命中门禁 {gate}（实际 {dims}）")
    return problems


class ThicknessSamples(unittest.TestCase):
    def test_golden_present(self):
        self.assertGreaterEqual(
            len([f for f in os.listdir(GOLDEN) if f.endswith(".html")]), 2)
        for f in os.listdir(GOLDEN):
            if f.endswith(".html"):
                self.assertGreater(os.path.getsize(os.path.join(GOLDEN, f)), 1024)

    def test_misuse_blocked(self):
        self.assertEqual(collect_problems(), [])
