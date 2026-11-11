# -*- coding: utf-8 -*-
"""L09 会话记忆层 (Persistent Session State & Disambiguation Memory Layer)
对标开源: MemGPT (Letta) / LangGraph State Store (Stars > 14k)
架构跃迁设计:
1. 记忆分层与槽位管理 (Hierarchical Memory & Multi-Slot State):
   - 参考 MemGPT 分层架构设计：Core Memory (工作区活跃槽位/固定上下文) + Recall Memory (多轮交互历史链) + Archival Storage (快照树库)；
   - 细粒度四槽位 (Metric / Dimension / TimeWindow / Filter) 状态管理，并支持动态槽位与置信度打标。
2. 版本快照树与一键无损回滚 (Snapshot Tree & Safe Rollback):
   - 参考 LangGraph State Store Checkpointing：每轮执行记录全量状态版本链 (snapshot_id, parent_id, timestamp, tags)；
   - 支持根据 snapshot_id 或 turn 回滚，保留回滚历史线并支持多步撤销 (undo) / 重做 (redo) 与分支溯源。
3. 多跳上下文追踪与代词/指代多重消歧 (Multi-Hop Disambiguation Engine):
   - 解析“刚才的”、“前一次”、“上个月的口径”、“换成按省份看刚才的指标”、“回退到第一个方案”等长距离和局部代词；
   - 局部重载机制：仅更新查询中明确变更的槽位，未变槽位精准继承上一轮状态。
"""
from __future__ import annotations
import contextlib
import copy
import hashlib
import json
import os
from core.workspace import role_workspace  # noqa: E402

import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union


