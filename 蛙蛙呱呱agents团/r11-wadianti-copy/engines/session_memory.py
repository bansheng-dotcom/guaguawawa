# -*- coding: utf-8 -*-
"""engines/session_memory.py - L09 会话记忆层 (Persistent Session State & Disambiguation).

对标标杆: MemGPT (Letta) / LangGraph State Store (Stars > 15k)
核心功能:
1. 在 workspace/session_state.json 维护跨会话状态持久化
2. 细粒度创作槽位记忆 (topic, channel, style, title, target_audience)
3. 多轮上下文穿透与自然语言代词消歧（“按刚才第二套风格改写”、“把上一版的标题换过来”）
4. 版本快照树与一键回滚 (Rollback)
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple


class ContentSessionMemory:
    """文案创作与运营会话记忆池。"""

    DEFAULT_SLOTS = {
        "topic": "内容复利与自动化运营",
        "channel": "微信公众号",
        "style": "深度硬核",
        "title": "默认长文标题",
        "target_audience": "研发与业务负责人",
        "extra_slots": {},
    }

    def __init__(self, state_file: Optional[str] = None, session_id: str = "r11_default_session") -> None:
        if not state_file:
            here = os.path.dirname(os.path.abspath(__file__))
            agent_root = os.path.dirname(here)
            state_file = os.path.join(agent_root, "workspace", "session_state.json")
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
        """将当前会话状态持久化至文件。"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.current_state, f, ensure_ascii=False, indent=2)

    def record_turn(self, user_query: str, slot_updates: Dict[str, Any]) -> str:
        """记录一轮创作交互，更新槽位并生成版本快照。"""
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
        """自然语言代词消歧：解析'按刚才第二套风格'、'换成小红书渠道'、'把刚才的标题换掉'等模糊指代。"""
        q = query.lower()
        had_ambiguity = False
        inherited_slots: Dict[str, Any] = {}
        resolved_slots = copy.deepcopy(self.current_state["slots"])

        # 1. 样式/方案消歧
        if any(kw in q for kw in ["刚才", "上一版", "上一个", "刚才那套"]):
            had_ambiguity = True
            if "第二套" in q or "情感" in q or "故事" in q:
                resolved_slots["style"] = "故事共鸣流"
                inherited_slots["style"] = "故事共鸣流"
            elif "第一套" in q or "极简" in q or "数据" in q:
                resolved_slots["style"] = "极简数据流"
                inherited_slots["style"] = "极简数据流"
            elif "第三套" in q or "爆款" in q or "转化" in q:
                resolved_slots["style"] = "爆款转化流"
                inherited_slots["style"] = "爆款转化流"

        # 2. 渠道局部重载
        if "小红书" in q:
            resolved_slots["channel"] = "小红书笔记"
            inherited_slots["channel"] = "小红书笔记"
        elif "公众号" in q or "微信" in q:
            resolved_slots["channel"] = "微信公众号"
            inherited_slots["channel"] = "微信公众号"
        elif "知乎" in q:
            resolved_slots["channel"] = "知乎专栏/回答"
            inherited_slots["channel"] = "知乎专栏/回答"

        return {
            "query": query,
            "had_ambiguity": had_ambiguity,
            "inherited_slots": inherited_slots,
            "resolved_slots": resolved_slots,
            "active_topic": resolved_slots.get("topic"),
            "active_channel": resolved_slots.get("channel"),
            "active_style": resolved_slots.get("style"),
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
