# -*- coding: utf-8 -*-
"""L09 会话记忆层 —— 持久化记忆池 + 代词消歧 + 快照回滚。

病灶（体检结论）：升级前 R18 每轮对话从零开始，人类必须反复重述
「按刚才第二套方案调整」「把上次的 SLA 改成 2 小时」；没有任何槽位持久化，
也没有版本快照可回滚，跨轮协作等于失忆。

对标标杆（Stars > 1k）：
- `MemGPT / Letta`（> 15k）：分层记忆池（core / recall / archival）；
- `langchain-ai/langgraph`（> 10k）：checkpoint 状态树与时间旅行回滚；
- 槽位双向同步（SOP §5.14）：slots 与顶层活跃实体必须同时落盘，防状态漂移。

本引擎落地：
1. `workspace/session_state.json` 持久化槽位 / 历史轮次 / 方案矩阵；
2. 代词消歧：第 N 套方案、上一版、SLA 改成 X 小时、该管道；
3. 版本快照树 + 一键 rollback（版本号严格递增，可审计）。
"""
from __future__ import annotations

import json
import os
from core.workspace import role_workspace  # noqa: E402

import re
import time
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0.0"
_ORDINALS = {"一": 0, "1": 0, "二": 1, "2": 1, "三": 2, "3": 2,
             "四": 3, "4": 3}
_SLA_RE = re.compile(r"SLA\s*(?:改成|改为|调整为|设为|调到)\s*(\d+(?:\.\d+)?)\s*(?:小时|h|H)")
_SCENARIO_RE = re.compile(r"第\s*([一二三四1-4])\s*套")
_PREV_RE = re.compile(r"上一版|上一套|刚才那版|上次的方案|回滚到上一版")


