"""Local metric formula checks; no analytics or ad-platform access."""
from __future__ import annotations
from typing import Any, Dict

def recalc(metrics: Dict[str, Any]) -> Dict[str, Any]:
    leads = float(metrics.get("leads", 0)); customers = float(metrics.get("customers", 0)); spend = float(metrics.get("spend", 0)); revenue = float(metrics.get("revenue", 0))
    conversion = customers / leads if leads else 0.0
    roi = (revenue - spend) / spend if spend else None
    ok = leads >= 0 and customers >= 0 and spend >= 0
    return {"ok": ok, "capability_status": "real", "capability_evidence": "local metrics and formulas recalculated", "conversion_rate": conversion, "roi": roi, "inputs": {"leads": leads, "customers": customers, "spend": spend, "revenue": revenue}, "next": "formula check complete; external attribution remains simulated"}
