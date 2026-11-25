# -*- coding: utf-8 -*-
"""统一入口路由器（D+）的选路测试。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import guagua


def _run(argv, capsys):
    code = guagua.main(argv)
    return code, json.loads(capsys.readouterr().out)


def test_role_routes_to_single(capsys):
    code, data = _run(["run", "--role", "r06", "--", "--help"], capsys)
    assert code == 0
    assert data["mode"] == "single"
    assert data["argv"][0] == "call"


def test_intent_routes_to_card(capsys):
    code, data = _run(["run", "--intent", "本周库存怎么补"], capsys)
    assert code == 0
    assert data["mode"] == "card"
    assert data["argv"][0] == "plan"


def test_dir_out_routes_to_inline(capsys):
    code, data = _run(["run", "--intent", "分析", "--dir", "p", "--out", "o"], capsys)
    assert code == 0
    assert data["mode"] == "inline"
    assert data["argv"][:3] == ["report", "run-line", "--intent"]


def test_cards_source_needs_claims(capsys):
    code, data = _run(["run", "--intent", "分析", "--dir", "p", "--out", "o",
                       "--source", "cards"], capsys)
    assert code == 2
    assert data["stage"] == "route"


def test_no_input_returns_2(capsys):
    code, data = _run(["run"], capsys)
    assert code == 2
    assert data["stage"] == "route"
