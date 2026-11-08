# -*- coding: utf-8 -*-
"""s02 硬门禁复核（gate）：run / audit 两动作。

口径来源：Intense-Visions__harness-engineering · harness-verify（硬门禁）
与 harness-audit-harness-strength（门禁强度 7 模式）。
- run：逐命令 subprocess 真实执行，0=PASS / 非0=FAIL / "NONE"=SKIPPED；
  全部命令都跑不短路；超时（thresholds.gate.timeout_s，可按命令覆盖）判 FAIL"TIMEOUT"；
  overall PASS iff 非 skipped 全过（全 SKIPPED 时 overall=PASS）；只记录不修复。
- audit：7 条 STRENGTH 模式在 JSON 证据上确定性判定，评分 0-100，
  error 存活即 FAIL；not evaluable 不是 pass。
阈值：thresholds.json → gate.* 与 strength.*。
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, List, Optional

from . import _common as c

NAME = "gate"
DESC = "硬门禁复核：run（逐命令真实执行、退出码是唯一信号）与 audit（STRENGTH-001..007 门禁强度审计）"

ACTIONS = {
    "run": "逐命令真实执行并记录 exit_code/stdout/stderr/elapsed_ms，零判断调用",
    "audit": "按 STRENGTH-001..007 审计门禁强度证据，出 0-100 评分与 solid/at-risk/theatre 分层",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# gate run
# --------------------------------------------------------------------------- #
def _run_one(gate: Dict[str, Any], th_gate: Dict[str, Any]) -> Dict[str, Any]:
    name = str(gate.get("name") or "unnamed-gate")
    command = str(gate.get("command") or "")
    timeout_s = gate.get("timeout_s", th_gate["timeout_s"])
    try:
        timeout_s = max(1, int(timeout_s))
    except (TypeError, ValueError):
        timeout_s = int(th_gate["timeout_s"])
    skipped_token = str(th_gate.get("skipped_command", "NONE"))
    rec: Dict[str, Any] = {"name": name, "command": command,
                           "timeout_s": timeout_s}
    if command.strip() == "" or command.strip().upper() == skipped_token.upper():
        rec.update({"status": "SKIPPED", "exit_code": None, "stdout": "",
                    "stderr": "", "elapsed_ms": 0})
        return rec
    t0 = time.time()
    # Windows 管道孤儿问题：shell=True 时管道会被孙进程持有，超时杀 cmd 后
    # communicate 仍要等管道 EOF。改用临时文件承接输出，超时即快速返回。
    out_path = os.path.join(c.agent_dir(), ".gate_out.tmp")
    err_path = os.path.join(c.agent_dir(), ".gate_err.tmp")
    timed_out = False
    exit_code: Any = None
    try:
        with open(out_path, "w", encoding="utf-8") as fo, \
                open(err_path, "w", encoding="utf-8") as fe:
            try:
                cp = subprocess.run(command, shell=True, stdout=fo, stderr=fe,
                                    timeout=timeout_s)
                exit_code = cp.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
    except OSError:
        try:
            cp = subprocess.run(command, shell=True, timeout=timeout_s)
            exit_code = cp.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    elapsed = int((time.time() - t0) * 1000)
    if timed_out:
        for p in (out_path, err_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
        rec.update({"status": "FAIL", "exit_code": None, "stdout": "",
                    "stderr": "", "elapsed_ms": elapsed,
                    "reason": "TIMEOUT", "timeout": True})
        return rec
    tail = int(th_gate.get("tail_chars", 500))
    stdout_text = ""
    stderr_text = ""
    try:
        with open(out_path, encoding="utf-8", errors="replace") as f:
            stdout_text = f.read()
    except OSError:
        pass
    try:
        with open(err_path, encoding="utf-8", errors="replace") as f:
            stderr_text = f.read()
    except OSError:
        pass
    for p in (out_path, err_path):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    rec.update({
        "status": "PASS" if exit_code == 0 else "FAIL",
        "exit_code": exit_code,
        "stdout": stdout_text[-tail:],
        "stderr": stderr_text[-tail:],
        "elapsed_ms": elapsed,
    })
    return rec


def _run_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th_gate = c.load_thresholds()["gate"]
    gates = data.get("gates") or []
    checks: List[Dict[str, Any]] = []
    records: List[Dict[str, Any]] = []
    if not gates:
        checks.append(c.ck(False, "门禁清单为空（无 gates 字段或为空数组）", "gate:run", "CRITICAL"))
    for g in gates:
        rec = _run_one(g, th_gate)
        records.append(rec)
        if rec["status"] == "SKIPPED":
            checks.append(c.ck(True, f"SKIPPED（未检出命令）：{rec['name']}",
                               f"gate:{rec['name']}", "INFO"))
        elif rec["status"] == "PASS":
            checks.append(c.ck(True, f"PASS：{rec['name']} exit_code=0 {rec['elapsed_ms']}ms",
                               f"gate:{rec['name']}"))
        elif rec.get("reason") == "TIMEOUT":
            checks.append(c.ck(False, f"FAIL：{rec['name']} TIMEOUT（>{rec['timeout_s']}s）",
                               f"gate:{rec['name']}", "CRITICAL"))
        else:
            checks.append(c.ck(False, f"FAIL：{rec['name']} exit_code={rec['exit_code']}",
                               f"gate:{rec['name']}", "CRITICAL"))
    executed = [r for r in records if r["status"] in ("PASS", "FAIL")]
    overall = "PASS" if all(r["status"] == "PASS" for r in executed) else "FAIL"
    out = c.result(checks,
                   records=records,
                   overall=overall,
                   pass_count=sum(1 for r in records if r["status"] == "PASS"),
                   fail_count=sum(1 for r in records if r["status"] == "FAIL"),
                   skipped_count=sum(1 for r in records if r["status"] == "SKIPPED"),
                   executed_count=len(executed),
                   default_timeout_s=th_gate["timeout_s"],
                   next="门禁全绿，产物可放行" if overall == "PASS" else "存在 FAIL 门禁：修复后重跑（本 Agent 只记录不修复）",
                   )
    out["ok"] = out["ok"] and overall == "PASS"
    return out


def run_gates(data: Dict[str, Any]) -> Dict[str, Any]:
    return _run_core(data)


# --------------------------------------------------------------------------- #
# gate audit：STRENGTH-001..007
# --------------------------------------------------------------------------- #
def _audit_core(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["strength"]
    patterns_cfg = th["patterns"]
    findings: List[Dict[str, Any]] = []
    checks: List[Dict[str, Any]] = []

    hooks = data.get("hooks") or []
    docs = data.get("docs") or []
    baseline = data.get("baseline")
    skip_categories = data.get("skip_categories")
    layers = data.get("layers")
    thresholds_cfg = data.get("thresholds")
    default_tier = data.get("default_tier")
    baseline_pr = data.get("baseline_update_pr")
    snapshot = data.get("snapshot")

    recognized = [x for x in (hooks, docs, baseline, skip_categories, layers,
                              thresholds_cfg, default_tier, baseline_pr, snapshot)
                  if x]
    if not recognized:
        out = c.result([c.ck(False, "证据为空或无可识别区段：not evaluable 不是 pass",
                             "gate:audit", "CRITICAL")],
                        findings=[], error_count=0, warning_count=0,
                        score=None, tier=None, verdict="NOT_EVALUABLE",
                        evaluated_patterns=[],
                        next="补齐门禁证据（hooks/docs/baseline/layers/snapshot 等）后重新 audit")
        out["ok"] = False
        return out

    # STRENGTH-001：文档/钩子声明 never blocks / always exits 0
    for holder, section in ((hooks, "hooks"), (docs, "docs")):
        for i, item in enumerate(holder or []):
            if isinstance(item, str):
                text = item
            elif isinstance(item, dict):
                text = str(item.get("text") or item.get("content") or "")
            else:
                text = ""
            if c.has_any(text.lower(), [m.lower() for m in th["never_blocks_markers"]]):
                findings.append({
                    "id": "STRENGTH-001", "pattern": patterns_cfg["STRENGTH-001"]["name"],
                    "severity": patterns_cfg["STRENGTH-001"]["severity"],
                    "evidence": f"{section}[{i}].text: {text[:80]}",
                    "remediation": patterns_cfg["STRENGTH-001"]["remediation"],
                })

    # STRENGTH-002：回归时自动更新基线
    if isinstance(baseline, dict):
        mode = str(baseline.get("auto_update") or baseline.get("update_mode") or "")
        if any(m in mode.lower() for m in th["baseline_auto_update_markers"]):
            findings.append({
                "id": "STRENGTH-002", "pattern": patterns_cfg["STRENGTH-002"]["name"],
                "severity": patterns_cfg["STRENGTH-002"]["severity"],
                "evidence": f"baseline.auto_update={baseline.get('auto_update')!r}",
                "remediation": patterns_cfg["STRENGTH-002"]["remediation"],
            })

    # STRENGTH-003：skip 类别 > 阈值 且存在无内联理由的类别
    if isinstance(skip_categories, list) and len(skip_categories) > th["skip_categories_max"]:
        unjustified = [sc for sc in skip_categories
                       if not str((sc.get("justification") if isinstance(sc, dict) else "") or "").strip()]
        if unjustified:
            names = [str((sc.get("name") if isinstance(sc, dict) else sc)) for sc in unjustified]
            findings.append({
                "id": "STRENGTH-003", "pattern": patterns_cfg["STRENGTH-003"]["name"],
                "severity": patterns_cfg["STRENGTH-003"]["severity"],
                "evidence": f"skip_categories 无 justification：{names}",
                "remediation": patterns_cfg["STRENGTH-003"]["remediation"],
            })

    # STRENGTH-004：layers 定义但无 thresholds
    if layers and not thresholds_cfg:
        findings.append({
            "id": "STRENGTH-004", "pattern": patterns_cfg["STRENGTH-004"]["name"],
            "severity": patterns_cfg["STRENGTH-004"]["severity"],
            "evidence": f"layers={layers} 但 thresholds 缺失或为空",
            "remediation": patterns_cfg["STRENGTH-004"]["remediation"],
        })

    # STRENGTH-005：默认档位设为最低档
    if default_tier is not None and str(default_tier).lower() in [t.lower() for t in th["lowest_default_tiers"]]:
        findings.append({
            "id": "STRENGTH-005", "pattern": patterns_cfg["STRENGTH-005"]["name"],
            "severity": patterns_cfg["STRENGTH-005"]["severity"],
            "evidence": f"default_tier={default_tier!r}",
            "remediation": patterns_cfg["STRENGTH-005"]["remediation"],
        })

    # STRENGTH-006：基线更新 PR 无独立评审自动批
    if isinstance(baseline_pr, dict):
        auto = bool(baseline_pr.get("auto_approve"))
        reviewers = baseline_pr.get("reviewers")
        if auto or (auto is False and not reviewers):
            findings.append({
                "id": "STRENGTH-006", "pattern": patterns_cfg["STRENGTH-006"]["name"],
                "severity": patterns_cfg["STRENGTH-006"]["severity"],
                "evidence": (f"baseline_update_pr.auto_approve={auto!r}, reviewers="
                             f"{reviewers!r}"),
                "remediation": patterns_cfg["STRENGTH-006"]["remediation"],
            })

    # STRENGTH-007：快照 passed:true 但 signals 里检查从未运行
    if isinstance(snapshot, dict) and snapshot.get("passed") is True:
        declared = list(snapshot.get("checks") or [])
        signals = snapshot.get("signals") or {}
        never_run = [chk for chk in declared if not (isinstance(signals, dict) and chk in signals)]
        for chk in never_run:
            findings.append({
                "id": "STRENGTH-007", "pattern": patterns_cfg["STRENGTH-007"]["name"],
                "severity": patterns_cfg["STRENGTH-007"]["severity"],
                "evidence": f"snapshot.passed=true 但 signals 中无检查 {chk!r} 的运行记录",
                "remediation": patterns_cfg["STRENGTH-007"]["remediation"],
            })

    # 评分与分层（确定性：起始 100，error/warning 按惩罚扣分，clamp 0..100）
    error_count = sum(1 for f in findings if f["severity"] == "error")
    warning_count = sum(1 for f in findings if f["severity"] == "warning")
    score = max(0, min(100, 100 - error_count * th["error_penalty"]
                       - warning_count * th["warning_penalty"]))
    if score >= th["solid_min"]:
        tier = "solid"
    elif score >= th["at_risk_min"]:
        tier = "at-risk"
    else:
        tier = "theatre"
    verdict = "FAIL" if error_count > 0 else "PASS"

    for f in findings:
        checks.append(c.ck(False, f"{f['id']} 命中：{f['evidence'][:60]}",
                           f"gate:{f['id']}", "CRITICAL" if f["severity"] == "error" else "HIGH"))
    evaluated = [{"pattern": pid, "triggered": any(f["id"] == pid for f in findings),
                   "severity": cfg["severity"]}
                  for pid, cfg in patterns_cfg.items()]
    checks.append(c.ck(verdict == "PASS",
                       f"评分 {score}（{tier}），error={error_count} warning={warning_count}",
                       "gate:score", "OK" if verdict == "PASS" else "CRITICAL"))
    out = c.result(checks,
                   findings=findings,
                   error_count=error_count,
                   warning_count=warning_count,
                   score=score,
                   tier=tier,
                   verdict=verdict,
                   evaluated_patterns=evaluated,
                   next="门禁强度达标，可继续放行" if verdict == "PASS"
                        else "error 存活即 FAIL：按 remediation 修复门禁本体后重新 audit",
                   )
    out["ok"] = out["ok"] and verdict == "PASS"
    return out


def audit(data: Dict[str, Any]) -> Dict[str, Any]:
    return _audit_core(data)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "run":
        return run_gates(data)
    if args.action == "audit":
        return audit(data)
    raise SystemExit(f"未知动作：{args.action}")