class AnalysisSessionMemoryPool:
    """会话记忆池，支持上下文穿透、细粒度槽位记忆、快照树管理与自然语言指代消歧。"""

    DEFAULT_SLOTS = {
        "metric": "amount",
        "dimension": "channel",
        "time_window": "2024-01",
        "filters": {},
        "extra_slots": {},
    }

    def __init__(self, state_file: Optional[str] = None, session_id: str = "default_session",
                 lock_ttl_sec: float = 5.0, lock_timeout_sec: float = 2.0):
        if not state_file:
            here = os.path.dirname(os.path.abspath(__file__))
            state_file = os.path.join(role_workspace(os.path.dirname(here)), "session_state.json")
        self.state_file = state_file
        self.session_id = session_id
        self.lock_path = f"{state_file}.lock"
        self.lock_ttl_sec = lock_ttl_sec
        self.lock_timeout_sec = lock_timeout_sec

        # 内存初始状态
        self.current_state: Dict[str, Any] = {
            "session_id": self.session_id,
            "version": "2.1.0",
            "last_active_metric": self.DEFAULT_SLOTS["metric"],
            "last_active_dimension": self.DEFAULT_SLOTS["dimension"],
            "last_active_time_window": self.DEFAULT_SLOTS["time_window"],
            "slots": copy.deepcopy(self.DEFAULT_SLOTS),
            "slot_confidences": {"metric": 0.95, "dimension": 0.95, "time_window": 0.90},
            "turn_count": 0,
            "active_turn": 0,
            "current_snapshot_id": None,
            "history": [],
            "snapshots": {},
            "schemes": {},
            "redo_stack": [],
            "branch_tree": {"root": "genesis", "current": "genesis", "nodes": {}},
        }
        self.load()

    def load(self) -> None:
        """从持久化文件加载会话状态。若旧版本结构存在，平滑兼容迁移。"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # 兼容老数据结构并升级
                        self.current_state.update(data)
                        if "slots" not in self.current_state:
                            self.current_state["slots"] = {
                                "metric": self.current_state.get("last_active_metric", "amount"),
                                "dimension": self.current_state.get("last_active_dimension", "channel"),
                                "time_window": self.current_state.get("last_active_time_window", "2024-01"),
                                "filters": {},
                                "extra_slots": {},
                            }
                        if "branch_tree" not in self.current_state:
                            self.current_state["branch_tree"] = {
                                "root": "genesis",
                                "current": self.current_state.get("current_snapshot_id", "genesis"),
                                "nodes": {},
                            }
                        for key, default in (("slot_confidences", {}), ("schemes", {}),
                                             ("redo_stack", []), ("active_turn", 0)):
                            self.current_state.setdefault(key, default)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # 跨进程文件锁（TTL 防死锁）
    # ------------------------------------------------------------------ #
    @contextlib.contextmanager
    def _file_lock(self):
        """带 TTL 的独占文件锁，崩溃遗留锁可被安全接管。"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        deadline = time.time() + self.lock_timeout_sec
        acquired = False
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, json.dumps({"pid": os.getpid(), "ts": time.time()}).encode("utf-8"))
                os.close(fd)
                acquired = True
                break
            except FileExistsError:
                try:
                    with open(self.lock_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    if time.time() - float(meta.get("ts", 0)) > self.lock_ttl_sec:
                        os.remove(self.lock_path)  # 过期锁接管
                        continue
                except Exception:
                    try:
                        os.remove(self.lock_path)
                        continue
                    except Exception:
                        pass
                if time.time() >= deadline:
                    break
                time.sleep(0.02)
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    os.remove(self.lock_path)
                except FileNotFoundError:
                    pass

    def save(self) -> None:
        """在 TTL 文件锁保护下原子持久化会话状态至 JSON 文件。"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with self._file_lock():
            tmp_file = f"{self.state_file}.tmp_{os.getpid()}"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.current_state, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self.state_file)

    def record_turn(
        self,
        query: str,
        context: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> str:
        """记录一轮对话/分析交互，更新槽位与核心上下文，并建立快照版本节点。

        返回生成的 snapshot_id。
        """
        self.current_state["turn_count"] += 1
        turn_no = self.current_state["turn_count"]
        parent_snap = self.current_state.get("current_snapshot_id")

        # 槽位同步更新
        slots = self.current_state.setdefault("slots", copy.deepcopy(self.DEFAULT_SLOTS))
        if "metric" in context and context["metric"]:
            self.current_state["last_active_metric"] = str(context["metric"])
            slots["metric"] = str(context["metric"])
        if "dimension" in context and context["dimension"]:
            self.current_state["last_active_dimension"] = str(context["dimension"])
            slots["dimension"] = str(context["dimension"])
        if "time_window" in context and context["time_window"]:
            self.current_state["last_active_time_window"] = str(context["time_window"])
            slots["time_window"] = str(context["time_window"])
        if "filters" in context and isinstance(context["filters"], dict):
            slots.setdefault("filters", {}).update(context["filters"])
        confidence_meta = context.get("_confidence", {}) or {}
        for slot_name in ("metric", "dimension", "time_window"):
            if context.get(slot_name):
                default_conf = 0.90 if slot_name == "time_window" else 0.95
                self.current_state.setdefault("slot_confidences", {})[slot_name] = float(
                    confidence_meta.get(slot_name, default_conf))
        for k, v in context.items():
            if k not in ("metric", "dimension", "time_window", "filters", "_confidence"):
                slots.setdefault("extra_slots", {})[k] = v

        snapshot_id = f"snap_v{turn_no}"
        timestamp = time.time()

        snapshot_record = {
            "snapshot_id": snapshot_id,
            "parent_id": parent_snap,
            "turn": turn_no,
            "query": query,
            "timestamp": timestamp,
            "metric": self.current_state["last_active_metric"],
            "dimension": self.current_state["last_active_dimension"],
            "time_window": self.current_state["last_active_time_window"],
            "slots": copy.deepcopy(slots),
            "tags": tags or [],
        }

        # 挂载到快照库和历史记录
        self.current_state.setdefault("snapshots", {})[snapshot_id] = snapshot_record
        self.current_state["current_snapshot_id"] = snapshot_id
        self.current_state["active_turn"] = turn_no
        self.current_state["redo_stack"] = []

        # 维护分支树结构
        bt = self.current_state.setdefault("branch_tree", {"root": "genesis", "current": "genesis", "nodes": {}})
        bt["nodes"][snapshot_id] = {
            "parent": parent_snap or "genesis",
            "children": [],
            "timestamp": timestamp,
            "summary": query[:60],
        }
        if parent_snap and parent_snap in bt["nodes"]:
            bt["nodes"][parent_snap].setdefault("children", []).append(snapshot_id)
        bt["current"] = snapshot_id

        self.current_state["history"].append({
            "turn": turn_no,
            "snapshot_id": snapshot_id,
            "query": query,
            "timestamp": timestamp,
            "context": copy.deepcopy(context),
            "slots": copy.deepcopy(slots),
        })

        self.save()
        return snapshot_id

    def resolve_pronouns(self, query: str) -> Dict[str, Any]:
        """对模糊代词、相对时间与局部微调进行多跳上下文指代消歧。
        
        支持代词识别：
        - “刚才的/之前的/上次的/同样/延续/照旧”
        - “把刚才的指标换成转化率” -> 继承 dimension/time_window，仅更新 metric
        - “换成按城市看刚才的金额” -> 继承 metric/time_window，仅更新 dimension
        - “上个月/去年同期/上周” -> 自动标注时间窗口微调
        """
        slots = self.current_state.get("slots", self.DEFAULT_SLOTS)
        curr_metric = slots.get("metric", self.current_state.get("last_active_metric", "amount"))
        curr_dim = slots.get("dimension", self.current_state.get("last_active_dimension", "channel"))
        curr_tw = slots.get("time_window", self.current_state.get("last_active_time_window", "2024-01"))
        curr_filters = copy.deepcopy(slots.get("filters", {}))

        ambiguous_keywords = [
            "刚才", "之前", "同样", "换个维度", "按这个", "延续", "照旧",
            "上次", "上述", "同上", "该指标", "该维度", "前一个", "刚才那套"
        ]
        had_ambiguity = any(kw in query for kw in ambiguous_keywords)

        resolved_metric = curr_metric
        resolved_dimension = curr_dim
        resolved_time_window = curr_tw
        disambiguation_details: Dict[str, Any] = {
            "inherited_slots": [],
            "overridden_slots": [],
            "referenced_turn": self.current_state.get("turn_count", 0),
        }

        # 1. 尝试从 query 中提取显式重载槽位
        # 检测显式指标（英文与中文映射为标准 key）
        metric_alias_map = {
            "gmv": "gmv", "成交额": "gmv", "销售额": "gmv",
            "revenue": "revenue", "收入": "revenue",
            "amount": "amount", "金额": "amount",
            "order_count": "order_count", "订单量": "order_count", "订单数": "order_count",
            "profit": "profit", "利润": "profit",
            "cvr": "cvr", "转化率": "cvr",
            "ctr": "ctr", "点击率": "ctr",
            "cost": "cost", "成本": "cost",
            "cac": "cac", "获客成本": "cac",
            "ltv": "ltv", "用户终身价值": "ltv",
            "mrr": "mrr", "arr": "arr",
            "客单价": "arpu", "退款率": "refund_rate",
        }
        for kw, std_metric in metric_alias_map.items():
            if kw in query.lower():
                resolved_metric = std_metric
                disambiguation_details["overridden_slots"].append("metric")
                break

        # 检测显式维度（英文与中文映射为标准 key）
        dim_alias_map = {
            "channel": "channel", "渠道": "channel",
            "category": "category", "品类": "category",
            "region": "region", "地区": "region",
            "province": "province", "省份": "province",
            "city": "city", "城市": "city",
            "platform": "platform", "平台": "platform",
            "user_group": "user_group", "用户群": "user_group", "人群": "user_group",
        }
        for kw, std_dim in dim_alias_map.items():
            if kw in query.lower():
                resolved_dimension = std_dim
                disambiguation_details["overridden_slots"].append("dimension")
                break

        # 检测显式相对时间窗口
        if any(w in query for w in ["上个月", "上月", "last_month"]):
            resolved_time_window = "2024-last-month"
            disambiguation_details["overridden_slots"].append("time_window")
        elif any(w in query for w in ["上周", "last_week"]):
            resolved_time_window = "2024-last-week"
            disambiguation_details["overridden_slots"].append("time_window")
        elif any(w in query for w in ["去年同期", "同比", "yoy"]):
            resolved_time_window = "2023-same-period"
            disambiguation_details["overridden_slots"].append("time_window")

        # 整理继承项
        for slot_name, current_val in [("metric", resolved_metric), ("dimension", resolved_dimension), ("time_window", resolved_time_window)]:
            if slot_name not in disambiguation_details["overridden_slots"]:
                disambiguation_details["inherited_slots"].append(slot_name)

        # 方案指代：第 N 套方案 / 第 N 个方案
        resolved_scheme: Optional[Dict[str, Any]] = None
        numeral_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
        scheme_match = re.search(r"第\s*([一二三四五1-5])\s*(?:套|个)\s*方案?", query)
        if scheme_match:
            token = scheme_match.group(1)
            index = int(token) if token.isdigit() else numeral_map.get(token, 0)
            scheme = self.current_state.get("schemes", {}).get(f"scheme_{index}")
            if scheme:
                resolved_scheme = copy.deepcopy(scheme["payload"])
                disambiguation_details.setdefault("scheme_reference", f"scheme_{index}")

        return {
            "query": query,
            "resolved_metric": resolved_metric,
            "resolved_dimension": resolved_dimension,
            "resolved_time_window": resolved_time_window,
            "resolved_filters": curr_filters,
            "resolved_scheme": resolved_scheme,
            "slot_confidences": copy.deepcopy(self.current_state.get("slot_confidences", {})),
            "had_ambiguity": had_ambiguity,
            "disambiguation_details": disambiguation_details,
        }

    def update_slot(self, name: str, value: Any, confidence: float = 0.9) -> Dict[str, Any]:
        """细粒度更新单个槽位，并记录置信度，保证槽位与顶层快照字段同步。"""
        slots = self.current_state.setdefault("slots", copy.deepcopy(self.DEFAULT_SLOTS))
        if name == "metric":
            self.current_state["last_active_metric"] = str(value)
            slots["metric"] = str(value)
        elif name == "dimension":
            self.current_state["last_active_dimension"] = str(value)
            slots["dimension"] = str(value)
        elif name == "time_window":
            self.current_state["last_active_time_window"] = str(value)
            slots["time_window"] = str(value)
        elif name == "filters" and isinstance(value, dict):
            slots.setdefault("filters", {}).update(value)
        else:
            slots.setdefault("extra_slots", {})[name] = value
        self.current_state.setdefault("slot_confidences", {})[name] = round(float(confidence), 3)
        self.save()
        return self.get_slot_summary()

    def set_scheme(self, index: int, payload: Dict[str, Any]) -> str:
        """登记第 N 套分析方案，供后续 "按第二套方案" 直接指代复用。"""
        key = f"scheme_{int(index)}"
        self.current_state.setdefault("schemes", {})[key] = {
            "index": int(index),
            "payload": copy.deepcopy(payload),
            "created_at": time.time(),
        }
        self.save()
        return key

    def redo(self, steps: int = 1) -> bool:
        """撤销后重做：从 redo 栈按后进先出恢复快照。"""
        stack = self.current_state.get("redo_stack", [])
        if not stack:
            return False
        target = None
        for _ in range(max(1, steps)):
            if not stack:
                break
            target = stack.pop()
        self.current_state["redo_stack"] = stack
        if not target:
            return False
        return self._restore(target, push_redo=False)

    def compact(self, ttl_days: float = 7.0, keep_last: int = 50) -> Dict[str, Any]:
        """按 TTL 与保留条数裁剪过期快照，防止长期会话文件膨胀。"""
        snapshots = self.current_state.get("snapshots", {})
        now = time.time()
        ttl_sec = ttl_days * 86400
        removable = []
        ordered = sorted(snapshots.values(), key=lambda s: s.get("timestamp", 0), reverse=True)
        keep_ids = {s["snapshot_id"] for s in ordered[:keep_last]}
        for sid, snap in snapshots.items():
            if sid not in keep_ids and now - float(snap.get("timestamp", now)) > ttl_sec:
                removable.append(sid)
        for sid in removable:
            snapshots.pop(sid, None)
        self.save()
        return {"pruned": len(removable), "remaining": len(snapshots)}

    def rollback_to(self, snapshot_id: str) -> bool:
        """回滚到指定历史快照，并恢复全部槽位状态。"""
        return self._restore(snapshot_id, push_redo=True)

    def _restore(self, snapshot_id: str, push_redo: bool) -> bool:
        snapshots = self.current_state.get("snapshots", {})
        if snapshot_id not in snapshots:
            return False

        current = self.current_state.get("current_snapshot_id")
        if push_redo and current and current != snapshot_id:
            self.current_state.setdefault("redo_stack", []).append(current)

        snap = snapshots[snapshot_id]
        self.current_state["last_active_metric"] = snap["metric"]
        self.current_state["last_active_dimension"] = snap["dimension"]
        self.current_state["last_active_time_window"] = snap["time_window"]
        self.current_state["active_turn"] = snap.get("turn", self.current_state.get("active_turn", 0))

        # 深度恢复槽位
        if "slots" in snap:
            self.current_state["slots"] = copy.deepcopy(snap["slots"])
        else:
            self.current_state["slots"] = {
                "metric": snap["metric"],
                "dimension": snap["dimension"],
                "time_window": snap["time_window"],
                "filters": {},
                "extra_slots": {},
            }

        self.current_state["current_snapshot_id"] = snapshot_id
        bt = self.current_state.setdefault("branch_tree", {})
        bt["current"] = snapshot_id
        self.save()
        return True

    def rollback_turns(self, steps: int = 1) -> bool:
        """沿着当前快照父节点链 (Snapshot Branch Tree) 向上回溯指定步数（撤销操作）。"""
        if steps <= 0:
            return False

        current_snap = self.current_state.get("current_snapshot_id")
        snapshots = self.current_state.get("snapshots", {})
        if not current_snap or current_snap not in snapshots:
            return False

        target_snap = current_snap
        for _ in range(steps):
            parent = snapshots.get(target_snap, {}).get("parent_id")
            if not parent or parent not in snapshots:
                break
            target_snap = parent

        if target_snap == current_snap:
            return False

        return self.rollback_to(target_snap)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """获取所有已持久化的快照简报列表。"""
        snapshots = self.current_state.get("snapshots", {})
        res = []
        for sid, s in snapshots.items():
            turn_val = s.get("turn")
            if turn_val is None:
                # 尝试从 sid 如 snap_v1 中解析
                m = re.search(r"\d+", str(sid))
                turn_val = int(m.group(0)) if m else 0
            res.append({
                "snapshot_id": sid,
                "turn": turn_val,
                "query": s.get("query"),
                "metric": s.get("metric"),
                "dimension": s.get("dimension"),
                "time_window": s.get("time_window"),
                "timestamp": s.get("timestamp"),
            })
        res.sort(key=lambda x: x.get("turn") or 0)
        return res

    def get_slot_summary(self) -> Dict[str, Any]:
        """获取当前工作区活跃槽位状态概览。"""
        return {
            "session_id": self.session_id,
            "turn_count": self.current_state.get("turn_count", 0),
            "active_turn": self.current_state.get("active_turn", 0),
            "current_snapshot_id": self.current_state.get("current_snapshot_id"),
            "slots": copy.deepcopy(self.current_state.get("slots", self.DEFAULT_SLOTS)),
            "slot_confidences": copy.deepcopy(self.current_state.get("slot_confidences", {})),
            "schemes": sorted(self.current_state.get("schemes", {}).keys()),
            "redo_available": len(self.current_state.get("redo_stack", [])),
            "snapshots_count": len(self.current_state.get("snapshots", {})),
        }

