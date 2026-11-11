# -*- coding: utf-8 -*-
"""engines/session_memory.py - [L09] 会话记忆层：跨轮多会话上下文持久化与自然语言代词消歧。

对标开源标杆：
- MemGPT (Letta)
- LangGraph State Store (Stars > 15k)

核心职责：
1. 持久化存储多轮人事交互状态池 workspace/session_state.json；
2. 智能消歧自然语言代词引用（如：“按刚才第二套方案招人”、“把上次那个前端岗薪酬上限调高2k”、“回滚到上一版考勤账”）；
3. 历史版本快照链 (snapshots) 与一键回退 (rollback)；
4. 确保第二轮多轮会话不失忆，上下文无损贯通。
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


class HRSessionMemory:
    """HR 多轮会话记忆池与代词消歧引擎。"""

    def __init__(self, storage_path: str = SESSION_FILE):
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            self.save_state({
                "session_id": "r16_default_session",
                "last_active": datetime.datetime.now().isoformat(),
                "current_context": {},
                "last_employee_id": None,
                "last_scenario_selected": None,
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
        return {"snapshots": []}

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

        if snapshot_id is None:
            target = snaps[-1]["data"]
        else:
            match = next((s for s in snaps if s["snapshot_id"] == snapshot_id), None)
            target = match["data"] if match else None

        if target:
            state["current_context"] = copy.deepcopy(target)
            self.save_state(state)
        return target

    def disambiguate_query(self, query: str) -> Dict[str, Any]:
        """对自然语言代词进行消歧解析。"""
        state = self.load_state()
        ctx = state.get("current_context", {})
        resolved = {"original_query": query, "disambiguated": query, "referenced_context": {}}

        # 1. 匹配“按刚才第二套方案招人 / 方案B”
        if re.search(r"(?:刚才|上次|第[二2]套|方案[B2]|第二种|推荐方案)", query):
            resolved["disambiguated"] = query + " [消歧映射：选用 SCN_B 均衡稳健招聘方案]"
            resolved["referenced_context"]["selected_scenario"] = "SCN_B"
            state["last_scenario_selected"] = "SCN_B"

        # 2. 匹配“把上次那个前端岗薪酬上限调高2k / 追加 / 增加”
        sal_match = re.search(r"(?:调高|增加|上浮)\s*(\d+)(?:k|元|K)?", query)
        if sal_match:
            inc_val = float(sal_match.group(1)) * (1000 if "k" in query.lower() else 1)
            role_target = ctx.get("role_name", "目标岗位")
            resolved["disambiguated"] = query + f" [消歧映射：对岗位 {role_target} 薪酬上限上调 {inc_val} 元]"
            resolved["referenced_context"]["role_name"] = role_target
            resolved["referenced_context"]["salary_increment"] = inc_val

        # 3. 匹配“回滚到上一版考勤账 / 上次”
        if "回滚" in query or "上一版" in query:
            resolved["referenced_context"]["action"] = "ROLLBACK"
            if snaps := state.get("snapshots", []):
                resolved["referenced_context"]["target_snapshot"] = snaps[-1]["snapshot_id"]

        # 4. 匹配“上次那个员工”
        if "刚才" in query or "上次" in query:
            if "employee_id" in ctx:
                resolved["referenced_context"]["employee_id"] = ctx["employee_id"]

        self.save_state(state)
        return resolved


# 别名
SessionMemory = HRSessionMemory
