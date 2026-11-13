# -*- coding: utf-8 -*-
"""R01 蛙全局 CEO 会话状态记忆与工作记忆池 (Executive Memory Pool)。

对标 GitHub 开源标杆:
- MemGPT (Letta 14k+ stars) / LangGraph State Management
- 支持跨轮决策会话持久化到 session_state.json、代词指代解析与一键版本快照回滚 (Rollback)。
"""
from __future__ import annotations
import copy
import json
import os
import time
from typing import Any, Dict, List, Optional

class ExecutiveMemoryPool:
    """CEO 会话工作状态记忆池。"""

    def __init__(self, state_file: str = "session_state.json"):
        self.state_file = state_file
        self.history: List[Dict[str, Any]] = []
        self.current_state: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_state = data.get("current_state", {})
                    self.history = data.get("history", [])
            except Exception:
                self.current_state = {}
                self.history = []

    def save(self) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump({
                "current_state": self.current_state,
                "history": self.history,
                "updated_at": time.time()
            }, f, ensure_ascii=False, indent=2)

    def commit(self, action: str, artifact: Dict[str, Any], prompt: str = "") -> int:
        """提交当前工作回合快照。"""
        snapshot = {
            "version": len(self.history) + 1,
            "timestamp": time.time(),
            "action": action,
            "prompt": prompt,
            "artifact": copy.deepcopy(artifact)
        }
        self.history.append(snapshot)
        self.current_state = copy.deepcopy(artifact)
        self.save()
        return snapshot["version"]

    def rollback(self, target_version: int) -> Optional[Dict[str, Any]]:
        """回滚至指定历史版本快照。"""
        for item in self.history:
            if item["version"] == target_version:
                self.current_state = copy.deepcopy(item["artifact"])
                self.save()
                return self.current_state
        return None

    def resolve_reference(self, text: str) -> Optional[Dict[str, Any]]:
        """解析代词指代（如“把刚才那个决策”、“上一份决策卡”）。"""
        ref_kws = ["刚才", "上一轮", "上一个", "前一个", "那个决策", "原决策"]
        if any(kw in text for kw in ref_kws):
            return self.current_state
        return None
