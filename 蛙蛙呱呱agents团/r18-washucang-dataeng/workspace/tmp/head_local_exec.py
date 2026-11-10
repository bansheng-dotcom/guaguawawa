"""Local ELT cleaning, lineage and data-quality gate; no external connectors."""
from __future__ import annotations

from typing import Any, Dict, List


def _rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("rows", "records", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
        return []
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    return []


def execute(payload: Any, source: str = "local_input") -> Dict[str, Any]:
    if isinstance(payload, dict):
        source = payload.get("source", source)
        rows = _rows(payload)
    else:
        rows = _rows(payload)
    if not rows:
        return {"ok": False, "capability_status": "blocked",
                "reason": "non-empty row list required", "side_effects": []}

    cleaned: List[Dict[str, Any]] = []
    for row in rows:
        cleaned.append({str(k).strip(): (v.strip() if isinstance(v, str) else v)
                        for k, v in row.items() if v is not None})
    keys = set(cleaned[0])
    schema_ok = all(set(row) == keys for row in cleaned)
    unique = len({repr(sorted(row.items())) for row in cleaned}) == len(cleaned)
    null_counts = {key: sum(1 for row in cleaned if row.get(key) in (None, ""))
                   for key in sorted(keys)}
    lineage = {"source": source, "transform": "trim strings/drop nulls",
               "target": "local_cleaned_rows"}
    quality = {"schema_consistent": schema_ok, "unique_rows": unique,
               "null_counts": null_counts, "row_count": len(cleaned)}
    ok = schema_ok and unique
    return {"ok": ok, "capability_status": "real" if ok else "blocked",
            "rows": cleaned, "lineage": lineage, "quality": quality,
            "side_effects": [], "external_connectors_used": 0}
