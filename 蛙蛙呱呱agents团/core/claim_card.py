# -*- coding: utf-8 -*-
"""core/claim_card —— 决策级断言的唯一 schema（升级 P1）。

一个 ClaimCard 回答五件事：

    1. 这句话是什么（statement / refs / values）
    2. 比较是否可比（comparability：同品/同期/同单位/同渠道）
    3. 还有什么解释没排除（rivals）
    4. 什么会推翻它（falsifier）
    5. 它能拿来做决策吗（actionable / confidence / grade / decision / expiry）

规则（写进代码，不靠纪律）：

    headline=true  => actionable=true
    actionable=true => comparability 无 unknown/no
                       rivals 全部 ruled / partially_ruled（且 partially 要有 evidence）
                       falsifier 非空
                       decision 非空
                       confidence ∈ {low, medium, high}
                       grade ∈ {A, B, C, D}

用法：

    python -m core.claim_card validate --claims workspace/report_upgrade/claims_fruit.json
    python -m core.claim_card audit    --claims workspace/report_upgrade/claims_fruit.json
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

GRADES = ("A", "B", "C", "D")
CONFIDENCES = ("low", "medium", "high")
COMPARABILITY_KEYS = ("same_product", "same_period", "same_unit", "same_channel")
COMPARABILITY_VALUES = ("yes", "no", "unknown", "n/a")
RIVAL_STATUS = ("ruled", "partially_ruled", "unruled")


@dataclass
class Rival:
    name: str
    status: str = "unruled"
    evidence: str = ""


@dataclass
class ClaimCard:
    id: str
    statement: str
    refs: List[str] = field(default_factory=list)
    values: Dict[str, Any] = field(default_factory=dict)
    comparability: Dict[str, str] = field(default_factory=dict)
    rivals: List[Rival] = field(default_factory=list)
    falsifier: str = ""
    confidence: str = "low"
    grade: str = "C"
    actionable: bool = False
    headline: bool = False
    decision: str = ""
    owner: str = ""
    expiry: str = ""
    kind: str = "general"
    evidence: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _blank(v: Any) -> bool:
    return not str(v or "").strip()


def _valid_date(s: str) -> bool:
    try:
        date.fromisoformat(str(s))
        return True
    except ValueError:
        return False


def _coerce(raw: Dict[str, Any] | ClaimCard) -> ClaimCard:
    if isinstance(raw, ClaimCard):
        return raw
    rivals = []
    for r in (raw.get("rivals") or []):
        if isinstance(r, dict):
            rivals.append(Rival(name=str(r.get("name") or ""),
                                status=str(r.get("status") or "unruled"),
                                evidence=str(r.get("evidence") or "")))
    return ClaimCard(
        id=str(raw.get("id") or ""),
        statement=str(raw.get("statement") or ""),
        refs=[str(x) for x in (raw.get("refs") or []) if str(x).strip()],
        values=dict(raw.get("values") or {}),
        comparability={str(k): str(v) for k, v in (raw.get("comparability") or {}).items()},
        rivals=rivals,
        falsifier=str(raw.get("falsifier") or ""),
        confidence=str(raw.get("confidence") or "low").lower(),
        grade=str(raw.get("grade") or "C").upper()[:1],
        actionable=bool(raw.get("actionable")),
        headline=bool(raw.get("headline")),
        decision=str(raw.get("decision") or ""),
        owner=str(raw.get("owner") or ""),
        expiry=str(raw.get("expiry") or ""),
        kind=str(raw.get("kind") or "general"),
        evidence=[str(x) for x in (raw.get("evidence") or [])],
        gaps=[str(x) for x in (raw.get("gaps") or [])],
        notes=str(raw.get("notes") or ""),
    )


def validate(raw: Dict[str, Any] | ClaimCard) -> Dict[str, Any]:
    """返回 {ok, errors, warnings, normalized}；errors 是 blocker。"""
    card = raw if isinstance(raw, ClaimCard) else _coerce(raw)
    errors: List[str] = []
    warnings: List[str] = []

    for key in ("id", "statement", "owner"):
        if _blank(getattr(card, key)):
            errors.append(f"缺字段或为空：{key}")

    if card.headline and not card.actionable:
        errors.append("headline=true 但 actionable=false：不可行动的断言不能进标题")
    if card.actionable and not card.refs:
        errors.append("actionable=true 但没有 refs：无法回溯")
    if card.actionable and not card.decision:
        errors.append("actionable=true 但没有 decision：不知道它支持哪个决定")

    if card.comparability:
        for k in COMPARABILITY_KEYS:
            v = str(card.comparability.get(k, "unknown")).lower()
            if v not in COMPARABILITY_VALUES:
                errors.append(f"comparability.{k} 非法：{v}（只允许 {COMPARABILITY_VALUES}）")
        if card.actionable:
            bad = [k for k in COMPARABILITY_KEYS
                   if str(card.comparability.get(k, "unknown")).lower() not in ("yes", "n/a")]
            if bad:
                errors.append("actionable=true 但比较不可比：" + ", ".join(bad))
    elif card.actionable:
        errors.append("actionable=true 但没有 comparability：无法判断是否可比")

    for r in card.rivals:
        if r.status not in RIVAL_STATUS:
            errors.append(f"rival「{r.name}」状态非法：{r.status}")
        if r.status == "partially_ruled" and not r.evidence:
            errors.append(f"rival「{r.name}」是 partially_ruled 但没有 evidence")

    if card.actionable:
        if not card.rivals:
            errors.append("actionable=true 但没有 rivals：没有列竞争解释")
        unruled = [r.name for r in card.rivals if r.status == "unruled"]
        if unruled:
            errors.append("actionable=true 但仍有未排除的竞争解释：" + ", ".join(unruled))
        if not card.falsifier:
            errors.append("actionable=true 但没有 falsifier：无法证伪")
        if card.confidence not in CONFIDENCES:
            errors.append(f"confidence 非法：{card.confidence}")
        if card.grade not in GRADES:
            errors.append(f"grade 非法：{card.grade}")
        if card.grade in ("C", "D"):
            warnings.append(f"grade={card.grade}：需敏感性/交叉验证支撑才能保持 actionable")

    if card.expiry and not _valid_date(card.expiry):
        errors.append(f"expiry 不是 YYYY-MM-DD：{card.expiry}")
    if card.kind in ("forecast", "prediction") and not card.expiry:
        errors.append("预测类断言必须写 expiry")

    normalized = card.to_dict()
    normalized["comparability"] = {k: str(card.comparability.get(k, "unknown")).lower()
                                   for k in COMPARABILITY_KEYS}
    normalized["rivals"] = [asdict(r) for r in card.rivals]
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "normalized": normalized}


def audit(cards: List[Dict[str, Any] | ClaimCard]) -> Dict[str, Any]:
    """对一组 claim 做体检，返回可写进 manifest 的摘要。"""
    rows: List[Dict[str, Any]] = []
    by_grade: Dict[str, int] = {g: 0 for g in GRADES}
    by_conf: Dict[str, int] = {c: 0 for c in CONFIDENCES}
    actionable = unidentified = headline_total = headline_actionable = 0
    bad: List[Dict[str, Any]] = []

    for raw in cards:
        v = validate(raw)
        card = _coerce(v["normalized"])
        row = {
            "id": card.id,
            "statement": card.statement,
            "headline": card.headline,
            "actionable": card.actionable,
            "grade": card.grade,
            "confidence": card.confidence,
            "ok": v["ok"],
            "errors": v["errors"],
            "warnings": v["warnings"],
        }
        rows.append(row)
        by_grade[card.grade] = by_grade.get(card.grade, 0) + 1
        by_conf[card.confidence] = by_conf.get(card.confidence, 0) + 1
        if card.actionable:
            actionable += 1
        else:
            unidentified += 1
        if card.headline:
            headline_total += 1
            if card.actionable:
                headline_actionable += 1
        if v["errors"]:
            bad.append({"id": card.id, "errors": v["errors"]})

    total = len(rows)
    checks = [
        {"id": "C1_headline_actionable", "ok": headline_total == headline_actionable,
         "msg": "所有 headline 断言必须 actionable",
         "value": f"{headline_actionable}/{headline_total}"},
        {"id": "C2_all_have_refs", "ok": all(bool(_coerce(r).refs) for r in cards),
         "msg": "所有断言必须有 refs", "value": f"{sum(1 for r in cards if _coerce(r).refs)}/{total}"},
        {"id": "C3_actionable_falsifier",
         "ok": all((not _coerce(r).actionable) or bool(_coerce(r).falsifier) for r in cards),
         "msg": "actionable 断言必须有 falsifier",
         "value": f"{sum(1 for r in cards if _coerce(r).actionable and _coerce(r).falsifier)}/"
                  f"{sum(1 for r in cards if _coerce(r).actionable)}"},
    ]
    return {
        "schema": "dsh.claim_audit/v1",
        "total": total,
        "actionable": actionable,
        "unidentified": unidentified,
        "actionable_ratio": round(actionable / total, 3) if total else 0.0,
        "headline_total": headline_total,
        "headline_actionable": headline_actionable,
        "headline_unactionable": headline_total - headline_actionable,
        "by_grade": by_grade,
        "by_confidence": by_conf,
        "errors": bad,
        "checks": checks,
        "ok": not bad and all(c["ok"] for c in checks),
        "rows": rows,
    }


def load_cards(path: str | Path) -> List[Dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        if isinstance(data.get("claims"), list):
            return data["claims"]
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("claims 文件必须是对象或数组")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="claim_card",
                                 description="决策级断言 ClaimCard：校验与体检")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="校验一条或一组 claim")
    v.add_argument("--claims", required=True)
    v.add_argument("--json", default=None)

    a = sub.add_parser("audit", help="对一组 claim 做体检")
    a.add_argument("--claims", required=True)
    a.add_argument("--json", default=None)

    args = ap.parse_args(argv)
    cards = load_cards(args.claims)

    if args.cmd == "validate":
        results = [validate(c) for c in cards]
        out = {"ok": all(r["ok"] for r in results),
               "results": [{"id": (r["normalized"] or {}).get("id"),
                            "ok": r["ok"], "errors": r["errors"],
                            "warnings": r["warnings"]} for r in results]}
    else:
        out = audit(cards)

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
    print(text[:12000])
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
