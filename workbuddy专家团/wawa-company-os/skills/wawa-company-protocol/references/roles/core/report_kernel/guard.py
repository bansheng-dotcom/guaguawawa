# -*- coding: utf-8 -*-
"""report_kernel · guard & cache

guard：L2 只能引用 L1 已出现的数字（可追溯），不能凭空造新数字。
cache：contract 级内容寻址缓存，键 = role+result+dataset+spec 的哈希。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

NUM = re.compile(r"-?\d+(?:\.\d+)?%?")
# 允许出现的非指标数字：年份、周次、版本号等
ALLOW = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "2025", "2026"}


def harvest_numbers(objs: Iterable[Any]) -> Set[str]:
    out: Set[str] = set()
    for o in objs:
        s = json.dumps(o, ensure_ascii=False, default=str)
        out.update(NUM.findall(s))
    return out


def assert_traceable(text: str, allowed: Set[str]) -> List[str]:
    """返回 text 里出现、但不在 allowed 里的数字（L2 违规项）。"""
    bad = []
    for m in NUM.findall(text):
        if m not in allowed and m not in ALLOW:
            bad.append(m)
    return bad


KERNEL_VERSION = "1.1.0"


def _digest(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ContractCache:
    """最简单可用的内容寻址缓存：命中则复用 contract，不重跑内核。"""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.hit = 0
        self.miss = 0

    def key(self, role: str, result: Dict[str, Any], dataset: Any, spec: Dict[str, Any]) -> str:
        return _digest(KERNEL_VERSION, role, result, dataset, spec)

    def get(self, key: str) -> Dict[str, Any] | None:
        p = self.root / f"{key}.json"
        if p.exists():
            self.hit += 1
            return json.loads(p.read_text(encoding="utf-8"))
        self.miss += 1
        return None

    def put(self, key: str, contract: Dict[str, Any]) -> None:
        (self.root / f"{key}.json").write_text(
            json.dumps(contract, ensure_ascii=False), encoding="utf-8")

    def stats(self) -> Dict[str, Any]:
        total = self.hit + self.miss
        return {"hit": self.hit, "miss": self.miss,
                "hit_rate": round(self.hit / total, 4) if total else 0.0}
