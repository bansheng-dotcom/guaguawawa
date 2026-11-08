"""Local workflow schema, mapping, and retry dry-run; never calls n8n."""

def execute(data):
    if not isinstance(data, dict): return {"ok": False, "capability_status": "blocked", "reason": "workflow must be object", "side_effects": []}
    if data.get("call_n8n") or data.get("execute_external"): return {"ok": False, "capability_status": "blocked", "reason": "n8n/external execution unavailable", "side_effects": []}
    nodes, fields = data.get("nodes", []), data.get("fields", {})
    if not fields and data.get("nodes"):
        fields = data.get("field_mapping", {})
    if not fields:
        fields = {"node": [n.get("name") for n in nodes if isinstance(n, dict)]}
    if not isinstance(nodes, list) or not nodes or not isinstance(fields, dict): return {"ok": False, "capability_status": "blocked", "reason": "nodes and fields schema required", "side_effects": []}
    names = [n.get("name") for n in nodes if isinstance(n, dict)]
    if len(names) != len(set(names)) or any(not n for n in names): return {"ok": False, "capability_status": "blocked", "reason": "invalid/duplicate node names", "side_effects": []}
    attempts = int(data.get("max_retries", 0))
    if attempts < 0 or attempts > 5: return {"ok": False, "capability_status": "blocked", "reason": "retry must be 0..5", "side_effects": []}
    return {"ok": True, "capability_status": "simulated", "schema_valid": True, "field_mapping_count": len(fields), "retry_policy": {"max_retries": attempts, "dry_run": True}, "external_calls": 0, "side_effects": []}