class DataEngSessionMemory:
    """L09 会话记忆池。"""

    def __init__(self, workspace_dir: Optional[str] = None,
                 session_id: str = "r18-default"):
        here = os.path.dirname(os.path.abspath(__file__))
        self.workspace_dir = workspace_dir or os.path.join(role_workspace(os.path.dirname(here)))
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.path = os.path.join(self.workspace_dir, "session_state.json")
        self.session_id = session_id
        self.state = self._load_or_init(session_id)

    # ------------------------------------------------------------------ #
    # 持久化
    # ------------------------------------------------------------------ #
    def _blank(self, session_id: str) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "session_id": session_id,
            "version": 0,
            "slots": {},
            "active": {},
            "history": [],
            "snapshots": {},
            "matrix": {},
            "updated_at": "",
        }

    def _load_or_init(self, session_id: str) -> Dict[str, Any]:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("session_id") == session_id:
                    return data
            except (OSError, ValueError):
                pass
        return self._blank(session_id)

    def save(self) -> None:
        self.state["version"] = int(self.state.get("version", 0)) + 1
        self.state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------ #
    # 槽位（双向同步，SOP §5.14）
    # ------------------------------------------------------------------ #
    def update_slot(self, key: str, value: Any) -> Dict[str, Any]:
        self.state.setdefault("slots", {})[key] = value
        # 顶层活跃实体双写，防代词消歧读到旧值
        self.state.setdefault("active", {})[key] = value
        self.state[f"active_{key}"] = value
        self.save()
        return {"ok": True, "key": key, "value": value,
                "slots": self.state["slots"].get(key),
                "active": self.state["active"].get(key),
                "mirror": self.state.get(f"active_{key}"),
                "version": self.state["version"]}

    def get_slot(self, key: str, default: Any = None) -> Any:
        return self.state.get("slots", {}).get(key, default)

    # ------------------------------------------------------------------ #
    # 历史
    # ------------------------------------------------------------------ #
    def remember_turn(self, user: str, assistant: str = "",
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        turn = {
            "turn": len(self.state.get("history", [])) + 1,
            "user": str(user),
            "assistant": str(assistant),
            "context": dict(context or {}),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }
        self.state.setdefault("history", []).append(turn)
        self.save()
        return turn

    def set_matrix(self, matrix: Dict[str, Any]) -> Dict[str, Any]:
        self.state["matrix"] = {
            "recommended_id": matrix.get("recommended_id"),
            "scenarios": [{"id": s.get("id"), "name": s.get("name"),
                           "rank": s.get("rank"), "score": s.get("total_score")}
                          for s in matrix.get("scenarios", [])],
        }
        self.save()
        return self.state["matrix"]

    # ------------------------------------------------------------------ #
    # 代词消歧
    # ------------------------------------------------------------------ #
    def resolve_scenario(self, text: str) -> Optional[Dict[str, Any]]:
        m = _SCENARIO_RE.search(str(text or ""))
        if not m:
            return None
        idx = _ORDINALS.get(m.group(1))
        scenarios = list(self.state.get("matrix", {}).get("scenarios") or [])
        if idx is None or idx >= len(scenarios):
            return None
        scn = scenarios[idx]
        return {"index": idx + 1, "id": scn.get("id"), "name": scn.get("name"),
                "score": scn.get("score")}

    def disambiguate(self, text: str) -> Dict[str, Any]:
        """代词消歧：一句话里可能同时含「第 N 套方案」与「SLA 改成 X」，全部落地。"""
        raw = str(text or "")
        applied: List[Dict[str, Any]] = []

        scenario = self.resolve_scenario(raw)
        if scenario:
            self.update_slot("current_scenario_id", scenario["id"])
            self.update_slot("current_scenario_name", scenario["name"])
            applied.append({"kind": "scenario", "slot": "current_scenario_id",
                            "value": scenario})

        m = _SLA_RE.search(raw)
        if m:
            hours = float(m.group(1))
            sync = self.update_slot("sla_hours", hours)
            applied.append({"kind": "sla", "slot": "sla_hours",
                            "value": hours, "sync": sync})

        if _PREV_RE.search(raw):
            snaps = list((self.state.get("snapshots") or {}).keys())
            if snaps:
                applied.append({"kind": "snapshot", "slot": "snapshot",
                                "value": snaps[-1]})

        if not scenario and re.search(r"该管道|这个管道|它", raw):
            slots = self.state.get("slots") or {}
            if slots.get("current_pipeline") or slots.get("current_scenario_name"):
                applied.append({"kind": "pipeline", "slot": "current_pipeline",
                                "value": slots.get("current_pipeline")
                                or slots.get("current_scenario_name")})

        if applied:
            return {"resolved": True, "kind": applied[0]["kind"],
                    "slot": applied[0]["slot"], "value": applied[0]["value"],
                    "applied": applied, "text": raw,
                    "slots": dict(self.state.get("slots", {}))}
        return {"resolved": False, "kind": "unknown", "text": raw,
                "reason": "无可用槽位/矩阵上下文，须人类补全指代"}

    # ------------------------------------------------------------------ #
    # 快照 / 回滚
    # ------------------------------------------------------------------ #
    def snapshot(self, label: str) -> Dict[str, Any]:
        self.state.setdefault("snapshots", {})[label] = {
            "version": self.state.get("version", 0),
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "slots": json.loads(json.dumps(self.state.get("slots", {}))),
            "active": json.loads(json.dumps(self.state.get("active", {}))),
        }
        self.save()
        return {"ok": True, "label": label, "version": self.state["version"]}

    def rollback(self, label: str) -> Dict[str, Any]:
        snap = (self.state.get("snapshots") or {}).get(label)
        if not snap:
            raise KeyError(f"快照不存在：{label}")
        before_slots = dict(self.state.get("slots", {}))
        self.state["slots"] = json.loads(json.dumps(snap["slots"]))
        self.state["active"] = json.loads(json.dumps(snap["active"]))
        for key in list(self.state.keys()):
            if key.startswith("active_"):
                self.state.pop(key)
        for key, value in self.state["active"].items():
            self.state[f"active_{key}"] = value
        self.save()
        return {"ok": True, "label": label, "restored_version": snap["version"],
                "slots": self.state["slots"],
                "changed": sorted(k for k in set(before_slots) | set(self.state["slots"])
                                  if before_slots.get(k) != self.state["slots"].get(k))}

    def history_digest(self) -> Dict[str, Any]:
        return {"session_id": self.state.get("session_id"),
                "version": self.state.get("version"),
                "turns": len(self.state.get("history", [])),
                "slots": self.state.get("slots", {}),
                "snapshots": list((self.state.get("snapshots") or {}).keys())}


# --------------------------------------------------------------------------- #
# CLI：python -m engines.session_memory --demo --out ...
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L09 会话记忆层")
    ap.add_argument("--demo", action="store_true", help="跑一遍消歧 + 快照回滚演示")
    ap.add_argument("--out", default="", help="演示结果 JSON")
    args = ap.parse_args(argv)

    from engines import DataEngScenarioMatrix
    mem = DataEngSessionMemory(session_id="r18-demo")
    matrix = DataEngScenarioMatrix().generate({})
    mem.set_matrix(matrix)
    mem.remember_turn("把 orders 最近30天增量做成看板，2小时内要新鲜",
                      "已裂变 3 套方案，推荐 " + matrix["recommended_name"])
    mem.update_slot("current_pipeline", "orders_daily_dashboard")

    dis = mem.disambiguate("按刚才第二套方案调整，SLA 改成 2 小时")
    mem.snapshot("before-sla-change")
    mem.update_slot("sla_hours", 4.0)
    rollback = mem.rollback("before-sla-change")

    out = {
        "ok": True,
        "session_file": mem.path,
        "disambiguation": dis,
        "rollback": rollback,
        "digest": mem.history_digest(),
        "scenario_resolved": mem.resolve_scenario("第三套方案"),
    }
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print("__AGENT_RESULT__ " + json.dumps(
        {"ok": out["ok"], "resolved": dis["resolved"], "kind": dis["kind"],
         "sla": mem.get_slot("sla_hours"), "rollback_changed": rollback["changed"],
         "session_file": mem.path}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
