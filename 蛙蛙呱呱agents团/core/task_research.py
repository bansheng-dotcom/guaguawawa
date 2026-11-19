# -*- coding: utf-8 -*-
"""core.task_research —— 来源账本与饱和判定（50 引用源 + 连续 15 源无新增）。

不负责联网抓取；由调用方（CLI/研究器）把来源与“新增维度”喂进来。
"""
from __future__ import annotations

from typing import Any, Dict, List

GRADES = {"A", "B", "C", "D", "E", "F"}


class SourceLedger:
    def __init__(self, no_new_streak: int = 15) -> None:
        self.sources: List[Dict[str, Any]] = []
        self.no_new_streak = int(no_new_streak)
        self._streak = 0
        self._max_streak = 0
        self._dimensions: set[str] = set()

    def add(self, source: Dict[str, Any]) -> None:
        sid = str(source.get("id") or "").strip()
        if not sid:
            raise ValueError("source 缺 id")
        if any(s.get("id") == sid for s in self.sources):
            raise ValueError(f"source id 重复: {sid}")
        if source.get("grade") not in GRADES:
            raise ValueError(f"source {sid} grade 非法")
        self.sources.append(dict(source))
        new_dims = [str(x) for x in (source.get("new_dimensions") or []) if str(x).strip()]
        added = [d for d in new_dims if d not in self._dimensions]
        if added:
            self._dimensions.update(added)
            self._streak = 0
        else:
            self._streak += 1
            self._max_streak = max(self._max_streak, self._streak)

    @property
    def cited(self) -> int:
        return len(self.sources)

    @property
    def reached(self) -> bool:
        return self.cited >= 50 and self._streak >= self.no_new_streak

    def status(self) -> Dict[str, Any]:
        return {
            "cited": self.cited,
            "no_new_streak": self._streak,
            "max_no_new_streak": self._max_streak,
            "dimensions": sorted(self._dimensions),
            "reached": self.reached,
            "needed": max(0, 50 - self.cited),
        }


def check(ledger: SourceLedger) -> Dict[str, Any]:
    st = ledger.status()
    bad = []
    if st["cited"] < 50:
        bad.append(f"引用源不足 50：{st['cited']}")
    if st["no_new_streak"] < ledger.no_new_streak:
        bad.append(f"连续无新增仅 {st['no_new_streak']}，需 {ledger.no_new_streak}")
    return {"ok": not bad, "bad": bad, **st}
