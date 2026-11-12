# -*- coding: utf-8 -*-
"""自有能力目录测试：能力卡落地、可执行能力可解析、运行时不绑外部平台。

注意（2026-11-12 修订）：不再写死「29 项能力 / 10 个可执行」这类魔数。
能力目录在升级中会持续增长（当前 84 项），写死数量只会让测试变成"改一次目录红一次"；
这里改成校验**结构不变量**：唯一性、归属、规则齐备、卡存在、入口可解析。
"""
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
    assert items, "能力目录为空"
    ids = [c["id"] for c in items]
    assert len(ids) == len(set(ids)), "能力 id 重复"
    for c in items:
        assert c["owner"] in ROLES, f"{c['id']} 的 owner 非法: {c['owner']}"
        for consumer in c["consumers"]:
            assert consumer in ROLES, f"{c['id']} 的消费者非法: {consumer}"
        assert c["kind"] in {"skill", "knowledge"}, f"{c['id']} kind 非法"
        assert c["rules"], f"{c['id']} 缺规则要点"
        assert c["summary"], f"{c['id']} 缺摘要"


def test_every_capability_has_card():
    missing = [c["id"] for c in caps.all_caps() if not os.path.isfile(caps.card_path(c))]
    assert not missing, f"缺能力卡：{missing}"


def test_no_external_dependencies_in_catalog():
    """目录里不允许出现外部平台路径/外链（MCP 是自有能力，不算外部平台）。"""
    text = open(caps.CATALOG_PATH, encoding="utf-8").read().lower()
    for forbidden in ("tra" + "e", "work" + "buddy", "http://", "https://"):
        assert forbidden not in text, f"能力目录残留外部痕迹：{forbidden}"


def test_executable_capabilities_point_to_real_skills():
    """每个可执行能力都要能落到「角色目录 + agent.py」，不写死名单。"""
    executable = [c for c in caps.all_caps() if c["entry"]]
    assert len(executable) >= 10, f"可执行能力过少（{len(executable)}），可能入口丢失"
    for cap in executable:
        role_dir = next((d for d in os.listdir(ROOT)
                         if d.startswith(cap["owner"] + "-")
                         and os.path.isdir(os.path.join(ROOT, d))), None)
        assert role_dir, f"{cap['id']} 的 owner 目录不存在: {cap['owner']}"
        assert os.path.isfile(os.path.join(ROOT, role_dir, "agent.py")), \
            f"{cap['id']} 缺 agent.py"
        # entry 有两种形态：技能（skill + actions）或脚本（script + actions）
        entry = cap["entry"] or {}
        target = entry.get("skill") or entry.get("script")
        assert target, f"{cap['id']} entry 既没有 skill 也没有 script"
        if entry.get("script"):
            assert os.path.isfile(os.path.join(ROOT, entry["script"])), \
                f"{cap['id']} 的脚本不存在: {entry['script']}"


def test_repository_has_no_platform_traces():
    """**运行时**代码不得绑外部平台（分发脚本与文档可以提到镜像，不算依赖）。"""
    tokens = ("tra" + "e", "work" + "buddy")
    runtime_roots = ["core", "shared", "report_specs", "configs", "styles", "templates"]
    hits = []
    for rel in runtime_roots:
        base_dir = os.path.join(ROOT, rel)
        if not os.path.isdir(base_dir):
            continue
        for base, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache")]
            for name in files:
                if not name.endswith((".md", ".py", ".json", ".txt", ".yaml")):
                    continue
                path = os.path.join(base, name)
                try:
                    text = open(path, encoding="utf-8", errors="ignore").read().lower()
                except OSError:
                    continue
                if any(t in text for t in tokens):
                    hits.append(os.path.relpath(path, ROOT))
    # 角色自己的技能代码也属于运行时
    for role_dir in sorted(os.listdir(ROOT)):
        if not (role_dir.startswith("r") and role_dir[1:3].isdigit()
                and os.path.isdir(os.path.join(ROOT, role_dir))):
            continue
        for name in ("agent.py", "contracts.py", "harness.py"):
            p = os.path.join(ROOT, role_dir, name)
            if not os.path.isfile(p):
                continue
            text = open(p, encoding="utf-8", errors="ignore").read().lower()
            if any(t in text for t in tokens):
                hits.append(os.path.join(role_dir, name))
    assert not hits, f"运行时仍有平台痕迹：{hits[:10]}"


def test_stats_shape():
    s = caps.stats()
    items = caps.all_caps()
    assert s["count"] == len(items)
    assert s["executable"] == sum(1 for c in items if c["entry"])
    assert sum(s["by_role"].values()) == len(items)
