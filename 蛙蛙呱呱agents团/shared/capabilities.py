# -*- coding: utf-8 -*-
"""团队自有能力目录。

能力分两类：
  - `skill`：已写成确定性代码，命令为 `agent.py <skill> <actions>`；
  - `knowledge`：以规范形式内化，没有独立命令，执行时按能力卡里的规则判断与产出。

目录是**自有资产**：不含任何外部平台依赖、路径或调用；能力卡由本团队撰写。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
CATALOG_PATH = os.path.join(_HERE, "capabilities", "catalog.json")


def load_catalog(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def all_caps() -> List[Dict[str, Any]]:
    return list(load_catalog().get("capabilities", []))


def get(cap_id: str) -> Optional[Dict[str, Any]]:
    return next((c for c in all_caps() if c["id"] == cap_id), None)


def list_caps(role: Optional[str] = None, q: Optional[str] = None,
              kind: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    for cap in all_caps():
        if role and cap["owner"] != role.lower() and role.lower() not in cap.get("consumers", []):
            continue
        if kind and cap["kind"] != kind:
            continue
        if q:
            hay = " ".join([cap["id"], cap["title"], cap["summary"],
                            " ".join(cap.get("triggers", []))]).lower()
            if q.lower() not in hay:
                continue
        out.append(cap)
    return out


def owned(role: str) -> List[Dict[str, Any]]:
    return [c for c in all_caps() if c["owner"] == role.lower()]


def card_path(cap: Dict[str, Any]) -> str:
    return os.path.join(_REPO, cap["dir"].replace("/", os.sep), "README.md")


def stats() -> Dict[str, Any]:
    caps = all_caps()
    by_kind: Dict[str, int] = {}
    by_role: Dict[str, int] = {}
    for c in caps:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        by_role[c["owner"]] = by_role.get(c["owner"], 0) + 1
    return {"count": len(caps), "by_kind": by_kind,
            "by_role": dict(sorted(by_role.items())),
            "executable": sum(1 for c in caps if c["entry"])}
