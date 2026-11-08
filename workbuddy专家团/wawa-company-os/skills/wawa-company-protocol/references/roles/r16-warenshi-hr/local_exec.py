"""Local PII redaction and payroll input checks; never pays wages."""
import re


def execute(data):
    if not isinstance(data, dict): return {"ok": False, "capability_status": "blocked", "reason": "input must be object", "side_effects": []}
    text = str(data)
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    redacted = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[REDACTED_PHONE]", redacted)
    payroll = data.get("payroll", {})
    try:
        amount = float(payroll.get("gross", 0))
        if amount < 0 or not payroll.get("source"): raise ValueError("gross must be nonnegative and source required")
    except (TypeError, ValueError) as exc:
        return {"ok": False, "capability_status": "blocked", "reason": str(exc), "redacted_preview": redacted, "side_effects": [], "payroll": "not paid"}
    return {"ok": True, "capability_status": "real", "redacted_preview": redacted, "payroll_validated": True, "side_effects": [], "payroll": "not paid"}
