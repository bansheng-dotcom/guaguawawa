# -*- coding: utf-8 -*-
"""R06 分析链（T8a）：从业务问题到可审计统计结论的 6 段链路。

用法（Python）：
    from analysis_chain import runner
    manifest = runner.run(question, data, out_dir, start, end, split)

各段也可单独调用：frame / plan / profile / explore / explain / test。
"""
from . import (common, explain, explore, frame, plan, profile, runner,
               stats_test, material_pack, verify, chart_pack, text_pack,
               deliver, report_runner)

__all__ = ["common", "frame", "plan", "profile", "explore", "explain",
           "stats_test", "runner", "material_pack", "verify", "chart_pack",
           "text_pack", "deliver", "report_runner"]
