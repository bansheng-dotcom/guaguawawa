# -*- coding: utf-8 -*-
"""R04 独立审计探针（只读源码，仅写 workspace/tmp 临时文件）。"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.dirname(HERE)
sys.path.insert(0, AGENT)

from engines import telemetry_watchdog as tw  # noqa: E402
from skills import s06_metrics as s06  # noqa: E402
import auto_evolve_runner as aer  # noqa: E402

OUT = {"a_status": {}, "b_ids": {}, "b_chain": {}, "c_secret": {}, "d_nsm": {}, "e_state": {}}
TMP = os.path.join(HERE, "tmp")
os.makedirs(TMP, exist_ok=True)


def read_lines(p):
    with open(p, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


# ---------- a) status 是否由真实结论推导 ---------- #
class TmpTracer(tw.TelemetryTracer):
    def __init__(self, *args, **kwargs):
        kwargs["path"] = os.path.join(TMP, "audit_a.jsonl")
        super().__init__(*args, **kwargs)


tele_a = os.path.join(TMP, "audit_a.jsonl")
if os.path.exists(tele_a):
    os.remove(tele_a)
orig_tracer = tw.TelemetryTracer
tw.TelemetryTracer = TmpTracer
try:
    fake_record = {"round": 10, "layer": "L10", "ok": True, "batch": 3,
                   "completed_at": "2026-01-01T00:00:00"}
    fake_reg = {"ok": False,
                "gates": {"legacy_run_tests": {"ok": False, "rc": 1},
                          "evolution_pytest": {"ok": True, "rc": 0}}}
    aer._emit_round_telemetry(fake_record, fake_reg)
finally:
    tw.TelemetryTracer = orig_tracer
recs = read_lines(tele_a)
OUT["a_status"] = {
    "spans": [(r["name"], r["status"], r["error"]) for r in recs],
    "failing_gate_is_error": any(r["name"] == "gate.legacy_run_tests" and r["status"] == "ERROR" for r in recs),
    "passing_gate_is_ok": any(r["name"] == "gate.evolution_pytest" and r["status"] == "OK" for r in recs),
    "persist_is_error": any(r["name"] == "evolve.round.persisted" and r["status"] == "ERROR" for r in recs),
}
# 真实探针里的 self_test status 与步骤结论是否一致
st = tw.self_test(telemetry_path=os.path.join(TMP, "audit_probe.jsonl"), tmp_dir=TMP)
OUT["a_status"]["self_test_ok"] = st["ok"]
OUT["a_status"]["probe_steps"] = [(s["step"], s["ok"]) for s in st["steps"]]
OUT["a_status"]["probe_span_statuses"] = sorted({r["status"] for r in read_lines(st["telemetry_path"])})

# ---------- b) id 随机性与链路校验 ---------- #
p1 = os.path.join(TMP, "audit_b1.jsonl")
p2 = os.path.join(TMP, "audit_b2.jsonl")
for p in (p1, p2):
    if os.path.exists(p):
        os.remove(p)
t1 = tw.TelemetryTracer(path=p1)
t2 = tw.TelemetryTracer(path=p2)
r1 = t1.log("span.one")
r2 = t1.log("span.two")
r3 = t2.log("span.one")
pure_seq = hashlib.sha256(b"r07-wademing-pm:trace:1").hexdigest()[:32]
OUT["b_ids"] = {
    "trace1": r1["trace_id"], "trace2_same_tracer": r2["trace_id"],
    "trace_other_tracer": r3["trace_id"],
    "span_len": len(r1["span_id"]), "trace_len": len(r1["trace_id"]),
    "same_process_diff_trace": r1["trace_id"] != r2["trace_id"],
    "cross_process_diff_trace": r1["trace_id"] != r3["trace_id"],
    "not_pure_seq_hash": r1["trace_id"] != pure_seq,
    "hex_only": all(c in "0123456789abcdef" for c in r1["trace_id"] + r1["span_id"]),
}
# verify_chain 对 重复 span / 悬空父 / 跨 trace 父引用 的判别
base = {"schema": tw.TELEMETRY_SCHEMA, "service": "x", "name": "n", "status": "OK",
        "duration_ms": 0.1, "sha256": "a" * 64, "bytes": 1, "attributes": {},
        "error": None, "ts": 1.0}


def mk(**kw):
    rec = dict(base)
    rec.update(kw)
    return rec


def chain_of(rows):
    p = os.path.join(TMP, "audit_chain.jsonl")
    with open(p, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return tw.TelemetryTracer(path=p).verify_chain()


rows_dup = [mk(trace_id="t" * 32, span_id="s" * 16, parent_span_id=None),
            mk(trace_id="t" * 32, span_id="s" * 16, parent_span_id="s" * 16)]
rows_dangle = [mk(trace_id="t" * 32, span_id="a" * 16, parent_span_id="f" * 16)]
rows_cross = [mk(trace_id="t" * 32, span_id="p" * 16, parent_span_id=None),
              mk(trace_id="u" * 32, span_id="c" * 16, parent_span_id="p" * 16)]
OUT["b_chain"] = {
    "dup_detected": chain_of(rows_dup)["duplicate_spans"],
    "dangling_detected": bool(chain_of(rows_dangle)["dangling_parents"]),
    "cross_trace_parent_flagged": chain_of(rows_cross)["ok"],
    "cross_trace_parent_detail": chain_of(rows_cross),
}

# ---------- c) 敏感载荷 marker ---------- #
p3 = os.path.join(TMP, "audit_c.jsonl")
if os.path.exists(p3):
    os.remove(p3)
t3 = tw.TelemetryTracer(path=p3)
m1 = "R07_PAYLOAD_SECRET_" + os.urandom(6).hex()
m2 = "R07_ATTR_SECRET_" + os.urandom(6).hex()
m3 = "R07_ERROR_SECRET_" + os.urandom(6).hex()
t3.log("payload.only", payload={"secret": m1})
t3.log("attr.leak", attributes={"secret": m2})
t3.log("error.leak", error=f"BOOM {m3}")
raw = open(p3, encoding="utf-8").read()
OUT["c_secret"] = {
    "payload_marker_leaked": m1 in raw,
    "attribute_marker_leaked": m2 in raw,
    "error_marker_leaked": m3 in raw,
    "sha256_present": len(read_lines(p3)[0]["sha256"]) == 64,
}

# ---------- d) 七判据逐一失败映射 ---------- #
base_ns = {
    "north_star": "7日核心功能使用留存率",
    "input_metrics": ["周复盘完成率", "模板复用率", "邀请协作数"],
    "guardrail": ["误报率"],
    "baseline": "当前 32%",
    "target": "目标 45%",
    "data_source": "埋点 event=core_action",
}
cases = {
    "is_metric_not_activity": {"north_star": "上线支付功能"},
    "non_vanity": {"north_star": "日下载量"},
    "leading": {"north_star": "周复盘完成率"},
    "input_metrics_band": {"input_metrics": ["周复盘完成率", "模板复用率"]},
    "guardrail_present": {"guardrail": []},
    "baseline_target_defined": {"baseline": ""},
    "data_source_declared": {"data_source": " "},
}
d = {}
for dim, patch in cases.items():
    data = dict(base_ns)
    data.update(patch)
    res = s06._northstar(data)
    failed = [c["dim"] for c in res["checks"] if not c["ok"]]
    d[dim] = {"ok": res["ok"], "failed_dims": failed,
              "expected_only": failed == [dim],
              "nsm_criteria": res.get("nsm_criteria"),
              "nsm_count": len(res.get("nsm_criteria", [])),
              "nsm_required": res.get("nsm_criteria_required"),
              "msg": [c["msg"] for c in res["checks"] if not c["ok"]]}
ok_all = s06._northstar(base_ns)
d["all_pass"] = {"ok": ok_all["ok"], "nsm_count": len(ok_all.get("nsm_criteria", []))}
d["docstring_criteria"] = ["可衡量", "先导性", "可行动", "团队可控", "非虚荣",
                           "有基线与目标", "有数据源"]
d["implemented_dims"] = [c["dim"] for c in ok_all["checks"]]
# 「可衡量/可行动/团队可控」是否有独立判据：喂不可量化的 NSM 看是否被拦
loose = dict(base_ns)
loose["north_star"] = "让用户更满意"
loose["input_metrics"] = ["a", "b", "c"]
loose["data_source"] = "x"
res_loose = s06._northstar(loose)
d["unmeasurable_passes"] = {"ok": res_loose["ok"],
                            "failed": [c["dim"] for c in res_loose["checks"] if not c["ok"]]}
OUT["d_nsm"] = d

# ---------- e) 状态机 ---------- #
sp = os.path.join(HERE, "evolution_state.json")
state = json.load(open(sp, encoding="utf-8"))
rounds = [h["round"] for h in state.get("round_history", [])]
statuses = {h["round"]: h["status"] for h in state.get("round_history", [])}
OUT["e_state"] = {
    "rounds": rounds,
    "rounds_unique": len(rounds) == len(set(rounds)) == 10,
    "history_len": len(rounds),
    "completed_rounds": state.get("completed_rounds"),
    "current_round": state.get("current_round"),
    "all_passed": all(v == "PASSED" for v in statuses.values()) and len(statuses) == 10,
    "artifacts_l10": [h.get("artifacts") for h in state["round_history"] if h["round"] == 10],
}

print(json.dumps(OUT, ensure_ascii=False, indent=2))
