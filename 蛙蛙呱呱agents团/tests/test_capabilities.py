# -*- coding: utf-8 -*-
"""自有能力目录测试：22 项能力、能力卡落地、无外部平台痕迹。"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared import capabilities as caps  # noqa: E402

ROLES = {"r01", "r02", "r03", "r04", "r05", "r06", "r07", "r08", "r09", "r10",
         "r11", "r12", "r13", "r14", "r15", "r16", "r17", "r18", "r19", "r20"}


def test_catalog_is_owned_and_complete():
    items = caps.all_caps()
    assert len(items) == 26
    assert len({c["id"] for c in items}) == 26
    for c in items:
        assert c["owner"] in ROLES
        for consumer in c["consumers"]:
            assert consumer in ROLES
        assert c["kind"] in {"skill", "knowledge"}
        assert c["rules"], f"{c['id']} 缺规则要点"
        assert c["summary"]


def test_every_capability_has_card():
    missing = [c["id"] for c in caps.all_caps() if not os.path.isfile(caps.card_path(c))]
    assert not missing, f"缺能力卡：{missing}"


def test_no_external_dependencies_in_catalog():
    """目录里不允许出现外部路径/客户端依赖。"""
    text = open(caps.CATALOG_PATH, encoding="utf-8").read().lower()
    for forbidden in ("tra" + "e", "work" + "buddy", "mcp", "http://", "https://"):
        assert forbidden not in text, f"能力目录残留外部痕迹：{forbidden}"


def test_executable_capabilities_point_to_real_skills():
    executable = {c["id"]: c for c in caps.all_caps() if c["entry"]}
    assert set(executable) == {"xhs-content-skills", "smart-product-selector",
                               "analyze-procurement", "ppt-generator", "brand-guardian",
                               "prd-authoring", "html-report-presentation", "image-ops",
                               "miniapp-builder"}
    for cap in executable.values():
        role_dir = next(d for d in os.listdir(ROOT)
                        if d.startswith(cap["owner"] + "-") and os.path.isdir(os.path.join(ROOT, d)))
        agent = os.path.join(ROOT, role_dir, "agent.py")
        assert os.path.isfile(agent)


def test_repository_has_no_platform_traces():
    tokens = ("tra" + "e", "work" + "buddy")
    self_path = os.path.abspath(__file__)
    hits = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("workspace", "__pycache__", ".git", ".pytest_cache")]
        for name in files:
            if not name.endswith((".md", ".py", ".json", ".txt", ".yaml")):
                continue
            path = os.path.join(base, name)
            if os.path.abspath(path) == self_path:
                continue
            try:
                text = open(path, encoding="utf-8", errors="ignore").read().lower()
            except OSError:
                continue
            if any(t in text for t in tokens):
                hits.append(os.path.relpath(path, ROOT))
    assert not hits, f"仍有平台痕迹：{hits[:10]}"


def test_stats_shape():
    s = caps.stats()
    assert s["count"] == 26
    assert s["executable"] == 9
    assert sum(s["by_role"].values()) == 26
