# -*- coding: utf-8 -*-
"""R06 报告生成流水线包。

与 `engines/`（L01~L10 演进元模型引擎）职责分离：
    - engines/   = 确定性分析/治理引擎，由 `agent.py evolve` 调度；
    - pipelines/ = 分析 → 组装 → 渲染的报告流水线，由 `agent.py deep` / `depth` 调度。

模块：
    deep_analysis      七步深度分析链（库，无 CLI）
    deep_report        七步链 → REP-001 深度决策报告（CLI）
    consulting_analysis 商业咨询五支分析（库，无 CLI）
    consulting_report  麦肯锡级咨询研报装配（CLI）

约定：产物一律落 workspace/，不写源码目录；本包不依赖 engines/。
详见同目录 README.md。
"""
