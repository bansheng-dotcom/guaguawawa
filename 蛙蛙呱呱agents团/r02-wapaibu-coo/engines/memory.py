# -*- coding: utf-8 -*-
"""R02 会话状态记忆与工作记忆池 (轮次 9 落地)。

对标高星标杆: MemGPT (Letta) / LangGraph State Management
维护跨轮次的会话上下文、历史快照与版本回滚机制。
"""
from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List, Optional

class SessionMemoryPool:
    """跨轮会话状态与工作记忆池。"""

    def __init__(self, storage_path: str = "session_state.json"):
        self.storage_path = storage_path
        self.state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"current_session": "default", "history": [], "context": {}}

    def save_state(self, key: str, value: Any) -> None:
        self.state["context"][key] = value
        self.state["history"].append({
            "ts": time.time(),
            "key": key,
            "snapshot": value
        })
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def get_latest(self, key: str) -> Optional[Any]:
        return self.state["context"].get(key)

    def rollback(self, steps: int = 1) -> Optional[Dict[str, Any]]:
        """回滚到前 N 步的状态。"""
        if len(self.state["history"]) >= steps:
            target = self.state["history"][-steps]
            return target.get("snapshot")
        return None
