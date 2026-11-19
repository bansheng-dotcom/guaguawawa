# -*- coding: utf-8 -*-
"""report_kernel.consistency —— 跨报告数字登记与冲突检查。

报告之间最容易出的不是算错，而是「同一个名字两个数」：
  - 调研写“加价率差 4 倍”，经营写“11.3 倍”；
  - 一份写牛肉 −0.18 元/斤，另一份写 −179 元/千斤；
  - 同一指标不同期次，被当成同一件事。

本模块用一个轻量 registry（metrics.json）做单一出处：
  {id, label, value, unit, period, source, tolerance}
同一 id 的 value 超差即冲突；同一 label 不同 period 只告警，不判冲突。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def parse_num(text: Any) -> Optional[float]:
    m = NUM.search(str(text or "").replace(",", "").replace("−", "-"))
    return float(m.group(0)) if m else None


def load_registry(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"schema": "report-metrics/v1", "metrics": []}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def save_registry(path: str | Path, reg: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")


def check_registry(reg: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    seen: Dict[str, Dict[str, Any]] = {}
    for i, m in enumerate(reg.get("metrics") or []):
        mid = str(m.get("id") or "").strip()
        if not mid:
            errors.append(f"metrics[{i}] 缺 id")
            continue
        val = m.get("value")
        if not isinstance(val, (int, float)):
            errors.append(f"{mid}: value 不是数字")
            continue
        if mid in seen:
            prev = seen[mid]
            tol = float(m.get("tolerance", prev.get("tolerance", 0.01)) or 0.01)
            if abs(float(val) - float(prev["value"])) > tol:
                errors.append(
                    f"{mid}: 同一 id 两个值 {prev['value']} vs {val}（容差 {tol}）")
            if str(m.get("unit") or "") != str(prev.get("unit") or ""):
                errors.append(f"{mid}: 单位不一致 {prev.get('unit')} vs {m.get('unit')}")
        else:
            seen[mid] = m
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "count": len(reg.get("metrics") or [])}


def metrics_from_contract(contract: Dict[str, Any],
                          report_id: str = "") -> List[Dict[str, Any]]:
    """从渲染契约的 metric_strip 抽指标；只抽能解析成数字的。"""
    out: List[Dict[str, Any]] = []
    for m in contract.get("metric_strip") or []:
        val = parse_num(m.get("value"))
        if val is None:
            continue
        label = str(m.get("label") or "").strip()
        if not label:
            continue
        out.append({
            "id": f"{report_id}:{label}" if report_id else label,
            "label": label,
            "value": val,
            "unit": str(m.get("unit") or ""),
            "period": str(contract.get("period") or ""),
            "source": str(m.get("note") or ""),
            "tolerance": 0.01,
        })
    return out


def compare_contracts(paths: List[str | Path], tolerance: float = 0.01) -> Dict[str, Any]:
    """同 label 跨报告比对；不同 period 只告警。"""
    errors: List[str] = []
    warnings: List[str] = []
    by_label: Dict[str, List[Dict[str, Any]]] = {}
    for p in paths:
        try:
            c = json.loads(Path(p).read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{Path(p).name}: 读不了契约（{exc}）")
            continue
        for m in metrics_from_contract(c, Path(p).stem):
            by_label.setdefault(m["label"], []).append(m)

    for label, items in by_label.items():
        vals = [x["value"] for x in items]
        periods = {x.get("period") or "" for x in items}
        if len(items) < 2:
            continue
        if max(vals) - min(vals) > tolerance:
            if len(periods) > 1 and "" not in periods:
                warnings.append(f"{label}: 跨期次数值不同 {vals}（期次 {sorted(periods)}）")
            else:
                errors.append(f"{label}: 跨报告数值冲突 {vals}")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "labels": len(by_label)}
