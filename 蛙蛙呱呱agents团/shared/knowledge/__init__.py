# -*- coding: utf-8 -*-
"""shared/knowledge —— 知识能力的共享层（不属报告层）。

目前只有 `brief`：把「卡」升级成「卡 + 专家工作说明书」。
报告层（`core/report_*.py`）**不得** import 本包，隔离由
`scripts/check_report_isolation.py` 守卫。
"""
