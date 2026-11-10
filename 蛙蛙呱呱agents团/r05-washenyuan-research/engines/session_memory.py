# -*- coding: utf-8 -*-
"""L09 会话记忆层：持久化研究会话状态、槽位双向同步、代词/数量指代消歧与真实回滚。

对标标杆:
- cpacker/MemGPT (Letta 14k⭐) / langchain-ai/langgraph (11k⭐ checkpoint)
吸收的机制:
- MemGPT 的分层记忆池：session 级 state（focus / slots / entities）+ 历史轮次，
  槽位写入同时落到顶层字段（SOP 五-14 双向同步），供下游按任一口径读取；
- LangGraph checkpoint 的“先快照后变更”：每次 record_turn/update_slot 先把当前
  state 深拷贝快照入 snapshots（含 version），rollback 整体恢复业务字段而不是
  只弹空列表；
- 检索式指代消歧：'刚才/上一轮/之前那个/上个' 解析到 current_focus /
  slots.current_market / entities.last_topic；'第二套方案/方案2' 解析到最近
  一条带 scenarios 的 history 的对应情景（中文数字支持到十）。

纯标准库实现（copy/json/os/re/time/uuid），Windows 路径安全。
"""
from __future__ import annotations
import copy
import datetime
import json
import os
import re
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# 记忆池体积护栏（core/memory_guard.py）：仓库根不在 sys.path 时降级为无护栏。
try:  # pragma: no cover - 依赖部署布局
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    from core.memory_guard import (  # noqa: F401
        enforce as _guard_enforce,
        load_json_guarded as _guarded_load,
        trim_snapshots as _trim_snapshots,
    )
except Exception:  # pragma: no cover
    _guard_enforce = None
    _guarded_load = None
    _trim_snapshots = None

# 中文数字到阿拉伯数字（SOP 只要求支持到十，额外兼容“两”）。
_CN_NUMERALS: Dict[str, int] = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# 代词/回指词表：命中即触发焦点回忆。
_PRONOUN_WORDS = ("刚才", "上一轮", "之前那个", "上个")

_ORDINAL_PATTERN = re.compile(r"第\s*([一二两三四五六七八九十\d]+)\s*套")
_SCENARIO_NUM_PATTERN = re.compile(r"方案\s*([0-9０-９一二两三四五六七八九十]+)")


def _default_storage_path() -> str:
    role_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(role_dir, "workspace", "tmp", "r05_session_state.json")


def _default_state() -> Dict[str, Any]:
    return {
        "session_id": f"r05_session_{uuid.uuid4().hex[:8]}",
        "version": 0,
        "current_focus": None,
        "slots": {},
        "entities": {},
        "history": [],
        "snapshots": [],
    }


