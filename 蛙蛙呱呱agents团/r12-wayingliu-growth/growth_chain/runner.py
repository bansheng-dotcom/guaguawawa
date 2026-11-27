# -*- coding: utf-8 -*-
"""增长链总跑：一条命令跑 7 段，产出 7 个 JSON + growth_manifest.json。

manifest 记录每段工件 sha256、门禁、跨段一致性：
- 归因分母 == diagnose 的 orders（同一口径）；
- paid 的 CAC 可由原始花费/新客复算，且支付渠道新客 == 归因末触转化；
- 留存队列规模 == diagnose 的 signups；
- 自媒体不得为失败态、不得补 0；MMM 留出验证必须通过。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from . import (attribution, common as c, diagnose, experiment, mmm, paid,
               retention, selfmedia)


def _path(base: str, value: str) -> str:
    return value if os.path.isabs(value) else os.path.normpath(
        os.path.join(base, value))


def _cross_checks(stages: Dict[str, Dict[str, Any]],
                  expect: Dict[str, Any]) -> List[Dict[str, Any]]:
    diag = stages["diagnose"]
    attr = stages["attribution"]
    ret = stages["retention"]
    pay = stages["paid"]
    media = stages["selfmedia"]
    model = stages["mmm"]

    metric_name = expect.get("attribution_denominator_metric", "orders")
    diag_orders = float(diag["totals"].get(metric_name) or 0)
    attr_den = float(attr["denominator"]["value"] or 0)
    paid_channel = expect.get("paid_channel", "paid_search")
    paid_new = float(pay["channels"].get(paid_channel, {}).get("new_customers") or 0)
    attr_paid = float(attr["models"]["last_touch"]["channels"]
                      .get(paid_channel, {}).get("conversions") or 0)
    cac_raw = float(pay["cac_recompute"]["cac"] or 0)
    cac_art = float(pay["totals"]["cac"] or 0)
    retention_metric = expect.get("retention_denominator_metric", "signups")
    ret_total = float(ret["total_cohort_size"])
    diag_ret = float(diag["totals"].get(retention_metric) or 0)

    return [
        c.check("归因分母=diagnose 指标",
                abs(attr_den - diag_orders) < 1e-6,
                f"attribution={attr_den} diagnose.{metric_name}={diag_orders}"),
        c.check("CAC 与 paid 数据一致", abs(cac_raw - cac_art) < 0.01,
                f"paid={cac_art} recompute={cac_raw}"),
        c.check("支付渠道新客=归因末触",
                abs(paid_new - attr_paid) < 1e-6,
                f"paid.{paid_channel}={paid_new} attr={attr_paid}"),
        c.check("留存队列=diagnose 指标",
                abs(ret_total - diag_ret) < 1e-6,
                f"retention={ret_total} diagnose.{retention_metric}={diag_ret}"),
        c.check("自媒体非失败且未补零",
                media["status"] != "failed" and not media["zero_filled"],
                f"status={media['status']} zero_filled={media['zero_filled']}"),
        c.check("MMM 留出验证通过", bool(model["gate"]["ok"]),
                f"holdout_r2={model['holdout_r2']}"),
    ]


def run(spec_path: str, out_dir: str) -> Dict[str, Any]:
    """执行全链并写盘，返回 manifest（含门禁与跨段一致性）。"""
    spec = c.load_json(spec_path)
    base = os.path.dirname(os.path.abspath(spec_path))
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    def cfg(stage: str) -> Dict[str, Any]:
        return spec.get(stage) or {}

    stages: Dict[str, Dict[str, Any]] = {}
    stages["diagnose"] = diagnose.build(_path(base, cfg("diagnose")["input"]))
    stages["experiment"] = experiment.build(
        _path(base, cfg("experiment")["input"]))
    attr_cfg = cfg("attribution")
    stages["attribution"] = attribution.build(
        _path(base, attr_cfg["input"]),
        evidence_path=_path(base, attr_cfg["evidence"]) if attr_cfg.get("evidence") else None,
        budget_total=float(attr_cfg.get("budget_total", 100000)),
        causal_claim=bool(attr_cfg.get("causal_claim", False)))
    stages["retention"] = retention.build(_path(base, cfg("retention")["input"]))
    paid_cfg = cfg("paid")
    stages["paid"] = paid.build(_path(base, paid_cfg["input"]),
                                payback_max=float(paid_cfg.get("payback_max", 18)))
    stages["selfmedia"] = selfmedia.build(_path(base, cfg("selfmedia")["input"]),
                                          platform=cfg("selfmedia").get("platform"))
    mmm_cfg = cfg("mmm")
    stages["mmm"] = mmm.build(_path(base, mmm_cfg["input"]),
                              decay=float(mmm_cfg.get("decay", 0.5)),
                              ridge_lambda=float(mmm_cfg.get("ridge_lambda", 1.0)),
                              holdout_r2_min=float(mmm_cfg.get("holdout_r2_min", 0.5)))

    stage_rows = []
    for name in c.STAGES:
        path = os.path.join(out_dir, c.ARTIFACT_FILES[name])
        c.write_json(path, stages[name])
        stage_rows.append({
            "stage": name,
            "file": c.ARTIFACT_FILES[name],
            "sha256": c.sha256_file(path),
            "verdict": stages[name]["gate"]["verdict"],
            "ok": stages[name]["gate"]["ok"],
        })

    cross = _cross_checks(stages, spec.get("expect") or {})
    stage_checks = [c.check(f"阶段 {name} 门禁",
                            stages[name]["gate"]["ok"],
                            stages[name]["gate"]["verdict"])
                    for name in c.STAGES]
    gate = c.gate(stage_checks + cross)

    manifest = {
        "role": "r12",
        "chain": list(c.STAGES),
        "spec": os.path.basename(spec_path),
        "spec_sha256": c.sha256_file(spec_path),
        "stages": stage_rows,
        "cross_checks": cross,
        "gate": gate,
        "ok": gate["ok"],
    }
    c.write_json(os.path.join(out_dir, c.MANIFEST_FILE), manifest)
    return manifest


def audit(dir_path: str) -> Dict[str, Any]:
    """复核已有工件：文件齐全、sha256 未漂移、门禁与跨段一致性全绿。"""
    manifest_path = os.path.join(dir_path, c.MANIFEST_FILE)
    manifest = c.load_json(manifest_path)
    checks = []
    missing = [c.ARTIFACT_FILES[s] for s in c.STAGES
               if not os.path.exists(os.path.join(dir_path, c.ARTIFACT_FILES[s]))]
    checks.append(c.check("7 段工件齐全", not missing, str(missing)))
    for row in manifest.get("stages", []):
        path = os.path.join(dir_path, row["file"])
        digest = c.sha256_file(path) if os.path.exists(path) else None
        checks.append(c.check(f"sha256 {row['stage']}", digest == row["sha256"],
                              "指纹漂移" if digest != row["sha256"] else ""))
    checks.append(c.check("各段门禁 PASS",
                          all(r.get("ok") for r in manifest.get("stages", [])),
                          ""))
    checks.append(c.check("跨段一致性 PASS",
                          all(r.get("ok") for r in manifest.get("cross_checks", [])),
                          ""))
    gate = c.gate(checks)
    return {"ok": gate["ok"], "verdict": gate["verdict"], "checks": checks,
            "artifact": manifest, "dir": os.path.abspath(dir_path)}
