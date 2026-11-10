# -*- coding: utf-8 -*-
"""engines/session_memory.py - L09 会话记忆层 (Persistent Session State & Disambiguation).

对标开源标杆（Stars > 1k）：
- MemGPT / Letta —— 分层记忆与持久化状态；
- langgraph State Store —— 状态快照、可回放与恢复；
- LangChain ConversationBufferMemory —— 槽位与指代消解。

解决 R07 历史断点：多轮需求对话中「按刚才第二套方案写 PRD」「把它加上移动端适配」
这类指代彻底失忆，跨进程重启后上下文归零。

核心能力：
1. 持久化记忆池 `workspace/session_state.json`（原子写 + 带 TTL 的文件锁，
   临时文件强制落在 workspace/tmp，规避 Windows 全局临时目录权限陷阱）；
2. 代词/序数消歧：第 N 套方案、刚才/上次、它/这个/该方案、渠道切换、追加特性；
3. 版本快照树 + 一键回滚（v1 → v2 → ...，每版记录父版本）；
4. 槽位与顶层实体字段双向同步（SOP §5.14），杜绝「读旧值」状态漂移。
"""
from __future__ import annotations

import copy
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["SessionMemory", "CHINESE_ORDINALS"]

SESSION_SCHEMA = "pm.session/v1"

CHINESE_ORDINALS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
                    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
                    "6": 6, "7": 7, "8": 8, "9": 9, "10": 10}

_REFERENCE_TOKENS = ("刚才", "刚刚", "上次", "上一个", "之前", "前面", "上述")
_PRONOUN_TOKENS = ("它", "这个", "该方案", "那套", "这套", "其")

_DEFAULT_SCENARIOS = ["lean_mvp", "commercial_standard", "enterprise_flagship"]

_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}


def _parse_ordinal(token: str) -> int:
    """阿拉伯数字或中文数字（一~九十九）转 int；无法解析返回 0。"""
    token = str(token).strip()
    if token.isdigit():
        return int(token)
    if token == "十":
        return 10
    if "十" in token:
        head, _, tail = token.partition("十")
        tens = _CN_DIGITS.get(head, 1) if head else 1
        ones = _CN_DIGITS.get(tail, 0) if tail else 0
        return tens * 10 + ones
    return _CN_DIGITS.get(token, 0)


