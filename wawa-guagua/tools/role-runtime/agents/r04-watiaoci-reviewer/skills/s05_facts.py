# -*- coding: utf-8 -*-
"""s05 事实与来源检查（facts）：check / trace 两动作。

口径：R04 独立评审五维事实核查（溯源 human-review/fact-check 域）。
- check：①数字可追溯（claim 的数字须在 source 中找到，找不到=hallucinated，critical）
  ②来源质量（source_type 白名单，unsourced 即 violation）
  ③引用完整性（有 source）
  ④数字精度一致（claim 与 source 逐字相等，不许四舍五入漂移；原始串找不到但压缩后能对上=drift）
  ⑤覆盖（key_assertions 必须能在 source 中定位）。
- trace：单数字逐个回溯到 source 文本。
阈值：thresholds.json → facts.*。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import _common as c

NAME = "facts"
DESC = "事实与来源检查：check（五维核查：可追溯/来源质量/引用/精度/覆盖）与 trace（单数字回溯）"

ACTIONS = {
    "check": "五维事实核查：可追溯/来源质量/引用完整性/精度一致/覆盖",
    "trace": "单数字逐个回溯 source 文本，找原始片段",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    ap = act.add_parser("check", help=ACTIONS["check"])
    ap.add_argument("--input", required=True)
    ap = act.add_parser("trace", help=ACTIONS["trace"])
    ap.add_argument("--input", required=True, help="numbers JSON（numbers: []）")
    ap.add_argument("--text", required=True, help="source 文本文件路径或字面文本")


# --------------------------------------------------------------------------- #
# 数字回溯原语（trace 与 check 共用）
# --------------------------------------------------------------------------- #
def _compress(s: str) -> str:
    """去掉空格/千分位逗号，保留其余字符（含 %、小数点）。"""
    return s.replace(" ", "").replace(",", "").replace("，", "")


def _trace_one(number: str, source: str) -> Dict[str, Any]:
    raw = str(number)
    raw_found = raw in source
    compressed_found = _compress(raw) in _compress(source)
    if raw_found:
        idx = source.find(raw)
        status = "verified"
    elif compressed_found:
        idx = _compress(source).find(_compress(raw))
        status = "drift"
    else:
        idx = -1
        status = "hallucinated"
    snippet = ""
    if idx >= 0:
        start = max(0, idx - 20)
        end = min(len(source), idx + len(raw) + 20)
        snippet = source[start:end]
    return {"number": raw, "status": status,
            "found_raw": raw_found, "found_compressed": compressed_found,
            "source_snippet": snippet}


def _load_text_arg(text_arg: str) -> str:
    """--text 优先按文件路径读，读不到按字面文本。"""
    if text_arg:
        try:
            with open(text_arg, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return text_arg
    return ""


# --------------------------------------------------------------------------- #
# trace
# --------------------------------------------------------------------------- #
def _trace_core(data: Dict[str, Any], source: str) -> Dict[str, Any]:
    numbers = [str(n) for n in (data.get("numbers") or [])]
    checks: List[Dict[str, Any]] = []
    if not numbers:
        checks.append(c.ck(False, "numbers 为空，无数字可回溯", "facts:trace", "CRITICAL"))
    traces = [_trace_one(n, source) for n in numbers]
    verified = sum(1 for t in traces if t["status"] == "verified")
    drift = sum(1 for t in traces if t["status"] == "drift")
    hallucinated = sum(1 for t in traces if t["status"] == "hallucinated")
    for t in traces:
        if t["status"] == "verified":
            checks.append(c.ck(True, f"{t['number']} verified：…{t['source_snippet'][:40]}…",
                               f"facts:trace:{t['number']}"))
        elif t["status"] == "drift":
            checks.append(c.ck(False, f"{t['number']} 精度漂移：source 中逐字形式不一致",
                               f"facts:trace:{t['number']}", "HIGH"))
        else:
            checks.append(c.ck(False, f"{t['number']} hallucinated：source 中找不到",
                               f"facts:trace:{t['number']}", "CRITICAL"))
    out = c.result(checks,
                   traces=traces,
                   total=len(traces), verified_count=verified,
                   drift_count=drift, hallucinated_count=hallucinated,
                   verdict="PASS" if hallucinated == 0 and drift == 0 else "FAIL",
                   next="数字全部可回溯" if hallucinated == 0 and drift == 0
                        else "不可回溯数字须回生产方改口或补 source",
                   )
    out["ok"] = out["ok"] and hallucinated == 0 and drift == 0
    return out


def trace(data: Dict[str, Any], source: str) -> Dict[str, Any]:
    return _trace_core(data, source)


# --------------------------------------------------------------------------- #
# check：五维
# --------------------------------------------------------------------------- #
def _check_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["facts"]
    sev_map = th["severities"]
    blocking = set(th["blocking_severities"])
    whitelist = th["source_type_whitelist"]
    facts = data.get("facts") or []
    checks: List[Dict[str, Any]] = []
    if not facts:
        checks.append(c.ck(False, "facts 为空，无事实可核查", "facts:check", "CRITICAL"))

    dims: Dict[str, Dict[str, Any]] = {
        "traceability": {"violations": [], "checked": 0},
        "source_quality": {"violations": [], "checked": 0},
        "citation": {"violations": [], "checked": 0},
        "precision": {"violations": [], "checked": 0},
        "coverage": {"violations": [], "checked": 0},
    }

    def viol(dim: str, fact_id: str, rule: str, detail: str, sev_key: str) -> None:
        dims[dim]["violations"].append({
            "fact_id": fact_id, "rule": rule, "detail": detail,
            "severity": sev_map[sev_key]})

    for fact in facts:
        fid = str(fact.get("id") or "")
        claim = str(fact.get("claim") or "")
        numbers = [str(n) for n in (fact.get("numbers") or [])]
        source = str(fact.get("source") or "")
        source_type = str(fact.get("source_type") or "")
        key_assertions = [str(a) for a in (fact.get("key_assertions") or [])]

        # ③ 引用完整性
        dims["citation"]["checked"] += 1
        if not source.strip():
            viol("citation", fid, "citation_missing", "claim 无任何 source 引用",
                 "citation_missing")
        # ② 来源质量
        dims["source_quality"]["checked"] += 1
        if source_type not in whitelist:
            viol("source_quality", fid, "invalid_source_type",
                 f"source_type {source_type!r} 不在白名单", "invalid_source_type")
        elif source_type == "unsourced":
            viol("source_quality", fid, "unsourced",
                 "source_type=unsourced：事实无来源背书", "unsourced")
        # ① 数字可追溯 + ④ 精度一致（逐字）
        for n in numbers:
            t = _trace_one(n, source)
            dims["traceability"]["checked"] += 1
            if t["status"] == "hallucinated":
                viol("traceability", fid, "hallucinated",
                     f"数字 {n!r} 在 source 中找不到（幻觉数字）", "hallucinated")
            dims["precision"]["checked"] += 1
            if t["status"] == "drift":
                viol("precision", fid, "precision_drift",
                     f"数字 {n!r} 逐字形式与 source 不一致（格式/舍入漂移）",
                     "precision_drift")
        # ⑤ 覆盖
        for a in key_assertions:
            dims["coverage"]["checked"] += 1
            if a not in source:
                viol("coverage", fid, "coverage_gap",
                     f"关键断言 {a!r} 无法在 source 中定位", "coverage_gap")

    all_violations: List[Dict[str, Any]] = []
    for d in dims.values():
        all_violations.extend(d["violations"])
    blocking_violations = [v for v in all_violations if v["severity"] in blocking]
    warn_violations = [v for v in all_violations if v["severity"] not in blocking]

    for v in all_violations:
        sev = "CRITICAL" if v["severity"] in ("critical",) else ("HIGH" if v["severity"] in blocking else "INFO")
        checks.append(c.ck(False, f"{v['fact_id']} {v['rule']}：{v['detail']}",
                           f"facts:{v['rule']}", sev, **{"fact_id": v["fact_id"]}))
    checked_total = sum(d["checked"] for d in dims.values())
    if facts and checked_total > 0 and not all_violations:
        checks.append(c.ck(True, f"五维全过（{len(facts)} 条事实，{checked_total} 项核查）",
                           "facts:check"))
    elif facts and checked_total == 0:
        checks.append(c.ck(False, "五维核查零覆盖：facts 既无数字也无来源可查", "facts:check", "CRITICAL"))

    verdict = "FAIL" if blocking_violations else "PASS"
    out = c.result(checks,
                   dimension_results=dims,
                   violations=all_violations,
                   violation_count=len(all_violations),
                   blocking_count=len(blocking_violations),
                   warn_count=len(warn_violations),
                   verdict=verdict,
                   next="事实链干净" if verdict == "PASS"
                        else "存在 critical/high 级事实违例：打回生产方修正数字或补来源",
                   )
    out["ok"] = out["ok"] and verdict == "PASS"
    return out


def check(data: Dict[str, Any]) -> Dict[str, Any]:
    return _check_core(data)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "check":
        return check(data)
    if args.action == "trace":
        source = _load_text_arg(args.text)
        return trace(data, source)
    raise SystemExit(f"未知动作：{args.action}")
