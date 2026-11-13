# -*- coding: utf-8 -*-
"""设计系统库集成测试（R10 ↔ R08）。

覆盖：
1. 31 份品牌 DESIGN.md 全部入库、可解析、九段式门禁全 PASS；
2. 项目类型推荐每个都给出 ≥3 个品牌；
3. 令牌契约形状满足 R08 的 design 门禁（color/typography/spacing + components）；
4. 落盘只写 DESIGN.md + design_tokens.json，且默认不覆盖；
5. R08 的 `design from-md` 能直接吃 R10 落盘的 DESIGN.md 并过门禁。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared import design_systems as ds  # noqa: E402

R08_DIR = os.path.join(ROOT, "r08-wajiancheng-mvp")


def test_library_has_31_systems():
    systems = ds.available()
    assert len(systems) == 31, f"期望 31 个设计系统，实际 {len(systems)}"
    for slug in systems:
        item = ds.get(slug)
        assert item and item["exists"], f"{slug} 元数据缺失"
        assert ds.read(slug).startswith("# Design System:")


def test_every_system_passes_nine_section_audit():
    failures = []
    for slug in ds.available():
        parsed = ds.parse(ds.read(slug))
        report = ds.audit(parsed, slug)
        if not report["ok"]:
            failures.append((slug, [c["msg"] for c in report["checks"] if not c["ok"]]))
    assert not failures, f"以下设计系统未过门禁：{failures}"


def test_every_project_type_recommends_at_least_three():
    for project in ds.PROJECT_TYPES:
        rec = ds.recommend(project)
        assert rec is not None, f"{project} 无推荐"
        assert len(rec["brands"]) >= 3, f"{project} 推荐不足 3 个：{rec['brands']}"
        assert all(b["exists"] for b in rec["brands"])


def test_tokens_shape_matches_r08_contract():
    bundle = ds.tokens(ds.parse(ds.read("linear.app")), "linear.app")
    tokens = bundle["tokens"]
    for kind in ("color", "typography", "spacing"):
        assert isinstance(tokens[kind], list) and tokens[kind], f"tokens.{kind} 为空"
        for item in tokens[kind]:
            assert str(item.get("name", "")).strip()
            assert str(item.get("value", "")).strip()
    assert isinstance(bundle["components"], list) and bundle["components"]
    for comp in bundle["components"]:
        assert comp["name"] and comp["platform"] and comp["states"]


def test_write_bundle_writes_two_files_and_respects_force(tmp_path):
    out = str(tmp_path / "bundle")
    report = ds.write_bundle("claude", out, force=True)
    assert report["verdict"] == "PASS"
    assert os.path.isfile(os.path.join(out, "DESIGN.md"))
    assert os.path.isfile(os.path.join(out, "design_tokens.json"))
    payload = json.loads(open(os.path.join(out, "design_tokens.json"), encoding="utf-8").read())
    assert payload["design_system"]["slug"] == "claude"

    again = ds.write_bundle("claude", out, force=False)
    assert again["written"] == [] and len(again["skipped"]) == 2


def test_unknown_brand_raises():
    with pytest.raises(FileNotFoundError):
        ds.read("no-such-brand")
    assert ds.get("no-such-brand") is None


def test_r08_from_md_bridge(tmp_path):
    ds.write_bundle("claude", str(tmp_path), force=True)
    design = os.path.join(str(tmp_path), "DESIGN.md")
    tokens = os.path.join(str(tmp_path), "tokens.json")
    proc = subprocess.run(
        [sys.executable, "agent.py", "design", "from-md",
         "--input", design, "--out", tokens, "--brand", "claude"],
        cwd=R08_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120)
    assert proc.returncode == 0, proc.stderr[-500:]
    line = next(l for l in proc.stdout.splitlines() if l.startswith("__AGENT_RESULT__"))
    payload = json.loads(line.split(" ", 1)[1])
    assert payload["ok"] is True, payload
    assert payload["verdict"] == "PASS"
    assert payload["component_count"] >= 1
    assert os.path.isfile(tokens)
    written = json.loads(open(tokens, encoding="utf-8").read())
    assert written["design_system"]["slug"] == "claude"
