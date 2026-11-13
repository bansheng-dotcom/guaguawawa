# -*- coding: utf-8 -*-
"""R05 蛙深远 · 报告适配器（薄壳）。

写作逻辑已抽到 `shared/report_writer.py` + `report_specs/writing/r05.yaml`；
本文件只负责把 r05 的上下文整理成证据包，再交给通用写作器。
没有台账（claims 为空）就返回 None，内核回落到通用映射——不伪装成报告。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared import report_writer  # noqa: E402


def _load(data: Any) -> Dict[str, Any]:
    if isinstance(data, str) and os.path.isfile(data):
        try:
            return json.load(open(data, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return data if isinstance(data, dict) else {}


def r05_contract(result: Dict[str, Any], skill: str, action: str, intent: str,
                 data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    ctx = _load(data)
    ledger = ctx.get("ledger") if isinstance(ctx.get("ledger"), dict) else None
    if ledger:  # 上下文包形态：台账 + 指标 + 图 + 观测 + 判断
        pack = {
            "topic": ctx.get("topic") or ledger.get("topic"),
            "window": ledger.get("window"),
            "claims": ledger.get("claims"),
            "sources": ledger.get("sources"),
            "sections": [
                dict(s, verdict=(ctx.get("verdicts") or {}).get(s.get("title")))
                for s in (ledger.get("sections") or [])
            ],
            "metrics": ctx.get("metrics"),
            "charts": ctx.get("charts"),
            "dataset": ctx.get("dataset"),
        }
    else:  # 直接给台账 / 证据包
        pack = ctx
    return report_writer.build("r05", pack, result, intent)
