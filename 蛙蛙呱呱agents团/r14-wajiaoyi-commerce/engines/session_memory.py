# -*- coding: utf-8 -*-
"""engines/session_memory.py - [L09] 会话记忆层：跨轮会话记忆池、交易槽位代词消歧与快照回滚引擎。

对标开源标杆：
- MemGPT (Letta) 层次化状态记忆架构 (Stars > 15k)
- LangGraph State Store 多轮会话持久化 (Stars > 20k)

核心职责：
1. 持久化维护 `workspace/session_state.json` 交易记忆池；
2. 交易意图与实体槽位（订单号、商品标的、结算方案、退款单）代词消歧（“按刚才第二套方案”、“把刚才那个订单增加一件”）；
3. 提供交易会话快照归档与版本一键回滚 (Rollback) 能力。
"""
from __future__ import annotations

import copy
import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
DEFAULT_SESSION_FILE = os.path.join(_PARENT, "workspace", "session_state.json")


class CommerceSessionMemory:
    """交易多轮会话持久化记忆与代词消歧引擎。"""

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
            "current_order_id": "ORD_20261110_001",
            "active_scenario": "steady_milestone",
            "recent_orders": ["ORD_20261110_001", "ORD_20261109_088"],
            "slots": {
                "order_amount": 50000.0,
                "currency": "CNY",
                "payment_status": "requires_payment_method",
                "last_selected_scenario": "稳健阶段版 (推荐)",
                "contract_id": "doc_sla_2026",
            },
            "history": [],
            "snapshots": [],
        }

    def save(self) -> None:
        """持久化保存会话状态到磁盘。"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def disambiguate_query(self, query: str) -> Dict[str, Any]:
        """对自然语言中的指代与代词进行确定性消歧。"""
        resolved_order = self.state.get("slots", {}).get("current_order_id") or self.state.get("current_order_id", "ORD_20261110_001")
        resolved_scenario = self.state.get("slots", {}).get("active_scenario") or self.state.get("active_scenario", "steady_milestone")
        rewritten = query

        # 1. 代词：刚才/第二套方案 -> steady_milestone
        if re.search(r"第二套|第2套|稳健|阶段版", query):
            resolved_scenario = "steady_milestone"
            rewritten = re.sub(r"刚才第二套方案|第二套方案", "稳健阶段版 (steady_milestone)", rewritten)
        elif re.search(r"第一套|第1套|极简|现结", query):
            resolved_scenario = "minimal_instant"
            rewritten = re.sub(r"刚才第一套方案|第一套方案", "极简现结版 (minimal_instant)", rewritten)
        elif re.search(r"第三套|第3套|弹性|用量", query):
            resolved_scenario = "flexible_metered"
            rewritten = re.sub(r"刚才第三套方案|第三套方案", "弹性用量版 (flexible_metered)", rewritten)

        # 2. 指代：刚才那个订单 / 上一单
        if re.search(r"刚才那个订单|上一个订单|上一笔订单|这笔订单", query):
            rewritten = re.sub(r"刚才那个订单|上一个订单|上一笔订单|这笔订单", f"订单 [{resolved_order}]", rewritten)

        return {
            "original_query": query,
            "resolved_query": rewritten,
            "resolved_order_id": resolved_order,
            "resolved_scenario": resolved_scenario,
            "slots": self.state.get("slots", {}),
        }

    def update_slot(self, key: str, value: Any) -> None:
        """更新槽位状态并持久化。"""
        if "slots" not in self.state:
            self.state["slots"] = {}
        self.state["slots"][key] = value
        if key in self.state:
            self.state[key] = value
        self.save()

    def create_snapshot(self, label: str = "manual_snapshot") -> str:
        """为当前会话状态生成快照。"""
        snap_id = f"snap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        snapshot_entry = {
            "snapshot_id": snap_id,
            "label": label,
            "timestamp": datetime.datetime.now().isoformat(),
            "state_dump": copy.deepcopy(self.state),
        }
        if "snapshots" not in self.state:
            self.state["snapshots"] = []
        self.state["snapshots"].append(snapshot_entry)
        self.save()
        return snap_id

    def rollback(self, snapshot_id: Optional[str] = None) -> bool:
        """回滚到指定快照或最新一次快照。"""
        snapshots = self.state.get("snapshots", [])
        if not snapshots:
            return False

        target_snap = None
        if snapshot_id:
            for s in snapshots:
                if s["snapshot_id"] == snapshot_id:
                    target_snap = s
                    break
        else:
            target_snap = snapshots[-1]

        if not target_snap:
            return False

        old_snapshots = copy.deepcopy(snapshots)
        self.state = copy.deepcopy(target_snap["state_dump"])
        self.state["snapshots"] = old_snapshots
        self.save()
        return True
