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

仍保留的「按层访问」懒加载入口（2026-11-23）：

    from core import gates
    gates.quality_gate          # == core.quality_gate
    gates.report_quality        # == core.report.report_quality

完整分层见 docs/CORE-MAP.md 与 docs/ARCHITECTURE-LEDGER.md。
"""
from __future__ import annotations

import importlib

__all__ = [
    # 入口
    "runner",
    # 真子包（P4）
    "base", "data", "sources", "charts", "claims", "cards", "report", "prose",
    # 逻辑分组（2026-11-23）
    "pipeline", "intent", "experts", "semantic",
    "narrative", "render", "gates", "coordination",
]

# 分组 → 成员模块名（与 docs/CORE-MAP.md 的 13 层一一对应）
# 注意：名字不能跟现有模块/真子包同名。`collab` 已是 core/collab.py，所以协作组叫
# `coordination`；`data` / `charts` / `cards` 已是真子包，不在此处定义。
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
    "semantic": [
        "report_ir", "ir_adapters", "semantic_pipeline", "ir_to_contract",
    ],
    "narrative": [
        "claims", "claim_consistency",
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

# 真子包：显式导入一次，让 `import core; core.data.fact_table` 直接可用。
# 子包的 __init__ 本身是懒加载的，代价只有 8 次空包导入。
from . import base, data, sources, charts, claims, cards, report, prose  # noqa: E402,F401

# 成员名 → 所属子包（供分组懒加载解析；改名只需改子包的 __all__）
_MOVED = {}
for _pkg in ("base", "data", "sources", "charts", "claims", "cards",
             "report", "prose"):
    for _name in getattr(globals()[_pkg], "__all__", []):
        _MOVED[_name] = _pkg
del _pkg, _name


class _Group:
    """懒加载的模块分组：访问 `core.gates.quality_gate` 时才 import。"""

    def __init__(self, name: str, members) -> None:
        self.__name__ = name
        self._members = tuple(members)

    def __getattr__(self, item: str):
        if item in self._members:
            pkg = _MOVED.get(item)
            target = "core.%s.%s" % (pkg, item) if pkg else "core." + item
            mod = importlib.import_module(target)
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
