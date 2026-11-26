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

逻辑分组（2026-11-23）
----------------------
139 个模块仍按文件平铺在 `core/` 下（**物理不动**，零迁移风险），
但对外多一层「按层访问」的懒加载入口：

    from core import gates
    gates.quality_gate          # == core.quality_gate
    gates.report_quality        # == core.report_quality

完整分层见 docs/CORE-MAP.md。分组本身不 import 任何模块——访问时才加载。
"""
from __future__ import annotations

import importlib

__all__ = [
    # 原有
    "protocol", "workspace", "registry", "runner", "report_bridge",
    # 逻辑分组（2026-11-23）
    "pipeline", "intent", "experts", "data", "cards", "semantic",
    "narrative", "charts", "render", "gates", "coordination",
]

# 分组 → 成员模块名（与 docs/CORE-MAP.md 的 13 层一一对应）
# 注意：名字不能跟现有模块同名。`collab` 已是 core/collab.py，所以协作组叫
# `coordination`；`charts` 已是 core/charts/ 真包，不在此处定义。
_GROUPS = {
    "pipeline": [
        "report_cli", "report_line", "report_dispatch", "report_flow",
        "report_bridge", "report_renderer", "decision_report",
        "report_layout", "report_contract", "flow_report",
    ],
    "intent": [
        "orchestrator", "decision", "report_clarify", "intake",
        "report_thesis", "report_structure",
        "domain_pack", "dor", "report_model",
    ],
    "experts": [
        "roster", "registry", "report_roles", "skill_graph", "skill_bridge",
        "analysis_methods", "analysis_desk", "analysis_pipeline",
        "methods",
    ],
    "data": [
        "fact_table", "evidence_pack", "data_model", "data_profile",
        "data_shape", "data_contract", "source_verify", "coverage_plan",
        "coverage_confirm", "coverage_policy", "panel",
    ],
    "semantic": [
        "report_ir", "ir_adapters", "semantic_pipeline", "ir_to_contract",
    ],
    "narrative": [
        "claims", "claims_v4", "claim_consistency",
        "report_assembly", "report_editorial", "synthesis",
    ],
    "render": ["report_theme"],
    "gates": [
        "quality_gate", "report_quality",
        "prose_style", "prose_spec", "report_prose_gen", "report_marks",
        "r04_audit", "r04_derive", "report_kernel",
    ],
    "coordination": [
        "workspace", "outcome_ledger", "memory_guard", "runner",
        "protocol", "prompt_kernel",
    ],
}


class _Group:
    """懒加载的模块分组：访问 `core.gates.quality_gate` 时才 import。"""

    def __init__(self, name: str, members) -> None:
        self.__name__ = name
        self._members = tuple(members)

    def __getattr__(self, item: str):
        if item in self._members:
            mod = importlib.import_module("core." + item)
            object.__setattr__(self, item, mod)   # 缓存，避免重复 import
            return mod
        raise AttributeError(
            "core.%s 没有模块 %r；可用：%s"
            % (self.__name__, item, ", ".join(sorted(self._members))))

    def __dir__(self):
        return sorted(self._members)

    def __repr__(self) -> str:
        return "<core.%s: %d modules>" % (self.__name__, len(self._members))


for _g, _members in _GROUPS.items():
    globals()[_g] = _Group(_g, _members)
del _g, _members

# `charts`、`cards` 已是真子包（core/charts/、core/cards/），不放进 _GROUPS，
# 否则会盖住真包。这里显式导入一次，让 `import core; core.cards.card_issue`
# 直接可用；两个子包的 __init__ 本身是懒加载的，代价只有一次空包导入。
from . import charts  # noqa: E402,F401
from . import cards  # noqa: E402,F401