class ResearchSessionStore:
    """多轮研究会话状态存储：槽位同步、指代消歧、快照回滚与 JSON 持久化。"""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = os.path.abspath(storage_path or _default_storage_path())
        self._state: Dict[str, Any] = _default_state()
        self.last_guard_notice: Optional[Dict[str, Any]] = None
        self.load()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    @property
    def state(self) -> Dict[str, Any]:
        return self._state

    def load(self) -> Dict[str, Any]:
        """从磁盘载入会话状态；缺失 / 损坏 / 超 100 MB 时回落到全新默认 state。"""
        if not os.path.exists(self.storage_path):
            return self._state
        if _guarded_load is not None:
            loaded, notice = _guarded_load(self.storage_path, dict)
            if isinstance(notice, dict):
                self.last_guard_notice = notice
        else:  # pragma: no cover - 护栏不可用时的降级路径
            try:
                with open(self.storage_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
            except (OSError, ValueError):
                return self._state
        if not isinstance(loaded, dict):
            return self._state
        merged = _default_state()
        merged.update(loaded)
        # 结构字段必须保持正确类型，避免外部手改文件破坏算子。
        if not isinstance(merged.get("slots"), dict):
            merged["slots"] = {}
        if not isinstance(merged.get("entities"), dict):
            merged["entities"] = {}
        if not isinstance(merged.get("history"), list):
            merged["history"] = []
        if not isinstance(merged.get("snapshots"), list):
            merged["snapshots"] = []
        try:
            merged["version"] = int(merged.get("version", 0))
        except (TypeError, ValueError):
            merged["version"] = 0
        self._state = merged
        return self._state

    def save(self) -> str:
        """JSON 持久化（ensure_ascii=False，保持中文可读）。"""
        directory = os.path.dirname(self.storage_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._write()
        # 体积护栏：文件超软上限（2 MB）时裁到最近 50 条快照后重写一次
        if _guard_enforce is not None and _guard_enforce(self.storage_path, self._state):
            self._write()
        return self.storage_path

    def _write(self) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as fh:
            json.dump(self._state, fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 快照
    # ------------------------------------------------------------------
    def _push_snapshot(self, reason: str) -> Dict[str, Any]:
        """把当前业务态深拷贝入栈，快照带 version。

        只存业务字段（焦点 / 槽位 / 实体 / 版本），**不复制 history 与 snapshots**：
        历史轮次用 ``history_len`` 记录长度，回滚时按长度截断即可还原时间线。
        旧实现把整份 history 复制进每条快照，第 i 条快照装 i 条历史，
        长期会话体积按 O(n²) 膨胀（80 轮 3 MB、1000 轮约 480 MB）。
        """
        payload = {key: value for key, value in self._state.items()
                   if key not in ("snapshots", "history")}
        payload["history_len"] = len(self._state.get("history") or [])
        snapshot = {
            "version": self._state.get("version", 0),
            "reason": reason,
            "at": datetime.datetime.now().isoformat(timespec="milliseconds"),
            "state": copy.deepcopy(payload),
        }
        snapshots = self._state.setdefault("snapshots", [])
        snapshots.append(snapshot)
        # 保留上限：只留最近 50 条，避免无限累积
        if _trim_snapshots is not None:
            _trim_snapshots(self._state, keep_last=50)
        return snapshot

    # ------------------------------------------------------------------
    # 写操作
    # ------------------------------------------------------------------
    def record_turn(self, user_query: str, agent_output: Dict[str, Any],
                    topic: Optional[str] = None) -> Dict[str, Any]:
        """记录一轮问答：先快照，再落 history/focus/entities/version。"""
        self._push_snapshot("record_turn")

        history = self._state.setdefault("history", [])
        turn_id = len(history) + 1
        entry = {
            "turn_id": turn_id,
            "user": user_query,
            "agent": copy.deepcopy(agent_output),
            "topic": topic,
            "at": datetime.datetime.now().isoformat(timespec="milliseconds"),
        }
        history.append(entry)

        entities = self._state.setdefault("entities", {})
        if topic:
            self._state["current_focus"] = topic
            entities["last_topic"] = topic
        elif self._state.get("current_focus"):
            entities.setdefault("last_topic", self._state["current_focus"])
        else:
            self._state["current_focus"] = user_query
            entities["last_topic"] = user_query

        previous_version = self._state.get("version", 0)
        try:
            self._state["version"] = int(previous_version) + 1
        except (TypeError, ValueError):
            self._state["version"] = 1
        self.save()
        return entry

    def update_slot(self, key: str, value: Any) -> Dict[str, Any]:
        """写入槽位：先快照，再同步 slots[key] 与顶层 state[key]（SOP 五-14）。"""
        if not isinstance(key, str) or not key:
            raise ValueError("槽位 key 必须是非空字符串")
        self._push_snapshot("update_slot")

        slots = self._state.setdefault("slots", {})
        slots[key] = copy.deepcopy(value)
        self._state[key] = copy.deepcopy(value)
        try:
            self._state["version"] = int(self._state.get("version", 0)) + 1
        except (TypeError, ValueError):
            self._state["version"] = 1
        self.save()
        return {"key": key, "value": copy.deepcopy(value),
                "version": self._state["version"]}

    def get_slot(self, key: str) -> Any:
        """读取槽位：优先 slots，其次顶层同名字段。"""
        slots = self._state.get("slots") or {}
        if key in slots:
            return slots[key]
        return self._state.get(key)

    # ------------------------------------------------------------------
    # 指代消歧
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_ordinal(text: str) -> Optional[int]:
        """从文本中解析“第 N 套 / 方案 N”的 1-based 序号。"""
        match = _ORDINAL_PATTERN.search(text)
        token: Optional[str] = None
        if match:
            token = match.group(1)
        else:
            match = _SCENARIO_NUM_PATTERN.search(text)
            if match:
                token = match.group(1)
        if not token:
            return None
        token = token.strip().translate(str.maketrans("０１２３４５６７８９",
                                                      "0123456789"))
        if token.isdigit():
            number = int(token)
        else:
            # 兼容“十二”这类简单组合（个位默认 0）。
            number = 0
            for char in token:
                number = number * 10 + _CN_NUMERALS.get(char, 0)
        return number if number > 0 else None

    def _scenarios_from_history(self) -> List[Any]:
        """取最近一条真正带 scenarios 的 history 的 agent.scenarios。"""
        for entry in reversed(self._state.get("history") or []):
            agent = entry.get("agent") if isinstance(entry, dict) else None
            if isinstance(agent, dict):
                scenarios = agent.get("scenarios")
                if isinstance(scenarios, list) and scenarios:
                    return scenarios
        return []

    def resolve_reference(self, text: str) -> Any:
        """解析指代：数量代词 → 情景；回指词 → 当前焦点实体；否则 None。"""
        if not isinstance(text, str) or not text.strip():
            return None

        # 1) 数量代词/序号指代：第二套方案 / 方案2 → scenarios[index]
        ordinal = self._parse_ordinal(text)
        if ordinal is not None:
            scenarios = self._scenarios_from_history()
            index = ordinal - 1
            if not scenarios or index >= len(scenarios):
                return None
            scenario = scenarios[index]
            if isinstance(scenario, dict):
                name = scenario.get("name") or scenario.get("scenario") or scenario.get("title")
            else:
                name = str(scenario)
            return {"scenario_index": index,
                    "scenario": copy.deepcopy(scenario),
                    "name": name}

        # 2) 回指代词：刚才 / 上一轮 / 之前那个 / 上个
        if any(word in text for word in _PRONOUN_WORDS):
            slots = self._state.get("slots") or {}
            entities = self._state.get("entities") or {}
            return (self._state.get("current_focus")
                    or slots.get("current_market")
                    or entities.get("last_topic"))
        return None

    # ------------------------------------------------------------------
    # 回滚
    # ------------------------------------------------------------------
    def rollback(self, steps: int = 1) -> bool:
        """回滚 steps 步：弹出最近快照并整体恢复业务字段（保留剩余快照）。"""
        snapshots = self._state.get("snapshots")
        if not isinstance(snapshots, list) or not snapshots:
            return False
        try:
            steps = max(1, int(steps))
        except (TypeError, ValueError):
            steps = 1

        restored: Optional[Dict[str, Any]] = None
        for _ in range(steps):
            if not snapshots:
                break
            restored = snapshots.pop()
        if restored is None:
            return False

        snapshot_state = restored.get("state")
        if not isinstance(snapshot_state, dict):
            return False

        recovered = copy.deepcopy(snapshot_state)
        recovered["snapshots"] = snapshots
        history_len = recovered.pop("history_len", None)
        current_history = self._state.get("history") or []
        if isinstance(history_len, int) and history_len >= 0:
            # 新格式：按长度把历史截断回快照时刻，保持“时间线回滚”语义
            recovered["history"] = current_history[:history_len]
        elif "history" not in recovered:
            # 兜底：既无 history_len 也无 history 时保留现有历史
            recovered["history"] = current_history
        self._state = recovered
        try:
            self._state["version"] = int(self._state.get("version", 0))
        except (TypeError, ValueError):
            self._state["version"] = 0
        self.save()
        return True
