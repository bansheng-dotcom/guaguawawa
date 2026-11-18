# -*- coding: utf-8 -*-
"""v11 唯一入口：`report "指令" --dir … --out …`。

历史：P9 有 produce / pack / research / run 四个兼容别名；
P1.7 删除它们；P5 把 build / decide 也删了——现在只剩一条路。
"""
from __future__ import annotations

import pytest

from core import report_cli


def test_only_one_entry(capsys):
    with pytest.raises(SystemExit):
        report_cli.main(["--help"])
    cap = capsys.readouterr()
    out = cap.out + cap.err
    assert "run-line" in out
    for gone in ("build", "decide", "produce", "pack", "research"):
        assert gone not in out.replace("run-line", ""), f"{gone} 不应再作为子命令出现"


def test_old_names_are_gone(capsys):
    """六个旧名字都必须已删除（argparse 直接报错退出）。"""
    for name in ("build", "decide", "produce", "pack", "research", "run"):
        with pytest.raises(SystemExit):
            report_cli.main([name, "--help"])
        capsys.readouterr()


def test_instruction_first_is_rewritten(capsys, monkeypatch):
    """`report "指令" …` 会被改写成 `run-line --intent "指令" …`。"""
    seen = {}

    def fake_run(args):
        seen["intent"] = args.intent
        seen["dir"] = args.dir
        return 0

    monkeypatch.setattr(report_cli, "cmd_run_line", fake_run)
    rc = report_cli.main(["内蒙古水果诊断", "--dir", "x", "--out", "y"])
    assert rc == 0
    assert seen == {"intent": "内蒙古水果诊断", "dir": "x"}
