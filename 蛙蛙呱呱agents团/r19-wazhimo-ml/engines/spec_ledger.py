# -*- coding: utf-8 -*-
"""L04 领域账本层 —— ML_SPEC.md 单一信任源 + 8 维发布硬门禁。

SOP v13.0 L04 体检病灶（R19 真实断点）：
    1. 8 个门禁的阈值与白名单散落在 `experience/thresholds.json`、7 个 skill、
       `review.py` 与 `contracts.py` 里，口径三处各写一遍，改一处漏两处；
    2. 没有「发布门禁」这一层概念：证据链、回归、资产溯源、阶段唯一性
       只是零散 checks，无法整体回答「这份工件到底能不能放行」；
    3. 无单一信任源，也没有账本指纹，审计时无法证明「当时用的是哪版口径」。

对标开源标杆（Stars > 1k）：
    * dbt-labs/dbt-semantic-layer (>10k) —— 指标定义单一信任源
    * mlflow/mlflow (>20k) Model Registry —— stage 唯一性与证据链
    * OASIS SARIF v2.1.0 —— 机器可消费的审计结果格式

落地的最低 3 项架构升级：
    1. 账本动态加载 + SHA256 指纹（改口径要留痕）；
    2. 8 维发布硬门禁统一裁决 `verify_gate_compliance()`（唯一出入口）；
    3. 账本一键导出为下游可消费的 `ml_gates.json` 与门禁矩阵 Markdown。

用法：
    python -m engines.spec_ledger --out workspace/rounds/L04_spec.json \
        --export-dir workspace/bundles
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SPEC_FILE = os.path.join(_ROLE, "ML_SPEC.md")

_NORTH_STAR: Dict[str, Dict[str, str]] = {
    "ERA": {"name": "评估可复算率", "target": "100.0%",
            "formula": "confusion(tp+fp+tn+fn)=n 且 accuracy=(tp+tn)/n，容差 0.00"},
    "GGR": {"name": "回归门禁通过率", "target": "100.0%",
            "formula": "PASS ⇒ regression_id ∧ fail_before ∧ pass_after ∧ existing_green"},
    "ATR": {"name": "资产可溯源率", "target": "100.0%",
            "formula": "assets[].path ∧ run_id ∧ sha256"},
    "CLR": {"name": "凭据零泄露率", "target": "100.0%", "formula": "credential_hits = 0"},
    "BTA": {"name": "勾稽容差绝对值", "target": "0.00", "formula": "|delta| <= 1e-9"},
}

_GATES: Dict[str, Dict[str, str]] = {
    "GATE-01": {"name": "评估指标可复算门禁", "dim": "metric_recomputability",
                "threshold": "记录含 expected/predicted 且混淆计数守恒", "action": "评估报告作废"},
    "GATE-02": {"name": "证据链完整门禁", "dim": "evidence_chain",
                "threshold": "verdict=PASS ⇒ evidence ≥ 1", "action": "降级 NEEDS_REVIEW"},
    "GATE-03": {"name": "回归门禁", "dim": "regression",
                "threshold": "PASS ⇒ regression_id + fail_before/pass_after/existing_green",
                "action": "退回补回归"},
    "GATE-04": {"name": "资产可溯源门禁", "dim": "artifact_traceability",
                "threshold": "path 非空 + run_id 绑定 + sha256 可校验", "action": "禁止入库"},
    "GATE-05": {"name": "凭据零泄露门禁", "dim": "credential_zero",
                "threshold": "凭据词命中数 = 0", "action": "退回密钥管理"},
    "GATE-06": {"name": "阶段唯一性门禁", "dim": "stage_uniqueness",
                "threshold": "production 版本数 ≤ 1", "action": "回滚多余版本"},
    "GATE-07": {"name": "枚举合规门禁", "dim": "enum_compliance",
                "threshold": "verdict/stage/risk_tier/license 白名单", "action": "按白名单归一"},
    "GATE-08": {"name": "越权移交门禁", "dim": "publication_handoff",
                "threshold": "发布动作声明 handoff / authorized_by", "action": "[REDLINE BLOCKED]"},
}

_ENUMS: Dict[str, List[str]] = {
    "stage": ["none", "staging", "production", "archived"],
    "verdict": ["PASS", "BLOCK", "NEEDS_REVIEW"],
    "risk_tier": ["low", "medium", "high"],
    "license": ["proprietary", "open_source", "research_only"],
    "feedback_source": ["HUMAN", "LLM_JUDGE", "CODE", "WEBHOOK"],
}

_CRED_WORDS = ["api_key", "apikey", "secret", "password", "token", "private_key",
               "私钥", "密钥", "密码", "连接串", "connection_string", "client_secret"]


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_spec_md(text: str) -> Tuple[List[str], List[str]]:
    kpis = re.findall(r"\|\s*\*\*([A-Z]{2,6})\*\*\s*\|", text)
    gates = re.findall(r"\|\s*\*\*(GATE-\d{2})\*\*\s*\|", text)
    dedup = lambda xs: list(dict.fromkeys(xs))  # noqa: E731
    return dedup(kpis), dedup(gates)


def _iter_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("checks", "msg", "dim"):
                continue
            yield from _iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_strings(v)


class R19SpecLedger:
    """ML_SPEC.md 账本加载器 + 8 维发布硬门禁裁决器。"""

    ENGINE = "R19SpecLedger"
    LAYER = "L04"
    CAPABILITIES = [
        "ML_SPEC.md 动态加载 + SHA256 账本指纹 + KPI/门禁完整性校验",
        "8 维发布硬门禁统一裁决 (verify_gate_compliance) 与违规定位",
        "账本一键导出 ml_gates.json / ml_gate_matrix.md 供下游机器消费",
        "[C2] 账本版本差量 diff (门禁/KPI 增删改 + 阈值变更影响面)",
        "[C2] 账本自洽 Lint (重复门禁/空阈值/口径漂移/指纹缺失)",
    ]

    def __init__(self, spec_path: Optional[str] = None):
        self.spec_path = spec_path or SPEC_FILE

    # ------------------------------------------------------------------ #
    # 1. 加载账本
    # ------------------------------------------------------------------ #
    def load_spec(self) -> Dict[str, Any]:
        kpis, gate_ids = [], []
        text, spec_hash = "", ""
        parse_ok = False
        if os.path.exists(self.spec_path):
            with open(self.spec_path, encoding="utf-8") as f:
                text = f.read()
            spec_hash = _sha256_file(self.spec_path)
            kpis, gate_ids = _parse_spec_md(text)
            parse_ok = (len(gate_ids) >= 8 and len(kpis) >= 5)
        # 解析失败时退回内置账本（不静默：parse_ok=false 会被门禁记录）
        kpi_codes = [k for k in kpis if k in _NORTH_STAR] or list(_NORTH_STAR)
        gate_list = [g for g in gate_ids if g in _GATES] or list(_GATES)
        north_star = {code: dict(_NORTH_STAR[code]) for code in kpi_codes}
        gates = {gid: dict(_GATES[gid]) for gid in sorted(gate_list)}
        missing = [g for g in _GATES if g not in gates]
        return {
            "role": "R19 蛙智模 · 模型工程与 AI 评估官",
            "version": "v13.0",
            "source": os.path.relpath(self.spec_path, _ROLE) if spec_hash else "(内置)",
            "spec_hash": spec_hash,
            "parse_ok": parse_ok,
            "gates_count": len(gates),
            "north_star_kpis": north_star,
            "kpi_codes": list(north_star),
            "gates": gates,
            "gate_ids": list(gates),
            "missing_gates": missing,
            "enums": {k: list(v) for k, v in _ENUMS.items()},
        }

    # ------------------------------------------------------------------ #
    # 1b. [Cycle 2] 账本版本差量
    # ------------------------------------------------------------------ #
    def diff_snapshots(self, old_spec: Dict[str, Any],
                       new_spec: Dict[str, Any]) -> Dict[str, Any]:
        old_spec = old_spec or {}
        new_spec = new_spec or {}
        old_gates = old_spec.get("gates") or {}
        new_gates = new_spec.get("gates") or {}
        added = sorted(set(new_gates) - set(old_gates))
        removed = sorted(set(old_gates) - set(new_gates))
        changed: List[Dict[str, Any]] = []
        for gid in sorted(set(old_gates) & set(new_gates)):
            fields = {}
            for key in ("name", "dim", "threshold", "action"):
                before = (old_gates[gid] or {}).get(key)
                after = (new_gates[gid] or {}).get(key)
                if before != after:
                    fields[key] = {"old": before, "new": after}
            if fields:
                changed.append({"gate": gid, "fields": fields,
                                "breaking": "threshold" in fields})
        old_kpis = old_spec.get("north_star_kpis") or {}
        new_kpis = new_spec.get("north_star_kpis") or {}
        kpi_added = sorted(set(new_kpis) - set(old_kpis))
        kpi_removed = sorted(set(old_kpis) - set(new_kpis))
        kpi_changed = []
        for code in sorted(set(old_kpis) & set(new_kpis)):
            fields = {}
            for key in ("name", "target", "formula"):
                before = (old_kpis[code] or {}).get(key)
                after = (new_kpis[code] or {}).get(key)
                if before != after:
                    fields[key] = {"old": before, "new": after}
            if fields:
                kpi_changed.append({"kpi": code, "fields": fields})
        hash_changed = (old_spec.get("spec_hash") != new_spec.get("spec_hash"))
        impact = ("NO_CHANGE" if not (added or removed or changed or kpi_added
                                      or kpi_removed or kpi_changed) else
                  "BREAKING" if (removed or any(c["breaking"] for c in changed))
                  else "COMPATIBLE")
        return {"ok": True, "gates_added": added, "gates_removed": removed,
                "gates_changed": changed, "kpi_added": kpi_added,
                "kpi_removed": kpi_removed, "kpi_changed": kpi_changed,
                "spec_hash_changed": hash_changed, "impact": impact,
                "change_count": len(added) + len(removed) + len(changed)
                                + len(kpi_added) + len(kpi_removed) + len(kpi_changed)}

    # ------------------------------------------------------------------ #
    # 1c. [Cycle 2] 账本自洽 Lint（含与内置账本的口径漂移）
    # ------------------------------------------------------------------ #
    def lint_spec(self, spec: Optional[Dict[str, Any]] = None,
                  raw_text: Optional[str] = None) -> Dict[str, Any]:
        spec = spec or self.load_spec()
        if raw_text is None and os.path.exists(self.spec_path):
            with open(self.spec_path, encoding="utf-8") as f:
                raw_text = f.read()
        raw_text = raw_text or ""
        findings: List[Dict[str, Any]] = []
        gate_ids = [g.strip() for g in (spec.get("gate_ids") or [])]
        dup = sorted({g for g in gate_ids if gate_ids.count(g) > 1})
        for gid in dup:
            findings.append({"code": "DUPLICATE_GATE", "sev": "BLOCKER",
                             "detail": f"{gid} 重复登记 {gate_ids.count(gid)} 次"})
        md_ids = re.findall(r"(GATE-\d+)", raw_text)
        md_dup = sorted({g for g in md_ids if md_ids.count(g) > 1})
        for gid in md_dup:
            findings.append({"code": "DUPLICATE_GATE_MD", "sev": "BLOCKER",
                             "detail": f"ML_SPEC.md 中 {gid} 出现 {md_ids.count(gid)} 次"})
        for gid, gate in (spec.get("gates") or {}).items():
            if not str(gate.get("threshold", "")).strip():
                findings.append({"code": "EMPTY_THRESHOLD", "sev": "BLOCKER",
                                 "detail": f"{gid} 阈值为空，门禁不可裁决"})
        for code, kpi in (spec.get("north_star_kpis") or {}).items():
            if not str(kpi.get("formula", "")).strip():
                findings.append({"code": "EMPTY_FORMULA", "sev": "HIGH",
                                 "detail": f"KPI {code} 缺少公式，不可复算"})
        if not spec.get("spec_hash"):
            findings.append({"code": "MISSING_SPEC_HASH", "sev": "HIGH",
                             "detail": "账本缺少 SHA256 指纹，来源不可追溯"})
        if not spec.get("parse_ok"):
            findings.append({"code": "SPEC_FALLBACK", "sev": "HIGH",
                             "detail": "ML_SPEC.md 解析失败，已退回内置账本"})
        missing = [g for g in _GATES if g not in (spec.get("gates") or {})]
        if missing:
            findings.append({"code": "MISSING_GATES", "sev": "HIGH",
                             "detail": f"缺少内置门禁 {missing}"})
        drift = []
        for gid, gate in (spec.get("gates") or {}).items():
            builtin = _GATES.get(gid)
            if builtin and str(builtin.get("threshold")) != str(gate.get("threshold")):
                drift.append({"gate": gid, "builtin": builtin.get("threshold"),
                              "current": gate.get("threshold")})
        if drift:
            findings.append({"code": "THRESHOLD_DRIFT", "sev": "MEDIUM",
                             "detail": f"{len(drift)} 个门禁阈值偏离内置口径",
                             "items": drift})
        blockers = sum(1 for f in findings if f["sev"] == "BLOCKER")
        return {"ok": blockers == 0, "findings": findings,
                "blockers": blockers, "warnings": len(findings) - blockers,
                "gate_count": len(gate_ids), "kpi_count": len(spec.get("north_star_kpis") or {})}

    # ------------------------------------------------------------------ #
    # 2. 8 维门禁裁决
    # ------------------------------------------------------------------ #
    def verify_gate_compliance(self, artifact_type: str,
                               data: Dict[str, Any]) -> Dict[str, Any]:
        data = data or {}
        checks: List[Dict[str, Any]] = []
        violations: List[Dict[str, Any]] = []

        def gate(gid: str, ok: Optional[bool], msg: str, sev: str = "BLOCKER") -> None:
            skipped = ok is None
            rec = {"gate": gid, "ok": bool(ok) if not skipped else True,
                   "skipped": skipped, "msg": msg, "sev": "OK" if (skipped or ok) else sev}
            checks.append(rec)
            if not skipped and not ok:
                violations.append({"gate": gid, "msg": msg, "sev": sev})

        # GATE-01 指标可复算
        records = data.get("records") if isinstance(data.get("records"), list) else None
        if records is not None:
            bad = [i for i, r in enumerate(records)
                   if not isinstance(r, dict)
                   or r.get("expected") is None or r.get("predicted") is None]
            gate("GATE-01", not bad,
                 f"评估记录 {len(records)} 条，expected/predicted 齐备"
                 if not bad else f"{len(bad)} 条记录缺 expected/predicted（索引 {bad[:5]}）")
        elif isinstance(data.get("metrics"), dict) and data["metrics"].get("confusion"):
            conf = data["metrics"]["confusion"]
            lhs = sum(int(conf.get(k, 0)) for k in ("tp", "fp", "tn", "fn"))
            n = int(data["metrics"].get("n", lhs))
            gate("GATE-01", lhs == n, f"混淆计数守恒 {lhs} == {n}（容差 0.00）")
        else:
            gate("GATE-01", None, "工件不含评估记录/指标，跳过")

        verdict = str(data.get("verdict", "")).upper()
        # GATE-02 证据链
        if verdict == "PASS":
            ev = data.get("evidence") or []
            gate("GATE-02", isinstance(ev, list) and len(ev) >= 1,
                 f"PASS 证据数 {len(ev) if isinstance(ev, list) else 0} ≥ 1")
        else:
            gate("GATE-02", None, "非 PASS 裁决，证据链非强制")

        # GATE-03 回归门禁
        if verdict == "PASS":
            ok_reg = (bool(str(data.get("regression_id", "")).strip())
                      and data.get("fail_before") is True
                      and data.get("pass_after") is True
                      and data.get("existing_green") is True)
            gate("GATE-03", ok_reg,
                 "PASS 挂回归且 fail-before/pass-after/existing-green 齐备"
                 if ok_reg else "PASS 缺回归报告或回归三证据不全")
        else:
            gate("GATE-03", None, "非 PASS 裁决，回归非强制")

        # GATE-04 资产可溯源
        assets = data.get("assets")
        if isinstance(assets, list):
            bad_assets = [i for i, a in enumerate(assets)
                          if not isinstance(a, dict)
                          or not str(a.get("path", "")).strip()
                          or not str(a.get("run_id", "")).strip()]
            gate("GATE-04", not bad_assets,
                 f"资产 {len(assets)} 个，path+run_id 齐备"
                 if not bad_assets else f"{len(bad_assets)} 个资产不可溯源（索引 {bad_assets[:5]}）")
        else:
            gate("GATE-04", None, "工件不含资产清单，跳过")

        # GATE-05 凭据零泄露
        blob = " ".join(_iter_strings(data))
        hits = sorted({w for w in _CRED_WORDS if w in blob})
        gate("GATE-05", not hits,
             "凭据词命中 0" if not hits else f"检出凭据词 {hits}", sev="CRITICAL")

        # GATE-06 阶段唯一性
        versions = data.get("versions")
        if isinstance(versions, list):
            prod = [v for v in versions if isinstance(v, dict)
                    and str(v.get("stage", "")).lower() == "production"]
            gate("GATE-06", len(prod) <= 1, f"production 版本数 {len(prod)} ≤ 1")
        else:
            stage = str(data.get("stage", "")).lower()
            gate("GATE-06", None if not stage else stage in _ENUMS["stage"],
                 f"stage={stage!r} 在白名单" if stage else "无 stage 字段，跳过")

        # GATE-07 枚举合规
        bad_enums: List[str] = []
        for field, allowed in _ENUMS.items():
            if field in data and isinstance(data[field], str) and data[field]:
                if data[field] not in allowed:
                    bad_enums.append(f"{field}={data[field]!r}")
        gate("GATE-07", not bad_enums,
             "枚举全部合规" if not bad_enums else f"枚举越界 {bad_enums}")

        # GATE-08 越权移交
        publish = bool(data.get("publish") or data.get("publication")
                       or artifact_type in ("publication", "release", "deploy"))
        if publish:
            declared = any(k in data for k in ("handoff", "authorized_by", "approved_by"))
            gate("GATE-08", declared,
                 "发布动作已声明 handoff/authorized_by" if declared
                 else "发布动作缺 handoff/authorized_by 授权声明", sev="CRITICAL")
        else:
            gate("GATE-08", None, "非发布动作，移交门禁跳过")

        evaluated = [c for c in checks if not c["skipped"]]
        compliant = not violations
        return {
            "ok": compliant,
            "engine": self.ENGINE, "layer": self.LAYER,
            "artifact_type": artifact_type,
            "compliant": compliant,
            "violations": violations,
            "violations_count": len(violations),
            "checks": checks,
            "gates_evaluated": len(evaluated),
            "gates_total": len(_GATES),
            "grade": "PASS" if compliant else (
                "FAIL" if any(v["sev"] == "CRITICAL" for v in violations) else "WARN"),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    # ------------------------------------------------------------------ #
    # 3. 导出
    # ------------------------------------------------------------------ #
    def render_gate_matrix(self, spec: Optional[Dict[str, Any]] = None) -> str:
        spec = spec or self.load_spec()
        lines = ["# R19 八维发布硬门禁矩阵", "",
                 f"- 账本：{spec['source']} | SHA256：`{spec['spec_hash'][:16]}…` | "
                 f"门禁数：{spec['gates_count']}", "",
                 "| 门禁 | 名称 | 刚性标准 | 破坏处置 |", "| :--- | :--- | :--- | :--- |"]
        for gid, g in spec["gates"].items():
            lines.append(f"| **{gid}** | {g['name']} | {g['threshold']} | {g['action']} |")
        lines += ["", "## 北极星 KPI", "", "| 代号 | 名称 | 目标 | 口径 |",
                  "| :--- | :--- | ---: | :--- |"]
        for code, k in spec["north_star_kpis"].items():
            lines.append(f"| **{code}** | {k['name']} | {k['target']} | {k['formula']} |")
        lines.append("")
        return "\n".join(lines)

    def export_gates(self, out_dir: str) -> Dict[str, Any]:
        spec = self.load_spec()
        os.makedirs(out_dir, exist_ok=True)
        json_path = os.path.join(out_dir, "ml_gates.json")
        md_path = os.path.join(out_dir, "ml_gate_matrix.md")
        payload = {"schema": "r19.ml_gates.v1", "spec": spec,
                   "exported_at": datetime.datetime.now().isoformat(timespec="seconds")}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.render_gate_matrix(spec))
        return {"ok": True, "json": json_path, "markdown": md_path,
                "bytes": os.path.getsize(json_path),
                "sha256": _sha256_file(json_path)}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L04 领域账本与 8 维门禁")
    ap.add_argument("--out", default=None, help="账本快照输出")
    ap.add_argument("--export-dir", default=None, help="导出 ml_gates.json 的目录")
    ap.add_argument("--artifact", default=None, help="待裁决工件 JSON")
    ap.add_argument("--artifact-type", default="general")
    args = ap.parse_args(argv)

    ledger = R19SpecLedger()
    spec = ledger.load_spec()
    out: Dict[str, Any] = {"ok": spec["gates_count"] == 8 and bool(spec["north_star_kpis"]),
                           "engine": ledger.ENGINE, "layer": ledger.LAYER,
                           "spec": spec, "capabilities": list(ledger.CAPABILITIES)}
    if args.export_dir:
        out["export"] = ledger.export_gates(args.export_dir)
    if args.artifact and os.path.exists(args.artifact):
        with open(args.artifact, encoding="utf-8-sig") as f:
            data = json.load(f)
        out["compliance"] = ledger.verify_gate_compliance(args.artifact_type, data)
        out["ok"] = out["ok"] and out["compliance"]["ok"]
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "gates": spec["gates_count"],
                      "kpis": len(spec["north_star_kpis"]),
                      "spec_hash": spec["spec_hash"][:12],
                      "export": out.get("export", {}).get("json"),
                      "out": args.out}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
