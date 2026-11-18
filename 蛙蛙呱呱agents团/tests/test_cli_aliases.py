# -*- coding: utf-8 -*-
"""v11 CLI 入口：一条命令 + 四种输入。

历史：P9 曾有 produce / pack / research / run 四个兼容别名；
P1.7（2026-11-18）已删除，只保留 run-line 与过渡期别名 build / decide。
"""
from __future__ import annotations

import pytest

from core import report_cli


def test_single_entry_and_transition_aliases(capsys):
    with pytest.raises(SystemExit):
        report_cli.main(["--help"])
    cap = capsys.readouterr()
    out = cap.out + cap.err
    assert "run-line" in out
    assert "build" in out
    assert "decide" in out


def test_old_aliases_are_gone(capsys):
    """produce / pack / research / run 必须已删除（argparse 直接报错退出）。"""
    for name in ("produce", "pack", "research", "run"):
        with pytest.raises(SystemExit):
            report_cli.main([name, "--help"])
        capsys.readouterr()


def test_decide_still_runs_the_line(capsys):
    """decide 是过渡别名，指向同一实现（这里只验参数被接受，不跑全流程）。"""
    assert hasattr(report_cli, "cmd_decide")
    assert hasattr(report_cli, "cmd_run_line")
