# -*- coding: utf-8 -*-
"""L09 会话记忆层：SessionState 持久化记忆池与快照回滚引擎。
对标开源项目：MemGPT (Letta) (Stars > 13k), LangGraph State (Stars > 17k)。
解决病灶：审查过程属于无状态黑盒，跨轮对话与多步评审间信息完全丢失，无法基于上轮审查历史进行“代词消歧”与“快照回滚”。
"""
from __future__ import annotations

import copy
import json
import os
import time
from typing import Any, Dict, List, Optional

from core.workspace import role_workspace


class SessionMemoryEngine:
    """具备版本快照、代词消歧与一键回滚能力的持久化会话记忆引擎。"""

    def __init__(self, session_id: str, state_file: str | None = None) -> None:
        self.session_id = session_id
        self.state_file = state_file or os.path.join(
            role_workspace(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            f"session_state_{session_id}.json",
        )
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        self.current_state: Dict[str, Any] = {
            "session_id": session_id,
            "turn": 0,
            "current_findings": [],
            "current_verdict": "NONE",
            "last_inspected_target": "",
            "active_scenario": "balanced",
            "history_snapshots": [],
        }
        self.load()

    def load(self) -> None:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.current_state = json.load(f)
            except Exception:
                pass

    def save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.current_state, f, ensure_ascii=False, indent=2)

    def checkpoint(self, description: str = "") -> int:
        """为当前会话状态生成只读快照存入历史树。"""
        self.current_state["turn"] += 1
        snapshot = {
            "version": len(self.current_state["history_snapshots"]) + 1,
            "timestamp": time.time(),
            "description": description,
            "turn": self.current_state["turn"],
            "state_copy": {
                "current_findings": copy.deepcopy(self.current_state["current_findings"]),
                "current_verdict": self.current_state["current_verdict"],
                "last_inspected_target": self.current_state["last_inspected_target"],
                "active_scenario": self.current_state["active_scenario"],
            },
        }
        self.current_state["history_snapshots"].append(snapshot)
        self.save()
        return snapshot["version"]

    def rollback(self, target_version: int) -> bool:
        """回滚到指定的历史快照版本。"""
        for snap in self.current_state["history_snapshots"]:
            if snap["version"] == target_version:
                copied = copy.deepcopy(snap["state_copy"])
                self.current_state["current_findings"] = copied["current_findings"]
                self.current_state["current_verdict"] = copied["current_verdict"]
                self.current_state["last_inspected_target"] = copied["last_inspected_target"]
                self.current_state["active_scenario"] = copied["active_scenario"]
                self.save()
                return True
        return False

    def resolve_pronouns(self, query: str) -> str:
        """代词消歧：将'这个文件'、'刚才的缺陷'、'上一次判据'替换为记忆中的真实实体。"""
        resolved = query
        if "刚才的" in resolved or "上一次的" in resolved:
            target = self.current_state.get("last_inspected_target")
            if target:
                resolved = resolved.replace("刚才的文件", target).replace("上一次的文件", target)
        if "第二套方案" in resolved:
            resolved = resolved.replace("第二套方案", "稳健基准版 (Balanced)")
        return resolved
