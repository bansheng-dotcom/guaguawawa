# -*- coding: utf-8 -*-
"""外部能力目录测试：26 个 Trae / WorkBuddy 能力是否登记完整、文档落地、探测可用。"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared import external_capabilities as ext  # noqa: E402


def test_catalog_has_26_unique_capabilities():
    caps = ext.all_caps()
    ids = [c["id"] for c in caps]
    assert len(caps) == 26
    assert len(set(ids)) == 26
    for cap in caps:
        assert cap["owner"] in ext.ROLES
        for consumer in cap["consumers"]:
            assert consumer in ext.ROLES, f"{cap['id']} 的消费方非法：{consumer}"
        assert cap["kind"] in {"skill", "multi", "mcp"}
        assert cap["triggers"], f"{cap['id']} 缺触发词"


def test_docs_landed_for_every_capability():
    missing = []
    for cap in ext.all_caps():
        path = ext.docs_path(cap)
        if not os.path.isdir(path):
            missing.append((cap["id"], "目录缺失"))
            continue
        docs = [os.path.join(r, f) for r, _d, fs in os.walk(path) for f in fs]
        if not docs:
            missing.append((cap["id"], "无文件"))
        if not cap["skills"]:
            missing.append((cap["id"], "无技能入口"))
    assert not missing, missing


def test_docs_dir_stays_inside_owner_role():
    for cap in ext.all_caps():
        assert cap["docs_dir"].startswith(ext.ROLES[cap["owner"]] + "/references/external/")


def test_role_filter_includes_owned_and_consumed():
    owned = ext.owned("r11")
    assert {c["id"] for c in owned} == {"rednote-post", "xhs-content-skills"}
    visible = {c["id"] for c in ext.list_caps(role="r11")}
    assert {"rednote-post", "xhs-content-skills"} <= visible
    assert "meitu-local-mcp" in visible  # r11 是消费方


def test_probe_shape_and_docs_check():
    for cap in ext.all_caps():
        result = ext.probe(cap)
        assert result["status"] in {"ready", "partial", "blocked"}
        docs_check = next(c for c in result["checks"] if c["dim"] == "ext.docs")
        assert docs_check["ok"], f"{cap['id']} 入口文档未落地"


def test_mcp_caps_expose_recipe_and_config():
    for cap in ext.all_caps():
        if cap["kind"] != "mcp":
            continue
        text = ext.recipe(cap)
        assert text and "mcpServers" in text, cap["id"]
        mcp_cfg = os.path.join(cap["source"], ".mcp.json")
        if os.path.isdir(cap["source"]):
            assert os.path.isfile(mcp_cfg), cap["id"]


def test_skill_caps_recipe_points_to_docs():
    cap = ext.get("rednote-post")
    text = ext.recipe(cap)
    assert "references/external/rednote-post" in text


def test_stats_matches_catalog():
    stats = ext.stats()
    assert stats["count"] == 26
    assert sum(stats["by_kind"].values()) == 26
    assert sum(stats["by_role"].values()) == 26


def test_unknown_lookup_returns_none():
    assert ext.get("does-not-exist") is None
