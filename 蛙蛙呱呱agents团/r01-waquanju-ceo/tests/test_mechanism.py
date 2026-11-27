# -*- coding: utf-8 -*-
"""R01 机制单测：报告级运行账本（run-manifest）。

覆盖：账本构建 → 逐步可追 → 篡改检测 → 误用样本被拒 → 黄金 HTML 合规。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import run_manifest as rm  # noqa: E402


def _golden_dir() -> str:
    return os.path.join(HERE, "golden")


def test_goldens_build_and_verify(tmp_path):
    out = rm.build_goldens(str(tmp_path))
    assert out["verify"]["ok"] is True, out["verify"]["violations"]
    assert out["verify"]["stages"] == 8
    assert out["verify"]["artifacts"] == 9
    steps = out["verify"]["trace"]
    assert [s["seq"] for s in steps] == list(range(1, 9))
    assert all(s["decision"].strip() for s in steps), "每个阶段必须有决策"
    assert steps[-1]["stage"] == "deliver"


def test_committed_golden_manifest_still_valid():
    manifest = rm.load_json(os.path.join(_golden_dir(), "run-manifest.json"))
    out = rm.verify_manifest(manifest, root=_golden_dir())
    assert out["ok"] is True, out["violations"]


def test_tampered_artifact_is_detected(tmp_path):
    out = rm.build_goldens(str(tmp_path))
    assert out["verify"]["ok"] is True
    victim = tmp_path / "artifacts" / "taskcard.json"
    victim.write_text('{"goal": "被手改"}', encoding="utf-8")
    again = rm.verify_manifest(out["manifest"], root=str(tmp_path))
    codes = {x["code"] for x in again["violations"]}
    assert "M05_HASH_MISMATCH" in codes


def test_golden_html_contract():
    for name in ("decision-pack.html", "run-manifest.html"):
        html = open(os.path.join(_golden_dir(), name), encoding="utf-8").read()
        assert "@page" in html and "A4" in html
        assert 'data-theme="light"' in html
        assert html.count("<h1") == 1
        assert html.count("<thead") >= 1 and "<th" in html
        assert "<br" not in html
        assert "italic" not in html


def test_misuse_cases_are_rejected():
    cases = ["manifest-missing-sha.json", "manifest-untraceable-and-unsigned.json"]
    for name in cases:
        out = rm.check_case(os.path.join(HERE, "misuse", name))
        assert out["rejected"] is True, name
        assert out["as_expected"] is True, (name, out["hit"], out["expect"])


def test_mutations_never_pass_silently():
    manifest = rm.load_json(os.path.join(_golden_dir(), "run-manifest.json"))
    for mut in rm.MUTATIONS:
        out = rm.verify_manifest(rm.apply_mutations(manifest, [mut]))
        assert not out["ok"], f"{mut} 居然没被拦住"
        assert out["violations"], mut
