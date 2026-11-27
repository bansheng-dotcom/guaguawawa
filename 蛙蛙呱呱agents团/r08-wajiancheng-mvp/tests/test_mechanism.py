# -*- coding: utf-8 -*-
"""R08 机制单测：部署 / 回滚（版本锁、幂等、健康检查、回滚计划）。"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import deploy_rollback as dr  # noqa: E402


def test_digest_changes_with_content():
    a = dr.digest_files({"index.html": "v1"})
    b = dr.digest_files({"index.html": "v2"})
    assert a != b and len(a) == 64
    assert dr.digest_files({"index.html": "v1"}) == a


def test_e2e_covers_deploy_idempotent_rollback(tmp_path):
    out = dr.run_e2e(str(tmp_path))
    assert out["ok"] is True, out["steps"]
    outcomes = [s["outcome"] for s in out["steps"]]
    assert outcomes == ["deployed", "noop", "auto_rolled_back", "deployed", "rolled_back"]
    assert out["steps"][1]["idempotent"] is True
    assert out["steps"][2]["rolled_back"] is True
    assert out["state"]["version"] == "mvp-1.1.0"
    assert out["health"]["ok"] is True
    assert len(out["history"]) == 5


def test_deploy_rejects_missing_rollback_plan(tmp_path):
    out = dr.deploy(dr.manifest("mvp-1.0.0", dr.BASE_FILES,
                                include_rollback=False), str(tmp_path))
    assert out["ok"] is False and out["outcome"] == "refused"
    assert "D01_NO_ROLLBACK_PLAN" in {v["code"] for v in out["violations"]}


def test_downgrade_must_use_rollback(tmp_path):
    dr.deploy(dr.manifest("mvp-1.1.0", dr.BASE_FILES), str(tmp_path))
    out = dr.deploy(dr.manifest("mvp-1.0.0", dr.BASE_FILES), str(tmp_path))
    assert out["ok"] is False
    assert "D02_VERSION_LOCK" in {v["code"] for v in out["violations"]}


def test_same_version_different_digest_rejected(tmp_path):
    dr.deploy(dr.manifest("mvp-1.1.0", dr.BASE_FILES), str(tmp_path))
    out = dr.deploy(dr.manifest("mvp-1.1.0", dr.NEXT_FILES), str(tmp_path))
    assert out["ok"] is False
    assert "D05_VERSION_DIGEST_MISMATCH" in {v["code"] for v in out["violations"]}


def test_health_failure_auto_rolls_back_and_restores_files(tmp_path):
    dr.deploy(dr.manifest("mvp-1.1.0", dr.BASE_FILES), str(tmp_path))
    out = dr.deploy(dr.manifest("mvp-1.2.0", dr.NEXT_FILES, healthy=False), str(tmp_path))
    assert out["outcome"] == "auto_rolled_back" and out["rolled_back"] is True
    assert dr._read(os.path.join(str(tmp_path), "release", "index.html")) == "<h1>MVP v1.1.0</h1>"
    assert dr.check_health(str(tmp_path))["ok"] is True


def test_misuse_cases_are_rejected():
    for name in ("deploy-no-rollback.json", "version-lock-drift.json"):
        out = dr.check_case(os.path.join(HERE, "misuse", name))
        assert out["rejected"] is True, name
        assert out["as_expected"] is True, (name, out["hit"], out["expect"])


def test_golden_html_contract():
    out = dr.build_goldens()
    assert out["ok"] is True
    for name in ("mvp-delivery-pack.html", "mvp-rollback-record.html"):
        html = open(os.path.join(HERE, "golden", name), encoding="utf-8").read()
        assert "@page" in html and "A4" in html
        assert 'data-theme="light"' in html
        assert html.count("<h1") == 1 and "<thead" in html
        assert "<br" not in html and "italic" not in html