class SessionMemory:
    """R07 多轮会话记忆体（确定性、可测试、可回滚）。"""

    def __init__(self, path: Optional[str] = None, agent: str = "r07-wademing-pm",
                 clock=None) -> None:
        here = os.path.dirname(os.path.abspath(__file__))
        self.agent_dir = os.path.dirname(here)
        self.path = path or os.path.join(self.agent_dir, "workspace", "session_state.json")
        self.tmp_dir = os.path.join(self.agent_dir, "workspace", "tmp")
        self.agent = agent
        self._clock = clock or (lambda: time.time())
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.data = self._load()

    # ------------------------------------------------------------------ #
    # 持久化（原子写 + TTL 文件锁）
    # ------------------------------------------------------------------ #
    def _empty(self) -> Dict[str, Any]:
        now = self._now()
        return {
            "schema": SESSION_SCHEMA,
            "agent": self.agent,
            "created_at": now,
            "updated_at": now,
            "turn": 0,
            "slots": {"scenarios": list(_DEFAULT_SCENARIOS)},
            "entities": {},
            "interactions": [],
            "snapshots": [],
            "current_snapshot": 0,
        }

    def _now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self._clock()))

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict) and data.get("schema") == SESSION_SCHEMA:
                    data.setdefault("slots", {})
                    data.setdefault("entities", {})
                    data.setdefault("interactions", [])
                    data.setdefault("snapshots", [])
                    return data
            except (OSError, ValueError):
                pass
        return self._empty()

    def _lock(self) -> str:
        """带 TTL 的文件锁：避免跨进程死锁（SOP §5.3）。"""
        lock_path = self.path + ".lock"
        ttl = 30.0
        try:
            if os.path.exists(lock_path):
                age = self._clock() - os.path.getmtime(lock_path)
                if age < ttl:
                    return lock_path
                os.remove(lock_path)  # 超时锁视为陈旧锁，强制剔除
        except OSError:
            pass
        try:
            with open(lock_path, "w", encoding="utf-8") as fh:
                fh.write(f"{os.getpid()} {self._clock()}")
        except OSError:
            pass
        return lock_path

    def save(self) -> Dict[str, Any]:
        lock_path = self._lock()
        self.data["updated_at"] = self._now()
        target_dir = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(target_dir, exist_ok=True)
        # 原子替换要求临时文件与目标同目录（跨盘符 os.replace 会抛 WinError 17）；
        # 若目标目录不可写，退回角色 workspace/tmp 下并直接写目标文件。
        tmp = os.path.join(target_dir, f".session_{os.getpid()}.json.tmp")
        payload = json.dumps(self.data, ensure_ascii=False, indent=2) + "\n"
        try:
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
            os.replace(tmp, self.path)
        except OSError:
            tmp = os.path.join(self.tmp_dir, f"session_{os.getpid()}.json.tmp")
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
            with open(self.path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(payload)
            try:
                os.remove(tmp)
            except OSError:
                pass
        try:
            os.remove(lock_path)
        except OSError:
            pass
        return {"saved": True, "path": self.path, "turn": self.data.get("turn", 0)}

    # ------------------------------------------------------------------ #
    # 槽位（双向同步）
    # ------------------------------------------------------------------ #
    def update_slot(self, key: str, value: Any) -> Dict[str, Any]:
        """写槽位：同时写 slots[key] 与顶层 key（SOP §5.14 双向同步）。"""
        self.data.setdefault("slots", {})[key] = value
        self.data[key] = value
        return {"slot": key, "value": value}

    def get_slot(self, key: str, default: Any = None) -> Any:
        slots = self.data.get("slots") or {}
        if key in slots:
            return slots[key]
        return self.data.get(key, default)

    # ------------------------------------------------------------------ #
    # 指代 / 序数消歧
    # ------------------------------------------------------------------ #
    def _last_entity(self, kind: str) -> Optional[Any]:
        for item in reversed(self.data.get("interactions", [])):
            resolved = item.get("resolved") or {}
            for ref in resolved:
                if ref.get("kind") == kind:
                    return ref.get("value")
            if item.get("intent_kind") == kind:
                return item.get("intent_value")
        return self.get_slot(f"last_{kind}")

    def resolve_reference(self, text: str) -> Dict[str, Any]:
        """解析一句自然语言里的指代/序数/切换指令，返回确定性解析结果。"""
        text = str(text or "")
        resolved: List[Dict[str, Any]] = []
        scenarios = self.get_slot("scenarios") or list(_DEFAULT_SCENARIOS)

        # ① 「第 N 套方案」序数消歧（支持 0~999 与一~九十九；越界/0 必须显式澄清）
        ordinal = re.search(r"第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*(?:套|个|种)\s*方案",
                            text)
        if ordinal:
            idx = _parse_ordinal(ordinal.group(1))
            if 1 <= idx <= len(scenarios):
                value = scenarios[idx - 1]
                self.update_slot("current_scenario", value)
                resolved.append({"token": ordinal.group(0), "kind": "scenario",
                                 "value": value, "reason": f"序数第 {idx} 套方案"})
            else:
                resolved.append({"token": ordinal.group(0), "kind": "unresolved",
                                 "value": None,
                                 "reason": f"序数第 {idx} 套超出可选范围 1~{len(scenarios)}"})
        elif any(tok in text for tok in _REFERENCE_TOKENS):
            last = self._last_entity("scenario") or self.get_slot("current_scenario")
            if last:
                resolved.append({"token": next(t for t in _REFERENCE_TOKENS if t in text),
                                 "kind": "scenario", "value": last,
                                 "reason": "回溯最近一次方案"})

        # ② 渠道切换
        channel = re.search(r"(?:切换|改|换)(?:到|成|为)?\s*([\u4e00-\u9fa5A-Za-z0-9]{1,12}?)"
                            r"(?:渠道|平台|投放)", text)
        if channel:
            value = channel.group(1)
            self.update_slot("channel", value)
            resolved.append({"token": channel.group(0), "kind": "channel",
                             "value": value, "reason": "渠道切换指令"})

        # ③ 追加特性（「把它加上移动端适配」「这个方案再加一个埋点」）
        pending = None
        if any(tok in text for tok in _PRONOUN_TOKENS) or "加上" in text or "再加" in text:
            add = re.search(r"(?:加上|再加|新增|加个|补个|补充|增加)\s*([^，。；;]+)", text)
            if add:
                pending = add.group(1).strip()
        feature_target_missing = False
        if pending:
            target = self.get_slot("current_scenario") or self._last_entity("scenario")
            feats = list(self.data.get("entities", {}).get("pending_features") or [])
            feats.append(pending)
            self.data.setdefault("entities", {})["pending_features"] = feats
            self.update_slot("pending_features", feats)
            feature_target_missing = target is None
            resolved.append({"token": pending, "kind": "feature", "value": pending,
                             "target": target,
                             "reason": "追加特性到当前方案" if target
                             else "追加特性但无可挂载方案，需澄清"})

        # ④ 兜底：出现代词但一个指代都没解析出来 → 必须显式要求澄清
        has_pronoun = any(tok in text for tok in _PRONOUN_TOKENS)
        needs_clarification = bool((has_pronoun and not resolved) or feature_target_missing)
        if has_pronoun and not resolved:
            resolved.append({"token": next(t for t in _PRONOUN_TOKENS if t in text),
                             "kind": "unresolved", "value": None,
                             "reason": "无历史指代对象"})
        elif any(r.get("kind") == "unresolved" for r in resolved):
            needs_clarification = True

        self.data["turn"] = int(self.data.get("turn", 0)) + 1
        self.data.setdefault("interactions", []).append({
            "turn": self.data["turn"], "role": "user", "text": text,
            "resolved": resolved, "at": self._now(),
        })
        return {"text": text, "resolved": resolved,
                "needs_clarification": needs_clarification,
                "slots": {
                    "current_scenario": self.get_slot("current_scenario"),
                    "channel": self.get_slot("channel"),
                    "pending_features": self.get_slot("pending_features"),
                }}

    # ------------------------------------------------------------------ #
    # 快照树与回滚
    # ------------------------------------------------------------------ #
    def reset(self) -> Dict[str, Any]:
        """重置记忆体（自检探针使用，保证多次运行结果确定且不累积脏快照）。"""
        created = self.data.get("created_at")
        self.data = self._empty()
        if created:
            self.data["created_at"] = created
        return {"reset": True}

    def _snapshot_payload(self) -> Dict[str, Any]:
        # 快照只固化「业务状态」（槽位 + 实体）；对话历史保持 append-only，
        # 回滚不得抹掉已发生的用户轮次，否则事后审计无法重建对话。
        return copy.deepcopy({
            "slots": self.data.get("slots", {}),
            "entities": self.data.get("entities", {}),
        })

    def create_snapshot(self, label: str = "") -> Dict[str, Any]:
        snapshots = self.data.setdefault("snapshots", [])
        # 版本号必须对全量快照单调递增，禁止用 current_snapshot+1（回滚后会撞号）
        version = max([int(s.get("version", 0)) for s in snapshots] or [0]) + 1
        parent = int(self.data.get("current_snapshot", 0))
        snapshots.append({
            "version": version,
            "label": label or f"v{version}",
            "parent": parent,
            "created_at": self._now(),
            "state": self._snapshot_payload(),
        })
        self.data["current_snapshot"] = version
        return {"version": version, "label": label, "parent": parent,
                "snapshots_total": len(snapshots)}

    def list_snapshots(self) -> List[Dict[str, Any]]:
        return [{"version": s["version"], "label": s["label"],
                 "parent": s.get("parent"), "created_at": s["created_at"]}
                for s in self.data.get("snapshots", [])]

    def rollback(self, version: int) -> Dict[str, Any]:
        target = None
        for snap in self.data.get("snapshots", []):
            if int(snap.get("version", -1)) == int(version):
                target = snap  # 同版本号取最后一条，杜绝撞号后回滚到旧状态
        if target is None:
            return {"ok": False, "error": f"快照版本不存在：{version}"}
        state = copy.deepcopy(target["state"])
        self.data["slots"] = state.get("slots", {})
        self.data["entities"] = state.get("entities", {})
        # 顶层镜像字段同步回滚：先清掉快照里不存在的残留镜像，再写回快照值
        structural = {"schema", "agent", "created_at", "updated_at", "turn",
                      "slots", "entities", "interactions", "snapshots",
                      "current_snapshot"}
        for key in list(self.data):
            if key not in structural and key not in state.get("slots", {}):
                del self.data[key]
        for key, value in state.get("slots", {}).items():
            self.data[key] = value
        self.data["current_snapshot"] = int(version)
        # 对话历史 append-only：回滚只追加一条系统标记，并真实递增 turn
        self.data["turn"] = int(self.data.get("turn", 0)) + 1
        self.data.setdefault("interactions", []).append({
            "turn": self.data["turn"], "role": "system",
            "text": f"rollback -> v{version}", "resolved": [], "at": self._now()})
        return {"ok": True, "rolled_back_to": int(version),
                "label": target["label"],
                "slots": dict(state.get("slots", {}))}

    # ------------------------------------------------------------------ #
    # 自检（CLI 物理探针）
    # ------------------------------------------------------------------ #
    def self_test(self) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        self.reset()  # 探针必须可重复执行：先清空历史快照与槽位

        def rec(name: str, ok: bool, detail: Any = "") -> None:
            steps.append({"step": name, "ok": bool(ok), "detail": detail})

        self.update_slot("scenarios", list(_DEFAULT_SCENARIOS))
        self.update_slot("current_scenario", "lean_mvp")
        rec("槽位双向同步", self.data.get("current_scenario") == "lean_mvp"
            and self.data["slots"]["current_scenario"] == "lean_mvp",
            "slots + 顶层实体字段一致")

        r1 = self.resolve_reference("按刚才第二套方案把 PRD 补全")
        rec("序数消歧（第二套方案）",
            r1["resolved"] and r1["resolved"][0]["value"] == "commercial_standard",
            r1["resolved"][0]["value"] if r1["resolved"] else None)

        snap1 = self.create_snapshot("before-channel-switch")
        r2 = self.resolve_reference("切换到小红书投放渠道")
        rec("渠道切换槽位", self.get_slot("channel") == "小红书", self.get_slot("channel"))
        snap2 = self.create_snapshot("after-channel-switch")
        rec("快照树父子链", snap2["parent"] == snap1["version"]
            and len(self.list_snapshots()) >= 2, self.list_snapshots())

        r3 = self.resolve_reference("把它加上移动端适配")
        rec("代词 + 追加特性", "移动端适配" in (self.get_slot("pending_features") or [])
            and r3["resolved"], r3["slots"])

        rollback = self.rollback(snap1["version"])
        rec("一键回滚", rollback["ok"] and self.get_slot("channel") is None,
            rollback.get("slots"))

        saved = self.save()
        rec("持久化落盘", os.path.isfile(saved["path"]), saved["path"])
        reloaded = SessionMemory(path=self.path)
        rec("跨进程重载（不失忆）",
            reloaded.get_slot("current_scenario") == "commercial_standard"
            and reloaded.get_slot("scenarios") == _DEFAULT_SCENARIOS,
            reloaded.get_slot("current_scenario"))

        ok = all(s["ok"] for s in steps)
        return {"ok": ok, "layer": "L09", "engine": "SessionMemory",
                "steps": steps, "state_path": self.path,
                "turn": self.data.get("turn"),
                "snapshots": self.list_snapshots()}
