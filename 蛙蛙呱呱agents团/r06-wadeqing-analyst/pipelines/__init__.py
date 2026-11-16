# -*- coding: utf-8 -*-
"""R06 报告流水线包（2026-11-14 起）。

旧 REP-001 深链（deep_analysis / deep_report / consulting_report）已下线并删除，
`agent.py` 的 depth/deep 入口只返回 DEPRECATED。

新的报告路径：
- 单动作：`guagua.py report one ...`（core/report_pipeline）
- 问题驱动：`guagua.py report analysis --pack analysis_pack.json`
  （core/report_analysis，Q/A/E/R/D，无质量分/熔断/灰度）
- 项目级：`guagua.py report project --dir ...`（core/report_project）
"""
