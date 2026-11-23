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


def from_probe(probe_res: Dict[str, Any], project: Optional[Path] = None
               ) -> Dict[str, Any]:
    """**从探测结果生成供给方案**（SUPPLY-SOP v7.1）。

    这是本模块最重要的函数：供给方案不是手写的口号清单，
    它是「格子需求 × 源匹配」的产物——每一条都有出处、覆盖数和缺口原因。

    probe_res 来自 `card_probe.probe()`，含：
        plan_demands / match matrix(per demand) / unavailable_demands
    """
    pr = probe_res or {}
    per: List[Dict[str, Any]] = []
    l2 = l1 = l0 = 0
    for d in pr.get("supply_demands") or []:
        lvl = str(d.get("level") or "L0")
        if lvl == "L2":
            l2 += 1
        elif lvl == "L1":
            l1 += 1
        else:
            l0 += 1
        per.append(d)
    rows = planned_rows({
        "levels": {"planned_rows": pr.get("planned_rows")}
    }) if pr.get("planned_rows") else None
    doc = {
        "schema": SCHEMA,
        "generated": True,
        "generated_at": pr.get("generated_at") or "",
        "generated_from": {
            "grid_cells": pr.get("cells"),
            "sources": pr.get("sources") or [],
        },
        "business": pr.get("business") or "",
        "demands": per,
        "summary": {
            "demands": len(per),
            "L2": l2, "L1": l1, "L0": l0,
            "planned_level": "L2" if l2 else ("L1" if l1 else "L0"),
            "planned_rows": rows,
        },
        "levels": {
            "L1_possible": bool(l1 or l2),
            "L2_possible": bool(l2),
            "L2_condition": pr.get("to_l2_condition") or "",
            "planned_rows": rows,
        },
        "reviewed_at": pr.get("generated_at") or "",
    }
    return doc


def load_or_generate(project: Any) -> Dict[str, Any]:
    """优先读生成物 `plan/supply.json`，退回手写 `supply.yaml`（legacy）。

    生成物是权威：它就是探测的结论。手写的只有在还没探测过时才用。
    """
    p = Path(project)
    if p.is_file():
        return _yaml(p)
    gen = p / "plan" / "supply.json"
    if gen.is_file():
        try:
            import json
            return json.loads(gen.read_text(encoding="utf-8-sig")) or {}
        except Exception:  # noqa: BLE001
            pass
    return load(p)


def save(doc: Dict[str, Any], project: Any) -> Optional[Path]:
    """把生成的供给方案写到 `<project>/plan/supply.json`。"""
    if not doc:
        return None
    import json
    p = Path(project) / "plan"
    p.mkdir(parents=True, exist_ok=True)
    out = p / "supply.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return out


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
    """收卡时算「计划 vs 实际」；这是降级判定的唯一出处。

    没有供给方案时**不假装有计划**：按实际级别回报，并注明"未声明方案"。
    老报告（已完成产物）走的就是这一支。
    """
    actual = actual_level(merged)
    if not supply:
        return {
            "planned": actual, "actual": actual, "level": actual,
            "degraded": False, "degraded_from": None,
            "planned_rows": None, "actual_rows": _rows_of(merged),
            "why": "未声明供给方案（按实际级别交付）",
            "L2_condition": "",
            "label": LEVEL_LABEL.get(actual, ""),
            "no_supply": True,
        }
    planned = planned_level(supply)
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
