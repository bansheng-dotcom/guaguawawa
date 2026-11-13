# -*- coding: utf-8 -*-
"""engines/session_memory.py - R10 视觉设计官 · L09 多轮交互会话记忆层 (Session Memory).

对标 MemGPT (Letta) / LangGraph State Store (Stars > 15k)：
1. 持久化存储设计上下文记忆池至 workspace/session_state.json；
2. 自然语言代词消歧（“按刚才第二套方案调整”、“把上次的海报换成赛博风”）；
3. 历史版本快照管理与一键无损回滚 (Rollback)。
"""
from __future__ import annotations

import datetime
import json
import os
from core.workspace import role_workspace  # noqa: E402

import re
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.dirname(HERE)
DEFAULT_STATE_FILE = os.path.join(role_workspace(AGENT_DIR), "session_state.json")


class VisualSessionMemory:
    """L09 视觉设计会话记忆管理池。"""

    def __init__(self, state_file: str = DEFAULT_STATE_FILE):
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
            "session_id": "r10-interactive-session",
            "initialized_at": datetime.datetime.now().isoformat(),
            "active_context": {
                "last_concept": "商业宣传主视觉",
                "last_style": "commercial-photography",
                "last_aspect_ratio": "1:1",
                "last_scenario": "commercial_editorial",
            },
            "snapshots": {},
            "history": [],
        }

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def save_snapshot(self, version: str, data: Dict[str, Any]) -> str:
        """保存设计工件快照。"""
        self.state["snapshots"][version] = {
            "version": version,
            "saved_at": datetime.datetime.now().isoformat(),
            "data": data,
        }
        self.state["active_context"]["latest_version"] = version
        self._save()
        return version

    def rollback_to(self, version: str) -> Optional[Dict[str, Any]]:
        """回滚到指定历史版本快照。"""
        snap = self.state["snapshots"].get(version)
        if snap:
            self.state["active_context"]["current_version"] = version
            self._save()
            return snap.get("data")
        return None

    def resolve_pronouns(self, query: str) -> Dict[str, Any]:
        """识别代词（刚才、上次、第二套）并结合记忆池消歧。"""
        had_ambiguity = False
        resolved = query
        ctx = self.state.get("active_context", {})

        pronoun_patterns = ["刚才", "上次", "上一套", "之前的", "刚刚", "那个", "这版"]
        if any(p in query for p in pronoun_patterns):
            had_ambiguity = True
            concept = ctx.get("last_concept", "商业主视觉")
            style = ctx.get("last_style", "商业精修")
            resolved = f"[基于上下文已锁定实体: {concept} (风格: {style})] {query}"

        if "第二套" in query or "方案二" in query:
            had_ambiguity = True
            resolved = f"{resolved} (绑定方案: commercial_editorial 商业大片版)"

        return {
            "had_ambiguity": had_ambiguity,
            "original_query": query,
            "disambiguated_query": resolved,
            "context_used": ctx,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.state.get("snapshots", {}).values())
