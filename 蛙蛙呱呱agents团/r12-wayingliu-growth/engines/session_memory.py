# -*- coding: utf-8 -*-
"""engines/session_memory.py - L09 会话记忆层 (Persistent Session State & Disambiguation).

对标标杆: MemGPT (Letta) / LangGraph State Store (Stars > 15k)
核心功能:
1. 在 workspace/session_state.json 维护跨会话状态持久化
2. 细粒度增长运营槽位记忆 (north_star, target_channel, budget, k_factor, audience, scenario)
3. 多轮交互穿透与自然语言代词消歧（“按刚才第二套方案投放”、“把预算切到小红书渠道”、“沿用上一版的北极星指标”）
4. 版本快照树与一键回滚 (Rollback)
"""
from __future__ import annotations

import copy
import json
import os
from core.workspace import role_workspace  # noqa: E402

import time
from typing import Any, Dict, List, Optional


class GrowthSessionMemory:
    """增长运营多轮交互会话记忆池与代词消歧引擎。"""

    DEFAULT_SLOTS = {
        "north_star": "WAU",
        "target_channel": "微信公众号",
        "budget": 50000.0,
        "target_cac": 120.0,
        "k_factor": 1.15,
        "scenario": "steady_lean",
        "audience": "高潜核心付费开发者",
        "extra_slots": {},
    }

    def __init__(self, state_file: Optional[str] = None, session_id: str = "r12_growth_session") -> None:
        if not state_file:
            here = os.path.dirname(os.path.abspath(__file__))
            agent_root = os.path.dirname(here)
            state_file = os.path.join(role_workspace(agent_root), "session_state.json")
        self.state_file = state_file
        self.session_id = session_id

        self.current_state: Dict[str, Any] = {
            "session_id": self.session_id,
            "version": "1.0.0",
            "slots": copy.deepcopy(self.DEFAULT_SLOTS),
            "turn_count": 0,
            "current_snapshot_id": None,
            "history": [],
            "snapshots": {},
        }
        self.load()

    def load(self) -> None:
        """从持久化文件加载会话状态。"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.current_state.update(data)
            except Exception:
                pass

    def save(self) -> None:
        """将当前会话状态持久化至 workspace/session_state.json。"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.current_state, f, ensure_ascii=False, indent=2)

    def record_turn(self, user_query: str, slot_updates: Dict[str, Any]) -> str:
        """记录一轮增长策略交互，更新槽位并生成版本快照。"""
        self.current_state["turn_count"] += 1
        for k, v in slot_updates.items():
            self.current_state["slots"][k] = v

        turn_id = f"turn_{self.current_state['turn_count']:03d}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

        turn_entry = {
            "turn_id": turn_id,
            "query": user_query,
            "updated_slots": slot_updates,
            "timestamp": now_str,
        }
        self.current_state["history"].append(turn_entry)

        # 自动生成快照
        snap_id = f"snap_{int(time.time()*1000)}"
        self.current_state["snapshots"][snap_id] = {
            "snapshot_id": snap_id,
            "turn_id": turn_id,
            "slots": copy.deepcopy(self.current_state["slots"]),
            "timestamp": now_str,
            "query": user_query,
        }
        self.current_state["current_snapshot_id"] = snap_id
        self.save()
        return snap_id

    def resolve_pronouns(self, query: str) -> Dict[str, Any]:
        """自然语言代词消歧：解析'按刚才第二套方案'、'切换到小红书渠道'、'把预算换回上一版'等模糊指代。"""
        q = query.lower()
        had_ambiguity = False
        inherited_slots: Dict[str, Any] = {}
        resolved_slots = copy.deepcopy(self.current_state["slots"])

        # 1. 方案/情景消歧
        if any(kw in q for kw in ["刚才", "上一版", "上一个", "刚才那套", "第"]):
            had_ambiguity = True
            if "第二套" in q or "稳健" in q or "steady" in q:
                resolved_slots["scenario"] = "steady_lean"
                inherited_slots["scenario"] = "steady_lean"
            elif "第一套" in q or "极速" in q or "minimal" in q:
                resolved_slots["scenario"] = "minimal_rapid"
                inherited_slots["scenario"] = "minimal_rapid"
            elif "第三套" in q or "全域" in q or "roi" in q or "balanced" in q:
                resolved_slots["scenario"] = "omnichannel_roi_balanced"
                inherited_slots["scenario"] = "omnichannel_roi_balanced"

        # 2. 渠道局部重载
        if "小红书" in q:
            resolved_slots["target_channel"] = "小红书"
            inherited_slots["target_channel"] = "小红书"
        elif "公众号" in q or "微信" in q:
            resolved_slots["target_channel"] = "微信公众号"
            inherited_slots["target_channel"] = "微信公众号"
        elif "信息流" in q or "付费" in q or "投放" in q:
            resolved_slots["target_channel"] = "付费信息流"
            inherited_slots["target_channel"] = "付费信息流"
        elif "aso" in q or "应用商店" in q:
            resolved_slots["target_channel"] = "ASO应用商店"
            inherited_slots["target_channel"] = "ASO应用商店"

        # 3. 北极星指标指代
        if "wau" in q:
            resolved_slots["north_star"] = "WAU"
            inherited_slots["north_star"] = "WAU"
        elif "mau" in q:
            resolved_slots["north_star"] = "MAU"
            inherited_slots["north_star"] = "MAU"
        elif "收入" in q or "arr" in q or "mrr" in q:
            resolved_slots["north_star"] = "MRR"
            inherited_slots["north_star"] = "MRR"

        return {
            "query": query,
            "had_ambiguity": had_ambiguity,
            "inherited_slots": inherited_slots,
            "resolved_slots": resolved_slots,
            "active_north_star": resolved_slots.get("north_star"),
            "active_channel": resolved_slots.get("target_channel"),
            "active_scenario": resolved_slots.get("scenario"),
        }

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """获取所有历史版本快照列表。"""
        return list(self.current_state.get("snapshots", {}).values())

    def rollback(self, snapshot_id: str) -> bool:
        """一键回滚到指定的快照版本。"""
        if snapshot_id in self.current_state.get("snapshots", {}):
            target_snap = self.current_state["snapshots"][snapshot_id]
            self.current_state["slots"] = copy.deepcopy(target_snap["slots"])
            self.current_state["current_snapshot_id"] = snapshot_id
            self.save()
            return True
        return False
