# -*- coding: utf-8 -*-
"""L09 会话记忆层 —— 持久化记忆池 + 代词消歧 + 快照回滚。

SOP v13.0 L09 体检病灶（R19 真实断点）：
    1. 第二轮对话彻底失忆：「按刚才第二套方案调整」「把上次那个模型的阈值调高 0.05」
       「换成上次的评估集」全部无法解析，人类只能把上下文重述一遍；
    2. 没有持久化记忆池，进程一退出状态全丢；
    3. 没有历史快照树与回滚能力，改错了无法退回。

对标开源标杆（Stars > 1k）：
    * MemGPT / letta (>15k)       —— 分层记忆与状态持久化
    * langchain-ai/langgraph (>10k) —— State Store 与检查点回放

落地的最低 3 项架构升级：
    1. `workspace/session_state.json` 持久化记忆池（slots + entities 双向同步，
       修掉 SOP §5.14「只写 slots 不写顶层实体」造成的代词消歧读到旧值）；
    2. 自然语言代词/序数/增量消歧（第二套方案 / 上次那个模型 / 阈值调高 0.05）；
    3. 历史版本快照树 + 一键回滚。

用法：
    python -m engines.session_memory --query "按刚才第二套方案调整" \
        --out workspace/rounds/L09_session.json
"""
from __future__ import annotations

import copy
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SCENARIO_ORDINAL = {"一": "SCN_A_QUICK", "1": "SCN_A_QUICK",
                     "二": "SCN_B_STEADY", "2": "SCN_B_STEADY",
                     "三": "SCN_C_STRICT", "3": "SCN_C_STRICT"}

_DEFAULT_STATE: Dict[str, Any] = {
    "schema": "r19.session_state.v1",
    "agent": "r19",
    "slots": {
        "selected_scenario": "SCN_B_STEADY",
        "current_model": "客服助手",
        "current_dataset": "客服对话评估集",
        "threshold": 0.80,
    },
    # 顶层实体镜像：与 slots 双向同步（SOP §5.14）
    "entities": {
        "selected_scenario": "SCN_B_STEADY",
        "current_model": "客服助手",
        "current_dataset": "客服对话评估集",
        "threshold": 0.80,
    },
    "snapshots": {},
    "snapshot_order": [],
    "history": [],
}


