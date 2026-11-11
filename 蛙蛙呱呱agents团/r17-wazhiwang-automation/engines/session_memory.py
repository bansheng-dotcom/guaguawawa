# -*- coding: utf-8 -*-
"""engines/session_memory.py - [L09] 会话记忆层：跨轮多会话上下文持久化与自然语言代词消歧。

对标开源标杆：
- MemGPT (Letta)
- LangGraph State Store (Stars > 15k)

核心职责：
1. 持久化存储多轮自动化交互状态池 workspace/session_state.json；
2. 智能消歧自然语言代词引用（如：“按刚才第二套方案生成工作流”、“把刚才的重试次数改成5次”、“回滚到上个版本的工作流”）；
3. 历史版本快照链 (snapshots) 与一键回退 (rollback)；
4. 确保跨轮多会话不失忆，上下文无损贯通。
"""
from __future__ import annotations

import copy
import datetime
import json
import os
from core.workspace import role_workspace  # noqa: E402

import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WS = os.path.join(role_workspace(_HERE))
SESSION_FILE = os.path.join(_WS, "session_state.json")


class AutomationSessionMemory:
    """自动化多轮会话记忆池与代词消歧引擎。"""

    def __init__(self, storage_path: str = SESSION_FILE):
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            self.save_state({
                "session_id": "r17_default_session",
                "last_active": datetime.datetime.now().isoformat(),
                "current_context": {},
                "last_workflow_id": None,
                "last_scenario_selected": None,
                "slots": {},
                "snapshots": [],
            })

    def load_state(self) -> Dict[str, Any]:
        """读取持久化会话记忆。"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"snapshots": [], "slots": {}}

    def save_state(self, state: Dict[str, Any]) -> None:
        """保存状态至 session_state.json。"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def record_snapshot(self, label: str, data: Dict[str, Any]) -> str:
        """创建历史状态快照节点，支持版本回退。"""
        state = self.load_state()
        snapshot_id = f"snap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(state.get('snapshots', []))}"
        snapshot_entry = {
            "snapshot_id": snapshot_id,
            "label": label,
            "created_at": datetime.datetime.now().isoformat(),
            "data": copy.deepcopy(data),
        }
        state.setdefault("snapshots", []).append(snapshot_entry)
        state["current_context"] = copy.deepcopy(data)
        state["last_active"] = datetime.datetime.now().isoformat()
        self.save_state(state)
        return snapshot_id

    def rollback(self, snapshot_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """回退到指定快照，若未传 snapshot_id 则回退到最近上一版本。"""
        state = self.load_state()
        snaps = state.get("snapshots", [])
        if not snaps:
            return None

        target = None
        if snapshot_id:
            for s in snaps:
                if s["snapshot_id"] == snapshot_id:
                    target = s
                    break
        else:
            # 默认回退到倒数第 2 个 (若只有一个则取首个)
            target = snaps[-2] if len(snaps) >= 2 else snaps[-1]

        if target:
            state["current_context"] = copy.deepcopy(target["data"])
            self.save_state(state)
            return target["data"]
        return None

    def disambiguate_query(self, query: str) -> Dict[str, Any]:
        """对自然语言中的指示代词进行上下文消歧与槽位解析。"""
        state = self.load_state()
        ctx = state.get("current_context", {})
        slots = state.get("slots", {})

        resolved = {"original_query": query, "resolved": True, "params": {}}

        # 代词消歧规则 1: "第N套方案" -> 从上下文场景中提取
        sc_match = re.search(r"第([一二三123])套方案", query)
        if sc_match:
            idx_map = {"一": 0, "1": 0, "二": 1, "2": 1, "三": 2, "3": 2}
            target_idx = idx_map[sc_match.group(1)]
            scenarios = ctx.get("scenarios") or [
                {"name": "极速轻量同步版"}, {"name": "稳健队列缓冲版"}, {"name": "企业分布式编排版"}
            ]
            if 0 <= target_idx < len(scenarios):
                resolved["params"]["selected_scenario"] = scenarios[target_idx]
                slots["selected_scenario"] = scenarios[target_idx]

        # 代词消歧规则 2: "把重试次数改成N次"
        retry_match = re.search(r"重试\s*(\d+)\s*次", query)
        if retry_match:
            resolved["params"]["max_retries"] = int(retry_match.group(1))
            slots["max_retries"] = int(retry_match.group(1))

        # 代词消歧规则 3: "回滚/撤销"
        if "回滚" in query or "撤回" in query or "恢复上个版本" in query:
            rb_data = self.rollback()
            resolved["params"]["rollback_executed"] = True
            resolved["params"]["restored_data"] = rb_data

        state["slots"] = slots
        self.save_state(state)
        return resolved


# 别名兼容
SessionMemory = AutomationSessionMemory
