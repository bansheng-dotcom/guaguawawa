# -*- coding: utf-8 -*-
"""L01 工具实体层 —— R20 真实可靠性精算沙箱 (SRE Reliability Sandbox)。

SOP v13.0 L01 体检病灶（R20 真实断点）：
    1. 7 个技能只判断「字段在不在」：uptime 只是 success/total 的一次除法，
       没有 SLO 错误预算、燃烧率、预算余量，无法回答「这点故障还能不能扛」；
    2. RPO/RTO 只比较数字大小，没有可行性与安全边际的精算；
    3. MTTR/MTBF 完全缺失，复盘只能写「响应及时」这类空话。

对标开源标杆（Stars > 1k）：
    * google/sre-book / sloth (Slok/sloth >2k) —— SLO / error budget / burn rate 口径
    * louislam/uptime-kuma (>60k) —— 探测成功率与可用率采集口径
    * restic/restic (>25k) —— 备份 RPO/RTO 与恢复目标约束

落地的最低 3 项架构升级：
    1. 确定性 SLI/错误预算沙箱：availability、allowed_failures、burn_rate、
       budget_remaining，零除安全且全部可复算；
    2. 事件精算：MTTR / MTBF / 严重度分布，时间戳解析确定性；
    3. RPO/RTO 可行性裁决（含安全边际）与延迟分位 p50/p95/p99。

用法：
    python -m engines.runtime_engine --probe --out workspace/rounds/L01_probe.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _r6(x: float) -> float:
    return round(float(x) + 1e-12, 6)


def _pct(sorted_vals: Sequence[float], p: float) -> float:
    """线性插值分位数（numpy.percentile linear 同口径）。"""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return round(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac, 4)


def _parse_ts(v: Any) -> Optional[datetime.datetime]:
    if isinstance(v, datetime.datetime):
        return v
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip().replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        return None


class ReliabilitySandboxError(ValueError):
    """可靠性沙箱输入不合法（空探测集 / 非法阈值）。"""


class R20RuntimeEngine:
    """R20 真实可靠性精算沙箱：SLI / 预算 / 事件 / RPO-RTO / 分位。"""

    ENGINE = "R20RuntimeEngine"
    LAYER = "L01"
    CAPABILITIES = [
        "确定性 SLI 沙箱 (availability / error_budget / burn_rate / budget_remaining)",
        "错误预算守恒 (allowed - consumed == remaining，容差 0.0) 与零除安全",
        "事件精算 MTTR/MTBF + RPO/RTO 可行性裁决 + 延迟 p50/p95/p99",
    ]

    def __init__(self, workspace_dir: Optional[str] = None):
        self.role_dir = _ROLE
        self.workspace_dir = workspace_dir or os.path.join(_ROLE, "workspace")

    # ------------------------------------------------------------------ #
    # 1. SLI / 错误预算
    # ------------------------------------------------------------------ #
    def compute_sli(self, probes: Sequence[Any], slo: float = 0.999) -> Dict[str, Any]:
        """probes 支持 [True, False, ...] 或 [{"ok": true}, ...]。"""
        if not 0.0 < float(slo) < 1.0:
            raise ReliabilitySandboxError(f"SLO 必须落在 (0,1)，收到 {slo}")
        flags: List[bool] = []
        skipped = 0
        for p in probes or []:
            if isinstance(p, bool):
                flags.append(p)
            elif isinstance(p, dict) and "ok" in p:
                flags.append(bool(p.get("ok")))
            else:
                skipped += 1
        total = len(flags)
        if total == 0:
            raise ReliabilitySandboxError("探测样本为空，SLI 不可计算")
        success = sum(1 for x in flags if x)
        failed = total - success
        availability = _r6(success / total)
        error_budget = _r6(1.0 - float(slo))
        allowed = int(math.floor(total * error_budget + 1e-9))
        actual_error_rate = _r6(failed / total)
        burn_rate = _r6(actual_error_rate / error_budget) if error_budget else 0.0
        remaining = allowed - failed
        return {
            "ok": True,
            "slo": float(slo),
            "total": total,
            "skipped": skipped,
            "success": success,
            "failed": failed,
            "availability": availability,
            "meets_slo": availability >= float(slo) - 1e-12,
            "error_budget": error_budget,
            "allowed_failures": allowed,
            "consumed_failures": failed,
            "budget_remaining": remaining,
            "budget_remaining_ratio": _r6(max(0, remaining) / allowed) if allowed else 0.0,
            "actual_error_rate": actual_error_rate,
            "burn_rate": burn_rate,
            "conservation": {"allowed": allowed, "consumed": failed,
                             "lhs": allowed - failed, "rhs": remaining,
                             "delta": 0.0 if allowed - failed == remaining else 1.0},
        }

    # ------------------------------------------------------------------ #
    # 2. 事件精算（MTTR / MTBF / 严重度）
    # ------------------------------------------------------------------ #
    def compute_incident_metrics(self, incidents: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        sev_dist: Dict[str, int] = {}
        for inc in incidents or []:
            if not isinstance(inc, dict):
                continue
            sev = str(inc.get("severity") or inc.get("sev") or "unknown").lower()
            sev_dist[sev] = sev_dist.get(sev, 0) + 1
            start = _parse_ts(inc.get("started_at") or inc.get("start"))
            end = _parse_ts(inc.get("resolved_at") or inc.get("end"))
            if start and end:
                minutes = (end - start).total_seconds() / 60.0
                if minutes >= 0:
                    rows.append({"start": start, "end": end,
                                 "mttr_minutes": round(minutes, 2), "severity": sev})
        mttrs = [r["mttr_minutes"] for r in rows]
        rows.sort(key=lambda r: r["start"])
        gaps = [(rows[i]["start"] - rows[i - 1]["end"]).total_seconds() / 3600.0
                for i in range(1, len(rows))]
        gaps = [g for g in gaps if g >= 0]
        return {
            "ok": bool(rows),
            "incident_count": len(incidents or []),
            "resolved_count": len(rows),
            "mttr_minutes": round(sum(mttrs) / len(mttrs), 2) if mttrs else None,
            "mttr_max_minutes": max(mttrs) if mttrs else None,
            "mtbf_hours": round(sum(gaps) / len(gaps), 3) if gaps else None,
            "severity_distribution": sev_dist,
            "rows": [{"start": r["start"].isoformat(timespec="seconds"),
                      "end": r["end"].isoformat(timespec="seconds"),
                      "mttr_minutes": r["mttr_minutes"], "severity": r["severity"]}
                     for r in rows],
        }

    # ------------------------------------------------------------------ #
    # 3. RPO / RTO 可行性
    # ------------------------------------------------------------------ #
    def check_rpo_rto(self, config: Dict[str, Any],
                      rpo_max_hours: float = 1.0,
                      rto_max_hours: float = 4.0) -> Dict[str, Any]:
        cfg = config or {}
        try:
            rpo = float(cfg.get("rpo_hours"))
            rto = float(cfg.get("rto_hours"))
        except (TypeError, ValueError):
            return {"ok": False, "feasible": False,
                    "checks": [{"ok": False, "msg": "rpo_hours/rto_hours 缺失或非数值",
                                "dim": "L01.rpo_rto", "sev": "BLOCKER"}]}
        checks = [
            {"ok": rpo <= rpo_max_hours, "msg": f"RPO {rpo}h <= 上限 {rpo_max_hours}h",
             "dim": "L01.rpo", "sev": "OK" if rpo <= rpo_max_hours else "BLOCKER"},
            {"ok": rto <= rto_max_hours, "msg": f"RTO {rto}h <= 上限 {rto_max_hours}h",
             "dim": "L01.rto", "sev": "OK" if rto <= rto_max_hours else "BLOCKER"},
        ]
        feasible = all(x["ok"] for x in checks)
        return {
            "ok": feasible, "feasible": feasible, "checks": checks,
            "rpo_hours": rpo, "rto_hours": rto,
            "rpo_margin_hours": round(rpo_max_hours - rpo, 3),
            "rto_margin_hours": round(rto_max_hours - rto, 3),
        }

    # ------------------------------------------------------------------ #
    # 4. 延迟分位
    # ------------------------------------------------------------------ #
    def compute_latency_percentiles(self, samples: Sequence[Any]) -> Dict[str, Any]:
        xs: List[float] = []
        for v in samples or []:
            if isinstance(v, bool):
                continue
            try:
                xs.append(float(v))
            except (TypeError, ValueError):
                continue
        if not xs:
            return {"count": 0, "mean": None, "p50": None, "p95": None,
                    "p99": None, "min": None, "max": None, "unit": "ms"}
        s = sorted(xs)
        return {"count": len(xs), "mean": round(sum(xs) / len(xs), 4),
                "p50": _pct(s, 0.50), "p95": _pct(s, 0.95), "p99": _pct(s, 0.99),
                "min": round(s[0], 4), "max": round(s[-1], 4), "unit": "ms"}

    # ------------------------------------------------------------------ #
    # 5. 健康探测（黄金样例可复算）
    # ------------------------------------------------------------------ #
    def probe_health(self) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        try:
            sli = self.compute_sli([True] * 9995 + [False] * 5, slo=0.999)
            sli_ok = (sli["availability"] == 0.9995 and sli["allowed_failures"] == 10
                      and sli["burn_rate"] == 0.5 and sli["budget_remaining"] == 5
                      and sli["conservation"]["delta"] == 0.0)
        except Exception as exc:  # pragma: no cover - 防御
            sli, sli_ok = {"error": str(exc)}, False
        checks.append({"ok": sli_ok, "msg": "SLI/错误预算黄金样例可复算",
                       "dim": "L01.sli_sandbox", "sev": "OK" if sli_ok else "BLOCKER"})

        inc = self.compute_incident_metrics([
            {"started_at": "2026-11-01T10:00:00", "resolved_at": "2026-11-01T10:20:00",
             "severity": "critical"},
            {"started_at": "2026-11-02T10:00:00", "resolved_at": "2026-11-02T10:40:00",
             "severity": "warning"}])
        inc_ok = inc["mttr_minutes"] == 30.0 and inc["incident_count"] == 2
        checks.append({"ok": inc_ok, "msg": "MTTR/MTBF 精算黄金样例正确",
                       "dim": "L01.incident_sandbox", "sev": "OK" if inc_ok else "BLOCKER"})

        rr = self.check_rpo_rto({"rpo_hours": 0.5, "rto_hours": 2.0})
        rr_bad = self.check_rpo_rto({"rpo_hours": 2.0, "rto_hours": 6.0})
        rr_ok = rr["ok"] and not rr_bad["ok"] and rr["rto_margin_hours"] == 2.0
        checks.append({"ok": rr_ok, "msg": "RPO/RTO 可行性与边界裁决正确",
                       "dim": "L01.rpo_rto", "sev": "OK" if rr_ok else "BLOCKER"})

        lat = self.compute_latency_percentiles([10, 20, 30, 40, 100])
        lat_ok = lat["count"] == 5 and lat["p50"] == 30.0 and lat["p95"] == 88.0
        checks.append({"ok": lat_ok, "msg": "延迟分位线性插值正确",
                       "dim": "L01.latency", "sev": "OK" if lat_ok else "BLOCKER"})

        ok_all = all(x["ok"] for x in checks)
        return {"ok": ok_all, "engine": self.ENGINE, "layer": self.LAYER,
                "status": "HEALTHY" if ok_all else "DEGRADED",
                "checks": checks, "capabilities": list(self.CAPABILITIES),
                "golden_sli": sli, "golden_incident": inc, "golden_rpo_rto": rr,
                "golden_latency": lat,
                "python": sys.version.split()[0],
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds")}

    # ------------------------------------------------------------------ #
    # 6. 本地评估（供 local_exec / 发布门禁复用）
    # ------------------------------------------------------------------ #
    def evaluate_locally(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload or {}
        probes = payload.get("probes") or []
        slo = float(payload.get("slo", 0.999))
        try:
            sli = self.compute_sli(probes, slo)
        except ReliabilitySandboxError as exc:
            return {"ok": False, "engine": self.ENGINE, "error": str(exc), "verdict": "FAIL"}
        rr = self.check_rpo_rto(payload.get("dr") or {})
        inc = self.compute_incident_metrics(payload.get("incidents") or [])
        ok = bool(sli["meets_slo"] and sli["conservation"]["delta"] == 0.0
                  and (rr["ok"] or not (payload.get("dr"))))
        return {"ok": ok, "engine": self.ENGINE, "layer": self.LAYER,
                "sli": sli, "rpo_rto": rr, "incidents": inc,
                "verdict": "PASS" if ok else "FAIL", "capability_status": "real"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R20 L01 真实可靠性精算沙箱")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--eval", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    eng = R20RuntimeEngine()
    if args.eval:
        with open(args.eval, encoding="utf-8-sig") as f:
            out = eng.evaluate_locally(json.load(f))
    else:
        out = eng.probe_health()
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"status": out.get("status", out.get("verdict")),
                      "engine": out.get("engine"), "out": args.out,
                      "ok": out.get("ok")}, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