class R19SessionMemory:
    """持久化会话记忆池：槽位同步、代词消歧、快照回滚。"""

    ENGINE = "R19SessionMemory"
    LAYER = "L09"
    CAPABILITIES = [
        "持久化 session_state.json 记忆池 + slots/entities 双向同步 (SOP §5.14)",
        "自然语言代词消歧 (第二套方案 / 上次那个模型 / 阈值调高 0.05)",
        "历史版本快照树 + 一键回滚 (rollback)",
        "[C2] 快照差量 diff (新增/删除/变更槽位)",
        "[C2] 多轮指代冲突消解 (后写胜出 + provenance 溯源)",
        "[C2] 槽位 TTL 过期 + 快照 LRU 压缩",
    ]

    def __init__(self, workspace_dir: Optional[str] = None,
                 state_path: Optional[str] = None):
        ws = workspace_dir or os.path.join(_ROLE, "workspace")
        self.state_path = state_path or os.path.join(ws, "session_state.json")
        self.state = self._load()

    # ------------------------------------------------------------------ #
    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "slots" in data:
                    data.setdefault("entities", dict(data["slots"]))
                    data.setdefault("snapshots", {})
                    data.setdefault("snapshot_order", [])
                    data.setdefault("history", [])
                    return data
            except (OSError, ValueError):
                pass
        return copy.deepcopy(_DEFAULT_STATE)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.state_path)), exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ #
    def update_slot(self, slot: str, value: Any, mirror: bool = True) -> Any:
        """写槽位：slots 与顶层 entities 同步落盘（SOP §5.14 双向同步）。"""
        self.state.setdefault("slots", {})[slot] = value
        if mirror:
            self.state.setdefault("entities", {})[slot] = value
            self.state[slot] = value  # 顶层实体字段
        self.state.setdefault("history", []).append(
            {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
             "op": "update_slot", "slot": slot, "value": value})
        self._save()
        return value

    def get_slot(self, slot: str, default: Any = None) -> Any:
        # 先读 slots，再兜底 entities 与顶层镜像，防状态漂移
        for key in ("slots", "entities"):
            if isinstance(self.state.get(key), dict) and slot in self.state[key]:
                return self.state[key][slot]
        return self.state.get(slot, default)

    # ------------------------------------------------------------------ #
    def record_snapshot(self, label: str, value: Any = None) -> str:
        n = len(self.state.get("snapshot_order", [])) + 1
        snap_id = f"snap_{n:03d}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.state.setdefault("snapshots", {})[snap_id] = {
            "label": label,
            "value": copy.deepcopy(value if value is not None else self.state.get("slots", {})),
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self.state.setdefault("snapshot_order", []).append(snap_id)
        self.state.setdefault("history", []).append(
            {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
             "op": "record_snapshot", "snap_id": snap_id, "label": label})
        self._save()
        return snap_id

    def rollback(self, snap_id: str) -> Any:
        snap = (self.state.get("snapshots") or {}).get(snap_id)
        if not snap:
            raise KeyError(f"快照不存在: {snap_id}")
        val = copy.deepcopy(snap["value"])
        if isinstance(val, dict):
            for k, v in val.items():
                self.update_slot(k, v)
        self.state["restored_from"] = snap_id
        self.state["restored_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        self.state.setdefault("history", []).append(
            {"ts": self.state["restored_at"], "op": "rollback", "snap_id": snap_id})
        self._save()
        return val

    # ------------------------------------------------------------------ #
    def disambiguate_query(self, query: str) -> Dict[str, Any]:
        q = str(query or "")
        refs: List[Dict[str, Any]] = []
        ctx: Dict[str, Any] = {}

        # 1. 序数方案消歧：「第二套方案」/「第2套」
        m = re.search(r"第\s*([一二三123])\s*套", q)
        if m:
            scn = _SCENARIO_ORDINAL[m.group(1)]
            self.update_slot("selected_scenario", scn)
            ctx["selected_scenario"] = scn
            refs.append({"type": "scenario_ordinal", "token": m.group(0), "value": scn})
        elif any(w in q for w in ("刚才那套", "刚才方案", "上次方案", "原来的方案")):
            scn = self.get_slot("selected_scenario", "SCN_B_STEADY")
            ctx["selected_scenario"] = scn
            refs.append({"type": "scenario_reference", "token": "刚才/上次方案", "value": scn})

        # 2. 模型代词：「上次那个模型」「刚才的模型」
        if re.search(r"(上次|刚才|之前).{0,4}(模型|model)", q):
            model = self.get_slot("current_model", "客服助手")
            ctx["model_name"] = model
            refs.append({"type": "model_pronoun", "token": "上次那个模型", "value": model})

        # 3. 阈值增量：「阈值调高 0.05」「threshold 降到 0.7」
        tm = re.search(r"(?:阈值|threshold)\s*(?:调高|提高|上调|降低|调低|下调|加|减)\s*"
                       r"(\d+(?:\.\d+)?)", q, re.IGNORECASE)
        if tm:
            delta = float(tm.group(1))
            if any(w in q for w in ("降低", "调低", "下调", "减")):
                delta = -delta
            base = float(self.get_slot("threshold", 0.80) or 0.0)
            new_val = round(base + delta, 4)
            self.update_slot("threshold", new_val)
            ctx["threshold_delta"] = delta
            ctx["threshold"] = new_val
            ctx["threshold_base"] = base
            refs.append({"type": "threshold_delta", "token": tm.group(0),
                         "value": new_val, "delta": delta})

        # 4. 评估集/数据集切换
        dm = re.search(r"(?:换成|切换到|改用|还是用)\s*(?:上次的|之前的)?\s*"
                       r"([A-Za-z0-9_\-\u4e00-\u9fa5]{2,24}?)(?:评估集|数据集)", q)
        if dm:
            ds = dm.group(1)
            self.update_slot("current_dataset", ds)
            ctx["dataset"] = ds
            refs.append({"type": "dataset_switch", "token": dm.group(0), "value": ds})

        # 5. 回滚意图
        if any(w in q for w in ("回滚", "退回", "还原", "撤销")):
            last = (self.state.get("snapshot_order") or [None])[-1]
            ctx["rollback_target"] = last
            refs.append({"type": "rollback", "token": "回滚", "value": last})

        # 组装消歧后的完整语句（把代词替换为确定值）
        disambiguated = q
        if "selected_scenario" in ctx:
            disambiguated = f"[scenario={ctx['selected_scenario']}] " + disambiguated
        if "model_name" in ctx:
            disambiguated = disambiguated.replace("上次那个模型", ctx["model_name"]) \
                                       .replace("刚才的模型", ctx["model_name"])
        if "threshold" in ctx:
            disambiguated += f" [threshold={ctx['threshold']}]"
        if "dataset" in ctx:
            disambiguated += f" [dataset={ctx['dataset']}]"

        confidence = round(min(1.0, 0.5 + 0.2 * len(refs)), 2) if refs else 0.2
        return {
            "ok": bool(refs),
            "engine": self.ENGINE, "layer": self.LAYER,
            "query": q,
            "disambiguated": disambiguated,
            "references": refs,
            "reference_count": len(refs),
            "referenced_context": ctx,
            "confidence": confidence,
            "state_file": self.state_path,
            "capabilities": list(self.CAPABILITIES),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    # ------------------------------------------------------------------ #
    # [Cycle 2] 快照 diff / 多轮冲突消解 / TTL + LRU
    # ------------------------------------------------------------------ #
    def diff_snapshots(self, left: Any, right: Any) -> Dict[str, Any]:
        def _value(side: Any) -> Dict[str, Any]:
            if isinstance(side, dict):
                return side
            snap = (self.state.get("snapshots") or {}).get(str(side))
            if not snap:
                raise KeyError(f"快照不存在: {side}")
            val = snap.get("value")
            return val if isinstance(val, dict) else {"value": val}
        a, b = _value(left), _value(right)
        added = sorted(set(b) - set(a))
        removed = sorted(set(a) - set(b))
        changed = [{"slot": k, "old": a[k], "new": b[k]}
                   for k in sorted(set(a) & set(b)) if a[k] != b[k]]
        return {"ok": True, "added": added, "removed": removed,
                "changed": changed, "change_count": len(added) + len(removed) + len(changed)}

    def resolve_multi_turn(self, turns: List[str]) -> Dict[str, Any]:
        slot_map = {"model_name": "current_model", "dataset": "current_dataset",
                    "selected_scenario": "selected_scenario", "threshold": "threshold"}
        provenance: Dict[str, Dict[str, Any]] = {}
        conflicts: List[Dict[str, Any]] = []
        resolutions: List[Dict[str, Any]] = []
        for idx, query in enumerate(turns or []):
            res = self.disambiguate_query(query)
            ctx = res.get("referenced_context") or {}
            writes = {}
            for key, value in ctx.items():
                if key in ("threshold_delta", "threshold_base", "rollback_target"):
                    continue
                writes[slot_map.get(key, key)] = value
            for slot, value in writes.items():
                if slot in provenance and provenance[slot]["value"] != value:
                    conflicts.append({"turn": idx, "slot": slot,
                                      "old": provenance[slot]["value"], "new": value})
                provenance[slot] = {"value": value, "turn": idx, "query": query}
            resolutions.append({"turn": idx, "query": query,
                                "writes": writes, "confidence": res.get("confidence")})
        return {"ok": True, "turn_count": len(resolutions),
                "slots": {k: v["value"] for k, v in provenance.items()},
                "provenance": provenance, "conflicts": conflicts,
                "conflict_count": len(conflicts), "policy": "last_write_wins",
                "resolutions": resolutions}

    def set_ttl(self, slot: str, seconds: float) -> Dict[str, Any]:
        expire = datetime.datetime.now() + datetime.timedelta(seconds=float(seconds))
        ttl = self.state.setdefault("slot_ttl", {})
        ttl[slot] = expire.isoformat(timespec="seconds")
        self._save()
        return {"ok": True, "slot": slot, "expires_at": ttl[slot]}

    def purge_expired(self, now: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        now = now or datetime.datetime.now()
        ttl = self.state.get("slot_ttl") or {}
        expired: List[str] = []
        for slot, iso in list(ttl.items()):
            try:
                if datetime.datetime.fromisoformat(iso) <= now:
                    expired.append(slot)
            except ValueError:
                expired.append(slot)
        for slot in expired:
            ttl.pop(slot, None)
            for key in ("slots", "entities"):
                if isinstance(self.state.get(key), dict):
                    self.state[key].pop(slot, None)
            self.state.pop(slot, None)
        if expired:
            self.state.setdefault("history", []).append(
                {"ts": now.isoformat(timespec="seconds"), "op": "purge_expired",
                 "slots": expired})
            self._save()
        return {"ok": True, "expired": expired, "expired_count": len(expired)}

    def compact_snapshots(self, keep: int = 5) -> Dict[str, Any]:
        keep = max(0, int(keep))
        order = list(self.state.get("snapshot_order") or [])
        pruned = order[:-keep] if keep else order
        for snap_id in pruned:
            (self.state.get("snapshots") or {}).pop(snap_id, None)
        self.state["snapshot_order"] = order[-keep:] if keep else []
        if pruned:
            self.state.setdefault("history", []).append(
                {"ts": datetime.datetime.now().isoformat(timespec="seconds"),
                 "op": "compact_snapshots", "pruned": pruned})
            self._save()
        return {"ok": True, "pruned": pruned, "pruned_count": len(pruned),
                "remaining": len(self.state.get("snapshot_order") or []),
                "policy": "keep_recent"}

    # ------------------------------------------------------------------ #
    def demo(self) -> Dict[str, Any]:
        snap = self.record_snapshot("initial_model",
                                    {"current_model": "客服助手", "threshold": 0.80})
        resolved = self.disambiguate_query("按刚才第二套方案调整")
        resolved2 = self.disambiguate_query("把上次那个模型的阈值调高0.05")
        return {"ok": True, "snapshot": snap, "first": resolved, "second": resolved2,
                "reference_count": resolved.get("reference_count", 0)
                + resolved2.get("reference_count", 0),
                "referenced_context": {**resolved.get("referenced_context", {}),
                                       **resolved2.get("referenced_context", {})},
                "slots": self.state.get("slots"), "snapshot_count": len(
                    self.state.get("snapshot_order", []))}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L09 会话记忆与代词消歧")
    ap.add_argument("--query", default=None)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    mem = R19SessionMemory()
    if args.demo or not args.query:
        out = mem.demo()
    else:
        out = mem.disambiguate_query(args.query)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "refs": out.get("reference_count"),
                      "ctx": out.get("referenced_context"),
                      "state_file": mem.state_path, "out": args.out},
                     ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
