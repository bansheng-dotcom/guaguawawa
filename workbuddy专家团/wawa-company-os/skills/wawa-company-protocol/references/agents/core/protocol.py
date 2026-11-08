"""交接协议：端口、任务卡、事件的数据结构与校验。

这是 20 个 Agent「如何相互协作」的契约层。每个 Agent 声明自己的
输入端口(inputs，它需要什么)与输出端口(outputs，它交付什么)；
编排器据此判断谁给谁喂数据、谁依赖谁完成。
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# 端口：Agent 之间交接的最小单元
# --------------------------------------------------------------------------- #
@dataclass
class Port:
    name: str            # 端口名，如 "orders.csv" / "monthly-report.md"
    kind: str            # data | artifact | decision | report
    media_type: str = "application/json"   # 预期产出格式
    note: str = ""       # 一句话说明，给编排器路由用

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# 事件：写入 workspace/events.jsonl 的只追加记录
# --------------------------------------------------------------------------- #
EVENT_TYPES = {
    "task_created", "task_assigned", "task_started",
    "task_finished", "task_failed", "handoff", "note", "verify",
}


@dataclass
class Event:
    ts: str                       # ISO 时间戳
    agent: str                    # 来源角色 id，如 r06
    type: str                     # 见 EVENT_TYPES
    task_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def now(agent: str, type_: str, task_id: Optional[str] = None,
            payload: Optional[Dict[str, Any]] = None) -> "Event":
        if type_ not in EVENT_TYPES:
            raise ValueError(f"未知事件类型: {type_}")
        return Event(
            ts=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            agent=agent, type=type_, task_id=task_id,
            payload=payload or {},
        )

    def to_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


# --------------------------------------------------------------------------- #
# 任务卡：编排器拆解意图后下发给执行角色的最小单元
# --------------------------------------------------------------------------- #
@dataclass
class Task:
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    owner: str = ""               # 角色 id，如 r06
    intent: str = ""              # 原始意图的一小段
    inputs: List[Port] = field(default_factory=list)     # 上游交付物
    outputs: List[Port] = field(default_factory=list)    # 本任务交付
    acceptance: List[str] = field(default_factory=list)  # 验收判据（可用脚本测）
    deps: List[str] = field(default_factory=list)        # 依赖的 task_id
    status: str = "pending"       # pending|assigned|running|done|failed
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["inputs"] = [p.to_dict() for p in self.inputs]
        d["outputs"] = [p.to_dict() for p in self.outputs]
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Task":
        d = dict(d)
        d["inputs"] = [Port(**p) for p in d.get("inputs", [])]
        d["outputs"] = [Port(**p) for p in d.get("outputs", [])]
        return Task(**d)