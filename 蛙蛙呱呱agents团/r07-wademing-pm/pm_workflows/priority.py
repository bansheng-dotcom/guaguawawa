# -*- coding: utf-8 -*-
"""W3 priority：机会分 / RICE / ICE → backlog → 路线图 → 发布说明。

门禁：
  - 排序可解释：每一项必须声明打分方法与分值来源（source），算子可复算；
  - backlog 可执行：每条有 P0~P3、验收标准与分值；
  - 路线图结果导向：segment → outcome → business_impact，拒绝功能交付清单；
  - 发布说明五分类齐备（New/Improvements/Bug Fixes/Breaking Changes/Deprecations）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import common as c

STAGE = "priority"
ARTIFACT = "priority_pack"

_METHODS = ("opportunity", "rice", "ice")
_PRIORITY_LEVELS = ("P0", "P1", "P2", "P3")


def _calc():
    try:
        from skills.s04_priority import PriorityCalculator
        return PriorityCalculator()
    except Exception:  # noqa: BLE001
        return None


def _score(calc: Any, item: Dict[str, Any], method: str) -> float:
    """按方法复算单项分数；与 skills.s04_priority 同一公式。"""
    if calc is not None:
        fn = getattr(calc, method, None)
        if callable(fn):
            try:
                return float(fn([dict(item)])[0]["score"])
            except Exception:  # noqa: BLE001
                pass
    # 退化实现（与 s04 公式一致）
    num = c.as_number
    if method == "rice":
        conf = num(item.get("confidence"))
        if conf > 1.0:
            conf /= 100.0
        return (num(item.get("reach")) * num(item.get("impact")) * conf) / max(
            num(item.get("effort"), 1.0), 0.1)
    if method == "ice":
        conf = num(item.get("confidence"))
        if conf > 1.0:
            conf /= 100.0
        return num(item.get("impact")) * conf * num(item.get("ease"))
    imp, sat = num(item.get("importance")), num(item.get("satisfaction"))
    return imp * (1.0 - sat) if sat <= 1.0 else imp + max(imp - sat, 0.0)


def _roadmap_gate(roadmap: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    checks = [c.ck(bool(roadmap), "路线图为空（roadmap）", "roadmap.input", "BLOCKER")]
    for idx, item in enumerate(roadmap):
        for key, label in (("segment", "人群"), ("outcome", "结果"),
                           ("business_impact", "业务影响")):
            checks.append(c.ck(not c.blank(item.get(key)),
                               f"路线图第 {idx} 条缺少{label}（{key}）",
                               f"roadmap.{key}", "BLOCKER"))
        checks.append(c.ck(len(str(item.get("outcome") or "").strip()) >= 4,
                           f"路线图第 {idx} 条结果描述过短，无法验收",
                           "roadmap.outcome", "BLOCKER"))
    return checks


def _release_gate(notes: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks = [c.ck(not c.blank(notes.get("title")), "发布说明缺少版本标题（title）",
                   "release.title", "BLOCKER")]
    sections = notes.get("sections") if isinstance(notes.get("sections"), dict) else {}
    required = ["New Features", "Improvements", "Bug Fixes",
                "Breaking Changes", "Deprecations"]
    for name in required:
        entries = sections.get(name)
        entries = entries if isinstance(entries, list) else []
        checks.append(c.ck(bool(entries), f"发布说明缺少 {name} 分类内容",
                           "release.category", "BLOCKER"))
    return checks


def build(data: Dict[str, Any]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    raw_items = [x for x in (data.get("items") or []) if isinstance(x, dict)]
    roadmap = [x for x in (data.get("roadmap") or []) if isinstance(x, dict)]
    notes = data.get("release_notes") if isinstance(data.get("release_notes"), dict) else {}
    calc = _calc()

    checks: List[Dict[str, Any]] = []
    scored: List[Dict[str, Any]] = []
    checks.append(c.ck(len(raw_items) >= 2,
                       f"待排序事项 {len(raw_items)} 条 < 2 条", "input", "BLOCKER"))
    for idx, item in enumerate(raw_items):
        title = str(item.get("title") or item.get("name") or "").strip()
        method = str(item.get("method") or "").strip().lower()
        checks.append(c.ck(bool(title), f"第 {idx} 项缺少 title", "score.title", "BLOCKER"))
        checks.append(c.ck(method in _METHODS,
                           f"第 {idx} 项 method={method!r} 不在 {_METHODS}",
                           "score.method", "BLOCKER"))
        checks.append(c.ck(not c.blank(item.get("source")),
                           f"第 {idx} 项缺少分值来源（source）",
                           "score.source", "BLOCKER"))
        score = _score(calc, item, method) if method in _METHODS else 0.0
        checks.append(c.ck(score > 0, f"第 {idx} 项复算分值 {score} 非正，输入不可信",
                           "score.value", "BLOCKER"))
        ac = item.get("acceptance_criteria")
        ac = ac if isinstance(ac, list) else []
        checks.append(c.ck(bool([x for x in ac if not c.blank(x)]),
                           f"第 {idx} 项缺少验收标准（acceptance_criteria）",
                           "backlog.acceptance", "BLOCKER"))
        row = dict(item)
        row["title"] = title
        row["method"] = method
        row["score"] = round(score, 4)
        scored.append(row)

    scored.sort(key=lambda r: (-float(r.get("score") or 0.0), str(r.get("title"))))
    backlog: List[Dict[str, Any]] = []
    for rank, row in enumerate(scored, start=1):
        row["rank"] = rank
        level = _PRIORITY_LEVELS[min(rank - 1, len(_PRIORITY_LEVELS) - 1)]
        backlog.append({
            "rank": rank, "title": row["title"], "score": row["score"],
            "method": row["method"], "source": row.get("source", ""),
            "priority": level,
            "acceptance_criteria": row.get("acceptance_criteria", []),
            "dependencies": row.get("dependencies", []),
        })

    checks.append(c.ck(bool(backlog), "Backlog 为空", "backlog.input", "BLOCKER"))
    checks.append(c.ck(all(b["score"] >= (backlog[i + 1]["score"] if i + 1 < len(backlog) else 0)
                           for i, b in enumerate(backlog)),
                       "Backlog 未按复算分值降序排列", "backlog.order", "BLOCKER"))
    checks.extend(_roadmap_gate(roadmap))
    checks.extend(_release_gate(notes))

    g = c.gate(checks, STAGE)
    return {
        "artifact": ARTIFACT,
        "stage": STAGE,
        "formula": {
            "opportunity": "Importance × (1 − Satisfaction)",
            "rice": "(Reach × Impact × Confidence) / max(Effort, 0.1)",
            "ice": "Impact × Confidence × Ease",
        },
        "ranked": scored,
        "backlog": backlog,
        "roadmap": roadmap,
        "release_notes": notes,
        "gate": g,
    }
