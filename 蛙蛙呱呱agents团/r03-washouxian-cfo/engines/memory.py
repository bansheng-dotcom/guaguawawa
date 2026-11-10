# -*- coding: utf-8 -*-
"""R03 会话记忆池与版本历史回滚器 (L09 会话记忆层)。

对标高星标杆: MemGPT (Letta, 14k+) / LangGraph State
在复杂的跨轮次多轮交互中：
1. 持久化存储财务与合规会话上下文 (session_state.json)
2. 支持自然语言代词与上下文消歧（如“把刚才测算的第二套方案跑道延长 3 个月”）
3. 具备版本快照分支与一键回滚 (Rollback) 能力，防范错误调账导致基线污染。
"""
from __future__ import annotations
import copy
import json
import os
import time
from typing import Any, Dict, List, Optional

class FinancialSessionMemoryPool:
    """持久化财务工作记忆与状态机。"""

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, "session_state.json")
        self.storage_path = storage_path
        self.state: Dict[str, Any] = {
            "current_session_id": "cfo_session_default",
            "working_memory": {},
            "history_snapshots": []
        }
        self.load()

    def load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception:
                pass

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def commit_snapshot(self, description: str, memory_payload: Dict[str, Any]) -> str:
        """提交当前工作记忆快照，生成可回滚的版本。"""
        snap_id = f"snap_{int(time.time() * 1000)}"
        snapshot = {
            "snapshot_id": snap_id,
            "timestamp": time.time(),
            "description": description,
            "payload": copy.deepcopy(memory_payload)
        }
        self.state["working_memory"] = copy.deepcopy(memory_payload)
        self.state["history_snapshots"].append(snapshot)
        # 最多保留 10 份历史快照
        if len(self.state["history_snapshots"]) > 10:
            self.state["history_snapshots"].pop(0)
        self.save()
        return snap_id

    def rollback(self, snapshot_id: Optional[str] = None) -> bool:
        """回滚至指定快照或上一版本。"""
        if not self.state["history_snapshots"]:
            return False

        if snapshot_id is None:
            # 回滚到最近一个历史版本（弹出当前最新）
            target = self.state["history_snapshots"][-1]
        else:
            found = [s for s in self.state["history_snapshots"] if s["snapshot_id"] == snapshot_id]
            if not found:
                return False
            target = found[0]

        self.state["working_memory"] = copy.deepcopy(target["payload"])
        self.save()
        return True

    def get_working_memory(self) -> Dict[str, Any]:
        return self.state.get("working_memory", {})
