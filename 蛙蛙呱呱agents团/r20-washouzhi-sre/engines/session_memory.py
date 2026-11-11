# -*- coding: utf-8 -*-
"""L09 会话记忆层 —— 持久化记忆池 + 代词消歧 + 快照回滚。

SOP v13.0 L09 体检病灶（R20 真实断点）：
    第二轮对话彻底失忆：「按刚才第二套方案调整」「把上次那个服务的阈值调高 0.05」
    「切换到防御加固版」都无法解析；记忆只存在进程内临时变量，退出即丢；
    没有历史版本快照，改错无法回滚。

对标开源标杆（Stars > 1k）：
    * MemGPT / Letta (>15k) —— 分层记忆与持久化状态
    * langchain-ai/langgraph (>10k) —— checkpoint 状态存储与回放

落地的最低 3 项架构升级：
    1. 持久化 session_state.json 记忆池，slots 与顶层实体双向同步（SOP §5.14）；
    2. 自然语言代词消歧（第二套方案 / 上次那个服务 / 阈值调高 0.05）；
    3. 历史版本快照树 + 一键回滚 rollback。

用法：
    python agent.py evolve memory --query "按刚才第二套方案调整，阈值调高0.05" --out ...
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
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SCENARIOS = ["SCN_A_RUSH", "SCN_B_STEADY", "SCN_C_HARDEN"]
_SCENARIO_ALIAS = {"第一套": _SCENARIOS[0], "第二套": _SCENARIOS[1],
                   "第三套": _SCENARIOS[2], "极速抢修": _SCENARIOS[0],
                   "稳健": _SCENARIOS[1], "防御加固": _SCENARIOS[2],
                   "方案1": _SCENARIOS[0], "方案2": _SCENARIOS[1],
                   "方案3": _SCENARIOS[2]}


class R20SessionMemory:
    """R20 持久化会话记忆池。"""

    ENGINE = "R20SessionMemory"
    LAYER = "L09"
    CAPABILITIES = [
        "持久化 session_state.json 记忆池 + slots/entities 双向同步 (SOP §5.14)",
        "自然语言代词消歧 (第二套方案 / 上次那个服务 / 阈值调高 0.05)",
        "历史版本快照树 + 一键回滚 rollback",
    ]

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or os.path.join(role_workspace(_ROLE))
        self.path = os.path.join(self.workspace_dir, "session_state.json")
        self.state = self._load()

    # ------------------------------------------------------------------ #
    # 持久化
    # ------------------------------------------------------------------ #
    def _default_state(self) -> Dict[str, Any]:
        return {
            "version": 0,
            "slots": {},
            "entities": {"service": None, "scenario": None,
                         "alert_threshold": None, "last_intent": None},
            "snapshots": [],
            "updated_at": None,
        }

    def _load(self) -> Dict[str, Any]:
        if os.path.isfile(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "slots" in data:
                    return data
            except (OSError, ValueError):
                pass
        return self._default_state()

    def save(self) -> None:
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.state["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ #
    # 槽位双向同步
    # ------------------------------------------------------------------ #
    def update_slot(self, key: str, value: Any) -> Dict[str, Any]:
        self.state.setdefault("slots", {})[key] = value
        # 顶层实体同步，防止代词消歧读到旧值（SOP §5.14）
        self.state.setdefault("entities", {})[key] = value
        return {"ok": True, "key": key, "value": value,
                "slots": self.state["slots"], "entities": self.state["entities"]}

    def snapshot(self, label: str = "") -> Dict[str, Any]:
        snaps = self.state.setdefault("snapshots", [])
        version = len(snaps) + 1
        snaps.append({"version": version, "label": label or f"v{version}",
                      "slots": copy.deepcopy(self.state.get("slots", {})),
                      "entities": copy.deepcopy(self.state.get("entities", {})),
                      "created_at": datetime.datetime.now().isoformat(timespec="seconds")})
        self.state["version"] = version
        return {"ok": True, "version": version, "label": label or f"v{version}",
                "snapshot_count": len(snaps)}

    def rollback(self, version: int) -> Dict[str, Any]:
        snaps = self.state.get("snapshots", [])
        target = next((s for s in snaps if s["version"] == int(version)), None)
        if not target:
            return {"ok": False, "error": f"快照 v{version} 不存在",
                    "available": [s["version"] for s in snaps]}
        self.state["slots"] = copy.deepcopy(target["slots"])
        self.state["entities"] = copy.deepcopy(target["entities"])
        self.state["version"] = target["version"]
        return {"ok": True, "rolled_back_to": target["version"],
                "label": target["label"], "slots": self.state["slots"]}

    # ------------------------------------------------------------------ #
    # 代词消歧
    # ------------------------------------------------------------------ #
    def disambiguate_query(self, query: str) -> Dict[str, Any]:
        q = query or ""
        resolved: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []

        for alias, sid in _SCENARIO_ALIAS.items():
            if alias in q:
                resolved.append({"ref": alias, "type": "scenario", "value": sid,
                                 "source": "slot" if self.state.get("slots", {}).get("scenario") else "alias"})
                actions.append({"action": "select_scenario", "scenario": sid})
                self.update_slot("scenario", sid)
                break

        if re.search(r"(上次|刚才|之前)那个?(服务|系统|应用)", q):
            svc = self.state.get("slots", {}).get("service") or self.state.get("entities", {}).get("service")
            resolved.append({"ref": "上次那个服务", "type": "service",
                             "value": svc, "source": "memory"})
            if svc:
                actions.append({"action": "use_service", "service": svc})

        m = re.search(r"阈值\s*(调高|提高|上调|增加|调低|降低|下调)\s*(\d+(?:\.\d+)?)", q)
        if m:
            delta = float(m.group(2))
            if m.group(1) in ("调低", "降低", "下调"):
                delta = -delta
            cur = self.state.get("slots", {}).get("alert_threshold")
            cur = float(cur) if isinstance(cur, (int, float)) else 0.9
            new = round(cur + delta, 4)
            resolved.append({"ref": "阈值", "type": "alert_threshold", "value": new,
                             "delta": delta, "source": "memory"})
            actions.append({"action": "set_alert_threshold", "value": new})
            self.update_slot("alert_threshold", new)

        self.update_slot("last_intent", q)
        return {
            "ok": bool(resolved),
            "engine": self.ENGINE, "layer": self.LAYER,
            "query": q, "resolved": resolved, "actions": actions,
            "slots": self.state.get("slots", {}),
            "entities": self.state.get("entities", {}),
            "memory_path": self.path,
            "capabilities": list(self.CAPABILITIES),
        }

    # ------------------------------------------------------------------ #
    # 演示
    # ------------------------------------------------------------------ #
    def demo(self, query: str = "") -> Dict[str, Any]:
        self.state = self._default_state()
        self.update_slot("service", "支付服务")
        self.update_slot("alert_threshold", 0.95)
        self.update_slot("scenario", _SCENARIOS[1])
        v1 = self.snapshot("初始状态")
        self.update_slot("alert_threshold", 0.90)
        v2 = self.snapshot("阈值下调后")
        rolled = self.rollback(v1["version"])
        resolved = self.disambiguate_query(
            query or "按刚才第二套方案调整，把上次那个服务的阈值调高0.05")
        self.save()
        return {
            "ok": bool(resolved["ok"] and rolled["ok"]),
            "engine": self.ENGINE, "layer": self.LAYER,
            "snapshots": [v1, v2], "rollback": rolled,
            "disambiguation": resolved,
            "state_version": self.state.get("version"),
            "memory_path": self.path,
            "capabilities": list(self.CAPABILITIES),
        }


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R20 L09 会话记忆")
    ap.add_argument("--query", default="")
    ap.add_argument("--workspace", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    mem = R20SessionMemory(args.workspace)
    out = mem.demo(args.query)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "resolved": len(out["disambiguation"]["resolved"]),
                      "version": out["state_version"]}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
