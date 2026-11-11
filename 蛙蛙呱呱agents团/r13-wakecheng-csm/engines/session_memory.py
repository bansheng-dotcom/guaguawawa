# -*- coding: utf-8 -*-
"""engines/session_memory.py - [L09] 会话记忆层：跨轮会话记忆池、代词消歧与版本回滚引擎。

对标开源标杆：
- MemGPT (Letta) 层次化状态记忆架构 (Stars > 15k)
- LangGraph State Store 多轮会话持久化 (Stars > 20k)

核心职责：
1. 持久化维护 `workspace/session_state.json` 记忆池；
2. 自然语言代词与模糊指代消歧（“按刚才第二套方案”、“给刚才那个流失客户增加回访”）；
3. 提供会话快照归档与版本一键回滚 (Rollback) 能力。
"""
from __future__ import annotations

import copy
import datetime
import json
import os
from core.workspace import role_workspace  # noqa: E402

import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
DEFAULT_SESSION_FILE = os.path.join(role_workspace(_PARENT), "session_state.json")


class CsmSessionMemory:
    """客户成功多轮会话持久化记忆与代词消歧引擎。"""

    def __init__(self, state_file: str = DEFAULT_SESSION_FILE):
        self.state_file = state_file
        self.state = self.load()

    def load(self) -> Dict[str, Any]:
        """从磁盘加载会话状态。"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "current_client": "A公司",
            "active_scenario": "steady_standard",
            "recent_clients": ["A公司", "B网络科技", "C制造集团"],
            "slots": {
                "health_score": 82.5,
                "nps": 35.0,
                "risk_level": "LOW",
                "last_selected_scenario": "稳健运营型 (推荐)",
            },
            "history": [],
            "snapshots": [],
        }

    def save(self) -> None:
        """持久化保存会话状态到磁盘。"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def resolve_pronouns(self, query: str) -> Dict[str, Any]:
        """对自然语言代词进行消歧解析。"""
        resolved_query = query
        disambiguated = False
        reasons = []

        # 1. 方案代词消歧
        if re.search(r"刚才(?:的)?第[二2]套(?:方案)?|第二套|刚才推荐的方案", query):
            resolved_query = re.sub(
                r"刚才(?:的)?第[二2]套(?:方案)?|第二套|刚才推荐的方案",
                f"【方案：{self.state.get('active_scenario', 'steady_standard')} (稳健运营型)】",
                resolved_query,
            )
            disambiguated = True
            reasons.append("消歧方案代词为当前活跃方案 steady_standard")

        # 2. 客户代词消歧
        if re.search(r"刚才(?:那个)?客户|当前客户|这家公司", query):
            curr_client = self.state.get("current_client", "A公司")
            resolved_query = re.sub(
                r"刚才(?:那个)?客户|当前客户|这家公司",
                f"【客户：{curr_client}】",
                resolved_query,
            )
            disambiguated = True
            reasons.append(f"消歧客户代词为当前客户 {curr_client}")

        return {
            "original_query": query,
            "resolved_query": resolved_query,
            "had_ambiguity": disambiguated,
            "reasons": reasons,
            "active_client": self.state.get("current_client"),
            "active_scenario": self.state.get("active_scenario"),
        }

    def update_context(self, client: Optional[str] = None, scenario: Optional[str] = None, **kwargs) -> None:
        """更新会话上下文槽位。"""
        if client:
            self.state["current_client"] = client
            if client not in self.state.get("recent_clients", []):
                self.state.setdefault("recent_clients", []).insert(0, client)
        if scenario:
            self.state["active_scenario"] = scenario

        for k, v in kwargs.items():
            self.state.setdefault("slots", {})[k] = v

        self.save()

    def create_snapshot(self, label: str = "manual_snapshot") -> str:
        """创建当前记忆快照。"""
        snap_id = f"snap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        snapshot = {
            "snapshot_id": snap_id,
            "label": label,
            "created_at": datetime.datetime.now().isoformat(),
            "data": copy.deepcopy({
                "current_client": self.state.get("current_client"),
                "active_scenario": self.state.get("active_scenario"),
                "slots": self.state.get("slots", {}),
            }),
        }
        self.state.setdefault("snapshots", []).append(snapshot)
        self.save()
        return snap_id

    def rollback(self, snapshot_id: str) -> bool:
        """根据快照 ID 一键回滚会话状态。"""
        snaps = self.state.get("snapshots", [])
        for s in snaps:
            if s.get("snapshot_id") == snapshot_id:
                data = copy.deepcopy(s.get("data", {}))
                self.state["current_client"] = data.get("current_client")
                self.state["active_scenario"] = data.get("active_scenario")
                self.state["slots"] = data.get("slots", {})
                self.save()
                return True
        return False
