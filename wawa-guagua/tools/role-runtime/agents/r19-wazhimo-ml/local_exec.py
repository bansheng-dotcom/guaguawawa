"""Local evaluation scoring and model-card generation; never publishes a model."""
from __future__ import annotations

import statistics
from typing import Any, Dict, List


def _rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("rows", "records", "predictions", "dataset"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
        return []
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    return []


def execute(payload: Any, model_name: str = "local-model") -> Dict[str, Any]:
    rows = _rows(payload)
    if not rows:
        return {"ok": False, "capability_status": "blocked",
                "reason": "non-empty evaluation row list required",
                "side_effects": [], "published": False}

    scored = []
    for index, row in enumerate(rows):
        expected = row.get("expected", row.get("y_true", row.get("label")))
        actual = row.get("actual", row.get("y_pred", row.get("prediction")))
        if expected is None or actual is None:
            return {"ok": False, "capability_status": "blocked",
                    "reason": f"row {index} missing expected/actual",
                    "side_effects": [], "published": False}
        match = 1.0 if str(expected) == str(actual) else 0.0
        scored.append({"index": index, "expected": expected, "actual": actual,
                       "correct": bool(match), "score": match})
    total = len(scored)
    hits = sum(1 for row in scored if row["correct"])
    accuracy = hits / total
    try:
        stdev = statistics.pstdev([row["score"] for row in scored])
    except statistics.StatisticsError:
        stdev = 0.0
    model_card = {
        "model_name": model_name,
        "evaluation_rows": total,
        "accuracy": round(accuracy, 6),
        "score_stdev": round(stdev, 6),
        "metric": "accuracy",
        "dataset_scope": "local evaluation input only",
        "publication_status": "not_published",
    }
    return {"ok": True, "capability_status": "real", "scored_rows": scored,
            "model_card": model_card, "accuracy": model_card["accuracy"],
            "side_effects": [], "published": False}
