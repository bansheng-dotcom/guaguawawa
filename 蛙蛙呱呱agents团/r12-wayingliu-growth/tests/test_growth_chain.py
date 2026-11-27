# -*- coding: utf-8 -*-
"""增长链测试：7 段门禁 + 3 条端到端 + 3 条误用拦截。"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from growth_chain import (attribution, diagnose, experiment, mmm, paid,
                          retention, runner, selfmedia)


def _fx(role_dir: str, name: str) -> str:
    return os.path.join(role_dir, "fixtures", name)


def _spec(role_dir: str) -> str:
    return _fx(role_dir, "chain_spec.json")


# ---------------------------------------------------------------- 各段门禁
def test_diagnose_gate(role_dir):
    art = diagnose.build(_fx(role_dir, "metrics_daily.csv"))
    assert art["gate"]["ok"], art["gate"]["failed"]
    assert art["metric_tree"]["levels"]
    assert len(art["funnel"]) == 4
    assert all(a.get("rule") for a in art["anomalies"])
    assert art["totals"]["orders"] > 0


def test_experiment_gate(role_dir):
    art = experiment.build(_fx(role_dir, "experiment_spec.json"))
    assert art["gate"]["ok"], art["gate"]["failed"]
    assert art["required_sample_size_per_arm"] > 0
    assert art["preregistration_sha256"]
    assert experiment.check(art)["ok"]


def test_attribution_gate(role_dir):
    art = attribution.build(_fx(role_dir, "attribution_touches.csv"))
    assert art["gate"]["ok"], art["gate"]["failed"]
    assert attribution.check(art)["ok"]
    for model in ("first_touch", "last_touch", "linear", "position_based"):
        assert abs(art["models"][model]["sum_conversions"]
                   - art["denominator"]["value"]) < 1e-6


def test_retention_gate(role_dir):
    art = retention.build(_fx(role_dir, "retention_cohort.csv"))
    assert art["gate"]["ok"], art["gate"]["failed"]
    assert art["overall_curve"]
    for cohort in art["cohorts"].values():
        assert cohort["curve"][0]["retention_rate"] == 1.0
        assert cohort["activation_rate"] > 0 and cohort["referral_rate"] >= 0


def test_paid_gate(role_dir):
    art = paid.build(_fx(role_dir, "paid_channels.csv"))
    assert art["gate"]["ok"], art["gate"]["failed"]
    assert art["totals"]["payback_months"] <= art["totals"]["payback_threshold"]
    assert abs(art["cac_recompute"]["cac"] - art["totals"]["cac"]) < 0.01


def test_selfmedia_tri_state(role_dir):
    art = selfmedia.build(_fx(role_dir, "selfmedia_90d.csv"))
    assert art["gate"]["ok"], art["gate"]["failed"]
    assert art["status"] == "normal"
    assert not art["zero_filled"]
    partial = selfmedia.analyze([
        {"日期": "2025-05-01", "平台": "抖音", "播放量": "100", "点赞": "",
         "评论": "1", "分享": "1", "涨粉": "2", "收入": "9"},
    ])
    assert partial["status"] == "partial"
    assert partial["rows"][0]["likes"] is None
    assert "likes" in partial["missing_fields"]


def test_mmm_gate(role_dir):
    art = mmm.build(_fx(role_dir, "mmm_weekly.csv"))
    assert art["gate"]["ok"], art["gate"]["failed"]
    assert art["holdout_r2"] >= art["holdout_r2_min"]
    assert all(len(v["ci90"]) == 2 for v in art["channels"].values())


# ---------------------------------------------------------------- 端到端
def test_e2e_run_chain(role_dir, tmp_path):
    manifest = runner.run(_spec(role_dir), str(tmp_path))
    assert manifest["ok"], manifest["gate"]["failed"]
    assert len(manifest["stages"]) == 7
    for row in manifest["stages"]:
        path = tmp_path / row["file"]
        assert path.is_file()
        assert len(row["sha256"]) == 64
    for check in manifest["cross_checks"]:
        assert check["ok"], check["name"]


def test_e2e_audit_and_tamper(role_dir, tmp_path):
    runner.run(_spec(role_dir), str(tmp_path))
    audit = runner.audit(str(tmp_path))
    assert audit["ok"], audit["checks"]
    (tmp_path / "paid.json").write_text("{}", encoding="utf-8")
    assert not runner.audit(str(tmp_path))["ok"]


def test_e2e_cli_is_deterministic(role_dir, tmp_path):
    out1, out2 = tmp_path / "a", tmp_path / "b"
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    for out in (out1, out2):
        proc = subprocess.run(
            [sys.executable, "agent.py", "growth_chain", "run",
             "--spec", _spec(role_dir), "--out-dir", str(out)],
            cwd=role_dir, capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env, timeout=300)
        assert proc.returncode == 0, proc.stderr[-800:]
        assert "__AGENT_RESULT__ " in proc.stdout
        payload = json.loads(proc.stdout.split("__AGENT_RESULT__ ", 1)[1])
        assert payload["ok"], payload.get("checks")
    m1 = json.loads((out1 / "growth_manifest.json").read_text(encoding="utf-8"))
    m2 = json.loads((out2 / "growth_manifest.json").read_text(encoding="utf-8"))
    assert [s["sha256"] for s in m1["stages"]] == [s["sha256"] for s in m2["stages"]]


# ---------------------------------------------------------------- 误用拦截
@pytest.mark.parametrize("name,checker,expected", [
    ("selfmedia-fill-zero.json", selfmedia.check, "缺数据不补零"),
    ("attribution-correlation-as-causation.json", attribution.check,
     "禁止把相关当因果"),
    ("experiment-insufficient-sample.json", experiment.check,
     "样本量不足不得下结论"),
])
def test_misuse_blocked(role_dir, name, checker, expected):
    with open(os.path.join(role_dir, "misuse", name), encoding="utf-8") as fh:
        artifact = json.load(fh)
    gate = checker(artifact)
    assert not gate["ok"]
    assert expected in gate["failed"], gate["failed"]
