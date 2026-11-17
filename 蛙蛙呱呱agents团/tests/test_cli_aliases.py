# -*- coding: utf-8 -*-
"""P9：旧 CLI 别名仍在（隐藏/兼容），但 build 是主入口。"""
from __future__ import annotations

import pytest

from core import report_cli


def test_old_aliases_are_present(capsys):
    with pytest.raises(SystemExit):
        report_cli.main(["--help"])
    cap = capsys.readouterr()
    out = cap.out + cap.err
    for name in ("build", "produce", "pack", "research", "run"):
        assert name in out


def test_run_without_evidence_is_rejected(capsys):
    rc = report_cli.main(["run", "--intent", "x", "--out", "tmp"])
    assert rc == 2
    assert "run 已下线" in capsys.readouterr().out
