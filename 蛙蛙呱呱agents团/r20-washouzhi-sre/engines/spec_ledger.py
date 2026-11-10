# -*- coding: utf-8 -*-
"""L04 领域账本层 —— SRE_SPEC.md 单一信任源 + 8 维发布硬门禁。

SOP v13.0 L04 体检病灶（R20 真实断点）：
    可用率阈值 0.999、RTO 4h、RPO 1h、MTTR 30min、快照数下限、升级链上限
    分别散落在 `skills/*.py`、`experience/thresholds.json`、`review.py` 与
    `contracts.py` 里，同一口径最多写四遍；没有「发布门禁」概念，也没有
    账本指纹，无法回答「本次交付到底过没过 R20 的线」。

对标开源标杆（Stars > 1k）：
    * dbt-labs/dbt-core (>9k) —— semantic layer / model contract 的单一信任源
    * open-policy-agent/conftest (>2k) —— 策略账本化与机器裁决
    * OASIS SARIF v2.1.0 —— 标准化的结果与规则表达

落地的最低 3 项架构升级：
    1. SRE_SPEC.md 动态加载 + SHA256 账本指纹 + KPI/门禁完整性校验；
    2. 8 维发布硬门禁统一裁决 `verify_gate_compliance`（逐维给证据）；
    3. 一键导出 `sre_gates.json` / `sre_gate_matrix.md` 供下游机器消费。

用法：
    python agent.py evolve spec --out workspace/rounds/L04_spec.json \
        --export-dir workspace/bundles
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import datetime
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SPEC_PATH = os.path.join(_ROLE, "SRE_SPEC.md")
_CRED_WORDS = ("password", "passwd", "secret", "token", "api_key", "apikey",
               "private_key", "私钥", "密码", "access_key")
_RELIABILITY_KEYS = ("availability", "uptime_ratio", "sli", "slo",
                     "availability_ratio", "success_rate")
_DESTRUCTIVE = ("恢复生产", "灾难切换", "rollback", "restore_production",
                "删除快照", "清空快照", "delete_snapshot")
_OBS_KEYS = ("monitor_id", "monitor_count", "alert_count", "telemetry",
             "trace_id", "uptime_ratio", "probe_count", "sli")
_ONCALL_KEYS = ("owner", "dri", "escalation", "oncall", "escalation_count", "pager")


class SpecLedgerError(ValueError):
    """账本缺失或结构破损。"""


class R20SpecLedger:
    """SRE_SPEC.md 账本加载、指纹、8 维门禁裁决与导出。"""

    ENGINE = "R20SpecLedger"
    LAYER = "L04"
    CAPABILITIES = [
        "SRE_SPEC.md 动态加载 + SHA256 账本指纹 + KPI/门禁完整性校验",
        "8 维发布硬门禁统一裁决 (verify_gate_compliance) 与违规定位",
        "账本一键导出 sre_gates.json / sre_gate_matrix.md 供下游消费",
    ]

    def __init__(self, spec_path: str = _SPEC_PATH):
        self.spec_path = spec_path

    # ------------------------------------------------------------------ #
    # 加载 / 指纹
    # ------------------------------------------------------------------ #
    def load_spec(self) -> Dict[str, Any]:
        if not os.path.isfile(self.spec_path):
            raise SpecLedgerError(f"账本不存在: {self.spec_path}")
        with open(self.spec_path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
        if not m:
            raise SpecLedgerError("SRE_SPEC.md 缺少 ```json 账本块")
        try:
            body = json.loads(m.group(1))
        except ValueError as exc:
            raise SpecLedgerError(f"账本 JSON 解析失败: {exc}")
        gates = body.get("release_gates") or []
        kpis = body.get("kpis") or []
        ns = body.get("north_star") or {}
        missing = [k for k in ("availability_slo", "error_budget_ratio",
                               "mttr_max_minutes", "rto_max_hours", "rpo_max_hours")
                   if k not in ns]
        return {
            "ok": len(gates) == 8 and len(kpis) >= 5 and not missing,
            "spec": body,
            "spec_version": body.get("spec_version"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "gates_count": len(gates),
            "kpis_count": len(kpis),
            "north_star": ns,
            "missing_north_star": missing,
        }

    # ------------------------------------------------------------------ #
    # 8 维门禁
    # ------------------------------------------------------------------ #
    def _numeric_reliability(self, artifact: Dict[str, Any]) -> List[float]:
        vals: List[float] = []
        for k in _RELIABILITY_KEYS:
            v = artifact.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vals.append(float(v))
        for sub in ("sli", "report", "metrics"):
            node = artifact.get(sub)
            if isinstance(node, dict):
                for k in _RELIABILITY_KEYS:
                    v = node.get(k)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        vals.append(float(v))
        return vals

    def _has_any_key(self, artifact: Dict[str, Any], keys) -> bool:
        blob = json.dumps(artifact, ensure_ascii=False).lower()
        return any(k.lower() in blob for k in keys)

    def verify_gate_compliance(self, artifact_type: str,
                               artifact: Dict[str, Any]) -> Dict[str, Any]:
        spec = self.load_spec()
        art = artifact if isinstance(artifact, dict) else {}
        slo = float(spec["north_star"].get("availability_slo", 0.999))
        checks_list = art.get("checks") if isinstance(art.get("checks"), list) else []
        blob = json.dumps(art, ensure_ascii=False)
        gates: List[Dict[str, Any]] = []

        def add(gid: str, name: str, ok: bool, msg: str):
            gates.append({"id": gid, "name": name, "ok": bool(ok),
                          "msg": msg, "sev": "OK" if ok else "BLOCKER"})

        # G1 结构
        add("G1", "结构完整性", bool(art) and isinstance(art.get("checks"), list) and len(checks_list) > 0,
            f"字段数={len(art)} checks={len(checks_list)}")

        # G2 SLO 口径
        vals = self._numeric_reliability(art)
        in_range = all(0.0 <= v <= 1.0 for v in vals)
        meets = bool(vals) and all(v >= slo - 1e-12 for v in vals) and in_range
        add("G2", "SLO 口径一致", meets,
            f"reliability={vals[:4]} slo={slo}")

        # G3 证据链
        good = [x for x in checks_list if isinstance(x, dict) and x.get("ok")]
        evidence_ok = len(good) >= 1 and all(x.get("dim") and x.get("msg") for x in good)
        add("G3", "证据链完整", evidence_ok, f"通过判据={len(good)}/{len(checks_list)}")

        # G4 授权
        destructive = any(w in blob for w in _DESTRUCTIVE)
        authorized = any(k in blob.lower() for k in ("authorization", "handoff", "授权", "审批", "approved_by"))
        add("G4", "授权与交接", (not destructive) or authorized,
            f"破坏性动作={'是' if destructive else '否'} 授权={authorized}")

        # G5 回滚
        needs_rollback = ("restore" in artifact_type.lower()
                          or any(w in blob for w in ("恢复生产", "灾难切换")))
        plan = art.get("rollback_plan") or []
        steps = art.get("step_count") or (len(plan) if isinstance(plan, list) else 0)
        add("G5", "回滚可执行", (not needs_rollback) or (steps >= 1),
            f"需要回滚={'是' if needs_rollback else '否'} 步骤={steps}")

        # G6 可观测性
        add("G6", "可观测性", self._has_any_key(art, _OBS_KEYS), "monitor/alert/telemetry 证据")
        # G7 值班
        esc = art.get("escalation_count") or art.get("escalation") or 0
        if isinstance(esc, list):
            esc = len(esc)
        level_ok = not isinstance(esc, (int, float)) or esc <= spec["north_star"].get("escalation_max_level", 3)
        add("G7", "值班与升级", self._has_any_key(art, _ONCALL_KEYS) and level_ok,
            f"值班证据={self._has_any_key(art, _ONCALL_KEYS)} 升级级数={esc}")
        # G8 卫生
        low = blob.lower()
        hygiene_ok = (not any(w in low for w in _CRED_WORDS)
                      and "todo" not in low and "待定" not in blob)
        add("G8", "卫生与凭据", hygiene_ok, "无凭据明文/无占位")

        passed = sum(1 for g in gates if g["ok"])
        return {
            "ok": passed == len(gates),
            "passed": passed, "total": len(gates),
            "score": round(passed / max(1, len(gates)), 4),
            "artifact_type": artifact_type,
            "spec_version": spec["spec_version"],
            "spec_sha256": spec["sha256"][:16],
            "gates": gates,
            "failed_gates": [g["id"] for g in gates if not g["ok"]],
        }

    # ------------------------------------------------------------------ #
    # 导出
    # ------------------------------------------------------------------ #
    def export_gates(self, out_dir: str) -> Dict[str, Any]:
        spec = self.load_spec()
        os.makedirs(out_dir, exist_ok=True)
        gates_path = os.path.join(out_dir, "sre_gates.json")
        with open(gates_path, "w", encoding="utf-8") as f:
            json.dump({"spec_version": spec["spec_version"],
                       "sha256": spec["sha256"],
                       "north_star": spec["north_star"],
                       "kpis": spec["spec"].get("kpis", []),
                       "release_gates": spec["spec"].get("release_gates", [])},
                      f, ensure_ascii=False, indent=2)
        md_path = os.path.join(out_dir, "sre_gate_matrix.md")
        lines = ["# R20 发布硬门禁矩阵", "",
                 f"- 账本版本：{spec['spec_version']}",
                 f"- 账本指纹：`{spec['sha256'][:16]}…`",
                 f"- 北极星：可用率 {spec['north_star'].get('availability_slo')} / "
                 f"MTTR {spec['north_star'].get('mttr_max_minutes')}min / "
                 f"RTO {spec['north_star'].get('rto_max_hours')}h / "
                 f"RPO {spec['north_star'].get('rpo_max_hours')}h", "",
                 "| 门禁 | 名称 | 维度 | 阈值 |", "| --- | --- | --- | --- |"]
        for g in spec["spec"].get("release_gates", []):
            lines.append(f"| {g['id']} | {g['name']} | {g['dim']} | {g['threshold']} |")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return {"gates_path": gates_path, "matrix_path": md_path,
                "gates_count": spec["gates_count"],
                "spec_sha256": spec["sha256"]}

    def demo_artifact(self) -> Dict[str, Any]:
        """干净发布工件：8 维门禁应全 PASS。"""
        return {
            "service": "支付服务",
            "availability": 0.9995,
            "slo": 0.999,
            "monitor_id": "mon-pay-01",
            "alert_count": 3,
            "escalation_count": 2,
            "owner": "蛙值守",
            "telemetry": {"trace_id": "tr-demo-0001"},
            "handoff": "R01 审批",
            "checks": [{"ok": True, "dim": "monitor", "msg": "探测通过"},
                       {"ok": True, "dim": "alert", "msg": "告警链路可用"}],
        }


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R20 L04 SRE_SPEC 账本")
    ap.add_argument("--artifact", default="")
    ap.add_argument("--artifact-type", default="release")
    ap.add_argument("--export-dir", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    ledger = R20SpecLedger()
    spec = ledger.load_spec()
    out: Dict[str, Any] = {"ok": spec["ok"], "engine": ledger.ENGINE,
                           "layer": ledger.LAYER, "spec": spec,
                           "capabilities": list(ledger.CAPABILITIES)}
    if args.export_dir:
        out["export"] = ledger.export_gates(args.export_dir)
    if args.artifact and os.path.exists(args.artifact):
        with open(args.artifact, encoding="utf-8-sig") as f:
            out["compliance"] = ledger.verify_gate_compliance(args.artifact_type, json.load(f))
        out["ok"] = out["ok"] and out["compliance"]["ok"]
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "gates": spec["gates_count"],
                      "spec_sha256": spec["sha256"][:12]}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
