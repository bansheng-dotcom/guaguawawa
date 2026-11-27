"""蛙式一人公司 —— 20 个本地 Agent 的协作底座。

本包提供跨角色协作的最小内核，纯 Python 标准库，无第三方依赖：
    protocol  —— 交接合同（端口 / 任务卡 / 事件）的数据结构
    workspace —— 共享工作区（事件流 + 任务卡 + 文件锁）
    registry  —— 20 个角色的注册表（能力、端口、集成来源）
    runner    —— 以子进程方式调用其它 Agent

设计原则（源自 Anthropic《Building effective agents》与《Multi-agent
coordination patterns》）：
    1. 简单可组合，不做重型框架；
    2. 协作用「编排器(Orchestrator) + 共享工作区(Shared-State)」；
    3. 交接靠明确的 input/output 端口契约，而非口头约定；
    4. 一切带终止条件，避免死循环。

物理分包（P4，2026-11-26）
--------------------------
`core/` 已按关注点分成真子包：base / data / sources / charts / claims /
cards / report / prose（另有 report_kernel、report_theme）。旧平铺路径的
兼容 shim 已全部退场，import 请走新路径：

    from core.report import report_flow
    from core.data import fact_table
    from core.base import paths

逻辑分组入口（core.gates / core.pipeline / …）已于 2026-11-27 删除（P5-6）：
它们零实际 import，只挡住真子包路径。需要模块就写全路径，不再提供 `core.<组>.<模块>`。

完整分层见 docs/CORE-MAP.md 与 docs/ARCHITECTURE-LEDGER.md。
"""
from __future__ import annotations

__all__ = [
    # 入口
    "runner",
    # 真子包（P4）
    "base", "data", "sources", "charts", "claims", "cards", "report", "prose",
]

# 真子包：显式导入一次，让 `import core; core.data.fact_table` 直接可用。
# 子包的 __init__ 本身是懒加载的，代价只有 8 次空包导入。
from . import base, data, sources, charts, claims, cards, report, prose  # noqa: E402,F401
