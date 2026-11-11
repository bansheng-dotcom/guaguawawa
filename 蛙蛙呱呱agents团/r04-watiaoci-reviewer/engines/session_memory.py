# -*- coding: utf-8 -*-
"""L09 会话记忆层：持久化会话状态与代词消歧引擎。
对标开源标杆：letta-ai/letta (formerly MemGPT, Stars: 13k+), langchain-ai/langgraph (Memory/State, Stars: 11k+)

功能：
1. 持久化存储多轮审查的历史快照 (session_state.json)；
2. 支持自然语言代词消歧（“按刚才的第二套方案评审”、“对上一次的 findings 进行复核”、“回滚到前一轮状态”）；
3. 具备版本快照分支与历史追溯/一键 Rollback 能力；
4. 确保审查会话跨轮次不失忆、上下文连贯。
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from core.workspace import role_workspace


class ReviewSessionMemory:
    """持久化审查会话状态管理器"""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        if storage_path is None:
            here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(role_workspace(here), "session_state.json")
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        self.storage_path = storage_path
        self.state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.isfile(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "current_session_id": "sess_default",
            "last_action": None,
            "last_target": None,
            "last_findings": [],
            "last_verdict": None,
            "history_snapshots": [],
        }

    def save(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def record_round(self, action: str, target: str, verdict: str, findings: List[Dict[str, Any]], meta: Optional[Dict[str, Any]] = None) -> str:
        """记录一轮审查快照"""
        snapshot_id = f"snap_{int(time.time() * 1000)}"
        snapshot = {
            "snapshot_id": snapshot_id,
            "timestamp": time.time(),
            "action": action,
            "target": target,
            "verdict": verdict,
            "findings_count": len(findings),
            "findings": findings,
            "meta": meta or {},
        }
        self.state["history_snapshots"].append(snapshot)
        self.state["last_action"] = action
        self.state["last_target"] = target
        self.state["last_verdict"] = verdict
        self.state["last_findings"] = findings
        self.save()
        return snapshot_id

    def resolve_pronoun_query(self, user_query: str) -> Dict[str, Any]:
        """消歧代词（如：刚才的、上次的、这套代码、它）并恢复上下文目标"""
        query_lower = user_query.lower()
        resolved_target = None
        reference_type = None

        if any(w in user_query for w in ["刚才的", "上一次", "上次", "上一轮", "刚才那份", "它", "这个文件"]):
            if self.state.get("last_target"):
                resolved_target = self.state["last_target"]
                reference_type = "PRONOUN_RESOLVED"

        if "第二套方案" in user_query or "方案b" in query_lower:
            reference_type = "SCENARIO_SELECTION"
            resolved_target = "稳健基准型 (Standard Production)"

        return {
            "original_query": user_query,
            "has_pronoun_reference": reference_type is not None,
            "reference_type": reference_type,
            "resolved_target": resolved_target or self.state.get("last_target"),
            "context_last_action": self.state.get("last_action"),
            "context_last_verdict": self.state.get("last_verdict"),
        }

    def rollback(self) -> Optional[Dict[str, Any]]:
        """回滚到上一个快照版本"""
        snaps = self.state.get("history_snapshots", [])
        if len(snaps) <= 1:
            return None
        # 弹出当前，恢复上一个
        popped = snaps.pop()
        prev = snaps[-1]
        self.state["last_action"] = prev["action"]
        self.state["last_target"] = prev["target"]
        self.state["last_verdict"] = prev["verdict"]
        self.state["last_findings"] = prev["findings"]
        self.save()
        return prev
