# -*- coding: utf-8 -*-
import json
import os

w = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团\r07-wademing-pm\workspace"
recs = [json.loads(l) for l in open(os.path.join(w, "telemetry.jsonl"), encoding="utf-8") if l.strip()]
req = ("schema", "trace_id", "span_id", "name", "status", "duration_ms", "sha256", "ts")
print("lines", len(recs))
print("missing_keys", [(i, [k for k in req if k not in r]) for i, r in enumerate(recs) if any(k not in r for k in req)])
print("lens", sorted({(len(r["trace_id"]), len(r["span_id"]), len(r["sha256"])) for r in recs}))
print("statuses", {r["status"] for r in recs})
byid = {r["span_id"]: r for r in recs}
print("parent_same_trace", all(byid[r["parent_span_id"]]["trace_id"] == r["trace_id"] for r in recs if r["parent_span_id"]))
print("dup_spans", len(recs) != len({r["span_id"] for r in recs}))
print("traces", sorted({r["trace_id"] for r in recs}))
print("names", [r["name"] for r in recs])
print("any_payload_field", any("payload" in r for r in recs))
st = json.load(open(os.path.join(w, "evolution_state.json"), encoding="utf-8"))
print("history", [(h["round"], h["status"]) for h in st["round_history"]])
print("unique", len({h["round"] for h in st["round_history"]}) == len(st["round_history"]) == 10)
prev = json.load(open(os.path.join(w, "tmp", "state_before_r10.json"), encoding="utf-8"))
print("prev_rounds", [h["round"] for h in prev["round_history"]])
print("round10_before", [h["completed_at"] for h in prev["round_history"] if h["round"] == 10])
print("round10_after ", [h["completed_at"] for h in st["round_history"] if h["round"] == 10])
print("unchanged_1_9", [h for h in prev["round_history"] if h["round"] < 10] == [h for h in st["round_history"] if h["round"] < 10])
print("l10_artifacts", [h["artifacts"] for h in st["round_history"] if h["round"] == 10])
print("state_size", os.path.getsize(os.path.join(w, "evolution_state.json")))
print("tele_size", os.path.getsize(os.path.join(w, "telemetry.jsonl")))
