"""Local CSV cleaning/deduplication and simple stage funnel calculation."""
from __future__ import annotations
import csv
from typing import Any, Dict, List

def clean_csv(path: str, id_column: str = "email", stage_column: str = "stage") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    kept: List[Dict[str, str]] = []; seen = set(); duplicates = 0; blank_ids = 0
    for row in rows:
        key = (row.get(id_column) or "").strip().lower()
        if not key:
            blank_ids += 1; continue
        if key in seen:
            duplicates += 1; continue
        seen.add(key); kept.append({str(k): (v or "").strip() for k, v in row.items()})
    funnel: Dict[str, int] = {}
    for row in kept:
        stage = (row.get(stage_column) or "unknown").strip() or "unknown"
        funnel[stage] = funnel.get(stage, 0) + 1
    return {"ok": True, "capability_status": "real", "capability_evidence": "local CSV parsed, cleaned and deduplicated", "rows_in": len(rows), "rows_out": len(kept), "duplicates_removed": duplicates, "blank_ids_removed": blank_ids, "funnel": funnel, "records": kept, "next": "local export analysis complete; CRM writes are not performed"}
