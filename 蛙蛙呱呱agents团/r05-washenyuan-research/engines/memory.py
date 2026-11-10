# -*- coding: utf-8 -*-
"""L09 会话记忆层：持久化会话状态与代词消歧工作记忆池。

对标标杆:
- cpacker/MemGPT (Letta 14k⭐) / langchain-ai/langgraph (11k⭐)
在多轮对话中持久化保存分析历史、代词实体解析（如“把刚才的方案A调高”）、
快照历史与版本回滚 (Rollback) 能力。
"""
from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List, Optional


class SessionMemoryPool:
    """多轮会话状态持久化与工作记忆池。"""

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "session_state.json")
        self.storage_path = storage_path
        self._state: Dict[str, Any] = {
            "session_id": "r05_default_session",
            "current_focus": None,
            "entities": {},
            "history": [],
            "snapshots": []
        }
        self.load()

    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    def load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except Exception:
                pass

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def record_turn(self, user_query: str, agent_output: Dict[str, Any], topic: Optional[str] = None):
        """记录一轮对话并保存快照。"""
        turn_id = len(self._state["history"]) + 1
        snapshot = {
            "turn_id": turn_id,
            "timestamp": time.time(),
            "topic": topic or "general",
            "output_summary": str(agent_output)[:200]
        }
        self._state["history"].append({"user": user_query, "agent": agent_output})
        self._state["snapshots"].append(snapshot)
        if topic:
            self._state["current_focus"] = topic
            self._state["entities"]["last_topic"] = topic
        self.save()

    def resolve_reference(self, text: str) -> Optional[str]:
        """代词消歧：解析“刚才的研究”、“上一个方案”指向的实体。"""
        if any(w in text for w in ["刚才", "上一轮", "之前那个", "上一个", "上个方案"]):
            return self._state.get("current_focus") or self._state.get("entities", {}).get("last_topic")
        return None

    def rollback(self, steps: int = 1) -> bool:
        """回滚指定步数的会话状态。"""
        if len(self._state["history"]) < steps:
            return False
        for _ in range(steps):
            if self._state["history"]:
                self._state["history"].pop()
            if self._state["snapshots"]:
                self._state["snapshots"].pop()
        self.save()
        return True
