# -*- coding: utf-8 -*-
"""core.supply_plan —— 数据供给方案（SUPPLY-SOP v7.0 · ⓪）。

**在拆卡之前**回答三件事：

    这个业务有哪些源（A 开放 / B 半开放 / C 封闭）
    最多能到几级（L1 点证据 / L2 序列）
    到 L2 需要什么条件（多少钱 / 多少时间）

供给方案是**基准线**：
    计划 L1 且交付 L1 → 正常交付，不叫降级
    计划 L2 实际 L1 → 降级，必须写 degraded_from
    计划 L2 且交付 L2 → 按计划

用法：
    from core import supply_plan as sup
    doc = sup.load(project / "supply.yaml")
    errs = sup.validate(doc)
    lvl = sup.planned_level(doc)        # "L2" / "L1" / "L0"
    rows = sup.planned_rows(doc)        # 真实长表行数（不是格子数）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "dsh.supply/v1"
LAYERS = ("A", "B", "C")          # A 开放 / B 半开放 / C 封闭
LEVELS = ("L0", "L1", "L2")
LEVEL_LABEL = {
    "L0": "只有拆解，出不了报告",
    "L1": "点证据（数字+来源），能答现状与对比",
    "L2": "序列证据（长表），能答趋势与分布",
}


def _yaml(p: Path) -> Dict[str, Any]:
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def load(path: Any) -> Dict[str, Any]:
    """读 supply.yaml；传目录也行（自动找 <dir>/supply.yaml）。"""
    p = Path(path)
    if p.is_dir():
        p = p / "supply.yaml"
    if not p.is_file():
        return {}
    return _yaml(p)


def validate(doc: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not doc:
        return ["没有 supply.yaml（供给方案是拆卡的前提）"]
    if doc.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    if not str(doc.get("business") or "").strip():
        errs.append("缺 business")
    srcs = doc.get("sources") or []
    if not srcs:
        errs.append("sources 为空（至少一个源）")
    seen_layers = set()
    for i, s in enumerate(srcs):
        lay = str(s.get("layer") or "")
        if lay not in LAYERS:
            errs.append("sources[%d].layer 必须是 %s" % (i, LAYERS))
        else:
            seen_layers.add(lay)
        if not str(s.get("name") or "").strip():
            errs.append("sources[%d] 缺 name" % i)
        if not (s.get("gives") or []):
            errs.append("sources[%d] 缺 gives（这个源给什么）" % i)
    lv = doc.get("levels") or {}
    l1 = bool(lv.get("L1_possible"))
    l2 = bool(lv.get("L2_possible"))
    if not l1 and not l2:
        errs.append("L1/L2 都不可得——这个业务不该开拆卡")
    # L2 不可得时，必须写清"要什么条件才能到 L2"
    if not l2 and not str(lv.get("L2_condition") or "").strip():
        errs.append("L2_possible=false 时必须写 L2_condition（要多少钱/多少时间）")
    # 声称 L2 却没有 C 层源 → 自相矛盾
    if l2 and "C" not in seen_layers:
        errs.append("L2_possible=true 但没有 C 层源（序列几乎只能从封闭源拿）")
    # 声明了真实行数就必须是正整数
    pr = lv.get("planned_rows")
    if pr is not None and (not isinstance(pr, int) or pr <= 0):
        errs.append("levels.planned_rows 必须是正整数")
    return errs


def planned_level(doc: Dict[str, Any]) -> str:
    """计划能到的最高级别。"""
    lv = (doc or {}).get("levels") or {}
    if lv.get("L2_possible"):
        return "L2"
    if lv.get("L1_possible"):
        return "L1"
    return "L0"


def planned_rows(doc: Dict[str, Any]) -> Optional[int]:
    """供给方案声明的真实长表行数；没声明返回 None。"""
    pr = ((doc or {}).get("levels") or {}).get("planned_rows")
    return int(pr) if isinstance(pr, int) and pr > 0 else None


def actual_level(merged: Dict[str, Any]) -> str:
    """收卡后：实际到哪一级。

    L2：有长表行（mart / dataset）；L1：有数字+来源；L0：都没有。
    """
    m = merged or {}
    for k in ("mart_rows", "datasets", "dataset_rows"):
        v = m.get(k)
        if isinstance(v, dict) and any(int(x or 0) > 0 for x in v.values()):
            return "L2"
        if isinstance(v, list) and v:
            return "L2"
    if m.get("numbers"):
        return "L1"
    return "L0"


def capability_of(supply: Dict[str, Any], merged: Dict[str, Any]) -> Dict[str, Any]:
    """收卡时算「计划 vs 实际」；这是降级判定的唯一出处。"""
    planned = planned_level(supply) if supply else "L1"
    actual = actual_level(merged)
    rank = {"L0": 0, "L1": 1, "L2": 2}
    degraded = rank.get(actual, 0) < rank.get(planned, 0)
    lv = (supply or {}).get("levels") or {}
    return {
        "planned": planned,
        "actual": actual,
        "level": actual,
        "degraded": degraded,
        "degraded_from": planned if degraded else None,
        "planned_rows": planned_rows(supply),
        "actual_rows": _rows_of(merged),
        "why": _why(planned, actual, lv),
        "L2_condition": str(lv.get("L2_condition") or ""),
        "label": LEVEL_LABEL.get(actual, ""),
    }


def _rows_of(merged: Dict[str, Any]) -> Optional[int]:
    for k in ("mart_rows", "datasets", "dataset_rows"):
        v = (merged or {}).get(k)
        if isinstance(v, dict) and v:
            return sum(int(x or 0) for x in v.values())
        if isinstance(v, list):
            return len(v)
    return None


def _why(planned: str, actual: str, lv: Dict[str, Any]) -> str:
    rank = {"L0": 0, "L1": 1, "L2": 2}
    if rank.get(actual, 0) >= rank.get(planned, 0):
        if actual == planned:
            return "按计划交付（%s）" % planned
        return "超出计划（计划 %s，实际 %s）" % (planned, actual)
    if actual == "L1":
        return "计划 %s，实际只有点证据（未做序列采集）" % planned
    return "计划 %s，实际没有可用数据" % planned


def gate(supply: Dict[str, Any], merged: Dict[str, Any]) -> Dict[str, Any]:
    """G-CAPABILITY（软门禁）：降级必须有理由。"""
    cap = capability_of(supply, merged)
    problems: List[str] = []
    if not supply:
        problems.append("没有供给方案：无法判断计划级别")
    if cap["degraded"] and not cap.get("why"):
        problems.append("降级了但没写理由")
    if cap["degraded"] and cap["planned"] == "L2" \
            and not str((supply or {}).get("levels", {}).get("L2_condition") or "").strip():
        problems.append("计划 L2 却降级，且没写补采条件")
    return {"id": "G-CAPABILITY", "ok": not problems, "hard": False,
            "msg": ("能力级别：计划 %s / 实际 %s" % (cap["planned"], cap["actual"])),
            "detail": {"capability": cap, "problems": problems}}
