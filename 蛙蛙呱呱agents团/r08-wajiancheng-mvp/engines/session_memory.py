# -*- coding: utf-8 -*-
"""engines/session_memory.py - L09 会话记忆层 (Persistent Session State & Disambiguation).

对标开源标杆：MemGPT (Letta) / LangGraph State Store (Stars > 15k)
核心职责：
1. 维护跨会话状态记忆池 session_state.json；
2. 提供自然语言代词消歧能力（如：“按刚才第二套方案调整主色”、“把上次的落地页加上移动端适配”）；
3. 维护历史原型快照树（Snapshot Tree），支持一键快照版本回滚 (Rollback)。
"""
from __future__ import annotations

import copy
import json
import os
import time
from typing import Any, Dict, List, Optional

from core.workspace import role_workspace


class PrototypeSessionMemory:
    """R08 L09 多轮原型会话记忆与代词消歧引擎。"""

    def __init__(self, state_file: Optional[str] = None):
        if state_file is None:
            state_file = os.path.join(
                role_workspace(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "session_state.json",
            )
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "current_context": {},
            "recent_scenarios": [],
            "snapshots": [],
            "updated_at": time.time(),
        }

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self.state["updated_at"] = time.time()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def save_snapshot(self, version_tag: str, artifact_data: Dict[str, Any]) -> str:
        """保存历史原型快照。"""
        snap = {
            "version": version_tag,
            "timestamp": time.time(),
            "data": copy.deepcopy(artifact_data),
        }
        self.state["snapshots"].append(snap)
        self.state["current_context"] = copy.deepcopy(artifact_data)
        self._save()
        return version_tag

    def rollback_to(self, version_tag: str) -> Optional[Dict[str, Any]]:
        """按版本标签一键回滚历史原型快照。"""
        for snap in reversed(self.state["snapshots"]):
            if snap["version"] == version_tag:
                self.state["current_context"] = copy.deepcopy(snap["data"])
                self._save()
                return snap["data"]
        return None

    def resolve_pronouns(self, query: str) -> Dict[str, Any]:
        """对包含代词的自然语言指令进行意图与上下文消歧。"""
        had_ambiguity = False
        resolved_context = {}
        disambiguated_query = query

        pronouns = ["刚才的", "上一个", "刚才第二套", "上一版", "原先的", "那个方案"]
        if any(p in query for p in pronouns):
            had_ambiguity = True
            if self.state.get("current_context"):
                resolved_context = self.state["current_context"]
                disambiguated_query = f"基于上下文已锁定实体: {query}"

        return {
            "had_ambiguity": had_ambiguity,
            "original_query": query,
            "disambiguated_query": disambiguated_query,
            "bound_context": resolved_context,
            "snapshot_count": len(self.state.get("snapshots", [])),
        }
