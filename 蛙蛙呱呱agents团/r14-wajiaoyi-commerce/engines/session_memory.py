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
from core.workspace import role_workspace  # noqa: E402

import re
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
DEFAULT_SESSION_FILE = os.path.join(role_workspace(_PARENT), "session_state.json")

# 记忆池体积护栏（core/memory_guard.py）：仓库根不在 sys.path 时降级为无护栏，
# 角色本身不因护栏缺失而不可用。
try:  # pragma: no cover - 依赖部署布局
    _REPO_ROOT = os.path.dirname(os.path.dirname(_PARENT))
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    from core.memory_guard import (  # noqa: F401
        HARD_LIMIT_BYTES as _GUARD_HARD_LIMIT,
        enforce as _guard_enforce,
        load_json_guarded as _guarded_load,
    )
except Exception:  # pragma: no cover
    _guard_enforce = None
    _guarded_load = None
    _GUARD_HARD_LIMIT = 0


class CommerceSessionMemory:
    """交易多轮会话持久化记忆与代词消歧引擎。"""

    def __init__(self, state_file: str = DEFAULT_SESSION_FILE):
        self.state_file = state_file
        self.last_guard_notice: Optional[Dict[str, Any]] = None
        self.state = self.load()

    def load(self) -> Dict[str, Any]:
        """从磁盘加载会话状态（>100 MB 直接隔离，不送入 json.load）。"""
        if _guarded_load is not None:
            data, notice = _guarded_load(self.state_file, dict)
            if isinstance(notice, dict):
                self.last_guard_notice = notice
            if isinstance(data, dict) and data:
                return data
        elif os.path.exists(self.state_file):
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
        """为当前会话状态生成快照。

        快照只归档**业务态**（订单号 / 槽位 / 场景…），既不复制 ``snapshots`` 自身，
        也不复制 ``history``：历史轮次用 ``history_len`` 记长度，回滚时按长度截断。
        两个"不复制"分别对应两类事故：
        - 复制 ``snapshots`` → 第 N 次快照把此前 N-1 个快照再复制一遍，体积按 2^N 膨胀
          （历史事故：19 次快照 → 966 MB / 52 万次嵌套）；
        - 复制 ``history`` → 第 i 条快照装 i 条历史，体积按 O(n²) 膨胀（R05 同款问题）。
        """
        snap_id = f"snap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        business_state = {k: v for k, v in self.state.items()
                          if k not in ("snapshots", "history")}
        business_state["history_len"] = len(self.state.get("history") or [])
        snapshot_entry = {
            "snapshot_id": snap_id,
            "label": label,
            "timestamp": datetime.datetime.now().isoformat(),
            "state_dump": copy.deepcopy(business_state),
        }
        if "snapshots" not in self.state:
            self.state["snapshots"] = []
        self.state["snapshots"].append(snapshot_entry)
        self.save()
        # 体积护栏：文件超软上限（2 MB）时只保留最近 50 条快照，防止长期会话累积
        if _guard_enforce is not None:
            if _guard_enforce(self.state_file, self.state):
                self.save()
        return snap_id

    def rollback(self, snapshot_id: Optional[str] = None) -> bool:
        """回滚到指定快照或最新一次快照。

        恢复业务态并按 ``history_len`` 截断历史（保持"时间线回滚"语义），
        快照列表整体保留——回滚本身不销毁历史版本，可继续回滚到更早的快照。
        """
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
        current_history = self.state.get("history") or []
        self.state = copy.deepcopy(target_snap["state_dump"])
        self.state["snapshots"] = old_snapshots
        history_len = self.state.pop("history_len", None)
        if isinstance(history_len, int) and history_len >= 0:
            self.state["history"] = current_history[:history_len]
        elif "history" not in self.state:
            self.state["history"] = current_history
        self.save()
        return True
