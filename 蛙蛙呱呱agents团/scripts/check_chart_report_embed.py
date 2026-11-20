# -*- coding: utf-8 -*-
"""兼容入口：ci_report_checks 仍调本文件名；实际校验 charts_pro。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_charts_pro import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
