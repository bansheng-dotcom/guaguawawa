"""Local inventory ledger and conservation checks; no ERP mutation."""
import csv, json

def execute(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f)) if path.lower().endswith(".csv") else json.load(f)
        if isinstance(rows, dict): rows = rows.get("entries", rows.get("bins", []))
        if not isinstance(rows, list) or not rows: raise ValueError("empty ledger")
        balance = {}
        for row in rows:
            sku = str(row.get("sku", row.get("item_code", ""))).strip()
            qty = row.get("qty", row.get("quantity", row.get("actual_qty", row.get("projected_qty"))))
            if qty is None: raise ValueError("missing sku or quantity")
            qty = float(qty)
            if not sku or qty == 0: raise ValueError("missing sku or zero quantity")
            balance[sku] = round(balance.get(sku, 0) + qty, 6)
        if any(v < 0 for v in balance.values()): raise ValueError("negative conserved balance")
        return {"ok": True, "capability_status": "real", "ledger_rows": len(rows), "balances": balance, "conservation_checked": True, "side_effects": []}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"ok": False, "capability_status": "blocked", "reason": str(exc), "side_effects": []}
