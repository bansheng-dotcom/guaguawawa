# -*- coding: utf-8 -*-
"""S04 优先级与 Backlog：opportunity / rice / ice / backlog 四条真实计算门禁。

算子是确定性的纯函数，禁止回填固定分数：
    RICE = (Reach × Impact × Confidence) / max(Effort, effort_min)
    ICE  = Impact × Confidence × Ease
    Opportunity（Ulwick，双量纲自适应）：
        satisfaction ∈ [0,1]  → Importance × (1 − Satisfaction)
        satisfaction > 1（10 分制）→ Importance + max(Importance − Satisfaction, 0)
"""
from __future__ import annotations

from typing import Any, Dict, List

from ._common import check, is_blank, load_thresholds, make_result

NAME = "priority"
DESC = "优先级与 Backlog"
ACTIONS = {"opportunity": "机会分（Importance × 满足度缺口）",
           "ice": "ICE 打分", "rice": "RICE 打分", "backlog": "Backlog 排序门禁"}

_PRIORITY_LEVELS = ("P0", "P1", "P2", "P3")


class PriorityCalculator:
    """R07 优先级确定性算子（L01 工具实体层的真实计算内核）。"""

    def __init__(self) -> None:
        self.effort_min = float(load_thresholds().get("prioritize", {}).get("effort_min", 0.1))

    @staticmethod
    def _num(item: Dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            return float(item.get(key, default) or default)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _confidence(value: float) -> float:
        # 兼容 0~1 与 0~100 两种 Confidence 量纲
        if value > 1.0:
            return value / 100.0
        return value

    def rice(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored = []
        for item in items:
            effort = max(self._num(item, "effort", 1.0), self.effort_min)
            score = (self._num(item, "reach") * self._num(item, "impact")
                     * self._confidence(self._num(item, "confidence", 0.0))) / effort
            row = dict(item)
            row["score"] = round(score, 4)
            scored.append(row)
        return self._rank(scored)

    def ice(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored = []
        for item in items:
            score = (self._num(item, "impact") * self._confidence(self._num(item, "confidence"))
                     * self._num(item, "ease"))
            row = dict(item)
            row["score"] = round(score, 4)
            scored.append(row)
        return self._rank(scored)

    def opportunity(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored = []
        for item in items:
            imp = self._num(item, "importance")
            sat = self._num(item, "satisfaction")
            if sat <= 1.0:
                score = imp * (1.0 - sat)
            else:
                score = imp + max(imp - sat, 0.0)
            row = dict(item)
            row["opportunity_score"] = round(score, 4)
            row["score"] = round(score, 4)
            row["gap"] = round(max(score, 0.0), 4)
            scored.append(row)
        return self._rank(scored)

    @staticmethod
    def _rank(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows.sort(key=lambda r: r["score"], reverse=True)
        for idx, row in enumerate(rows, start=1):
            row["rank"] = idx
        return rows


def _items(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = input_data.get("items")
    return [i for i in (items if isinstance(items, list) else []) if isinstance(i, dict)]


def _scored(action: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    calc = PriorityCalculator()
    items = _items(input_data)
    checks = [check(bool(items), "待打分项为空（items）", "input")]
    for idx, item in enumerate(items):
        checks.append(check(not is_blank(item.get("name")),
                            f"第 {idx} 项缺少 name", "input"))
    if action == "rice":
        ranked = calc.rice(items)
        formula = "RICE = (Reach × Impact × Confidence) / max(Effort, effort_min)"
    elif action == "ice":
        ranked = calc.ice(items)
        formula = "ICE = Impact × Confidence × Ease"
    else:
        ranked = calc.opportunity(items)
        formula = ("Opportunity = Importance × (1 − Satisfaction)  [Satisfaction ∈ 0~1]；"
                   "或 Importance + max(Importance − Satisfaction, 0)  [10 分制]")
    checks.append(check(all(r["score"] > 0 for r in ranked) if ranked else False,
                        "存在得分非正的条目，算子输入不可信", "score"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "priority", action, checks,
                       formula=formula, ranked=ranked, item_count=len(ranked))


def _opportunity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _scored("opportunity", input_data)


def _ice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _scored("ice", input_data)


def _rice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _scored("rice", input_data)


def _backlog(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Backlog 门禁：条目必须可验收 + 依赖可解析，输出「依赖先行 + 分数降序」拓扑序。"""
    checks = []
    items = _items(input_data)
    checks.append(check(bool(items), "Backlog 为空（items）", "input"))
    titles = [str(i.get("title") or "") for i in items]
    for idx, item in enumerate(items):
        title = str(item.get("title") or "")
        checks.append(check(not is_blank(title), f"第 {idx} 项缺少 title", "item"))
        checks.append(check(bool(item.get("acceptance_criteria")),
                            f"条目「{title}」缺少验收标准", "acceptance"))
        checks.append(check(str(item.get("priority") or "") in _PRIORITY_LEVELS,
                            f"条目「{title}」priority 不在 {'/'.join(_PRIORITY_LEVELS)}",
                            "priority"))
        try:
            float(item.get("score", 0))
        except (TypeError, ValueError):
            checks.append(check(False, f"条目「{title}」score 非数值", "score"))
        deps = item.get("dependencies") or []
        if not isinstance(deps, list):
            checks.append(check(False, f"条目「{title}」dependencies 应为数组", "dependency"))
            continue
        for dep in deps:
            checks.append(check(str(dep) in titles,
                                f"条目「{title}」依赖的「{dep}」不在 Backlog 内",
                                "dependency"))

    # 依赖先行 + 同层按 score 降序（Kahn 贪心，循环依赖必须阻断）
    remaining = [(idx, dict(item)) for idx, item in enumerate(items)]
    ordered_items: List[Dict[str, Any]] = []
    placed: set = set()
    while remaining:
        ready = [(idx, item) for idx, item in remaining
                 if all(str(d) in placed for d in (item.get("dependencies") or []))]
        if not ready:
            checks.append(check(False, "Backlog 存在循环依赖，无法拓扑排序", "dependency"))
            break
        ready.sort(key=lambda pair: (-float(pair[1].get("score", 0) or 0), pair[0]))
        pick_idx, pick = ready[0]
        ordered_items.append(pick)
        placed.add(str(pick.get("title") or ""))
        remaining = [(idx, item) for idx, item in remaining if idx != pick_idx]

    checks.append(check(all(float(ordered_items[i].get("score", 0) or 0)
                            >= float(ordered_items[i + 1].get("score", 0) or 0)
                            for i in range(len(ordered_items) - 1)
                            if not (ordered_items[i + 1].get("dependencies") or [])),
                        "Backlog 同层条目未按 score 降序排列", "order"))
    ok = all(c["ok"] for c in checks)
    return make_result(ok, "priority", "backlog", checks,
                       item_count=len(ordered_items), ordered=ordered_items)


def opportunity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _opportunity(input_data)


def ice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _ice(input_data)


def rice(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _rice(input_data)


def backlog(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return _backlog(input_data)
