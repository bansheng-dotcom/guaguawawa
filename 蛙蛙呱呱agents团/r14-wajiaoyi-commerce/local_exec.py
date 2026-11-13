"""Safe local commerce state, idempotency, and money checks; never charges."""
from decimal import Decimal, InvalidOperation


def _money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise ValueError()
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid non-negative money amount")


def execute(data):
    if not isinstance(data, dict):
        return {"ok": False, "capability_status": "blocked", "reason": "input must be object", "side_effects": []}
    if data.get("external_payment") or data.get("charge"):
        return {"ok": False, "capability_status": "blocked", "reason": "external payment is unavailable; no charge attempted", "side_effects": []}
    lines = data.get("items", [])
    try:
        total = sum((_money(x["unit_price"]) * int(x["quantity"]) for x in lines), Decimal("0"))
        total = total.quantize(Decimal("0.01"))
        declared = _money(data.get("total", total))
        if total != declared or any(int(x["quantity"]) <= 0 for x in lines):
            raise ValueError("amount or quantity mismatch")
    except (ValueError, KeyError, TypeError):
        return {"ok": False, "capability_status": "blocked", "reason": "invalid amount/quantity or total mismatch", "side_effects": []}
    keys = [str(x.get("idempotency_key", "")).strip() for x in data.get("events", [])]
    if any(not k for k in keys) or len(keys) != len(set(keys)):
        return {"ok": False, "capability_status": "blocked", "reason": "missing or duplicate idempotency key", "side_effects": []}
    return {"ok": True, "capability_status": "real", "total": str(total), "events_checked": len(keys), "state_validated": True, "side_effects": [], "payment": "not charged"}
